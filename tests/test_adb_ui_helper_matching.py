#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线回归：helper 精确匹配 + dismiss 安全 + gkd version 一致（不连设备）。"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAB_HELPER = Path(r"C:\GkDesktop\GitProjects\GkAndroidLab\scripts\ecommerce")
sys.path.insert(0, str(LAB_HELPER))

from adb_ui_helper import AdbUIHelper, SAFE_DISMISS_TEXT  # noqa: E402


def _tree(text: str = "", desc: str = "") -> ET.Element:
    root = ET.Element("hierarchy")
    ET.SubElement(
        root,
        "node",
        {
            "text": text,
            "content-desc": desc,
            "resource-id": "",
            "bounds": "[100,200][300,400]",
            "clickable": "true",
        },
    )
    return root


@pytest.fixture
def helper() -> AdbUIHelper:
    h = object.__new__(AdbUIHelper)
    h.screen_width = 1440
    h.screen_height = 3168
    return h


def test_exact_text_match_not_joined_with_desc(helper: AdbUIHelper):
    root = _tree(text="打卡", desc="")
    assert len(helper.find_nodes(root, text_regex=r"^打卡$")) == 1
    assert len(helper.find_nodes(root, text_regex=r"打卡")) == 1


def test_desc_field_separate(helper: AdbUIHelper):
    root = _tree(text="", desc="打卡")
    assert len(helper.find_nodes(root, desc_regex=r"^打卡$")) == 1
    assert len(helper.find_nodes(root, text_regex=r"^打卡$")) == 0


def test_checkin_title_not_exact(helper: AdbUIHelper):
    root = _tree(text="打卡送积分", desc="")
    assert len(helper.find_nodes(root, text_regex=r"^打卡$")) == 0


def test_dismiss_safe_patterns():
    assert "去使用" not in SAFE_DISMISS_TEXT
    assert "继续" not in SAFE_DISMISS_TEXT
    # 开心收下仅作关弹窗，不作领取
    assert re.search(r"开心收下", SAFE_DISMISS_TEXT)
    assert re.search(r"残忍拒绝", SAFE_DISMISS_TEXT)


def test_gkd_version_aligned():
    raw = (ROOT / "dist" / "gkd.json5").read_text(encoding="utf-8")
    ver_file = (ROOT / "dist" / "gkd.version.json5").read_text(encoding="utf-8")
    m = re.search(r"version:\s*(\d+)", raw)
    m2 = re.search(r"version:\s*(\d+)", ver_file)
    assert m and m2
    assert m.group(1) == m2.group(1)
    assert int(m.group(1)) >= 7


def test_gkd_unverified_keys_disabled():
    raw = (ROOT / "dist" / "gkd.json5").read_text(encoding="utf-8")
    # key 4/5/6/7 遗留或未经验证入口默认关；key8 为有序流水线默认开
    for key in (4, 5, 6, 7):
        block = re.search(
            rf"key:\s*{key},.*?enable:\s*(true|false)",
            raw,
            re.S,
        )
        assert block, f"missing key {key}"
        assert block.group(1) == "false", f"key {key} should be disabled by default"
    key8 = re.search(r"key:\s*8,.*?enable:\s*(true|false)", raw, re.S)
    assert key8 and key8.group(1) == "true"
    assert "excludeMatches" in raw
    assert 'text="立即领取"' in raw


def test_gkd_no_fuzzy_yuan_quan_in_key5():
    raw = (ROOT / "dist" / "gkd.json5").read_text(encoding="utf-8")
    # key5 规则 matches 不应再含模糊兜底或通用收下
    key5 = re.search(r"key:\s*5,.*?key:\s*6,", raw, re.S)
    assert key5
    body = key5.group(0)
    assert 'text*="共"' not in body
    assert 'text*="元券"' not in body
    rules = re.search(r"rules:\s*\[(.*)", body, re.S)
    assert rules
    assert "开心收下" not in rules.group(1)
    assert "一键全领" not in rules.group(1)


def test_claim_candidates_skip_zero_bounds():
    sys.path.insert(0, str(ROOT / "scripts"))
    import claim_region_exclusive as region  # noqa: WPS433

    h = object.__new__(AdbUIHelper)
    h.screen_width = 1440
    h.screen_height = 3168
    root = ET.Element("hierarchy")
    for bounds in ("[0,0][0,0]", "[73,1376][437,1478]", "[1421,1376][1440,1478]"):
        ET.SubElement(
            root,
            "node",
            {
                "text": "立即领取",
                "content-desc": "",
                "resource-id": "",
                "bounds": bounds,
                "clickable": "true",
            },
        )
    cands = region._claim_candidates(h, root)
    assert len(cands) == 1
    assert cands[0]["bounds"] == (73, 1376, 437, 1478)
