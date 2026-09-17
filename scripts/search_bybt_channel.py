#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""搜索「百亿补贴」→ 进入频道 → 找消费券入口 → 地区专享。"""
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
import enter_coupon_venue as enter  # noqa: E402

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


ui.stop_app("com.xunmeng.pinduoduo")
time.sleep(1)
ui.start_app("com.xunmeng.pinduoduo")
time.sleep(3)
root = dump()
for h in ui.find_nodes(root, text_regex=r"^首页$"):
    if h["center"][1] > 2900:
        ui.tap_node(h, delay=1.0)
        break
# dismiss lucky bag if any
ui.dismiss_popups(1)
ui.back(0.5) if False else None
root = dump()
# open search - tap placeholder area
ui.tap(720, 247, delay=1.0)
ui.clear_and_input_text("百亿补贴")
ui.press_enter()
time.sleep(3)
root = snap("search_bybt2")
print("after search")
for n in root.iter("node"):
    t = n.attrib.get("text", "")
    if any(k in t for k in ("进入", "百亿", "频道", "消费券", "补贴")):
        print(t, n.attrib.get("bounds"))

for rx in (r"进入百亿补贴", r"进入频道", r"^百亿补贴$", r"官方频道"):
    hits = ui.find_nodes(root, text_regex=rx)
    print("rx", rx, [(h["text"], h["center"]) for h in hits[:5]])
    if hits:
        # prefer top
        hits = sorted(hits, key=lambda z: z["center"][1])
        ui.tap_node(hits[0], delay=3.5)
        break
else:
    # tap first result banner area
    ui.tap(720, 500, delay=3.0)

root = snap("bybt_channel")
sig = page_signals(ui, root)
print("channel", json.dumps(sig, ensure_ascii=False))
for n in root.iter("node"):
    t = n.attrib.get("text", "")
    if any(k in t for k in ("消费券", "会员", "待领", "打卡", "点亮", "双重", "地区")):
        print("T", t, n.attrib.get("bounds"))

# try a11y enter 百亿消费券
hits = ui.find_nodes(root, text_regex=r"百亿消费券|消费券")
if hits:
    ui.tap_node(sorted(hits, key=lambda z: z["center"][1])[0], delay=3.0)
    root = snap("after_xfq_text")
    print("xfq text", json.dumps(page_signals(ui, root), ensure_ascii=False))
else:
    # image enter
    code = enter.run(ui.serial, observe=False, open_subsidy=False, allow_fallback="603,777")
    print("enter code", code)
    root = dump()

sig = page_signals(ui, root)
if not (sig["venue"] or sig["region_tab"]):
    # member path at least
    mem = ui.find_nodes(root, text_regex=r"^会员$")
    if mem:
        ui.tap_node(mem[0], delay=2.5)
    else:
        ui.tap(1200, 236, delay=2.5)
    root = snap("member_from_bybt")
    print("member", json.dumps(page_signals(ui, root), ensure_ascii=False))
    raise SystemExit(3)

report = TaskReport(mode="script", serial=ui.serial)
region.ensure_region_tab(ui, report, skip=False)
code = region.run(ui.serial, observe=False, skip_tab=True, max_claims=8, max_rounds=10)
print("region", code)
raise SystemExit(code)
