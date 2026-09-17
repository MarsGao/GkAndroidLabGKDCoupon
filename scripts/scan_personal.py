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
    for _ in range(8):
        try:
            return ui.dump_ui()
        except AdbError:
            time.sleep(0.8)
    raise AdbError("dump")


def snap(name):
    root = dump()
    (DATA / f"{name}.tsv").write_text(
        "\n".join(
            f"{n.attrib.get('text','')}\t{n.attrib.get('content-desc','')}\t{n.attrib.get('bounds','')}"
            for n in root.iter("node")
            if n.attrib.get("text") or n.attrib.get("content-desc")
        ),
        encoding="utf-8",
    )
    ui.run_shell(f"screencap -p /sdcard/{name}.png")
    ui.run_cmd(["pull", f"/sdcard/{name}.png", str((DATA / f"{name}.png").resolve())])
    return root


ui.start_app("com.xunmeng.pinduoduo")
time.sleep(2)
root = dump()
for n in ui.find_nodes(root, text_regex=r"^个人中心$"):
    if n["center"][1] > 2900:
        ui.tap_node(n, delay=2.5)
        break
root = snap("personal")
print(json.dumps(page_signals(ui, root), ensure_ascii=False))
for n in root.iter("node"):
    t = n.attrib.get("text", "")
    d = n.attrib.get("content-desc", "")
    if any(k in (t + d) for k in ("百亿", "消费券", "会员", "优惠券", "补贴", "券")):
        print(f"{t}\t{d}\t{n.attrib.get('bounds')}")
