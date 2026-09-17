#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从「我的优惠券」或深链恢复到消费券会场，再地区专享领取。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, r"C:\GkDesktop\GitProjects\GkAndroidLab\scripts\ecommerce")
from adb_ui_helper import AdbUIHelper  # noqa: E402
from pdd_common import StepResult, TaskReport, page_signals  # noqa: E402
import claim_region_exclusive as region  # noqa: E402

DATA = ROOT / "data"
ui = AdbUIHelper("3B159H003D600000")


def snap(name):
    root = ui.dump_ui()
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


def in_venue(root) -> bool:
    s = page_signals(ui, root)
    return s["venue"] or (s["dual_tab"] and s["region_tab"])


# 冷启动后再开深链
ui.stop_app("com.xunmeng.pinduoduo")
time.sleep(1.5)
ui.start_app("com.xunmeng.pinduoduo")
time.sleep(3)
ui.run_shell(
    "am start -a android.intent.action.VIEW -d 'pinduoduo://com.xunmeng.pinduoduo/coupons.html'"
)
time.sleep(5)
root = snap("venue_cold")
print("cold", json.dumps(page_signals(ui, root), ensure_ascii=False))

if not in_venue(root):
    # 我的优惠券路径：点「百亿消费券活动」来源或领券中心
    for rx in (
        r"百亿消费券活动",
        r"领券中心",
        r"领更多好券",
        r"百亿补贴频道",
    ):
        hits = ui.find_nodes(root, text_regex=rx)
        print("try", rx, len(hits))
        if hits:
            ui.tap_node(hits[0], delay=3.0)
            root = snap("from_wallet")
            print("after", json.dumps(page_signals(ui, root), ensure_ascii=False))
            if in_venue(root):
                break
    if not in_venue(root):
        # 再试若干候选 URI
        for url in (
            "pinduoduo://com.xunmeng.pinduoduo/coupons.html?_pdd_fs=1&_pdd_tc=ffffff&_pdd_sbs=1",
            "pinduoduo://com.xunmeng.pinduoduo/pdd_subject.html?subject_id=coupon",
        ):
            ui.run_shell(f"am start -a android.intent.action.VIEW -d '{url}'")
            time.sleep(4)
            root = snap("uri_retry")
            print(url, json.dumps(page_signals(ui, root), ensure_ascii=False))
            if in_venue(root):
                break

if not in_venue(root):
    print("FAILED recover venue")
    raise SystemExit(2)

report = TaskReport(mode="script", serial=ui.serial)
print("tab", region.ensure_region_tab(ui, report, skip=False))
root = snap("region_on")
print("region sig", json.dumps(page_signals(ui, root), ensure_ascii=False))
code = region.run(ui.serial, observe=False, skip_tab=True, max_claims=6, max_rounds=8)
print("exit", code)
print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
