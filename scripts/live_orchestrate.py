#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真机编排：GKD 脚本模式准备 → 导航百亿补贴 → 跑状态机。"""
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
DATA.mkdir(exist_ok=True)
SERIAL = "3B159H003D600000"


def save_nodes(ui: AdbUIHelper, name: str) -> Path:
    root = ui.dump_ui()
    lines = []
    for n in root.iter("node"):
        t = n.attrib.get("text", "")
        d = n.attrib.get("content-desc", "")
        b = n.attrib.get("bounds", "")
        chk = n.attrib.get("checked", "")
        cls = n.attrib.get("class", "").split(".")[-1]
        if t or d or chk:
            lines.append(f"{cls}\t{t}\t{d}\tchecked={chk}\t{b}")
    path = DATA / f"{name}.tsv"
    path.write_text("\n".join(lines), encoding="utf-8")
    ui.run_shell(f"screencap -p /sdcard/{name}.png")
    ui.run_cmd(["pull", f"/sdcard/{name}.png", str((DATA / f"{name}.png").resolve())])
    return path


def dump_retry(ui: AdbUIHelper, tries: int = 8, delay: float = 1.2):
    last = None
    for i in range(tries):
        try:
            return ui.dump_ui()
        except AdbError as e:
            last = e
            time.sleep(delay)
    raise AdbError(f"dump_retry failed: {last}")


def gkd_disable_marsgao_pdd(ui: AdbUIHelper) -> None:
    ui.start_app("li.songe.gkd")
    time.sleep(2)
    # 订阅 tab
    root = dump_retry(ui)
    tabs = ui.find_nodes(root, text_regex=r"^订阅$")
    if tabs:
        # bottom nav 订阅 often lower
        bottom = [t for t in tabs if t["center"][1] > 2800]
        ui.tap_node(bottom[0] if bottom else tabs[-1], delay=1.5)
    root = dump_retry(ui)
    # 全局规则匹配按钮
    for n in root.iter("node"):
        d = n.attrib.get("content-desc", "")
        if "规则匹配已启用" in d:
            b = ui.parse_bounds(n.attrib.get("bounds", ""))
            if b:
                ui.tap((b[0] + b[2]) // 2, (b[1] + b[3]) // 2, delay=1.0)
            break
    root = dump_retry(ui)
    mars = ui.find_nodes(root, text_regex=r"MarsGao薅羊毛领券")
    if not mars:
        raise AdbError("未找到 MarsGao 订阅")
    ui.tap_node(mars[0], delay=2.0)
    root = dump_retry(ui)
    save_nodes(ui, "gkd_before_disable")
    # 关闭拼多多应用规则开关：点行右侧开关区域
    pdd = ui.find_nodes(root, text_regex=r"^拼多多$")
    if pdd:
        x1, y1, x2, y2 = pdd[0]["bounds"]
        # Switch 通常在同行右侧
        ui.tap(int(ui.screen_width * 0.90), (y1 + y2) // 2, delay=1.0)
    save_nodes(ui, "gkd_after_disable")
    print("[gkd] MarsGao 拼多多规则开关已尝试关闭")


def open_pdd_home(ui: AdbUIHelper) -> None:
    ui.start_app("com.xunmeng.pinduoduo")
    time.sleep(3)
    # 关福袋：优先点关闭类，否则 BACK 一次
    root = dump_retry(ui)
    closed = False
    for n in root.iter("node"):
        d = n.attrib.get("content-desc", "")
        t = n.attrib.get("text", "")
        if d in ("关闭", "close") or t in ("关闭",):
            rect = ui.parse_bounds(n.attrib.get("bounds", ""))
            if rect:
                ui.tap((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2, delay=1.0)
                closed = True
                break
    if not closed:
        # 福袋 X 常见约在弹窗右上；先试 BACK
        ui.back(delay=1.0)
    save_nodes(ui, "pdd_home2")


def navigate_bybt(ui: AdbUIHelper) -> bool:
    """从首页进百亿补贴频道：搜索优先，避免坏 deeplink。"""
    root = dump_retry(ui)
    # 点搜索框
    search = ui.find_nodes(root, text_regex=r".*")  # placeholder
    # 顶部搜索：content-desc 搜索 or text containing 搜索 hint
    candidates = []
    for n in root.iter("node"):
        t = n.attrib.get("text", "")
        d = n.attrib.get("content-desc", "")
        b = ui.parse_bounds(n.attrib.get("bounds", ""))
        if not b:
            continue
        if d == "搜索" or "搜索" in d:
            if b[1] < 400:
                candidates.append((b, t, d))
        if t and b[1] < 400 and b[3] < 350 and len(t) >= 2:
            # search bar placeholder text
            if "花洒" in t or "搜索" in t:
                candidates.append((b, t, d))
    if candidates:
        b, t, d = candidates[0]
        ui.tap((b[0] + b[2]) // 2, (b[1] + b[3]) // 2, delay=1.0)
        ui.clear_and_input_text("百亿补贴")
        ui.press_enter()
        time.sleep(2.5)
        root = dump_retry(ui)
        # 点搜索结果里的百亿补贴频道/官方入口
        hits = ui.find_nodes(root, text_regex=r"百亿补贴")
        print("[nav] search hits", len(hits), [(h["text"], h["center"]) for h in hits[:8]])
        for h in hits:
            # 避开商品卡过低位置
            if h["center"][1] < 2200:
                ui.tap_node(h, delay=3.0)
                save_nodes(ui, "pdd_after_search_bybt")
                return True
    # 回退：点首页「百亿补贴」区块标题
    root = dump_retry(ui)
    hits = ui.find_nodes(root, text_regex=r"^百亿补贴$")
    if hits:
        ui.tap_node(sorted(hits, key=lambda z: z["center"][1])[0], delay=3.0)
        save_nodes(ui, "pdd_after_title_bybt")
        return True
    return False


def main() -> int:
    ui = AdbUIHelper(SERIAL)
    ui.unlock_and_wake()
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    if phase in ("gkd", "all"):
        gkd_disable_marsgao_pdd(ui)
    if phase in ("nav", "all"):
        open_pdd_home(ui)
        ok = navigate_bybt(ui)
        print("[nav] ok=", ok)
        root = dump_retry(ui)
        print(json.dumps(page_signals(ui, root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AdbError as e:
        print("FAIL", e)
        raise SystemExit(3)
