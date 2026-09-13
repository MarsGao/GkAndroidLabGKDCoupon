#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地区专享：单张券闭环（观察 → 唯一目标 → 单次动作 → 核验）。

结果：verified | already_claimed | unavailable | failed | needs_review
不做：一次 dump 连点多张；无状态变化不算成功；固定坐标盲点。

用法：
  python scripts/claim_region_exclusive.py --observe
  python scripts/claim_region_exclusive.py
  python scripts/claim_region_exclusive.py --skip-tab --max-claims 5
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


def _claim_candidates(ui: AdbUIHelper, root) -> list[dict]:
    nodes = ui.find_nodes(root, text_regex=r"^立即领取$")
    out = []
    for n in nodes:
        cx, cy = n["center"]
        x1, y1, x2, y2 = n["bounds"]
        w, h = x2 - x1, y2 - y1
        if cy < 350 or cy > ui.screen_height * 0.92:
            continue
        if w > 520 or h > 220:
            continue
        out.append(n)
    out.sort(key=lambda z: (z["center"][1], z["center"][0]))
    return out


def _fingerprint(node: dict) -> str:
    x1, y1, x2, y2 = node["bounds"]
    return f"立即领取@{x1},{y1},{x2},{y2}"


def ensure_region_tab(ui: AdbUIHelper, report: TaskReport, skip: bool) -> StepResult:
    root = ui.dump_ui(require_nodes=True)
    sig = page_signals(ui, root)
    if not sig["venue"] and not sig["region_tab"]:
        report.add("region_tab", StepResult.FAILED, "不在消费券会场（缺双重补贴/地区专享）")
        return StepResult.FAILED
    if skip:
        report.add("region_tab", StepResult.VERIFIED, "skip-tab")
        return StepResult.VERIFIED

    tabs = ui.find_nodes(root, text_regex=r"^地区专享$")
    if not tabs:
        report.add("region_tab", StepResult.UNAVAILABLE, "无「地区专享」节点")
        return StepResult.UNAVAILABLE

    # 上半屏 Tab；多候选取 y 最小
    upper = [t for t in tabs if t["center"][1] < ui.screen_height * 0.55]
    target = sorted(upper or tabs, key=lambda t: t["center"][1])[0]
    before = _fingerprint(target) if False else f"tab@{target['center']}"
    ui.tap_node(target, delay=2.0)

    root2 = ui.dump_ui(require_nodes=True)
    sig2 = page_signals(ui, root2)
    # 切 Tab 后仍应在会场；若误进商品则失败
    if sig2["product_trap"]:
        ui.back(delay=1.0)
        report.add("region_tab", StepResult.FAILED, "切 Tab 后疑似商品页", before=before)
        return StepResult.FAILED
    if not sig2["region_tab"]:
        report.add("region_tab", StepResult.NEEDS_REVIEW, "点击后未见地区专享文案", before=before)
        return StepResult.NEEDS_REVIEW

    report.add("region_tab", StepResult.VERIFIED, "已点击并仍见地区专享", before=before)
    return StepResult.VERIFIED


def claim_one(ui: AdbUIHelper, report: TaskReport, idx: int) -> StepResult:
    """每次重新 dump；只处理排序后第一张可点券。"""
    root = ui.dump_ui(require_nodes=True)
    sig = page_signals(ui, root)
    if sig["product_trap"]:
        report.add(f"claim[{idx}]", StepResult.FAILED, "商品/国补遮挡，停机")
        return StepResult.FAILED
    if not sig["venue"] and not sig["region_tab"]:
        report.add(f"claim[{idx}]", StepResult.FAILED, "已离开会场")
        return StepResult.FAILED

    candidates = _claim_candidates(ui, root)
    if not candidates:
        if sig["go_use"] and not sig["claimable"]:
            report.add(f"claim[{idx}]", StepResult.ALREADY_CLAIMED, "可见去使用、无立即领取")
            return StepResult.ALREADY_CLAIMED
        report.add(f"claim[{idx}]", StepResult.UNAVAILABLE, "本屏无立即领取")
        return StepResult.UNAVAILABLE

    if len(candidates) > 1:
        # 只点第一张，但记录歧义供审查；不连点其余
        pass

    target = candidates[0]
    fp = _fingerprint(target)
    before_count = len(candidates)
    before_go = len(ui.find_nodes(root, text_regex=r"^去使用$"))

    ui.tap_node(target, delay=1.4)
    root_after = ui.dump_ui(require_nodes=True)
    sig_after = page_signals(ui, root_after)

    if sig_after["product_trap"]:
        # 尝试一次已知恢复：逛逛别的或返回
        alt = ui.find_nodes(root_after, text_regex=r"^逛逛别的$")
        if alt:
            ui.tap_node(alt[0], delay=1.0)
        else:
            ui.back(delay=1.0)
        report.add(
            f"claim[{idx}]",
            StepResult.FAILED,
            "点击后误进商品/遮挡",
            before=fp,
        )
        return StepResult.FAILED

    after_nodes = _claim_candidates(ui, root_after)
    after_go = len(ui.find_nodes(root_after, text_regex=r"^去使用$"))
    still_same = any(_fingerprint(n) == fp for n in after_nodes)

    if after_go > before_go and not still_same:
        report.add(
            f"claim[{idx}]",
            StepResult.VERIFIED,
            f"去使用 {before_go}->{after_go}；立即领取 {before_count}->{len(after_nodes)}",
            before=fp,
            after=f"go_use={after_go}",
        )
        return StepResult.VERIFIED

    if not still_same and len(after_nodes) < before_count:
        report.add(
            f"claim[{idx}]",
            StepResult.VERIFIED,
            f"目标位消失；立即领取 {before_count}->{len(after_nodes)}",
            before=fp,
        )
        return StepResult.VERIFIED

    if still_same and after_go == before_go:
        report.add(
            f"claim[{idx}]",
            StepResult.NEEDS_REVIEW,
            "点击后目标仍在且去使用未增",
            before=fp,
        )
        return StepResult.NEEDS_REVIEW

    report.add(
        f"claim[{idx}]",
        StepResult.NEEDS_REVIEW,
        "状态变化无法对应同一券",
        before=fp,
    )
    return StepResult.NEEDS_REVIEW


def scroll_coupon_area(ui: AdbUIHelper, horizontal: bool) -> None:
    """在券区滑动；用屏幕比例，避免写死全屏 y 业务坐标以外的魔法。"""
    w, h = ui.screen_width, ui.screen_height
    if horizontal:
        y = int(h * 0.46)
        ui.swipe(int(w * 0.82), y, int(w * 0.22), y, 380)
    else:
        ui.swipe(w // 2, int(h * 0.72), w // 2, int(h * 0.42), 400)


def run(
    serial: str,
    observe: bool,
    skip_tab: bool,
    max_claims: int,
    max_rounds: int,
    confirm_gkd_off: bool = False,
) -> int:
    report = TaskReport(mode="observe" if observe else "script", serial=serial)
    try:
        ui = make_helper(serial)
        if not observe:
            assert_script_mode_preflight(ui, confirm_gkd_off=confirm_gkd_off)
            ui.dismiss_popups(max_attempts=2)

        tab_res = ensure_region_tab(ui, report, skip=skip_tab)
        if tab_res in (StepResult.FAILED, StepResult.NEEDS_REVIEW) and not skip_tab:
            print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
            return 2

        if observe:
            root = ui.dump_ui(require_nodes=True)
            sig = page_signals(ui, root)
            cands = _claim_candidates(ui, root)
            report.add(
                "observe",
                StepResult.VERIFIED if sig["region_tab"] else StepResult.NEEDS_REVIEW,
                detail=f"claimable={len(cands)} go_use={sig['go_use']} venue={sig['venue']}",
            )
            print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
            return 0

        verified = 0
        empty_streak = 0
        claim_idx = 0
        for round_i in range(max_rounds):
            if verified >= max_claims:
                break
            res = claim_one(ui, report, claim_idx)
            claim_idx += 1
            if res == StepResult.VERIFIED:
                verified += 1
                empty_streak = 0
                continue
            if res == StepResult.FAILED:
                break
            if res in (StepResult.UNAVAILABLE, StepResult.ALREADY_CLAIMED):
                scroll_coupon_area(ui, horizontal=True)
                time.sleep(0.7)
                res2 = claim_one(ui, report, claim_idx)
                claim_idx += 1
                if res2 == StepResult.VERIFIED:
                    verified += 1
                    empty_streak = 0
                    continue
                if res2 == StepResult.FAILED:
                    break
                scroll_coupon_area(ui, horizontal=False)
                time.sleep(0.7)
                empty_streak += 1
                if empty_streak >= 2:
                    report.add(
                        "traverse_stop",
                        StepResult.ALREADY_CLAIMED if res == StepResult.ALREADY_CLAIMED else StepResult.UNAVAILABLE,
                        "相邻轮无新券，停止遍历（不代表全站领完）",
                    )
                    break
            if res == StepResult.NEEDS_REVIEW:
                # 不确定时停机，避免连点
                break

        print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
        failed = any(r.result == StepResult.FAILED for r in report.records)
        return 1 if failed else 0
    except AdbError as e:
        report.add("adb", StepResult.FAILED, str(e))
        print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
        return 3


def main() -> int:
    ap = argparse.ArgumentParser(description="地区专享单券闭环")
    ap.add_argument("--serial", default=SERIAL_DEFAULT)
    ap.add_argument("--observe", action="store_true", help="只观察，不点击领取")
    ap.add_argument("--skip-tab", action="store_true")
    ap.add_argument("--max-claims", type=int, default=8)
    ap.add_argument("--max-rounds", type=int, default=10)
    ap.add_argument(
        "--confirm-gkd-off",
        action="store_true",
        help="确认已停用重叠 GKD 拼多多点击规则（脚本模式必填，或设 PDD_CONFIRM_GKD_OFF=1）",
    )
    args = ap.parse_args()
    return run(
        args.serial,
        args.observe,
        args.skip_tab,
        args.max_claims,
        args.max_rounds,
        confirm_gkd_off=args.confirm_gkd_off,
    )


if __name__ == "__main__":
    raise SystemExit(main())
