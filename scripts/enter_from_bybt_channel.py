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
    lines = [
        f"{n.attrib.get('text','')}|{n.attrib.get('bounds','')}"
        for n in root.iter("node")
        if n.attrib.get("text")
    ]
    (DATA / f"{name}.tsv").write_text("\n".join(lines), encoding="utf-8")
    ui.run_shell(f"screencap -p /sdcard/{name}.png")
    ui.run_cmd(["pull", f"/sdcard/{name}.png", str((DATA / f"{name}.png").resolve())])
    return root


root = dump()
print("sig0", json.dumps(page_signals(ui, root), ensure_ascii=False))
for n in root.iter("node"):
    t = n.attrib.get("text", "")
    if any(k in t for k in ("消费券", "会员", "加倍", "福袋", "待领", "频道", "点亮")):
        print(repr(t), n.attrib.get("bounds"))

hits = ui.find_nodes(root, text_regex=r"百亿消费券")
print("hits", [(h["text"], h["center"], h["bounds"]) for h in hits])
if hits:
    target = sorted(hits, key=lambda z: (z["bounds"][3] - z["bounds"][1], z["center"][1]))[0]
    ui.tap_node(target, delay=3.5)
else:
    # 右侧「百亿消费券」模块（避开抽福袋按钮偏下位置，点标题区）
    ui.tap(1100, 700, delay=3.5)

root = snap("in_venue_try")
sig = page_signals(ui, root)
print("after", json.dumps(sig, ensure_ascii=False))

if not (sig["venue"] or sig["region_tab"]):
    # 再试模块中心
    ui.back(delay=1.0)
    ui.tap(1080, 780, delay=3.5)
    root = snap("in_venue_try2")
    sig = page_signals(ui, root)
    print("after2", json.dumps(sig, ensure_ascii=False))

if not (sig["venue"] or sig["region_tab"]):
    raise SystemExit(2)

# 点亮（若有）
if sig["light_available"]:
    lights = ui.find_nodes(root, text_regex=r"^立即点亮$")
    if lights:
        ui.tap_node(lights[0], delay=1.5)
        go = ui.find_nodes(dump(), text_regex=r"去看看")
        if go:
            ui.tap_node(go[0], delay=1.0)
        t0 = time.time()
        while time.time() - t0 < 10:
            ui.swipe_up(0.12)
            time.sleep(1.0)
        for _ in range(5):
            ui.back(delay=1.0)
            r = dump()
            if page_signals(ui, r)["venue"]:
                root = r
                break
        snap("after_light3")

report = TaskReport(mode="script", serial=ui.serial)
print("tab", region.ensure_region_tab(ui, report, skip=False))
snap("region_on3")
code = region.run(ui.serial, observe=False, skip_tab=True, max_claims=8, max_rounds=10)
print("region", code)
raise SystemExit(code)
