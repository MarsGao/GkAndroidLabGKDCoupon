#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a local, read-only daily benefits report from sanitized observed JSON."""

from __future__ import annotations

import argparse
import html
import json
import math
import re
from pathlib import Path
from typing import Any


class ReportInputError(ValueError):
    pass


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReportInputError(f"{field} 必须是对象")
    return value


def _list(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ReportInputError(f"{field} 必须是对象数组")
    return value


def _text(value: Any, field: str, default: str = "未知") -> str:
    if value is None:
        value = default
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise ReportInputError(f"{field} 必须是文本或数字")
    if isinstance(value, float) and not math.isfinite(value):
        raise ReportInputError(f"{field} 不允许 NaN 或 Infinity")
    safe = re.sub(r"[\x00-\x1f\x7f]", " ", str(value))
    safe = " ".join(safe.split())
    return html.escape(safe, quote=True).replace("|", "&#124;")


def _amount(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ReportInputError(f"{field} 必须是有限的非负金额")
    try:
        amount = float(value)
    except (TypeError, ValueError) as exc:
        raise ReportInputError(f"{field} 必须是有限的非负金额") from exc
    if not math.isfinite(amount) or amount < 0:
        raise ReportInputError(f"{field} 必须是有限的非负金额")
    return amount


def build_report(data: dict[str, Any]) -> str:
    """Render only supplied observations; never infer account entitlements."""
    data = _object(data, "输入")
    date = _text(data.get("date", "未知日期"), "date")
    lines = [f"# 拼多多会员权益盘点（{date}）", "", "> 仅汇总输入的页面证据；未提供的信息不作推断。", ""]

    checkin = _object(data.get("checkin", {}), "checkin")
    lines += ["## 今日任务", "", f"- 打卡：{_text(checkin.get('status', '未观察'), 'checkin.status')}" ]
    if checkin.get("points") is not None:
        lines[-1] += f"；页面显示积分 {_text(checkin['points'], 'checkin.points')}"
    for index, task in enumerate(_list(data.get("tasks", []), "tasks")):
        lines.append(
            f"- {_text(task.get('name', '未命名任务'), f'tasks[{index}].name')}："
            f"{_text(task.get('status', '未观察'), f'tasks[{index}].status')}"
            f"（{_text(task.get('evidence', '无证据说明'), f'tasks[{index}].evidence')}）"
        )

    lines += ["", "## 优惠券", ""]
    coupons = _list(data.get("coupons", []), "coupons")
    if not coupons:
        lines.append("未提供券样本；不能判断当前账户的可领券或已领券。")
    else:
        lines += ["| 状态 | 名称 | 面额 | 门槛 | 范围 | 有效期 | 来源 |", "|---|---|---:|---:|---|---|---|"]
        for index, coupon in enumerate(coupons):
            values = [_text(coupon.get(k, "未知"), f"coupons[{index}].{k}") for k in ("status", "name", "amount", "threshold", "scope", "validity", "source")]
            lines.append("| " + " | ".join(values) + " |")

    points = _object(data.get("points", {}), "points")
    lines += ["", "## 积分", ""]
    if points.get("balance") is None:
        lines.append("未提供积分余额/兑券档位；本报告不自动建议兑换。")
    else:
        lines.append(f"页面观察积分余额：{_text(points['balance'], 'points.balance')}。仅在有明确购买计划时比较兑券档位与有效期。")
    lines.append("积分兑换：只读盘点，未执行兑换。")

    purchase = data.get("purchase")
    lines += ["", "## 购买前分析", ""]
    if purchase is None:
        lines.append("暂无具体购买计划；不推荐为凑券门槛增加消费。")
    else:
        purchase = _object(purchase, "purchase")
        required = ("baseline_price", "pdd_settlement", "membership_fee_allocated", "extra_spend", "risk_discount")
        missing = [key for key in required if purchase.get(key) is None]
        amount = {key: _amount(purchase[key], f"purchase.{key}") for key in required if purchase.get(key) is not None}
        if missing:
            lines.append(f"信息不足，暂不计算净节省；缺少：{', '.join(missing)}。")
        else:
            saving = amount["baseline_price"] - amount["pdd_settlement"] - amount["membership_fee_allocated"] - amount["extra_spend"] - amount["risk_discount"]
            lines.append(f"输入值计算的估算净节省：{saving:.2f}。基准价及结算价须为同规格可信证据；仅供人工决策，不触发下单。")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="人工整理并脱敏的当前页面 JSON")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ReportInputError(f"非法数值 {value}")))
        print(build_report(data), end="")
    except (OSError, json.JSONDecodeError, ReportInputError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
