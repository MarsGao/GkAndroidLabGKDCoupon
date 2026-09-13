#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""关闭当前 GKD 拼多多规则组全部开关（脚本任务模式）。"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, r"C:\GkDesktop\GitProjects\GkAndroidLab\scripts\ecommerce")
from adb_ui_helper import AdbUIHelper  # noqa: E402

DATA = ROOT / "data"
SERIAL = "3B159H003D600000"


def main() -> int:
    ui = AdbUIHelper(SERIAL)
    root = ui.dump_ui()
    # 右侧开关：class 含 Switch 或 checked=true 且宽度较小的可点区域
    switches = []
    for n in root.iter("node"):
        cls = n.attrib.get("class", "")
        checked = n.attrib.get("checked")
        clickable = n.attrib.get("clickable")
        b = ui.parse_bounds(n.attrib.get("bounds", ""))
        if not b:
            continue
        x1, y1, x2, y2 = b
        w, h = x2 - x1, y2 - y1
        if x1 < 1100:
            continue
        if "Switch" in cls or (checked == "true" and clickable == "true" and 80 < w < 280 and 80 < h < 220):
            switches.append((y1, (x1 + x2) // 2, (y1 + y2) // 2, checked, cls))
    # 去重：按 y 聚类
    switches.sort()
    uniq = []
    for s in switches:
        if not uniq or abs(s[0] - uniq[-1][0]) > 40:
            uniq.append(s)
    print("switches found", len(uniq), uniq)
    for y1, cx, cy, checked, cls in uniq:
        if checked == "true" or "Switch" in cls:
            print(f"tap off {cx},{cy}")
            ui.tap(cx, cy, delay=0.6)
    time.sleep(0.5)
    root = ui.dump_ui()
    still_on = 0
    for n in root.iter("node"):
        if n.attrib.get("checked") == "true":
            b = ui.parse_bounds(n.attrib.get("bounds", ""))
            if b and b[0] > 1100:
                still_on += 1
    print("still_on_right_checked", still_on)
    lines = []
    for n in root.iter("node"):
        t = n.attrib.get("text", "")
        if t.startswith("领券") or t.startswith("弹窗"):
            lines.append(t)
    (DATA / "gkd_rules_after_off.tsv").write_text("\n".join(lines), encoding="utf-8")
    ui.run_shell("screencap -p /sdcard/gkd_rules_off.png")
    ui.run_cmd(["pull", "/sdcard/gkd_rules_off.png", str((DATA / "gkd_rules_off.png").resolve())])
    return 0 if still_on == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
