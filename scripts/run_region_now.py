#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, r"C:\GkDesktop\GitProjects\GkAndroidLab\scripts\ecommerce")
from adb_ui_helper import AdbUIHelper  # noqa: E402
from pdd_common import page_signals  # noqa: E402
import claim_region_exclusive as region  # noqa: E402

DATA = ROOT / "data"
ui = AdbUIHelper("3B159H003D600000")


def snap(name):
    root = ui.dump_ui()
    lines = [
        f"{n.attrib.get('text','')}\t{n.attrib.get('bounds','')}"
        for n in root.iter("node")
        if n.attrib.get("text")
    ]
    (DATA / f"{name}.tsv").write_text("\n".join(lines), encoding="utf-8")
    ui.run_shell(f"screencap -p /sdcard/{name}.png")
    ui.run_cmd(["pull", f"/sdcard/{name}.png", str((DATA / f"{name}.png").resolve())])
    return root


ui.run_shell(
    "am start -a android.intent.action.VIEW -d 'pinduoduo://com.xunmeng.pinduoduo/coupons.html'"
)
time.sleep(5)
root = snap("reopen_venue")
print("sig", json.dumps(page_signals(ui, root), ensure_ascii=False))

# dismiss if needed
ui.dismiss_popups(max_attempts=2)
root = ui.dump_ui()
print("sig2", json.dumps(page_signals(ui, root), ensure_ascii=False))

if not page_signals(ui, root)["venue"]:
    print("NOT VENUE")
    raise SystemExit(2)

# switch region tab
from pdd_common import TaskReport, StepResult

report = TaskReport(mode="script", serial=ui.serial)
res = region.ensure_region_tab(ui, report, skip=False)
print("tab", res, report.summary())
root = snap("region_ready")
print("sig3", json.dumps(page_signals(ui, root), ensure_ascii=False))

# claim loop
code = region.run(ui.serial, observe=False, skip_tab=True, max_claims=6, max_rounds=8)
print("claim_exit", code)
