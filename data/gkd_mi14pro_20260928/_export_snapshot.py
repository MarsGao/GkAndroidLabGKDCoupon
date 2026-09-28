#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从已拉取的 mi14pro GKD 快照生成可对照恢复的 Markdown + JSON。"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[1]
TZ = timezone(timedelta(hours=8))


def load_sub_meta(path: Path) -> dict:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # json5-ish: strip // comments roughly
        lines = []
        for line in raw.splitlines():
            s = line.strip()
            if s.startswith("//"):
                continue
            lines.append(line)
        return json.loads("\n".join(lines))


def group_index(sub: dict) -> dict[tuple[str, int], dict]:
    """(appId|'', groupKey) -> {name, enable_default, category}"""
    idx: dict[tuple[str, int], dict] = {}
    for g in sub.get("globalGroups") or []:
        idx[("", int(g["key"]))] = {
            "name": g.get("name", ""),
            "enable_default": g.get("enable", True),
            "scope": "global",
        }
    for app in sub.get("apps") or []:
        app_id = app.get("id", "")
        for g in app.get("groups") or []:
            idx[(app_id, int(g["key"]))] = {
                "name": g.get("name", ""),
                "enable_default": g.get("enable", True),
                "scope": "app",
            }
    return idx


def category_index(sub: dict) -> dict[int, dict]:
    out = {}
    for c in sub.get("categories") or []:
        out[int(c["key"])] = {
            "name": c.get("name", ""),
            "enable_default": c.get("enable", True),
        }
    return out


def enable_label(v) -> str:
    if v is None:
        return "默认(跟随订阅)"
    return "开" if int(v) == 1 else "关"


def main() -> None:
    store = json.loads((OUT / "store.json").read_text(encoding="utf-8"))
    con = sqlite3.connect(str(OUT / "gkd.db"))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA wal_checkpoint(FULL)")
    cur = con.cursor()

    subs_items = [
        dict(r)
        for r in cur.execute(
            'SELECT * FROM subs_item ORDER BY "order", id'
        )
    ]
    subs_configs = [dict(r) for r in cur.execute("SELECT * FROM subs_config ORDER BY subs_id, app_id, group_key")]
    cat_configs = [dict(r) for r in cur.execute("SELECT * FROM category_config ORDER BY subs_id, category_key")]
    app_configs = [dict(r) for r in cur.execute("SELECT * FROM app_config ORDER BY subs_id, app_id")]
    con.close()

    sub_metas: dict[int, dict] = {}
    for item in subs_items:
        sid = int(item["id"])
        meta = load_sub_meta(OUT / "subscription" / f"{sid}.json")
        sub_metas[sid] = meta

    # device meta (filled by caller env file if present)
    device = {
        "serial": "4236fdb8",
        "model": "23116PN5BC",
        "device": "shennong",
        "brand": "Xiaomi",
        "alias": "mi14pro",
        "screen": "1440x3200",
        "gkd_version": "1.12.1",
        "pinduoduo_version": "8.26.0",
        "accessibility_services": "com.x8bit.bitwarden/.Accessibility.AccessibilityService",
        "gkd_a11y_component_expected": (
            "li.songe.gkd/com.google.android.accessibility.selecttospeak.SelectToSpeakService"
        ),
        "gkd_a11y_enabled": False,
        "captured_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "note": "只读快照；未修改手机 GKD 数据。供 OnePlus 13 对照恢复。",
    }

    snapshot = {
        "device": device,
        "store": store,
        "subscriptions": [],
        "subs_config_overrides": [],
        "category_config_overrides": [],
        "app_config_overrides": app_configs,
        "pinduoduo_focus": [],
    }

    md_lines: list[str] = []
    md_lines.append("# mi14pro GKD 配置快照")
    md_lines.append("")
    md_lines.append(f"- 抓取时间：`{device['captured_at']}`")
    md_lines.append(f"- 设备：{device['alias']} `{device['serial']}` · {device['model']}/{device['device']} · {device['screen']}")
    md_lines.append(f"- GKD `{device['gkd_version']}` · 拼多多 `{device['pinduoduo_version']}`")
    md_lines.append(f"- 系统无障碍：`{device['accessibility_services']}`")
    md_lines.append(f"- GKD 无障碍组件是否启用：**否**（当前仅 Bitwarden）")
    md_lines.append("- 来源：`/sdcard/Android/data/li.songe.gkd/files/` 只读拉取（store + db + subscription）")
    md_lines.append("- 用途：OnePlus 13 配置丢失后对照恢复；含已订阅但总开关关闭的条目")
    md_lines.append("")
    md_lines.append("## 全局 store（关键设置）")
    md_lines.append("")
    key_store = [
        ("enableMatch", "规则匹配"),
        ("enableStatusService", "状态栏/服务相关"),
        ("enableAutomator", "自动操作器"),
        ("toastWhenClick", "点击提示"),
        ("actionToast", "点击 Toast 文案"),
        ("updateSubsInterval", "订阅更新间隔(ms)"),
        ("httpServerPort", "HTTP 端口"),
        ("showDisabledRule", "显示已禁用规则"),
    ]
    md_lines.append("| 键 | 含义 | 值 |")
    md_lines.append("|---|---|---|")
    for k, label in key_store:
        md_lines.append(f"| `{k}` | {label} | `{store.get(k)}` |")
    md_lines.append("")
    md_lines.append(
        f"**结论**：全局规则匹配 `enableMatch={store.get('enableMatch')}`；"
        f"与无障碍关闭一致，当前不会自动点击。"
    )
    md_lines.append("")
    md_lines.append("## 订阅列表（含未启用）")
    md_lines.append("")
    md_lines.append("| 顺序 | id | 名称 | 版本 | 总开关 | 自动更新 | updateUrl |")
    md_lines.append("|---:|---:|---|---:|---|---|---|")

    for item in sorted(subs_items, key=lambda x: (x["order"], x["id"])):
        sid = int(item["id"])
        meta = sub_metas.get(sid) or {}
        name = meta.get("name") or ("本地订阅" if sid == -2 else f"id={sid}")
        version = meta.get("version")
        author = meta.get("author", "")
        entry = {
            "order": item["order"],
            "id": sid,
            "name": name,
            "author": author,
            "version": version,
            "enable": bool(item["enable"]),
            "enable_update": bool(item["enable_update"]),
            "update_url": item["update_url"],
            "ctime": item["ctime"],
            "mtime": item["mtime"],
        }
        snapshot["subscriptions"].append(entry)
        md_lines.append(
            f"| {item['order']} | `{sid}` | {name}"
            + (f" · {author}" if author else "")
            + f" | {version if version is not None else '-'} | "
            + ("**开**" if item["enable"] else "关")
            + " | "
            + ("开" if item["enable_update"] else "关")
            + f" | `{item['update_url'] or ''}` |"
        )

    md_lines.append("")
    md_lines.append("## 分类开关覆盖（category_config）")
    md_lines.append("")
    md_lines.append("| 订阅 | category_key | 名称 | 覆盖 |")
    md_lines.append("|---|---:|---|---|")
    for row in cat_configs:
        sid = int(row["subs_id"])
        meta = sub_metas.get(sid) or {}
        cats = category_index(meta)
        ckey = int(row["category_key"])
        cname = cats.get(ckey, {}).get("name", "")
        snapshot["category_config_overrides"].append(
            {
                "subs_id": sid,
                "category_key": ckey,
                "name": cname,
                "enable": row["enable"],
                "enable_label": enable_label(row["enable"]),
            }
        )
        md_lines.append(
            f"| `{sid}` {(meta.get('name') or '')} | {ckey} | {cname} | {enable_label(row['enable'])} |"
        )

    md_lines.append("")
    md_lines.append("## 规则组开关覆盖（subs_config）")
    md_lines.append("")
    md_lines.append(
        "说明：`enable=null` 表示未单独覆盖，跟随订阅默认；表中仍列出全部覆盖行（含排除 Activity）。"
    )
    md_lines.append("")
    md_lines.append("| 订阅 | type | app_id | group_key | 规则名 | 覆盖 | exclude |")
    md_lines.append("|---|---:|---|---:|---|---|---|")

    for row in subs_configs:
        sid = int(row["subs_id"])
        meta = sub_metas.get(sid) or {}
        gidx = group_index(meta)
        app_id = row["app_id"] or ""
        gkey = int(row["group_key"])
        ginfo = gidx.get((app_id, gkey)) or gidx.get(("", gkey)) or {}
        gname = ginfo.get("name", "")
        entry = {
            "subs_id": sid,
            "type": row["type"],
            "app_id": app_id,
            "group_key": gkey,
            "name": gname,
            "enable": row["enable"],
            "enable_label": enable_label(row["enable"]),
            "exclude": row["exclude"],
            "enable_default": ginfo.get("enable_default"),
        }
        snapshot["subs_config_overrides"].append(entry)
        if app_id == "com.xunmeng.pinduoduo" or "拼多多" in gname or "领券" in gname:
            snapshot["pinduoduo_focus"].append(entry)
        md_lines.append(
            f"| `{sid}` | {row['type']} | `{app_id or '(global)'}` | {gkey} | {gname} | "
            f"{enable_label(row['enable'])} | `{row['exclude'].replace(chr(10), ' / ') if row['exclude'] else ''}` |"
        )

    md_lines.append("")
    md_lines.append("## 拼多多相关（恢复时优先核对）")
    md_lines.append("")

    # MarsGao all groups from subscription + effective enable
    mars = sub_metas.get(82640113) or {}
    mars_groups = group_index(mars)
    mars_overrides = {
        (r["app_id"] or "", int(r["group_key"])): r["enable"]
        for r in subs_configs
        if int(r["subs_id"]) == 82640113
    }
    md_lines.append("### 本仓订阅 `82640113` MarsGao薅羊毛领券")
    md_lines.append("")
    mars_item = next((s for s in snapshot["subscriptions"] if s["id"] == 82640113), None)
    if mars_item:
        md_lines.append(
            f"- 总开关：{'**开**' if mars_item['enable'] else '关'} · 版本 v{mars_item['version']} · "
            f"updateUrl `{mars_item['update_url']}`"
        )
    md_lines.append("")
    md_lines.append("| group_key | 名称 | 订阅默认 | 手机覆盖 | 有效推测 |")
    md_lines.append("|---:|---|---|---|---|")
    for (app_id, gkey), info in sorted(mars_groups.items(), key=lambda x: x[0][1]):
        ov = mars_overrides.get((app_id, gkey), mars_overrides.get(("", gkey)))
        default = info["enable_default"]
        if ov is None:
            effective = default
            ov_label = "无覆盖"
        else:
            effective = bool(int(ov))
            ov_label = enable_label(ov)
        md_lines.append(
            f"| {gkey} | {info['name']} | {'开' if default else '关'} | {ov_label} | "
            f"{'开' if effective else '关'} |"
        )
        snapshot["pinduoduo_focus"].append(
            {
                "subs_id": 82640113,
                "app_id": app_id or "com.xunmeng.pinduoduo",
                "group_key": gkey,
                "name": info["name"],
                "enable_default": default,
                "override": ov,
                "effective": effective,
            }
        )

    md_lines.append("")
    md_lines.append("### 第三方订阅中拼多多 group 覆盖")
    md_lines.append("")
    md_lines.append("| 订阅 | group_key | 规则名 | 覆盖 |")
    md_lines.append("|---|---:|---|---|")
    for row in snapshot["subs_config_overrides"]:
        if row["app_id"] == "com.xunmeng.pinduoduo" and row["subs_id"] != 82640113:
            md_lines.append(
                f"| `{row['subs_id']}` | {row['group_key']} | {row['name']} | {row['enable_label']} |"
            )

    md_lines.append("")
    md_lines.append("## OnePlus 13 恢复清单（稍后执行）")
    md_lines.append("")
    md_lines.append("1. 安装 GKD 1.12.1（或同主版本），打开无障碍前先按目标模式决定是否启用。")
    md_lines.append("2. 按上表顺序添加订阅（含总开关为关的 AIsouler `666` 与本地 `-2`）。")
    md_lines.append("3. 导入/更新本仓 `82640113` 到相同 version；updateUrl 可改为本机发布地址或文件导入。")
    md_lines.append("4. 对照 `subs_config` / `category_config` 逐项设置开关与 exclude。")
    md_lines.append("5. 将 `store.json` 关键项对齐（至少 `enableMatch` / Toast / 更新间隔）。")
    md_lines.append("6. 回读：订阅列表 UI + 再拉一次 db/store 核对，不得假设点击即成功。")
    md_lines.append("")
    md_lines.append("## 原始文件")
    md_lines.append("")
    md_lines.append("目录：`data/gkd_mi14pro_20260928/`")
    md_lines.append("")
    md_lines.append("| 文件 | 说明 | 是否建议入库 |")
    md_lines.append("|---|---|---|")
    md_lines.append("| `SNAPSHOT.md` | 本说明 | 是 |")
    md_lines.append("| `snapshot.json` | 机读摘要 | 是 |")
    md_lines.append("| `store.json` | 全局设置原样 | 是 |")
    md_lines.append("| `subs_item.json` 等导出 | 表导出 | 是 |")
    md_lines.append("| `gkd.db*` | SQLite 原库 | 否（体积/日志） |")
    md_lines.append("| `subscription/*.json` | 订阅正文缓存 | 否（可从源更新；本仓权威仍是 `dist/gkd.json5`） |")
    md_lines.append("")

    (OUT / "SNAPSHOT.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    (OUT / "snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "subs_item.json").write_text(
        json.dumps(subs_items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "subs_config.json").write_text(
        json.dumps(subs_configs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "category_config.json").write_text(
        json.dumps(cat_configs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("Wrote", OUT / "SNAPSHOT.md")
    print("subs", len(subs_items), "subs_config", len(subs_configs), "category", len(cat_configs))


if __name__ == "__main__":
    main()
