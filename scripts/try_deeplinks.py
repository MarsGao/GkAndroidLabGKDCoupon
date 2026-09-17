#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""尝试多种 deep link / 搜索进入百亿补贴或消费券会场。"""
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
    for _ in range(6):
        try:
            return ui.dump_ui()
        except AdbError:
            time.sleep(0.8)
    raise AdbError("dump fail")


def snap(name):
    root = dump()
    lines = [
        f"{n.attrib.get('text','')}\t{n.attrib.get('content-desc','')}\t{n.attrib.get('bounds','')}"
        for n in root.iter("node")
        if n.attrib.get("text") or n.attrib.get("content-desc")
    ]
    (DATA / f"{name}.tsv").write_text("\n".join(lines), encoding="utf-8")
    ui.run_shell(f"screencap -p /sdcard/{name}.png")
    ui.run_cmd(["pull", f"/sdcard/{name}.png", str((DATA / f"{name}.png").resolve())])
    return root


def interesting(root):
    keys = ("双重", "地区", "立即领取", "去使用", "点亮", "消费券", "会员", "打卡", "待领", "百亿消费", "页面加载", "返回首页", "知道了")
    out = []
    for n in root.iter("node"):
        t = n.attrib.get("text", "")
        if any(k in t for k in keys):
            out.append((t, n.attrib.get("bounds")))
    return out


URLS = [
    "pinduoduo://com.xunmeng.pinduoduo/brand_rebate.html",
    "https://mobile.yangkeduo.com/brand_rebate.html",
    "pinduoduo://com.xunmeng.pinduoduo/coupon.html",
    "pinduoduo://com.xunmeng.pinduoduo/coupons.html",
    "pinduoduo://com.xunmeng.pinduoduo/pincard_ask.html",
    "pinduoduo://com.xunmeng.pinduoduo/transac_virtual_card.html",
]

for i, url in enumerate(URLS):
    print("=== try", url)
    ui.run_shell(f"am start -a android.intent.action.VIEW -d '{url}'")
    time.sleep(4.5)
    root = snap(f"link_{i}")
    print("sig", json.dumps(page_signals(ui, root), ensure_ascii=False))
    print("hit", interesting(root)[:12])
    texts = " ".join(n.attrib.get("text", "") for n in root.iter("node"))
    if "页面加载不成功" in texts:
        n = ui.find_nodes(root, text_regex=r"^返回首页$")
        if n:
            ui.tap_node(n[0], delay=2.0)
        continue
    if page_signals(ui, root)["venue"] or page_signals(ui, root)["member"] or page_signals(ui, root)["checkin_available"]:
        print("SUCCESS", url)
        break
    if "打卡送积分" in texts or "双重补贴" in texts or "百亿补贴会员" in texts:
        print("SUCCESS soft", url)
        break
else:
    print("all links failed; try search 百亿消费券")
    ui.start_app("com.xunmeng.pinduoduo")
    time.sleep(2)
    root = dump()
    # tap search
    for n in root.iter("node"):
        d = n.attrib.get("content-desc", "")
        b = ui.parse_bounds(n.attrib.get("bounds", ""))
        if d == "搜索" and b and b[1] < 400:
            ui.tap((b[0] + b[2]) // 2, (b[1] + b[3]) // 2, delay=1.0)
            break
    else:
        ui.tap(720, 247, delay=1.0)
    ui.clear_and_input_text("百亿消费券")
    ui.press_enter()
    time.sleep(2.5)
    root = snap("search_coupon")
    print("sig", json.dumps(page_signals(ui, root), ensure_ascii=False))
    print("hit", interesting(root)[:20])
    hits = ui.find_nodes(root, text_regex=r"百亿消费券|消费券会场|去领取")
    print("candidates", [(h["text"], h["center"]) for h in hits[:10]])
    if hits:
        ui.tap_node(hits[0], delay=3.0)
        root = snap("after_search_coupon")
        print("final", json.dumps(page_signals(ui, root), ensure_ascii=False))
        print("hit", interesting(root)[:20])
