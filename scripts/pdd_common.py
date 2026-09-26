#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拼多多领券脚本公共：结果枚举、Lab helper 导入、页面识别。"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

LAB_ECOMMERCE = Path(r"C:\GkDesktop\GitProjects\GkAndroidLab\scripts\ecommerce")
if str(LAB_ECOMMERCE) not in sys.path:
    sys.path.insert(0, str(LAB_ECOMMERCE))

from adb_ui_helper import AdbError, AdbUIHelper  # noqa: E402

PDD_PKG = "com.xunmeng.pinduoduo"
SERIAL_DEFAULT = os.environ.get("ANDROID_SERIAL") or None
REPO_ROOT = Path(__file__).resolve().parents[1]

# 与 AGENTS.md / 审核 Plan 一致
RESULT_VALUES = (
    "verified",
    "already_claimed",
    "unavailable",
    "failed",
    "needs_review",
)


class StepResult(str, Enum):
    VERIFIED = "verified"
    ALREADY_CLAIMED = "already_claimed"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


@dataclass
class ActionRecord:
    step: str
    result: StepResult
    detail: str = ""
    evidence_before: str = ""
    evidence_after: str = ""


@dataclass
class TaskReport:
    mode: str
    serial: str
    records: list[ActionRecord] = field(default_factory=list)

    def add(self, step: str, result: StepResult, detail: str = "", before: str = "", after: str = "") -> None:
        self.records.append(
            ActionRecord(
                step=step,
                result=result,
                detail=detail,
                evidence_before=before,
                evidence_after=after,
            )
        )

    def summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {k: 0 for k in RESULT_VALUES}
        for r in self.records:
            counts[r.result.value] = counts.get(r.result.value, 0) + 1
        return {
            "mode": self.mode,
            "serial": self.serial,
            "counts": counts,
            "records": [
                {
                    "step": r.step,
                    "result": r.result.value,
                    "detail": r.detail,
                    "evidence_before": r.evidence_before,
                    "evidence_after": r.evidence_after,
                }
                for r in self.records
            ],
        }

    def exit_code(self) -> int:
        """Do not let review-required or failed steps look like task success."""
        results = {record.result for record in self.records}
        if StepResult.FAILED in results:
            return 1
        if StepResult.NEEDS_REVIEW in results:
            return 2
        return 0


def make_helper(serial: Optional[str] = None) -> AdbUIHelper:
    return AdbUIHelper(serial=serial or SERIAL_DEFAULT)


def texts_on_screen(ui: AdbUIHelper, root=None) -> list[str]:
    if root is None:
        root = ui.dump_ui()
    out: list[str] = []
    for n in root.iter("node"):
        t = n.attrib.get("text", "")
        if t:
            out.append(t)
    return out


def page_signals(ui: AdbUIHelper, root=None) -> dict[str, bool]:
    """组合特征，不用 Activity 名区分业务页。"""
    if root is None:
        root = ui.dump_ui()
    joined = "\n".join(texts_on_screen(ui, root))
    return {
        "pdd_foreground": ui.foreground_package() == PDD_PKG,
        "member": any(k in joined for k in ("打卡送积分", "百亿补贴会员", "等级礼包", "无门槛券")),
        "checkin_available": bool(ui.find_nodes(root, text_regex=r"^打卡$")),
        "checkin_done_hint": any(k in joined for k in ("已打卡", "今日已签到", "签到成功")),
        "venue": any(k in joined for k in ("双重补贴", "地区专享")) and ("消费券" in joined or "立即领取" in joined or "去使用" in joined),
        "dual_tab": "双重补贴" in joined,
        "region_tab": "地区专享" in joined,
        "claimable": bool(ui.find_nodes(root, text_regex=r"^立即领取$")),
        "go_use": bool(ui.find_nodes(root, text_regex=r"^去使用$")),
        "light_available": bool(
            ui.find_nodes(root, text_regex=r"^(立即点亮|解锁点亮)$")
        ),
        "light_done": "今日已点亮" in joined or "已点亮" in joined,
        "product_trap": ("去用补贴" in joined or "逛逛别的" in joined)
        or ("款式" in joined and "立即领取" not in joined and "地区专享" not in joined),
        "share_trap": any(k in joined for k in ("抽福袋", "微信", "邀请好友", "助力")),
    }


def assert_script_mode_preflight(ui: AdbUIHelper, confirm_gkd_off: bool = False) -> None:
    """脚本任务模式硬闸：前台拼多多 + 显式确认已停用重叠 GKD 点击规则。"""
    pkg = ui.foreground_package()
    if pkg and pkg != PDD_PKG:
        raise AdbError(f"前台包名不是拼多多: {pkg}")
    env_ok = os.environ.get("PDD_CONFIRM_GKD_OFF", "").strip() in ("1", "true", "yes")
    if not (confirm_gkd_off or env_ok):
        raise AdbError(
            "脚本模式拒绝执行：请先停用本订阅全部拼多多自动点击规则及第三方订阅中所有重叠规则，"
            "并传入 --confirm-gkd-off（或环境变量 PDD_CONFIRM_GKD_OFF=1）。"
            "无法通过 API 核验 GKD 开关；PC 锁不能证明互斥。"
        )
    print(
        "[preflight] 已确认 GKD 重叠点击规则停用；脚本模式请关闭本订阅全部拼多多自动点击规则及第三方重叠规则；"
        "订阅版本和无障碍状态将由只读预检核对。"
    )


def read_project_subscription(ui: AdbUIHelper) -> dict[str, Any]:
    """Read the public GKD subscription files without touching its database."""
    try:
        names = ui.run_shell(
            "ls -1 /sdcard/Android/data/li.songe.gkd/files/subscription"
        ).splitlines()
        for name in names:
            name = name.strip()
            if not name.endswith(".json"):
                continue
            content = ui.run_shell(
                f"cat /sdcard/Android/data/li.songe.gkd/files/subscription/{name}"
            )
            try:
                payload = json.loads(content)
            except (ValueError, TypeError):
                continue
            if payload.get("id") == 82640113:
                return {
                    "installed": True,
                    "version": payload.get("version"),
                    "name": payload.get("name", ""),
                }
    except AdbError:
        raise
    return {"installed": False, "version": None, "name": ""}


def runtime_preflight(ui: AdbUIHelper) -> dict[str, Any]:
    """Collect read-only device, app, accessibility and subscription evidence."""
    import re

    def getprop(key: str) -> str:
        return ui.run_shell(f"getprop {key}").strip()
    pdd_package = ui.run_shell("dumpsys package com.xunmeng.pinduoduo")
    gkd_package = ui.run_shell("dumpsys package li.songe.gkd")
    pdd_version = re.search(r"versionName=([^\s]+)", pdd_package)
    gkd_version = re.search(r"versionName=([^\s]+)", gkd_package)
    screen = ui.run_shell("wm size")
    enabled_services = ui.run_shell(
        "settings get secure enabled_accessibility_services"
    ).strip()
    # GKD 1.12.1 declares its accessibility service under the Select-to-Speak
    # component name. Match a full component entry; package-substring matching
    # also matches unrelated service names and produced a false positive.
    gkd_service_component = (
        "li.songe.gkd/com.google.android.accessibility.selecttospeak."
        "SelectToSpeakService"
    )
    enabled_components = {
        item.strip() for item in enabled_services.split(":") if item.strip()
    }
    project_sub = read_project_subscription(ui)
    version_text = (REPO_ROOT / "dist" / "gkd.version.json5").read_text(encoding="utf-8")
    version_match = re.search(r"version:\s*(\d+)", version_text)
    expected_sub_version = int(version_match.group(1)) if version_match else None
    day = date.today().strftime("%Y%m%d")
    project_log_hits = ui.run_shell(
        "grep -F '82640113' "
        f"/sdcard/Android/data/li.songe.gkd/files/log/gkd-{day}.log | tail -n 5"
    ).strip()
    return {
        "serial": ui.serial,
        "model": getprop("ro.product.model"),
        "device": getprop("ro.product.device"),
        "screen": screen.strip().splitlines()[-1] if screen.strip() else "unknown",
        "foreground": ui.foreground_package(),
        "pinduoduo_version": pdd_version.group(1) if pdd_version else "unknown",
        "gkd_version": gkd_version.group(1) if gkd_version else "unknown",
        "gkd_accessibility_enabled": gkd_service_component in enabled_components,
        "project_subscription": project_sub,
        "expected_subscription_version": expected_sub_version,
        "project_gkd_log_hits_today": project_log_hits.splitlines(),
    }


def script_runtime_blockers(live: dict[str, Any]) -> list[str]:
    """Return hard blockers for any mutating Pinduoduo task run."""
    blockers = []
    if live["foreground"] != PDD_PKG:
        blockers.append(f"前台不是拼多多: {live['foreground'] or 'unknown'}")
    # The script executor requires GKD to be inactive, not enabled. A disabled
    # GKD accessibility service is the strongest available runtime evidence;
    # the operator must still confirm all overlapping rule switches are off.
    if live["gkd_accessibility_enabled"]:
        blockers.append("GKD 无障碍服务已启用，脚本执行器无法证明互斥")
    sub = live["project_subscription"]
    expected = live["expected_subscription_version"]
    if not sub["installed"] or sub["version"] != expected:
        blockers.append(f"本项目订阅与仓库版本不一致（期望 {expected}）: {sub}")
    return blockers
