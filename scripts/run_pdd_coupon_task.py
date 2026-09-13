#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拼多多领券脚本任务模式状态机（短期主基线）。

阶段：preflight → member_checkin → level_gift → enter_venue → dual_claim
      → light_browse → region_exclusive → summary

不自动中途切换到 GKD；不宣称必然领全。
已完成步骤可按页面状态跳过。

用法：
  python scripts/run_pdd_coupon_task.py --observe
  python scripts/run_pdd_coupon_task.py --from-stage region
  python scripts/run_pdd_coupon_task.py --stages member,venue,region
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
)
from adb_ui_helper import AdbError, AdbUIHelper  # noqa: E402

import claim_region_exclusive as region_mod  # noqa: E402
import enter_coupon_venue as enter_mod  # noqa: E402

ALL_STAGES = (
    "preflight",
    "member",
    "level",
    "venue",
    "dual",
    "light",
    "region",
)


def step_checkin(ui: AdbUIHelper, report: TaskReport, observe: bool) -> StepResult:
    root = ui.dump_ui(require_nodes=True)
    sig = page_signals(ui, root)
    if not sig["member"] and not sig["checkin_available"]:
        report.add("member_checkin", StepResult.UNAVAILABLE, "未见会员/打卡页特征")
        return StepResult.UNAVAILABLE
    nodes = ui.find_nodes(root, text_regex=r"^打卡$")
    if not nodes:
        if sig["checkin_done_hint"]:
            report.add("member_checkin", StepResult.ALREADY_CLAIMED, "已有已打卡提示")
            return StepResult.ALREADY_CLAIMED
        report.add("member_checkin", StepResult.UNAVAILABLE, "无打卡按钮")
        return StepResult.UNAVAILABLE
    if observe:
        report.add("member_checkin", StepResult.VERIFIED, f"observe 可见打卡 x{len(nodes)}")
        return StepResult.VERIFIED
    if len(nodes) > 1:
        report.add("member_checkin", StepResult.NEEDS_REVIEW, f"打卡候选歧义 {len(nodes)}")
        return StepResult.NEEDS_REVIEW
    # 文案中心常偏下；略上移点到橙色按钮本体
    n = nodes[0]
    cx, cy = n["center"]
    ui.tap(cx, max(cy - 40, n["bounds"][1] + 8), delay=1.5)
    root2 = ui.dump_ui(require_nodes=True)
    after = ui.find_nodes(root2, text_regex=r"^打卡$")
    sig2 = page_signals(ui, root2)
    # 必要证据：精确「打卡」消失；「已打卡」文案仅为辅助
    if not after:
        report.add(
            "member_checkin",
            StepResult.VERIFIED,
            "打卡按钮消失",
            before="text=打卡",
            after=f"done_hint={sig2['checkin_done_hint']}",
        )
        return StepResult.VERIFIED
    report.add("member_checkin", StepResult.NEEDS_REVIEW, "点击后打卡仍在或证据不足")
    return StepResult.NEEDS_REVIEW


def step_level_gift(ui: AdbUIHelper, report: TaskReport, observe: bool) -> StepResult:
    root = ui.dump_ui(require_nodes=True)
    free = ui.find_nodes(root, text_regex=r"无门槛券")
    claims = ui.find_nodes(root, text_regex=r"^领取$")
    if not free:
        report.add("level_gift", StepResult.UNAVAILABLE, "未见无门槛券")
        return StepResult.UNAVAILABLE
    # 同屏「领取」；多候选时取与无门槛券纵向接近者
    if not claims:
        used = ui.find_nodes(root, text_regex=r"^(去使用|已使用|已领取)$")
        if used:
            report.add("level_gift", StepResult.ALREADY_CLAIMED, "可见已领/去使用")
            return StepResult.ALREADY_CLAIMED
        report.add("level_gift", StepResult.UNAVAILABLE, "无领取按钮")
        return StepResult.UNAVAILABLE
    # 选与任一「无门槛券」中心 y 差最小的领取
    best = None
    best_d = 10**9
    for c in claims:
        for f in free:
            d = abs(c["center"][1] - f["center"][1]) + abs(c["center"][0] - f["center"][0]) * 0.2
            if d < best_d:
                best_d = d
                best = c
    if best is None or best_d > 400:
        report.add("level_gift", StepResult.NEEDS_REVIEW, f"领取与无门槛券距离过大 d={best_d}")
        return StepResult.NEEDS_REVIEW
    if observe:
        report.add("level_gift", StepResult.VERIFIED, f"observe 关联领取 d={best_d:.0f}")
        return StepResult.VERIFIED
    before = f"领取@{best['bounds']}"
    ui.tap_node(best, delay=1.5)
    root2 = ui.dump_ui(require_nodes=True)
    after_claim = ui.find_nodes(root2, text_regex=r"^领取$")
    after_use = ui.find_nodes(root2, text_regex=r"^(去使用|已使用|已领取)$")
    if len(after_use) > 0 and (not any(n["bounds"] == best["bounds"] for n in after_claim)):
        report.add("level_gift", StepResult.VERIFIED, "出现已领态且原领取位变化", before=before)
        return StepResult.VERIFIED
    if not any(n["bounds"] == best["bounds"] for n in after_claim):
        report.add("level_gift", StepResult.VERIFIED, "原领取按钮消失", before=before)
        return StepResult.VERIFIED
    report.add("level_gift", StepResult.NEEDS_REVIEW, "点击后证据不足", before=before)
    return StepResult.NEEDS_REVIEW


def step_dual_claim(ui: AdbUIHelper, report: TaskReport, observe: bool, max_n: int) -> StepResult:
    """双重补贴区：逐张领取（与地区专享同一闭环语义）。"""
    root = ui.dump_ui(require_nodes=True)
    # 若在地区专享，先点双重补贴 Tab
    dual_tabs = ui.find_nodes(root, text_regex=r"^双重补贴$")
    if dual_tabs and not observe:
        top = sorted(dual_tabs, key=lambda t: t["center"][1])[0]
        if top["center"][1] < ui.screen_height * 0.55:
            ui.tap_node(top, delay=1.8)

    if observe:
        root = ui.dump_ui(require_nodes=True)
        n = len(region_mod._claim_candidates(ui, root))
        report.add("dual_claim", StepResult.VERIFIED, f"observe claimable={n}")
        return StepResult.VERIFIED

    verified = 0
    for i in range(max_n):
        res = region_mod.claim_one(ui, report, 100 + i)
        # 复用 claim_one 但 step 名在 report 里是 claim[1xx]；额外记 dual
        if res == StepResult.VERIFIED:
            verified += 1
            continue
        if res in (StepResult.UNAVAILABLE, StepResult.ALREADY_CLAIMED):
            region_mod.scroll_coupon_area(ui, horizontal=True)
            time.sleep(0.6)
            res2 = region_mod.claim_one(ui, report, 100 + i + 50)
            if res2 == StepResult.VERIFIED:
                verified += 1
                continue
            break
        if res in (StepResult.FAILED, StepResult.NEEDS_REVIEW):
            break
    if verified:
        report.add("dual_claim", StepResult.VERIFIED, f"verified_count={verified}")
        return StepResult.VERIFIED
    report.add("dual_claim", StepResult.UNAVAILABLE, "本轮无新核销")
    return StepResult.UNAVAILABLE


def step_light_browse(ui: AdbUIHelper, report: TaskReport, observe: bool, browse_sec: float) -> StepResult:
    root = ui.dump_ui(require_nodes=True)
    sig = page_signals(ui, root)
    if sig["light_done"]:
        report.add("light_browse", StepResult.ALREADY_CLAIMED, "今日已点亮")
        return StepResult.ALREADY_CLAIMED
    lights = ui.find_nodes(root, text_regex=r"^立即点亮$")
    if not lights:
        report.add("light_browse", StepResult.UNAVAILABLE, "无立即点亮")
        return StepResult.UNAVAILABLE
    if observe:
        report.add("light_browse", StepResult.VERIFIED, "observe 可见立即点亮")
        return StepResult.VERIFIED
    if len(lights) > 1:
        report.add("light_browse", StepResult.NEEDS_REVIEW, "点亮按钮歧义")
        return StepResult.NEEDS_REVIEW
    ui.tap_node(lights[0], delay=1.2)
    # 引导「去看看」仅在点亮后短窗口内点一次
    root2 = ui.dump_ui(require_nodes=True)
    go = ui.find_nodes(root2, text_regex=r"去看看")
    if go:
        ui.tap_node(go[0], delay=1.0)
    # 浏览：保持前台并轻滑；被遮挡则 needs_review
    t0 = time.time()
    while time.time() - t0 < browse_sec:
        if ui.foreground_package() != "com.xunmeng.pinduoduo":
            report.add("light_browse", StepResult.NEEDS_REVIEW, "浏览期间离开拼多多前台")
            return StepResult.NEEDS_REVIEW
        ui.swipe_up(0.15)
        time.sleep(1.0)
    # 返回会场并核验「今日已点亮」
    for _ in range(3):
        ui.back(delay=1.0)
        root3 = ui.dump_ui(require_nodes=True)
        sig3 = page_signals(ui, root3)
        if sig3["light_done"]:
            report.add("light_browse", StepResult.VERIFIED, f"浏览{browse_sec}s 后见今日已点亮")
            return StepResult.VERIFIED
        if sig3["venue"]:
            break
    root_f = ui.dump_ui(require_nodes=True)
    if page_signals(ui, root_f)["light_done"]:
        report.add("light_browse", StepResult.VERIFIED, "见今日已点亮")
        return StepResult.VERIFIED
    report.add("light_browse", StepResult.NEEDS_REVIEW, "浏览结束未见今日已点亮（sleep 不算成功）")
    return StepResult.NEEDS_REVIEW


def run_stages(
    serial: str,
    observe: bool,
    stages: list[str],
    browse_sec: float,
) -> int:
    report = TaskReport(mode="observe" if observe else "script", serial=serial)
    try:
        ui = make_helper(serial)
        if "preflight" in stages:
            if not observe:
                assert_script_mode_preflight(ui)
            ui.unlock_and_wake()
            report.add(
                "preflight",
                StepResult.VERIFIED,
                f"fg={ui.foreground_package()} {ui.screen_width}x{ui.screen_height}",
            )

        stop_on = {StepResult.FAILED, StepResult.NEEDS_REVIEW}

        if "member" in stages:
            r = step_checkin(ui, report, observe)
            if r in stop_on and not observe:
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return 1

        if "level" in stages:
            r = step_level_gift(ui, report, observe)
            if r == StepResult.FAILED and not observe:
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return 1

        if "venue" in stages:
            code = enter_mod.run(serial, observe=observe, open_subsidy=False, allow_fallback=None)
            # enter 已打印；合并关键记录困难，补一条
            report.add(
                "venue_enter",
                StepResult.VERIFIED if code == 0 else StepResult.FAILED if code == 1 else StepResult.NEEDS_REVIEW,
                f"enter_exit_code={code}",
            )
            if code not in (0,) and not observe:
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return code

        if "dual" in stages:
            step_dual_claim(ui, report, observe, max_n=5)

        if "light" in stages:
            r = step_light_browse(ui, report, observe, browse_sec)
            if r == StepResult.FAILED and not observe:
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return 1

        if "region" in stages:
            code = region_mod.run(
                serial,
                observe=observe,
                skip_tab=False,
                max_claims=8,
                max_rounds=8,
            )
            report.add(
                "region_exclusive",
                StepResult.VERIFIED if code == 0 else StepResult.FAILED if code in (1, 3) else StepResult.NEEDS_REVIEW,
                f"region_exit_code={code}",
            )

        print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
        if any(r.result == StepResult.FAILED for r in report.records):
            return 1
        return 0
    except AdbError as e:
        report.add("adb", StepResult.FAILED, str(e))
        print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
        return 3


def main() -> int:
    ap = argparse.ArgumentParser(description="PDD 领券脚本任务状态机")
    ap.add_argument("--serial", default=SERIAL_DEFAULT)
    ap.add_argument("--observe", action="store_true")
    ap.add_argument(
        "--stages",
        default=",".join(ALL_STAGES),
        help=f"逗号分隔，可选: {','.join(ALL_STAGES)}",
    )
    ap.add_argument("--from-stage", default=None, help="从该阶段起执行到结束")
    ap.add_argument("--browse-sec", type=float, default=10.0)
    args = ap.parse_args()

    stages = [s.strip() for s in args.stages.split(",") if s.strip()]
    if args.from_stage:
        if args.from_stage not in ALL_STAGES:
            print(f"未知阶段: {args.from_stage}", file=sys.stderr)
            return 2
        idx = ALL_STAGES.index(args.from_stage)
        stages = list(ALL_STAGES[idx:])
    for s in stages:
        if s not in ALL_STAGES:
            print(f"未知阶段: {s}", file=sys.stderr)
            return 2
    return run_stages(args.serial, args.observe, stages, args.browse_sec)


if __name__ == "__main__":
    raise SystemExit(main())
