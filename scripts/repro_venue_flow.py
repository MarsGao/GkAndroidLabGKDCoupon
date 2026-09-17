#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""复现：加载失败页 → 返回首页 → coupons.html → 会场。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, r"C:\GkDesktop\GitProjects\GkAndroidLab\scripts\ecommerce")
from adb_ui_helper import AdbError, AdbUIHelper  # noqa: E402
from pdd_common import TaskReport, page_signals  # noqa: E402
import claim_region_exclusive as region  # noqa: E402

DATA = ROOT / "data"
ui = AdbUIHelper("3B159H003D600000")


def dump():
    for _ in range(10):
        try:
            return ui.dump_ui()
        except AdbError:
            time.sleep(0.8)
    raise AdbError("dump")


def snap(name):
    root = dump()
    (DATA / f"{name}.tsv").write_text(
        "\n".join(
            f"{n.attrib.get('text','')}\t{n.attrib.get('bounds','')}"
            for n in root.iter("node")
            if n.attrib.get("text")
        ),
        encoding="utf-8",
    )
    ui.run_shell(f"screencap -p /sdcard/{name}.png")
    ui.run_cmd(["pull", f"/sdcard/{name}.png", str((DATA / f"{name}.png").resolve())])
    return root


ui.unlock_and_wake()
ui.run_shell(
    "am start -a android.intent.action.VIEW -d 'pinduoduo://com.xunmeng.pinduoduo/coupon.html'"
)
time.sleep(4)
root = dump()
back = ui.find_nodes(root, text_regex=r"^返回首页$")
print("fail page backs", len(back))
if back:
    ui.tap_node(back[0], delay=2.5)
else:
    ui.start_app("com.xunmeng.pinduoduo")
    time.sleep(2)

ui.run_shell(
    "am start -a android.intent.action.VIEW -d 'pinduoduo://com.xunmeng.pinduoduo/coupons.html'"
)
time.sleep(5)
root = snap("repro_venue")
sig = page_signals(ui, root)
print("sig", json.dumps(sig, ensure_ascii=False))

if not (sig["venue"] or sig["region_tab"]):
    print("repro failed")
    raise SystemExit(2)

# 点亮
lights = ui.find_nodes(root, text_regex=r"^立即点亮$")
if lights and not sig["light_done"]:
    ui.tap_node(lights[0], delay=1.5)
    root2 = dump()
    go = ui.find_nodes(root2, text_regex=r"去看看")
    if go:
        ui.tap_node(go[0], delay=1.0)
    t0 = time.time()
    while time.time() - t0 < 10:
        if ui.foreground_package() != "com.xunmeng.pinduoduo":
            break
        ui.swipe_up(0.12)
        time.sleep(1.0)
    for _ in range(5):
        ui.back(delay=1.0)
        r = dump()
        if page_signals(ui, r)["venue"] or page_signals(ui, r)["light_done"]:
            break
    snap("after_light2")
    print("light sig", json.dumps(page_signals(ui, dump()), ensure_ascii=False))

report = TaskReport(mode="script", serial=ui.serial)
print("tab", region.ensure_region_tab(ui, report, skip=False))
snap("region_final")
code = region.run(ui.serial, observe=False, skip_tab=True, max_claims=8, max_rounds=10)
print("region exit", code)
raise SystemExit(code)
