#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

p = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\GkDesktop\GitProjects\GkAndroidLabGKDCoupon\data\subsidy_probe.xml")
t = p.read_text(encoding="utf-8", errors="ignore")
print("len", len(t), "hierarchy", "<hierarchy" in t)
texts = re.findall(r'text="([^"]*)"', t)
descs = re.findall(r'content-desc="([^"]*)"', t)
keys = ["百亿", "消费券", "待领", "会员", "打卡", "双重", "地区", "领取", "点亮", "补贴", "券"]
print("=== matching texts ===")
for tx in texts:
    if any(k in tx for k in keys):
        print("TEXT:", tx[:100])
print("=== matching descs ===")
for d in descs:
    if d and any(k in d for k in keys):
        print("DESC:", d[:100])
print("node_count", t.count("<node"))
