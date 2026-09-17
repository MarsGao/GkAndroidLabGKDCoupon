#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从任意页恢复到拼多多首页，再尝试进入百亿补贴主会场。"""
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


def dump(ui: AdbUIHelper):
    last = None
    for _ in range(8):
        try:
            return ui.dump_ui()
        except AdbError as e:
            last = e
            time.sleep(1.0)
    raise AdbError(str(last))


def save(ui, name):
    root = dump(ui)
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


def dismiss_known(ui: AdbUIHelper) -> bool:
    root = dump(ui)
    for regex in (r"^知道了$", r"^我知道了$", r"^关闭按钮$", r"^残忍拒绝$", r"^以后再说$", r"^逛逛别的$"):
        nodes = ui.find_nodes(root, text_regex=regex)
        if nodes:
            ui.tap_node(nodes[0], delay=1.0)
            return True
    # desc 关闭
    for n in root.iter("node"):
        d = n.attrib.get("content-desc", "")
        t = n.attrib.get("text", "")
        if d in ("关闭", "close") or t == "关闭":
            b = ui.parse_bounds(n.attrib.get("bounds", ""))
            if b:
                ui.tap((b[0] + b[2]) // 2, (b[1] + b[3]) // 2, delay=1.0)
                return True
    return False


def back_to_home(ui: AdbUIHelper) -> None:
    ui.start_app("com.xunmeng.pinduoduo")
    time.sleep(2)
    for _ in range(6):
        if dismiss_known(ui):
            continue
        root = dump(ui)
        home = ui.find_nodes(root, text_regex=r"^首页$")
        # 底部首页 tab
        bottom = [h for h in home if h["center"][1] > 2900]
        if bottom and ui.find_nodes(root, text_regex=r"^推荐$"):
            # already home-ish
            sig_texts = " ".join(
                n.attrib.get("text", "") for n in root.iter("node")
            )
            if "充值中心" in sig_texts or "多多果园" in sig_texts:
                ui.tap_node(bottom[0], delay=1.0)
                return
        if bottom:
            ui.tap_node(bottom[0], delay=1.2)
            root = dump(ui)
            texts = " ".join(n.attrib.get("text", "") for n in root.iter("node"))
            if "充值中心" in texts:
                return
        ui.back(delay=1.0)
    save(ui, "pdd_home_recover")


def open_bybt_channel(ui: AdbUIHelper) -> bool:
    """多种入口尝试。"""
    root = dump(ui)
    # 1) 顶部类目是否有百亿补贴（可能需横滑）
    for _ in range(3):
        hits = [h for h in ui.find_nodes(root, text_regex=r"^百亿补贴$") if h["center"][1] < 600]
        if hits:
            ui.tap_node(hits[0], delay=3.0)
            save(ui, "bybt_from_tab")
            return True
        # 横滑顶栏
        ui.swipe(1200, 400, 400, 400, 300)
        time.sleep(0.8)
        root = dump(ui)

    # 2) 首页货架标题「百亿补贴」（y 较大）——历史可能进频道
    hits = ui.find_nodes(root, text_regex=r"^百亿补贴$")
    if hits:
        ui.tap_node(sorted(hits, key=lambda z: z["center"][1])[0], delay=3.5)
        save(ui, "bybt_from_shelf")
        root = dump(ui)
        texts = " ".join(n.attrib.get("text", "") for n in root.iter("node"))
        if any(k in texts for k in ("会员", "消费券", "待领", "立即领取", "打卡")):
            return True
        # 若进了商品/列表，返回再试别的
        ui.back(delay=1.5)

    # 3) deeplink 候选
    for url in (
        "pinduoduo://com.xunmeng.pinduoduo/brand_rebate.html",
        "pinduoduo://com.xunmeng.pinduoduo/bye_rebate.html",
        "pinduoduo://com.xunmeng.pinduoduo/sub_brand_rebate.html",
    ):
        ui.run_shell(f"am start -a android.intent.action.VIEW -d '{url}'")
        time.sleep(4)
        dismiss_known(ui)
        root = dump(ui)
        texts = " ".join(n.attrib.get("text", "") for n in root.iter("node"))
        save(ui, "bybt_deeplink_try")
        if "页面加载不成功" in texts or "返回首页" in texts:
            print("deeplink fail", url)
            if ui.find_nodes(root, text_regex=r"^返回首页$"):
                ui.tap_text(r"^返回首页$", delay=2.0)
            continue
        if any(k in texts for k in ("会员", "百亿补贴", "消费券", "打卡送积分")):
            # 排除纯商品详情
            if "发起拼单" in texts and "充值中心" not in texts and "打卡" not in texts:
                ui.back(delay=1.0)
                continue
            return True
    return False


def find_member_entry(ui: AdbUIHelper) -> bool:
    root = dump(ui)
    for regex in (r"^会员$", r"百亿补贴会员", r"会员中心"):
        nodes = ui.find_nodes(root, text_regex=regex)
        if nodes:
            ui.tap_node(nodes[0], delay=2.5)
            save(ui, "member_entry")
            return True
    # 右上角常见会员图标坐标（历史）
    ui.tap(1200, 236, delay=2.5)
    save(ui, "member_coord_try")
    root = dump(ui)
    texts = " ".join(n.attrib.get("text", "") for n in root.iter("node"))
    return "打卡" in texts or "会员" in texts


def main():
    ui = AdbUIHelper(SERIAL)
    ui.unlock_and_wake()
    back_to_home(ui)
    save(ui, "home_ready")
    ok = open_bybt_channel(ui)
    print("bybt", ok)
    root = dump(ui)
    print(json.dumps(page_signals(ui, root), ensure_ascii=False))
    mem = find_member_entry(ui)
    print("member", mem)
    root = dump(ui)
    print(json.dumps(page_signals(ui, root), ensure_ascii=False))
    save(ui, "final_nav")


if __name__ == "__main__":
    main()
