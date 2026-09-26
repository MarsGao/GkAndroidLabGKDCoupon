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

from pdd_common import (
    SERIAL_DEFAULT,
    StepResult,
    TaskReport,
    make_helper,
    page_signals,
    runtime_preflight,
    script_runtime_blockers,
)  # noqa: E402
from adb_ui_helper import AdbError  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="消费券会场页面探查（默认观察）")
    ap.add_argument("--serial", default=SERIAL_DEFAULT)
    ap.add_argument("--click-enter", action="store_true", help="已废止：探查器严格只读，请改用受控业务脚本入口")
    args = ap.parse_args()
    report = TaskReport(mode="observe", serial=args.serial or "auto")

    try:
        ui = make_helper(args.serial)
        report.serial = ui.serial
        if args.click_enter:
            report.add(
                "click_enter",
                StepResult.NEEDS_REVIEW,
                "该观察器保证零触屏动作；--click-enter 已废止，请单独审查并使用受控业务流程",
            )
            print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
            return report.exit_code()
        live = runtime_preflight(ui)
        blockers = script_runtime_blockers(live)
        report.add(
            "device_preflight",
            StepResult.NEEDS_REVIEW if blockers else StepResult.VERIFIED,
            "; ".join(blockers) if blockers else json.dumps(live, ensure_ascii=False),
        )
        root = ui.dump_ui(require_nodes=False)
        sig = page_signals(ui, root)
        report.add(
            "page_probe",
            StepResult.VERIFIED if sig["venue"] or sig["region_tab"] else StepResult.UNAVAILABLE,
            detail=json.dumps(sig, ensure_ascii=False),
        )

        claims = ui.find_nodes(ui.dump_ui(), text_regex=r"^(立即领取|一键全领|立即点亮)$")
        report.add(
            "visible_targets",
            StepResult.NEEDS_REVIEW if claims else StepResult.UNAVAILABLE,
            detail=f"count={len(claims)}; " + ",".join(c["text"] for c in claims[:12]),
        )
        report.add(
            "note",
            StepResult.NEEDS_REVIEW,
            "本脚本只做页面探查，不证明 GKD 规则命中或领取成功",
        )
        print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
        return report.exit_code()
    except AdbError as e:
        report.add("adb", StepResult.FAILED, str(e))
        print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
        return report.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
