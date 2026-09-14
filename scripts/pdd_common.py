#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拼多多领券脚本公共：结果枚举、Lab helper 导入、页面识别。"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

LAB_ECOMMERCE = Path(r"C:\GkDesktop\GitProjects\GkAndroidLab\scripts\ecommerce")
if str(LAB_ECOMMERCE) not in sys.path:
    sys.path.insert(0, str(LAB_ECOMMERCE))

from adb_ui_helper import AdbError, AdbUIHelper  # noqa: E402

PDD_PKG = "com.xunmeng.pinduoduo"
SERIAL_DEFAULT = os.environ.get("ANDROID_SERIAL", "3B159H003D600000")

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
        "checkin_done_hint": any(k in joined for k in ("已打卡", "连续打卡")),
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
            "脚本模式拒绝执行：请先停用 MarsGao key4/5/6/7 及第三方重叠拼多多点击规则，"
            "并传入 --confirm-gkd-off（或环境变量 PDD_CONFIRM_GKD_OFF=1）。"
            "无法通过 API 核验 GKD 开关；PC 锁不能证明互斥。"
        )
    print(
        "[preflight] 已确认 GKD 重叠点击规则停用；请保证手机订阅已到 v7，"
        "脚本模式请关闭 key5/key8（及第三方重叠拼多多点击）；无障碍须正常。"
    )
