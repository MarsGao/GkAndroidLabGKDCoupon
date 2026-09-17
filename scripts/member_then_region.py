#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""会员打卡 + 等级礼包；再回频道点消费券进会场领地区专享。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, r"C:\GkDesktop\GitProjects\GkAndroidLab\scripts\ecommerce")
from adb_ui_helper import AdbError, AdbUIHelper  # noqa: E402
from pdd_common import TaskReport, StepResult, page_signals  # noqa: E402
import claim_region_exclusive as region  # noqa: E402
import run_pdd_coupon_task as sm  # noqa: E402

DATA = ROOT / "data"
ui = AdbUIHelper("3B159H003D600000")
report = TaskReport(mode="script", serial=ui.serial)


def dump():
    for _ in range(8):
        try:
            return ui.dump_ui()
        except AdbError:
            time.sleep(0.7)
    raise AdbError("dump")


def snap(name):
    root = dump()
    (DATA / f"{name}.tsv").write_text(
        "\n".join(
            f"{n.attrib.get('text','')}|{n.attrib.get('bounds','')}"
            for n in root.iter("node")
            if n.attrib.get("text")
        ),
        encoding="utf-8",
    )
    ui.run_shell(f"screencap -p /sdcard/{name}.png")
    ui.run_cmd(["pull", f"/sdcard/{name}.png", str((DATA / f"{name}.png").resolve())])
    return root


print("=== member checkin ===")
print(json.dumps(page_signals(ui, dump()), ensure_ascii=False))
r = sm.step_checkin(ui, report, observe=False)
print("checkin", r)
snap("after_checkin")

print("=== level gift ===")
# 点等级礼包图标入口
root = dump()
pack = ui.find_nodes(root, text_regex=r"等级礼包")
if pack:
    ui.tap_node(pack[0], delay=2.5)
    snap("level_page")
r2 = sm.step_level_gift(ui, report, observe=False)
print("level", r2)
snap("after_level")

# 回百亿补贴频道
for _ in range(4):
    ui.back(delay=1.0)
    root = dump()
    texts = " ".join(n.attrib.get("text", "") for n in root.iter("node"))
    if "百亿消费券" in texts or "百亿加倍补" in texts:
        break
else:
    ui.run_shell(
        "am start -a android.intent.action.VIEW -d "
        "'pinduoduo://com.xunmeng.pinduoduo/search_result.html?search_key=%E7%99%BE%E4%BA%BF%E8%A1%A5%E8%B4%B4'"
    )
    time.sleep(4)

root = snap("back_bybt")
print("bybt", json.dumps(page_signals(ui, root), ensure_ascii=False))

# 点「百亿消费券」标题（不要点抽福袋）
hits = ui.find_nodes(root, text_regex=r"^百亿消费券$")
if not hits:
    hits = ui.find_nodes(root, text_regex=r"百亿消费券")
print("xfq hits", [(h["text"], h["center"], h["bounds"]) for h in hits])
if hits:
    # 取 y 较小、高度较小的标题
    hits = sorted(hits, key=lambda z: (z["center"][1], z["bounds"][3] - z["bounds"][1]))
    ui.tap_node(hits[0], delay=3.5)
else:
    # 右卡标题区：根据 1440 屏，标题约在右半上沿
    ui.tap(1080, 720, delay=3.5)

root = snap("venue_again")
sig = page_signals(ui, root)
print("venue", json.dumps(sig, ensure_ascii=False))
if not (sig["venue"] or sig["region_tab"]):
    print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
    raise SystemExit(2)

# light + region
if sig.get("light_available"):
    print(sm.step_light_browse(ui, report, False, 10.0))

print("tab", region.ensure_region_tab(ui, report, skip=False))
code = region.run(ui.serial, observe=False, skip_tab=True, max_claims=8, max_rounds=10)
print("region", code)
print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
raise SystemExit(0 if code == 0 else code)
