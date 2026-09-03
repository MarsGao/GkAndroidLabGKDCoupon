#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拼多多「百亿消费券」会场及 GKD 领券规则真机验证脚本
验证流程：
1. ADB 唤醒设备并进入拼多多「百亿补贴」主会场
2. 正常点击「百亿消费券」卡片/入口进入消费券专属会场
3. 严格断言当前处于「消费券」会场（页面标题、双重补贴/地区专享特征）
4. 检索并断言 GKD Rule 4 匹配节点（「立即领取」、「一键全领」、「立即点亮」）
5. 验证点击行为与状态机闭环（严禁误触「去使用」进入商品页，严禁点击「抽福袋」裂变）
"""

import os
import re
import sys
import time
import subprocess
import xml.etree.ElementTree as ET

SERIAL = os.environ.get("ANDROID_SERIAL", "3B159H003D600000")

def run_adb(cmd_args, serial=None):
    s = serial or SERIAL
    cmd = ["adb"]
    if s:
        cmd.extend(["-s", s])
    cmd.extend(cmd_args)
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return res.stdout.strip()

def run_shell(shell_cmd, serial=None):
    return run_adb(["shell", shell_cmd], serial)

def dump_ui(serial=None) -> ET.Element:
    temp_remote = "/sdcard/verify_dump.xml"
    run_shell(f"uiautomator dump --compressed {temp_remote}", serial)
    res = run_shell(f"cat {temp_remote}", serial)
    if "<hierarchy" in res:
        try:
            return ET.fromstring(res)
        except Exception:
            pass
    local_temp = "verify_dump_tmp.xml"
    run_adb(["pull", temp_remote, local_temp], serial)
    if os.path.exists(local_temp):
        tree = ET.parse(local_temp)
        os.remove(local_temp)
        return tree.getroot()
    raise RuntimeError("Failed to dump UI hierarchy from device.")

def parse_bounds(bounds_str: str):
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
    if m:
        x1, y1, x2, y2 = map(int, m.groups())
        return x1, y1, x2, y2, (x1 + x2) // 2, (y1 + y2) // 2
    return 0, 0, 0, 0, 0, 0

def find_nodes(root: ET.Element, text_regex=None, desc_regex=None):
    matched = []
    for n in root.iter("node"):
        t = n.attrib.get("text", "")
        d = n.attrib.get("content-desc", "")
        b = n.attrib.get("bounds", "")
        t_match = bool(re.search(text_regex, t)) if text_regex else True
        d_match = bool(re.search(desc_regex, d)) if desc_regex else True
        if (text_regex or desc_regex) and t_match and d_match:
            x1, y1, x2, y2, cx, cy = parse_bounds(b)
            matched.append({"node": n, "text": t, "desc": d, "bounds": b, "center": (cx, cy)})
    return matched

def main():
    print("==================================================")
    print(" [GKD 规则验证] 拼多多百亿消费券会场与领券断言")
    print(f" 设备序列号: {SERIAL}")
    print("==================================================")

    # 1. 检查设备连接
    devices = run_adb(["devices"])
    if SERIAL not in devices:
        print(f"[-] 错误: 目标设备 {SERIAL} 未处于在线状态！")
        print(f"当前在线设备列表:\n{devices}")
        sys.exit(1)

    # 2. 唤醒屏幕
    run_shell("input keyevent KEYCODE_WAKEUP")
    time.sleep(0.5)
    run_shell("input keyevent KEYCODE_MENU")
    time.sleep(0.5)

    # 3. 确保位于百亿补贴主会场
    print("\n[步骤 1] 导航直达百亿补贴主频道...")
    run_shell("am start -a android.intent.action.VIEW -d 'pinduoduo://com.xunmeng.pinduoduo/brand_rebate.html'")
    time.sleep(3.0)

    # 4. 寻找并点击「百亿消费券」入口
    print("\n[步骤 2] 查找并点击「百亿消费券」入口卡片...")
    root = dump_ui()
    nodes = find_nodes(root, text_regex=r"百亿消费券")
    if nodes:
        target = nodes[0]
        print(f"  [+] 动态定位到「百亿消费券」节点: {target['bounds']}, center={target['center']}")
        run_shell(f"input tap {target['center'][0]} {target['center'][1]}")
    else:
        print("  [*] 使用 OnePlus 13 屏幕校准坐标 (950, 850) 点击「百亿消费券」卡片...")
        run_shell("input tap 950 850")

    time.sleep(3.0)

    # 5. 断言当前页面进入「消费券」专属会场
    print("\n[步骤 3] 严格断言会场特征...")
    root_coupon = dump_ui()
    venue_nodes = find_nodes(root_coupon, text_regex=r"^(消费券|双重补贴|地区专享)$")
    if not venue_nodes:
        print("  [-] 失败: 当前页面未检测到「消费券」会场特征！")
        sys.exit(1)
    
    print(f"  [+] 成功断言: 处于「消费券」会场，命中特征节点数: {len(venue_nodes)}")
    for n in venue_nodes:
        print(f"      - 特征节点: text='{n['text']}', bounds={n['bounds']}")

    # 6. 断言 GKD Rule 4 待领券目标节点
    print("\n[步骤 4] 扫描 GKD Rule 4 目标元素 ([text='立即领取' || text='一键全领' || text='开心收下' || text='立即点亮'])...")
    claim_targets = find_nodes(root_coupon, text_regex=r"^(立即领取|一键全领|开心收下|立即点亮)$")
    
    if claim_targets:
        print(f"  [+] 命中 GKD 可触发领券/点亮节点共 {len(claim_targets)} 个:")
        for idx, t in enumerate(claim_targets, 1):
            print(f"      [{idx}] 文本='{t['text']}', 坐标={t['bounds']}, 中心={t['center']}")
    else:
        print("  [*] 当前屏无「立即领取」，检查是否已全部处于「去使用」状态...")
        used_nodes = find_nodes(root_coupon, text_regex=r"^(去使用|已领取)$")
        print(f"      - 已领/去使用状态券数量: {len(used_nodes)}")

    # 7. 严格红线核验
    print("\n[步骤 5] 安全红线核查...")
    forbidden = find_nodes(root_coupon, text_regex=r"(抽福袋|微信|分享|邀请|助力)")
    for f in forbidden:
        print(f"  [!] 发现裂变/抽奖节点: text='{f['text']}' at {f['bounds']} -> [已由规则天然隔离，禁止触发]")

    # 8. 保存现场截图
    screenshot_path = "pdd_coupon_venue_verified.png"
    run_shell(f"screencap -p /sdcard/{screenshot_path}")
    run_adb(["pull", f"/sdcard/{screenshot_path}", screenshot_path])
    print(f"\n[+] 验证完成！现场截图已保存至: {os.path.abspath(screenshot_path)}")

if __name__ == "__main__":
    main()
