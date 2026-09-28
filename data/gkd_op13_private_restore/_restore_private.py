#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 mi14pro GKD 快照写入目标机私有目录（需 root / KernelSU）。

依赖：data/gkd_mi14pro_20260928/{subs_item,category_config,subs_config,store}.json
订阅正文需现场从发布源或本仓 dist 准备到 WORK/subscription/，或由调用方 push。
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MI = REPO / "data" / "gkd_mi14pro_20260928"
WORK = Path(__file__).resolve().parent
SERIAL_DEFAULT = "3B159H003D600000"
PKG = "li.songe.gkd"
PRIV = f"/data/data/{PKG}/files"
SD_STAGING = "/sdcard/Download/gkd_restore_stage"
APP_UID = "u0_a444"  # OnePlus 13 现场；其他机请 dumpsys package 核对

SCHEMA = """
CREATE TABLE IF NOT EXISTS subs_item (
  id INTEGER NOT NULL PRIMARY KEY,
  ctime INTEGER NOT NULL,
  mtime INTEGER NOT NULL,
  enable INTEGER NOT NULL,
  enable_update INTEGER NOT NULL,
  "order" INTEGER NOT NULL,
  update_url TEXT
);
CREATE TABLE IF NOT EXISTS category_config (
  id INTEGER NOT NULL PRIMARY KEY,
  enable INTEGER,
  subs_id INTEGER NOT NULL,
  category_key INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS subs_config (
  id INTEGER NOT NULL PRIMARY KEY,
  type INTEGER NOT NULL,
  enable INTEGER,
  subs_id INTEGER NOT NULL,
  app_id TEXT NOT NULL,
  group_key INTEGER NOT NULL,
  exclude TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS app_config (
  id INTEGER NOT NULL PRIMARY KEY,
  enable INTEGER NOT NULL,
  subs_id INTEGER NOT NULL,
  app_id TEXT NOT NULL
);
"""


def adb(serial: str, *args: str, check: bool = True) -> str:
    r = subprocess.run(
        ["adb", "-s", serial, *args], capture_output=True, text=True, timeout=120
    )
    if check and r.returncode != 0:
        raise RuntimeError(f"adb {args} failed\n{r.stderr or r.stdout}")
    return r.stdout


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_db() -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    dst = WORK / "gkd.db"
    if dst.exists():
        dst.unlink()
    con = sqlite3.connect(str(dst))
    con.executescript(SCHEMA)
    cur = con.cursor()

    items = load_json(MI / "subs_item.json")
    for it in items:
        if it["id"] == 82640113:
            it["update_url"] = (
                "https://raw.githubusercontent.com/MarsGao/GkAndroidLabGKDCoupon/"
                "main/dist/gkd.json5"
            )
    cats = load_json(MI / "category_config.json")
    cfgs = load_json(MI / "subs_config.json")

    for it in items:
        cur.execute(
            'INSERT INTO subs_item (id, ctime, mtime, enable, enable_update, "order", update_url) '
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                it["id"],
                it["ctime"],
                it["mtime"],
                it["enable"],
                it["enable_update"],
                it["order"],
                it["update_url"],
            ),
        )
    for row in cats:
        cur.execute(
            "INSERT INTO category_config (id, enable, subs_id, category_key) VALUES (?, ?, ?, ?)",
            (row["id"], row["enable"], row["subs_id"], row["category_key"]),
        )
    for row in cfgs:
        cur.execute(
            "INSERT INTO subs_config (id, type, enable, subs_id, app_id, group_key, exclude) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                row["id"],
                row["type"],
                row["enable"],
                row["subs_id"],
                row["app_id"],
                row["group_key"],
                row["exclude"],
            ),
        )
    con.commit()
    con.close()

    store = load_json(MI / "store.json")
    (WORK / "store.json").write_text(
        json.dumps(store, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    return dst


def push_private(serial: str, app_uid: str) -> None:
    adb(serial, "shell", "am", "force-stop", PKG)
    adb(serial, "shell", f"rm -rf {SD_STAGING}; mkdir -p {SD_STAGING}/subscription")
    adb(serial, "push", str(WORK / "gkd.db"), f"{SD_STAGING}/gkd.db")
    adb(serial, "push", str(WORK / "store.json"), f"{SD_STAGING}/store.json")
    sub_dir = WORK / "subscription"
    if sub_dir.is_dir():
        for f in sub_dir.glob("*.json"):
            adb(serial, "push", str(f), f"{SD_STAGING}/subscription/{f.name}")
    adb(serial, "push", str(WORK / "install_private.sh"), f"{SD_STAGING}/install_private.sh")
    # install_private.sh 内 UID 可能需改；此处用 sed 注入
    adb(
        serial,
        "shell",
        "su",
        "-c",
        f"sed -i 's/^APP_UID=.*/APP_UID={app_uid}/' {SD_STAGING}/install_private.sh; "
        f"sh {SD_STAGING}/install_private.sh",
    )


def verify_ui(serial: str) -> None:
    import xml.etree.ElementTree as ET

    adb(serial, "shell", "am", "start", "-n", f"{PKG}/.MainActivity")
    time.sleep(2.5)
    adb(serial, "shell", "input", "tap", "540", "3050")
    time.sleep(1.5)
    adb(serial, "shell", "uiautomator", "dump", "/sdcard/gkd_op13_ui.xml")
    local = WORK / "ui_verify.xml"
    adb(serial, "pull", "/sdcard/gkd_op13_ui.xml", str(local))
    root = ET.parse(local).getroot()
    print("=== UI verify ===")
    for n in root.iter("node"):
        t = n.attrib.get("text") or ""
        d = n.attrib.get("content-desc") or ""
        if any(
            k in (t + d)
            for k in ["MarsGao", "AIsouler", "奥怪", "本地", "规则匹配", "v406", "v89", "v7"]
        ):
            print(repr(t), "|", repr(d))


def main() -> int:
    serial = sys.argv[1] if len(sys.argv) > 1 else SERIAL_DEFAULT
    app_uid = sys.argv[2] if len(sys.argv) > 2 else APP_UID
    build_db()
    con = sqlite3.connect(str(WORK / "gkd.db"))
    print(
        "work subs",
        list(con.execute('SELECT id, enable, "order" FROM subs_item ORDER BY "order"')),
    )
    print(
        "work cat/cfg",
        con.execute("SELECT COUNT(*) FROM category_config").fetchone()[0],
        con.execute("SELECT COUNT(*) FROM subs_config").fetchone()[0],
    )
    con.close()
    if "--build-only" in sys.argv:
        return 0
    push_private(serial, app_uid)
    verify_ui(serial)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
