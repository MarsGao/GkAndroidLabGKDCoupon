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

DATA = ROOT / "data"
ui = AdbUIHelper("3B159H003D600000")


def dump():
    err = None
    for _ in range(6):
        try:
            return ui.dump_ui()
        except AdbError as e:
            err = e
            time.sleep(0.8)
    raise AdbError(str(err))


def snap(name: str):
    root = dump()
    lines = []
    for n in root.iter("node"):
        t = n.attrib.get("text", "")
        d = n.attrib.get("content-desc", "")
        b = n.attrib.get("bounds", "")
        if t or d:
            lines.append(f"{t}\t{d}\t{b}")
    (DATA / f"{name}.tsv").write_text("\n".join(lines), encoding="utf-8")
    ui.run_shell(f"screencap -p /sdcard/{name}.png")
    ui.run_cmd(["pull", f"/sdcard/{name}.png", str((DATA / f"{name}.png").resolve())])
    return root


root = dump()
for n in ui.find_nodes(root, text_regex=r"优惠|中秋立减"):
    if n["center"][1] > 2900:
        ui.tap_node(n, delay=2.0)
        break
root = snap("youhui2")

for rx in (r"大促消费券", r"消费券", r"^百亿补贴$", r"加倍补贴", r"整点抢券"):
    hits = ui.find_nodes(root, text_regex=rx)
    print(rx, [(h["text"], h["center"]) for h in hits[:5]])

hits = ui.find_nodes(root, text_regex=r"大促消费券|消费券")
if hits:
    ui.tap_node(hits[0], delay=3.0)
else:
    # 券条视觉中心（截图里 100/30/50/8 元一行）
    ui.tap(720, 1180, delay=3.0)
root = snap("after_coupon_strip")
print("signals", json.dumps(page_signals(ui, root), ensure_ascii=False))
for n in root.iter("node"):
    t = n.attrib.get("text", "")
    if any(
        k in t
        for k in (
            "双重",
            "地区",
            "立即领取",
            "去使用",
            "点亮",
            "消费券",
            "会员",
            "打卡",
            "待领",
            "百亿消费",
            "知道了",
        )
    ):
        print("T", t, n.attrib.get("bounds"))
