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


def dump_soft():
    for i in range(10):
        try:
            return ui.dump_ui()
        except AdbError:
            time.sleep(1.0)
    return None


def snap(name):
    root = dump_soft()
    if root is None:
        ui.run_shell(f"screencap -p /sdcard/{name}.png")
        ui.run_cmd(["pull", f"/sdcard/{name}.png", str((DATA / f"{name}.png").resolve())])
        return None
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


# 路径 A：失败页上下文后再开 coupons
ui.run_shell(
    "am start -a android.intent.action.VIEW -d 'pinduoduo://com.xunmeng.pinduoduo/brand_rebate.html'"
)
time.sleep(3)
root = dump_soft()
if root and ui.find_nodes(root, text_regex=r"返回首页"):
    # 不点返回，直接叠 coupons
    pass
ui.run_shell(
    "am start -a android.intent.action.VIEW -d 'pinduoduo://com.xunmeng.pinduoduo/coupons.html'"
)
time.sleep(5)
root = snap("stack_coupons")
print("stack", None if root is None else json.dumps(page_signals(ui, root), ensure_ascii=False))

if root is None or not (page_signals(ui, root)["venue"] or page_signals(ui, root)["region_tab"]):
    # 路径 B：领券中心
    root = dump_soft() or root
    if root:
        for rx in (r"领券中心", r"领更多好券"):
            hits = ui.find_nodes(root, text_regex=rx)
            if hits:
                ui.tap_node(hits[0], delay=3.0)
                root = snap("coupon_center")
                print("center", json.dumps(page_signals(ui, root), ensure_ascii=False) if root else None)
                break

if root and (page_signals(ui, root)["venue"] or page_signals(ui, root)["region_tab"]):
    report = TaskReport(mode="script", serial=ui.serial)
    print("ensure tab", region.ensure_region_tab(ui, report, skip=False))
    snap("region_ready2")
    # light first if available
    root = dump_soft()
    if root:
        lights = ui.find_nodes(root, text_regex=r"^立即点亮$")
        if lights:
            print("light tap")
            ui.tap_node(lights[0], delay=1.5)
            go = ui.find_nodes(ui.dump_ui(), text_regex=r"去看看")
            if go:
                ui.tap_node(go[0], delay=1.0)
            t0 = time.time()
            while time.time() - t0 < 10:
                ui.swipe_up(0.12)
                time.sleep(1.0)
            for _ in range(4):
                ui.back(delay=1.0)
                r2 = dump_soft()
                if r2 and page_signals(ui, r2)["venue"]:
                    break
            snap("after_light")
    code = region.run(ui.serial, observe=False, skip_tab=True, max_claims=6, max_rounds=8)
    print("claim", code)
else:
    print("still not venue; dump focus")
    print(ui.run_shell("dumpsys window | grep mCurrentFocus"))
    snap("final_fail")
    raise SystemExit(2)
