#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进入拼多多「百亿消费券」会场。

主会场 H5 常无障碍空树，优先截图识别红标题条；
失败默认停机（needs_review），不自动盲点固定坐标。
缺 Pillow/NumPy 时明确失败，不改写为危险兜底。

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
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pdd_common import (  # noqa: E402
    SERIAL_DEFAULT,
    StepResult,
    TaskReport,
    make_helper,
    page_signals,
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


def run(serial: str, observe: bool, open_subsidy: bool, allow_fallback: str | None) -> int:
    report = TaskReport(mode="observe" if observe else "script", serial=serial)
    try:
        ui = make_helper(serial)
        if open_subsidy:
            # 稳定路径：百亿补贴搜索深链 → 点消费券卡标题区（抽福袋上方）
            # brand_rebate / 裸 coupons.html 不稳定（失败页或「我的优惠券」）
            ui.run_shell(
                "am start -a android.intent.action.VIEW -d "
                "'pinduoduo://com.xunmeng.pinduoduo/search_result.html?search_key=%E7%99%BE%E4%BA%BF%E8%A1%A5%E8%B4%B4'"
            )
            time.sleep(4.5)
            # 右卡「百亿消费券」标题区（抽福袋按钮约 y=1065，点其上方）
            ui.tap(1000, 980, delay=3.5)
            ok, why = venue_ok(ui)
            if ok:
                report.add("enter", StepResult.VERIFIED, f"bybt_search+card_tap proof={why}")
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return 0
            report.add("enter", StepResult.NEEDS_REVIEW, "搜索进百亿补贴后点消费券卡未进会场")
            # fall through to a11y/image attempts below

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

        if observe:
            report.add("enter", StepResult.VERIFIED, f"observe_only method={method} xy={xy}")
            print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
            return 0

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
        return 3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", default=SERIAL_DEFAULT)
    ap.add_argument("--observe", action="store_true")
    ap.add_argument("--open-subsidy", action="store_true")
    ap.add_argument(
        "--allow-fallback-xy",
        default=None,
        metavar="X,Y",
        help="仅当显式传入时才允许固定坐标（历史证据 603,777）",
    )
    args = ap.parse_args()
    return run(args.serial, args.observe, args.open_subsidy, args.allow_fallback_xy)


if __name__ == "__main__":
    raise SystemExit(main())
