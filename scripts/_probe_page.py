#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""页面探针：打印会场相关信号与关键节点 bounds。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pdd_common import make_helper, page_signals  # noqa: E402

KEYS = ("立即领取", "立即点亮", "解锁点亮", "地区专享", "双重补贴", "消费券", "去使用", "今日已点亮", "百亿")


def main() -> int:
    serial = os.environ.get("ANDROID_SERIAL") or sys.argv[1] if len(sys.argv) > 1 else None
    ui = make_helper(serial)
    root = ui.dump_ui(require_nodes=True)
    print(json.dumps(page_signals(ui, root), ensure_ascii=False, indent=2))
    for n in root.iter("node"):
        t = n.attrib.get("text", "")
        if any(k in t for k in KEYS):
            print(f"{t}\t{n.attrib.get('bounds')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
