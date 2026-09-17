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
from pdd_common import page_signals  # noqa: E402
import claim_region_exclusive as region  # noqa: E402
from pdd_common import TaskReport  # noqa: E402

DATA = ROOT / "data"
ui = AdbUIHelper("3B159H003D600000")


def dump():
    for _ in range(8):
        try:
            return ui.dump_ui()
        except AdbError:
            time.sleep(0.8)
    raise AdbError("dump fail")


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


ui.start_app("com.xunmeng.pinduoduo")
time.sleep(2)
# 回首页
root = dump()
for h in ui.find_nodes(root, text_regex=r"^首页$"):
    if h["center"][1] > 2900:
        ui.tap_node(h, delay=1.2)
        break
root = dump()
# 点搜索框
tapped = False
for n in root.iter("node"):
    d = n.attrib.get("content-desc", "")
    b = ui.parse_bounds(n.attrib.get("bounds", ""))
    if not b or b[1] > 400:
        continue
    if d == "搜索" or "搜索" in d:
        ui.tap((b[0] + b[2]) // 2, (b[1] + b[3]) // 2, delay=1.0)
        tapped = True
        break
if not tapped:
    ui.tap(700, 247, delay=1.0)
ui.clear_and_input_text("百亿消费券")
ui.press_enter()
time.sleep(3)
root = snap("search_byxfq")
print("sig", json.dumps(page_signals(ui, root), ensure_ascii=False))
# print all texts containing 消费 or 百亿
for n in root.iter("node"):
    t = n.attrib.get("text", "")
    if any(k in t for k in ("消费券", "百亿", "会场", "领取", "双重", "地区")):
        print("T", t, n.attrib.get("bounds"))

# prefer exact-ish activity entries
cands = []
for n in ui.find_nodes(root, text_regex=r"百亿消费券|消费券会场|去领取|立即领取"):
    if n["center"][1] < 2500 and n["bounds"][2] - n["bounds"][0] > 10:
        cands.append(n)
print("cands", [(c["text"], c["center"]) for c in cands[:12]])
for c in cands[:3]:
    ui.tap_node(c, delay=3.0)
    root = snap("after_search_tap")
    sig = page_signals(ui, root)
    print("after tap", c["text"], json.dumps(sig, ensure_ascii=False))
    if sig["venue"] or sig["region_tab"]:
        report = TaskReport(mode="script", serial=ui.serial)
        region.ensure_region_tab(ui, report, skip=False)
        code = region.run(ui.serial, observe=False, skip_tab=True, max_claims=6, max_rounds=8)
        print("DONE", code)
        raise SystemExit(0)
    ui.back(delay=1.5)

print("search path failed")
raise SystemExit(2)
