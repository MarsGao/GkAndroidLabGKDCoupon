#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进入拼多多「百亿消费券」会场（ADB 坐标/红标题条定位）。

原因：百亿补贴主会场 H5 横滑卡在多数机型上无障碍树几乎为空，
GKD 文本规则无法匹配「百亿消费券 …待领」。进会场后节点正常，
由 GKD 规则 key5 自动点「立即领取」。

用法（需已停在百亿补贴主会场，或本脚本会尝试 deeplink）：
  python scripts/enter_coupon_venue.py
  python scripts/enter_coupon_venue.py --serial 3B159H003D600000
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from collections import Counter

SERIAL_DEFAULT = os.environ.get("ANDROID_SERIAL", "3B159H003D600000")


def adb(serial: str, args: list[str]) -> str:
    cmd = ["adb", "-s", serial, *args]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return (r.stdout or "") + (r.stderr or "")


def shell(serial: str, cmd: str) -> str:
    return adb(serial, ["shell", cmd])


def screencap_local(serial: str, local_path: str) -> None:
    shell(serial, "screencap -p /sdcard/enter_coupon.png")
    adb(serial, ["pull", "/sdcard/enter_coupon.png", local_path])


def find_red_header_tap(png_path: str) -> tuple[int, int] | None:
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return None
    im = Image.open(png_path).convert("RGB")
    arr = __import__("numpy").array(im)
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    mask = (r > 160) & (g < 90) & (b < 100) & (r > g + 60)
    ys, xs = __import__("numpy").where(mask)
    sel = (ys > 750) & (ys < 950)
    ys, xs = ys[sel], xs[sel]
    if len(xs) < 50:
        return None
    ym = Counter(ys.tolist()).most_common(1)[0][0]
    row = sorted(xs[abs(ys - ym) < 5].tolist())
    if len(row) < 30:
        return None
    # 「百亿消费券」四字在红条左侧；点文字即可进场，勿点右侧商品图/下方抽福袋
    tapx = row[0] + int((row[-1] - row[0]) * 0.22)
    tapy = ym + 8
    return tapx, tapy


def dump_has_venue(serial: str) -> bool:
    shell(serial, "uiautomator dump /sdcard/enter_coupon.xml")
    time.sleep(0.5)
    out = shell(serial, "cat /sdcard/enter_coupon.xml")
    return any(k in out for k in ("双重补贴", "地区专享", "立即领取", ">消费券<"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", default=SERIAL_DEFAULT)
    ap.add_argument("--open-subsidy", action="store_true", help="先 deeplink 打开百亿补贴（可能加载失败）")
    ap.add_argument("--fallback-xy", default="603,777", help="图像定位失败时的兜底坐标（百亿消费券文字）")
    args = ap.parse_args()
    serial = args.serial

    devices = adb(serial, ["devices"])
    if serial not in devices or "device" not in devices:
        print(f"设备未在线: {serial}\n{devices}")
        return 1

    if args.open_subsidy:
        shell(serial, "am start -a android.intent.action.VIEW -d 'pinduoduo://com.xunmeng.pinduoduo/brand_rebate.html'")
        time.sleep(5)

    local = os.path.join(os.path.dirname(__file__), "..", "pdd_enter_probe.png")
    local = os.path.abspath(local)
    screencap_local(serial, local)
    xy = find_red_header_tap(local)
    if xy is None:
        fx, fy = map(int, args.fallback_xy.split(","))
        xy = (fx, fy)
        print(f"[!] 红标题条未识别，使用兜底坐标 {xy}")
    else:
        print(f"[+] 红标题条定位 tap={xy}")

    # 避开微信通知：先轻点空白
    shell(serial, "input tap 720 500")
    time.sleep(0.3)
    shell(serial, f"input tap {xy[0]} {xy[1]}")
    time.sleep(3.0)

    if dump_has_venue(serial):
        print("[+] 已进入消费券会场（检测到双重补贴/立即领取等）。请保持页面，让 GKD 规则5自动点领取。")
        return 0

    print("[-] 未检测到会场特征。请确认当前在百亿补贴主会场且「百亿消费券」红卡可见后重试。")
    return 2


if __name__ == "__main__":
    sys.exit(main())
