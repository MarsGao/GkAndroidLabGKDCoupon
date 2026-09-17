#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""轻量导航：首页顶 → 百亿补贴 / 优惠 / 会员。"""
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
SERIAL = "3B159H003D600000"


def dump(ui, n=5):
    err = None
    for _ in range(n):
        try:
            return ui.dump_ui()
        except AdbError as e:
            err = e
            time.sleep(0.8)
    raise AdbError(str(err))


def snap(ui, name):
    root = dump(ui)
    lines = [
        f"{n.attrib.get('text','')}\t{n.attrib.get('content-desc','')}\t{n.attrib.get('bounds','')}"
        for n in root.iter("node")
        if n.attrib.get("text") or n.attrib.get("content-desc")
    ]
    (DATA / f"{name}.tsv").write_text("\n".join(lines), encoding="utf-8")
    ui.run_shell(f"screencap -p /sdcard/{name}.png")
    ui.run_cmd(["pull", f"/sdcard/{name}.png", str((DATA / f"{name}.png").resolve())])
    return root


def main():
    ui = AdbUIHelper(SERIAL)
    ui.unlock_and_wake()
    # 点底部首页复位
    root = dump(ui)
    for h in ui.find_nodes(root, text_regex=r"^首页$"):
        if h["center"][1] > 2900:
            ui.tap_node(h, delay=1.0)
            break
    # 上滑到顶
    for _ in range(3):
        ui.swipe_down(0.5)
        time.sleep(0.4)
    root = snap(ui, "home_top")
    print("signals", json.dumps(page_signals(ui, root), ensure_ascii=False))

    # 优先点快捷入口以外的「百亿补贴」标题（货架）
    bybt = ui.find_nodes(root, text_regex=r"^百亿补贴$")
    print("bybt nodes", [(b["center"], b["bounds"]) for b in bybt])

    # 点底部「优惠」大按钮（中秋立减）
    youhui = [n for n in ui.find_nodes(root, text_regex=r"优惠|中秋立减") if n["center"][1] > 2900]
    print("youhui", [(y["text"], y["center"]) for y in youhui])
    if youhui:
        ui.tap_node(youhui[0], delay=3.0)
        root = snap(ui, "youhui_page")
        print("after youhui", json.dumps(page_signals(ui, root), ensure_ascii=False))
        texts = "\n".join(n.attrib.get("text", "") for n in root.iter("node"))
        for key in ("百亿", "消费券", "会员", "领券", "补贴", "打卡"):
            if key in texts:
                print("found key", key)

    # 若仍无会场，试货架百亿补贴
    root = dump(ui)
    if not page_signals(ui, root)["venue"]:
        # 回首页
        for h in ui.find_nodes(root, text_regex=r"^首页$"):
            if h["center"][1] > 2900:
                ui.tap_node(h, delay=1.2)
                break
        root = dump(ui)
        bybt = ui.find_nodes(root, text_regex=r"^百亿补贴$")
        if bybt:
            ui.tap_node(sorted(bybt, key=lambda z: z["center"][1])[0], delay=3.0)
            root = snap(ui, "bybt_shelf2")
            print("after shelf", json.dumps(page_signals(ui, root), ensure_ascii=False))
            # 若像主会场，点右上角会员
            texts = " ".join(n.attrib.get("text", "") for n in root.iter("node"))
            print("sample texts", [t for t in texts.split() if t][:30])
            mem = ui.find_nodes(root, text_regex=r"^会员$")
            if mem:
                ui.tap_node(mem[0], delay=2.5)
            else:
                ui.tap(1200, 236, delay=2.5)
            root = snap(ui, "member_try2")
            print("member", json.dumps(page_signals(ui, root), ensure_ascii=False))


if __name__ == "__main__":
    main()
