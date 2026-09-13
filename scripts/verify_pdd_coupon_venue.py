#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
页面探查（默认只观察，不代点领取）。

不再把 XML 文本命中称为「GKD Rule 验证」。
GKD 引擎验收需另做：核对订阅 version、规则开关、无障碍点击记录（见审核 Plan P1-C）。

用法：
  python scripts/verify_pdd_coupon_venue.py
  python scripts/verify_pdd_coupon_venue.py --click-enter   # 显式才点击入口
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pdd_common import SERIAL_DEFAULT, StepResult, TaskReport, make_helper, page_signals  # noqa: E402
from adb_ui_helper import AdbError  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="消费券会场页面探查（默认观察）")
    ap.add_argument("--serial", default=SERIAL_DEFAULT)
    ap.add_argument("--click-enter", action="store_true", help="显式允许点击「百亿消费券」入口")
    args = ap.parse_args()
    report = TaskReport(mode="observe", serial=args.serial)

    try:
        ui = make_helper(args.serial)
        ui.unlock_and_wake()
        root = ui.dump_ui(require_nodes=False)
        sig = page_signals(ui, root)
        report.add(
            "page_probe",
            StepResult.VERIFIED,
            detail=json.dumps(sig, ensure_ascii=False),
        )

        if args.click_enter and not sig["venue"]:
            nodes = ui.find_nodes(root, text_regex=r"百亿消费券")
            if len(nodes) == 1:
                ui.tap_node(nodes[0], delay=3.0)
                sig = page_signals(ui)
                report.add("click_enter", StepResult.VERIFIED if sig["venue"] else StepResult.FAILED, str(sig))
            elif not nodes:
                report.add("click_enter", StepResult.UNAVAILABLE, "无百亿消费券节点（可能空树，需图像进场脚本）")
            else:
                report.add("click_enter", StepResult.NEEDS_REVIEW, f"入口歧义 n={len(nodes)}")

        claims = ui.find_nodes(ui.dump_ui(), text_regex=r"^(立即领取|一键全领|立即点亮)$")
        report.add(
            "visible_targets",
            StepResult.VERIFIED,
            detail=f"count={len(claims)}; " + ",".join(c["text"] for c in claims[:12]),
        )
        report.add(
            "note",
            StepResult.NEEDS_REVIEW,
            "本脚本只做页面探查，不证明 GKD 规则命中或领取成功",
        )
        print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
        return 0
    except AdbError as e:
        report.add("adb", StepResult.FAILED, str(e))
        print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
