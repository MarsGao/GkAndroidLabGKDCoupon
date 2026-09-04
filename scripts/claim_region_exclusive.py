#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消费券会场：切换「地区专享」并逐个点击「立即领取」。

前置：已在拼多多「消费券」会场（可见双重补贴/地区专享）。
红线：不点去使用/抽福袋；若误进商品/国补弹窗则返回。

用法：
  python scripts/claim_region_exclusive.py
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import time

SERIAL_DEFAULT = os.environ.get("ANDROID_SERIAL", "3B159H003D600000")


def adb(serial: str, args: list[str]) -> str:
    r = subprocess.run(
        ["adb", "-s", serial, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    return (r.stdout or "") + (r.stderr or "")


def shell(serial: str, cmd: str) -> str:
    return adb(serial, ["shell", cmd])


def dump_ui(serial: str) -> str:
    t = ""
    for _ in range(5):
        shell(serial, "uiautomator dump /sdcard/region_claim.xml")
        time.sleep(0.4)
        t = shell(serial, "cat /sdcard/region_claim.xml")
        if "<hierarchy" in t and len(t) > 3000:
            return t
    return t


def find_text(xml: str, exact: str) -> list[dict]:
    hits: list[dict] = []
    for m in re.finditer(r"<node[^>]+>", xml):
        tag = m.group(0)
        tx_m = re.search(r'text="([^"]*)"', tag)
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
        tx = tx_m.group(1) if tx_m else ""
        if tx != exact or not b:
            continue
        a, y1, c, y2 = map(int, b.groups())
        w, h = c - a, y2 - y1
        if w < 60 or h < 20 or (w > 1400 and h > 2500):
            continue
        cx, cy = (a + c) // 2, (y1 + y2) // 2
        if cx < 90 or cx > 1350 or cy < 180 or cy > 3000:
            continue
        hits.append({"cx": cx, "cy": cy, "y1": y1, "w": w, "bounds": (a, y1, c, y2)})
    uniq: list[dict] = []
    for h in hits:
        if not any(abs(h["cx"] - u["cx"]) < 35 and abs(h["cy"] - u["cy"]) < 35 for u in uniq):
            uniq.append(h)
    return uniq


def is_trap(xml: str) -> bool:
    if "去用补贴" in xml or "逛逛别的" in xml:
        return True
    if "款式" in xml and "立即领取" not in xml and "地区专享" not in xml:
        return True
    return False


def escape_trap(serial: str) -> None:
    xml = dump_ui(serial)
    for h in find_text(xml, "逛逛别的"):
        shell(serial, f"input tap {h['cx']} {h['cy']}")
        time.sleep(0.8)
        return
    if is_trap(xml):
        shell(serial, "input keyevent KEYCODE_BACK")
        time.sleep(1.0)


def switch_region_tab(serial: str) -> bool:
    xml = dump_ui(serial)
    tabs = find_text(xml, "地区专享")
    if not tabs:
        print("[-] 未找到「地区专享」")
        return False
    # 消费券会场 Tab 通常在上半屏；多个时取 y 较小者
    top = sorted([t for t in tabs if t["y1"] < 1600], key=lambda t: t["y1"]) or sorted(
        tabs, key=lambda t: t["y1"]
    )
    t = top[0]
    # 点文字中心；若右侧有「送5折券」徽章，略偏右更稳
    tapx = min(t["cx"] + 40, t["bounds"][2] + 30, 1250)
    print(f"[+] 点击地区专享 {tapx},{t['cy']}")
    shell(serial, f"input tap {tapx} {t['cy']}")
    time.sleep(2.3)
    return True


def claim_visible(serial: str) -> int:
    xml = dump_ui(serial)
    claims = [
        c
        for c in find_text(xml, "立即领取")
        if 350 < c["cy"] < 2900 and c["w"] < 520
    ]
    claimed = 0
    for c in sorted(claims, key=lambda z: (z["cy"], z["cx"])):
        shell(serial, f"input tap {c['cx']} {c['cy']}")
        time.sleep(1.35)
        after = dump_ui(serial)
        if is_trap(after):
            print(f"  [!] 误进商品 {c['cx']},{c['cy']}，返回")
            escape_trap(serial)
            continue
        print(f"  [+] 领取 {c['cx']},{c['cy']}")
        claimed += 1
    return claimed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", default=SERIAL_DEFAULT)
    ap.add_argument("--skip-tab", action="store_true", help="已在地区专享时跳过切 Tab")
    args = ap.parse_args()
    serial = args.serial

    if serial not in adb(serial, ["devices"]):
        print("设备未在线")
        return 1

    escape_trap(serial)
    if not args.skip_tab:
        if not switch_region_tab(serial):
            return 2

    total = 0
    empty = 0
    for i in range(8):
        escape_trap(serial)
        n = claim_visible(serial)
        total += n
        print(f"round{i} +{n}")
        if n == 0:
            # 横滑券卡再试
            shell(serial, "input swipe 1200 1450 350 1450 380")
            time.sleep(0.9)
            n2 = claim_visible(serial)
            total += n2
            if n2 == 0:
                shell(serial, "input swipe 720 2300 720 1300 400")
                time.sleep(0.9)
                empty += 1
                if empty >= 2:
                    break
            else:
                empty = 0
        else:
            empty = 0

    xml = dump_ui(serial)
    left = find_text(xml, "立即领取")
    used = find_text(xml, "去使用")
    print(f"[done] claimed={total} remain_立即领取={len(left)} 去使用={len(used)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
