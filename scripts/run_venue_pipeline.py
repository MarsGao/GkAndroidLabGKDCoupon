#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消费券会场有序流水线（脚本任务模式权威编排）

顺序（硬顺序，不靠 GKD 并发猜测）：
  1) 切「地区专享」并核验
  2) 逐张「立即领取」直到本观察范围无新券
  3) 「立即点亮/解锁点亮」+ 浏览计时 + 回会场核验

GKD 无法可靠完成「领完再点亮」的业务时序 + 计时浏览；
GKD 仅适合同页原子点击，用 excludeMatches/order/preKeys 做弱约束。

用法：
  uv run python scripts/run_venue_pipeline.py --observe
  uv run python scripts/run_venue_pipeline.py --confirm-gkd-off
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pdd_common import (  # noqa: E402
    SERIAL_DEFAULT,
    StepResult,
    TaskReport,
    assert_script_mode_preflight,
    make_helper,
    page_signals,
    AdbError,
)
import claim_region_exclusive as region  # noqa: E402


def _scroll_venue_top(ui, rounds: int = 3) -> None:
    """领券横向/纵向滑动后，点亮区常在顶部，先滚回再找按钮。"""
    w, h = ui.screen_width, ui.screen_height
    for _ in range(rounds):
        ui.swipe(w // 2, int(h * 0.28), w // 2, int(h * 0.78), 420)
        time.sleep(0.35)


def step_light(ui, report: TaskReport, browse_sec: float) -> StepResult:
    _scroll_venue_top(ui)
    root = ui.dump_ui(require_nodes=True)
    sig = page_signals(ui, root)
    if sig["light_done"]:
        report.add("light", StepResult.ALREADY_CLAIMED, "今日已点亮/已点亮")
        return StepResult.ALREADY_CLAIMED

    # 仍有可领券时拒绝点亮（顺序闸）
    if region._claim_candidates(ui, root):
        report.add("light", StepResult.NEEDS_REVIEW, "仍有立即领取，拒绝点亮（顺序闸）")
        return StepResult.NEEDS_REVIEW

    lights = ui.find_nodes(root, text_regex=r"^(立即点亮|解锁点亮)$")
    if not lights:
        # 再滚一次顶部重试
        _scroll_venue_top(ui, rounds=2)
        root = ui.dump_ui(require_nodes=True)
        lights = ui.find_nodes(root, text_regex=r"^(立即点亮|解锁点亮)$")
    if not lights:
        report.add("light", StepResult.UNAVAILABLE, "无点亮按钮")
        return StepResult.UNAVAILABLE
    if len(lights) > 1:
        report.add("light", StepResult.NEEDS_REVIEW, f"点亮歧义 n={len(lights)}")
        return StepResult.NEEDS_REVIEW

    ui.tap_node(lights[0], delay=1.2)
    try:
        root2 = ui.dump_ui(require_nodes=True)
        go = ui.find_nodes(root2, text_regex=r"去看看")
        if go:
            ui.tap_node(go[0], delay=1.0)
    except AdbError:
        # 点亮后转场偶发空树，不阻断浏览计时
        pass

    t0 = time.time()
    while time.time() - t0 < browse_sec:
        if ui.foreground_package() != "com.xunmeng.pinduoduo":
            report.add("light", StepResult.NEEDS_REVIEW, "浏览期间离开拼多多")
            return StepResult.NEEDS_REVIEW
        ui.swipe_up(0.12)
        time.sleep(1.0)

    for _ in range(5):
        ui.back(delay=1.2)
        time.sleep(0.8)
        try:
            root3 = ui.dump_ui(require_nodes=True)
        except AdbError:
            continue
        sig3 = page_signals(ui, root3)
        if sig3["light_done"]:
            report.add("light", StepResult.VERIFIED, f"浏览{browse_sec}s 后见已点亮")
            return StepResult.VERIFIED
        if sig3["venue"]:
            break

    try:
        root_f = ui.dump_ui(require_nodes=True)
    except AdbError as e:
        report.add("light", StepResult.NEEDS_REVIEW, f"浏览后 dump 失败: {e}")
        return StepResult.NEEDS_REVIEW
    if page_signals(ui, root_f)["light_done"]:
        report.add("light", StepResult.VERIFIED, "见已点亮")
        return StepResult.VERIFIED
    report.add("light", StepResult.NEEDS_REVIEW, "浏览结束未见已点亮证据")
    return StepResult.NEEDS_REVIEW


def run(serial: str, observe: bool, confirm_gkd_off: bool, browse_sec: float) -> int:
    report = TaskReport(mode="observe" if observe else "script", serial=serial)
    try:
        ui = make_helper(serial)
        if not observe:
            assert_script_mode_preflight(ui, confirm_gkd_off=confirm_gkd_off)

        root = ui.dump_ui(require_nodes=True)
        sig = page_signals(ui, root)
        report.add(
            "page",
            StepResult.VERIFIED if sig["venue"] or sig["region_tab"] else StepResult.FAILED,
            detail=json.dumps(sig, ensure_ascii=False),
        )
        if not (sig["venue"] or sig["region_tab"]):
            print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
            return 2

        if observe:
            cands = region._claim_candidates(ui, root)
            lights = ui.find_nodes(root, text_regex=r"^(立即点亮|解锁点亮)$")
            report.add(
                "observe_order",
                StepResult.VERIFIED,
                detail=f"claimable={len(cands)} light={len(lights)} recommended=claim_then_light",
            )
            print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
            return 0

        # 1) 地区专享
        tab = region.ensure_region_tab(ui, report, skip=False)
        if tab == StepResult.FAILED:
            print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
            return 1

        # 2) 逐张领取（开局无券则跳过滑动遍历，避免把顶部点亮区滚没）
        verified = 0
        empty = 0
        root0 = ui.dump_ui(require_nodes=True)
        if not region._claim_candidates(ui, root0):
            report.add(
                "claim_stop",
                StepResult.UNAVAILABLE,
                "开局观察范围无立即领取，直接进入点亮阶段",
            )
        else:
            for i in range(10):
                res = region.claim_one(ui, report, i)
                if res == StepResult.VERIFIED:
                    verified += 1
                    empty = 0
                    continue
                if res == StepResult.FAILED:
                    break
                if res in (StepResult.UNAVAILABLE, StepResult.ALREADY_CLAIMED):
                    region.scroll_coupon_area(ui, horizontal=True)
                    time.sleep(0.6)
                    res2 = region.claim_one(ui, report, i + 50)
                    if res2 == StepResult.VERIFIED:
                        verified += 1
                        empty = 0
                        continue
                    if res2 == StepResult.FAILED:
                        break
                    region.scroll_coupon_area(ui, horizontal=False)
                    time.sleep(0.6)
                    empty += 1
                    if empty >= 2:
                        report.add(
                            "claim_stop",
                            StepResult.ALREADY_CLAIMED if res == StepResult.ALREADY_CLAIMED else StepResult.UNAVAILABLE,
                            "观察范围内无新券，进入点亮阶段",
                        )
                        break
                if res == StepResult.NEEDS_REVIEW:
                    print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                    return 1

        report.add("claim_summary", StepResult.VERIFIED if verified else StepResult.UNAVAILABLE, f"verified={verified}")
        if any(r.result == StepResult.FAILED for r in report.records):
            print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
            return 1

        # 3) 点亮（仅当无立即领取）
        light_res = step_light(ui, report, browse_sec)
        print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
        if any(r.result == StepResult.FAILED for r in report.records):
            return 1
        if light_res == StepResult.VERIFIED or light_res == StepResult.ALREADY_CLAIMED:
            return 0
        if light_res == StepResult.UNAVAILABLE:
            return 0  # 当日无点亮入口可视为跳过
        return 2  # needs_review：点过但未核验，不伪装成功
    except AdbError as e:
        report.add("adb", StepResult.FAILED, str(e))
        print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
        return 3


def main() -> int:
    ap = argparse.ArgumentParser(description="会场有序流水线：地区专享领取 → 点亮浏览")
    ap.add_argument("--serial", default=SERIAL_DEFAULT)
    ap.add_argument("--observe", action="store_true")
    ap.add_argument("--confirm-gkd-off", action="store_true")
    ap.add_argument("--browse-sec", type=float, default=10.0)
    args = ap.parse_args()
    return run(args.serial, args.observe, args.confirm_gkd_off, args.browse_sec)


if __name__ == "__main__":
    raise SystemExit(main())
