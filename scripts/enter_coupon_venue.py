#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进入拼多多「百亿消费券」会场。

主会场 H5 常无障碍空树；默认仅点击唯一可访问的语义入口。
旧红条颜色与固定坐标仅留显式兼容探查，不用于默认自动进场。
无法确认入口时返回 needs_review，不以截图颜色当成业务身份。

用法：
  python scripts/enter_coupon_venue.py --observe
  python scripts/enter_coupon_venue.py
  python scripts/enter_coupon_venue.py --allow-fallback-xy 603,777   # 显式才允许
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pdd_common import (  # noqa: E402
    SERIAL_DEFAULT,
    StepResult,
    TaskReport,
    make_helper,
    page_signals,
    assert_script_mode_preflight,
    runtime_preflight,
    script_runtime_blockers,
)
from adb_ui_helper import AdbError  # noqa: E402


def find_red_header_tap(png_path: str) -> tuple[int, int] | None:
    try:
        from PIL import Image
        import numpy as np
    except ImportError as e:
        raise AdbError(
            "缺少 Pillow/NumPy，无法做图像定位。请 uv sync 后重试；"
            "不会自动退回固定坐标。"
        ) from e

    im = Image.open(png_path).convert("RGB")
    arr = np.array(im)
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    mask = (r > 160) & (g < 90) & (b < 100) & (r > g + 60)
    ys, xs = np.where(mask)
    # 历史证据：红条约在 y=750–950（OnePlus 13）；低置信度则放弃
    sel = (ys > 750) & (ys < 950)
    ys, xs = ys[sel], xs[sel]
    if len(xs) < 80:
        return None
    ym = Counter(ys.tolist()).most_common(1)[0][0]
    row = sorted(xs[abs(ys - ym) < 5].tolist())
    if len(row) < 40:
        return None
    # 「百亿消费券」在红条左侧文字区；勿点右侧商品图
    tapx = row[0] + int((row[-1] - row[0]) * 0.22)
    tapy = ym + 8
    return tapx, tapy


def venue_ok(ui) -> tuple[bool, str]:
    root = ui.dump_ui(require_nodes=True)
    sig = page_signals(ui, root)
    if sig["venue"]:
        return True, "venue_signals"
    # 较弱：有地区专享+立即领取/去使用
    if sig["region_tab"] and (sig["claimable"] or sig["go_use"]):
        return True, "region+claim_state"
    return False, "no_venue_features"


def run(
    serial: str,
    observe: bool,
    open_subsidy: bool,
    allow_fallback: str | None,
    confirm_gkd_off: bool = False,
) -> int:
    report = TaskReport(mode="observe" if observe else "script", serial=serial or "auto")
    try:
        ui = make_helper(serial)
        report.serial = ui.serial
        if observe and open_subsidy:
            report.add(
                "enter",
                StepResult.NEEDS_REVIEW,
                "observe 模式不执行打开补贴页或点击入口；请先手动进入目标页面",
            )
            print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
            return report.exit_code()
        if observe:
            root = ui.dump_ui(require_nodes=False)
            sig = page_signals(ui, root)
            if sig["venue"]:
                report.add("venue_probe", StepResult.VERIFIED, "已处于消费券会场")
            else:
                entries = ui.find_nodes(root, text_regex=r"百亿消费券")
                result = StepResult.VERIFIED if len(entries) == 1 else StepResult.NEEDS_REVIEW
                report.add(
                    "entry_probe",
                    result,
                    f"可访问树中入口候选={len(entries)}；不截图、不触屏操作",
                )
            print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
            return report.exit_code()
        if not observe:
            assert_script_mode_preflight(ui, confirm_gkd_off=confirm_gkd_off)
            live = runtime_preflight(ui)
            report.add("device_preflight", StepResult.VERIFIED, json.dumps(live, ensure_ascii=False))
            blockers = script_runtime_blockers(live)
            if blockers:
                report.records[-1].result = StepResult.FAILED
                report.records[-1].detail = "; ".join(blockers)
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return report.exit_code()
        if open_subsidy:
            report.add(
                "enter",
                StepResult.NEEDS_REVIEW,
                "--open-subsidy 的旧搜索深链和固定坐标未通过 mi14Pro 验证；请先人工进入百亿补贴频道",
            )
            print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
            return report.exit_code()

        # 优先无障碍：若已有「百亿消费券」文本节点则点它
        root = ui.dump_ui()
        entry = ui.find_nodes(root, text_regex=r"百亿消费券")
        xy = None
        method = ""
        if entry:
            # 多候选歧义 → 停机
            if len(entry) > 2:
                report.add(
                    "enter",
                    StepResult.NEEDS_REVIEW,
                    f"百亿消费券节点过多({len(entry)})，拒绝盲选",
                )
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return 2
            xy = entry[0]["center"]
            method = "a11y_text"

        if xy is None:
            # H5 的红色条带并不等于「百亿消费券」语义；旧 OnePlus 13 的
            # 绝对 y 范围不能作为 mi14Pro 自动点击依据。
            if not allow_fallback:
                report.add(
                    "enter",
                    StepResult.NEEDS_REVIEW,
                    "无可访问的唯一入口节点；动态 H5 需要新鲜截图 OCR 与会场回查，未执行颜色/固定坐标猜测",
                )
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return report.exit_code()
            local = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "data", "pdd_enter_probe.png")
            )
            os.makedirs(os.path.dirname(local), exist_ok=True)
            ui.run_shell("screencap -p /sdcard/enter_coupon.png", check=False)
            ui.run_cmd(["pull", "/sdcard/enter_coupon.png", local], check=False)
            if not os.path.exists(local):
                report.add("enter", StepResult.FAILED, "截图拉取失败")
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return 3
            xy = find_red_header_tap(local)
            method = "red_header_image"

        if xy is None:
            if allow_fallback:
                fx, fy = map(int, allow_fallback.split(","))
                xy = (fx, fy)
                method = "explicit_fallback_xy"
                report.add(
                    "enter_locate",
                    StepResult.NEEDS_REVIEW,
                    f"图像未识别，用户显式允许坐标 {xy}",
                )
            else:
                report.add(
                    "enter",
                    StepResult.NEEDS_REVIEW,
                    "无法定位入口（无节点且红条置信不足）；未启用 --allow-fallback-xy",
                )
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return 2

        # 不点「空白区」——可能点到别的入口
        ui.tap(xy[0], xy[1], delay=3.0)
        ok, why = venue_ok(ui)
        if ok:
            report.add("enter", StepResult.VERIFIED, f"method={method} xy={xy} proof={why}")
            print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
            return 0

        report.add(
            "enter",
            StepResult.FAILED,
            f"点击后未见会场特征 method={method} xy={xy}",
        )
        print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
        return 1
    except AdbError as e:
        report.add("adb", StepResult.FAILED, str(e))
        print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
        return report.exit_code()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", default=SERIAL_DEFAULT)
    ap.add_argument("--observe", action="store_true")
    ap.add_argument("--open-subsidy", action="store_true")
    ap.add_argument("--confirm-gkd-off", action="store_true")
    ap.add_argument(
        "--allow-fallback-xy",
        default=None,
        metavar="X,Y",
        help="仅当显式传入时才允许固定坐标（历史证据 603,777）",
    )
    args = ap.parse_args()
    return run(
        args.serial,
        args.observe,
        args.open_subsidy,
        args.allow_fallback_xy,
        confirm_gkd_off=args.confirm_gkd_off,
    )


if __name__ == "__main__":
    raise SystemExit(main())
