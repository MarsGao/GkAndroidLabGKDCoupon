#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拼多多领券脚本任务模式状态机（短期主基线）。

阶段：preflight → member_checkin → level_gift → enter_venue → dual_claim
      → region_exclusive → light_browse → summary

硬顺序：地区/会场「立即领取」必须先于「立即点亮」。
不自动中途切换到 GKD；不宣称必然领全。
会场单页有序闭环也可直接：scripts/run_venue_pipeline.py

用法：
  python scripts/run_pdd_coupon_task.py --observe
  python scripts/run_pdd_coupon_task.py --from-stage region --confirm-gkd-off
  python scripts/run_pdd_coupon_task.py --stages member,venue,region,light
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pdd_common import (  # noqa: E402
    SERIAL_DEFAULT,
    StepResult,
    TaskReport,
    assert_script_mode_preflight,
    make_helper,
    page_signals,
    runtime_preflight,
    script_runtime_blockers,
)
from adb_ui_helper import AdbError, AdbUIHelper  # noqa: E402

import claim_region_exclusive as region_mod  # noqa: E402
import enter_coupon_venue as enter_mod  # noqa: E402

ALL_STAGES = (
    "preflight",
    "member",
    "level",
    "venue",
    "dual",
    "region",  # 必须先于 light
    "light",
)


def _member_balance(ui: AdbUIHelper, root) -> int | None:
    """Read the number directly beside the member page's top-right 积分 label."""
    labels = [
        n for n in ui.find_nodes(root, text_regex=r"^积分$")
        if n["center"][1] < ui.screen_height * 0.4
    ]
    numbers = ui.find_nodes(root, text_regex=r"^\d+$")
    for label in labels:
        adjacent = [
            n for n in numbers
            if n["center"][0] < label["bounds"][0]
            and 0 <= label["bounds"][0] - n["bounds"][2] <= 100
            and abs(n["center"][1] - label["center"][1]) <= 80
        ]
        if len(adjacent) == 1:
            return int(adjacent[0]["text"])
    return None


def _checkin_card(ui: AdbUIHelper, root, action_text: str) -> tuple[int, int] | None:
    """Bind the highlighted day's reward to its action by visible geometry."""
    actions = ui.find_nodes(root, text_regex=rf"^{action_text}$")
    if len(actions) != 1:
        return None
    action = actions[0]
    days = [
        n for n in ui.find_nodes(root, text_regex=r"^第\d+天$")
        if 0 < n["center"][1] - action["center"][1] < 240
        and abs(n["center"][0] - action["center"][0]) < 100
    ]
    rewards = [
        n for n in ui.find_nodes(root, text_regex=r"^\d+$")
        if 0 < action["center"][1] - n["center"][1] < 280
        and abs(n["center"][0] - action["center"][0]) < 100
    ]
    if len(days) != 1 or len(rewards) != 1:
        return None
    return int(days[0]["text"][1:-1]), int(rewards[0]["text"])


def step_checkin(ui: AdbUIHelper, report: TaskReport, observe: bool) -> StepResult:
    root = ui.dump_ui(require_nodes=True)
    sig = page_signals(ui, root)
    if not sig["member"] and not sig["checkin_available"]:
        report.add("member_checkin", StepResult.NEEDS_REVIEW, "当前不是可识别的会员打卡页；需先导航到目标页")
        return StepResult.NEEDS_REVIEW
    nodes = ui.find_nodes(root, text_regex=r"^打卡$")
    if not nodes:
        next_card = _checkin_card(ui, root, "待打卡")
        balance = _member_balance(ui, root)
        if sig["member"] and next_card is not None and next_card[0] > 1 and balance is not None:
            report.add(
                "member_checkin", StepResult.ALREADY_CLAIMED,
                f"当前无打卡按钮；积分 {balance}，第{next_card[0]}天为待打卡（本周上一天已过）",
            )
            return StepResult.ALREADY_CLAIMED
        report.add("member_checkin", StepResult.NEEDS_REVIEW, "会员页无当日打卡按钮；单屏不能区分已打卡与尚未开放")
        return StepResult.NEEDS_REVIEW
    if observe:
        report.add("member_checkin", StepResult.NEEDS_REVIEW, f"observe 仅发现打卡候选 x{len(nodes)}；未执行领取")
        return StepResult.NEEDS_REVIEW
    if len(nodes) > 1:
        report.add("member_checkin", StepResult.NEEDS_REVIEW, f"打卡候选歧义 {len(nodes)}")
        return StepResult.NEEDS_REVIEW
    balance_before = _member_balance(ui, root)
    card_before = _checkin_card(ui, root, "打卡")
    if balance_before is None or card_before is None:
        report.add("member_checkin", StepResult.NEEDS_REVIEW, "打卡按钮可见但无法绑定当日奖励与会员积分；未点击")
        return StepResult.NEEDS_REVIEW
    # 文案中心常偏下；略上移点到橙色按钮本体
    n = nodes[0]
    cx, cy = n["center"]
    ui.tap(cx, max(cy - 40, n["bounds"][1] + 8), delay=1.5)
    root2 = ui.dump_ui(require_nodes=True)
    after = ui.find_nodes(root2, text_regex=r"^打卡$")
    sig2 = page_signals(ui, root2)
    balance_after = _member_balance(ui, root2)
    card_after = _checkin_card(ui, root2, "待打卡")
    if (
        not after and balance_before is not None and balance_after is not None
        and card_before is not None and card_after is not None
        and card_after[0] == card_before[0] + 1
        and balance_after - balance_before == card_before[1]
    ):
        report.add(
            "member_checkin", StepResult.VERIFIED,
            f"积分 {balance_before}→{balance_after} (+{card_before[1]})；"
            f"第{card_before[0]}天打卡→第{card_after[0]}天待打卡",
            before=f"day={card_before[0]},balance={balance_before},reward={card_before[1]}",
            after=f"day={card_after[0]},balance={balance_after},state=待打卡",
        )
        return StepResult.VERIFIED
    # 全屏的「已打卡」提示无法关联到本次点击的卡片；强证据缺失时停机。
    if not after:
        report.add(
            "member_checkin", StepResult.NEEDS_REVIEW,
            f"打卡按钮消失，但积分/次日卡片未形成同页正向证据；全屏提示={sig2['checkin_done_hint']}",
        )
        return StepResult.NEEDS_REVIEW
    report.add("member_checkin", StepResult.NEEDS_REVIEW, "点击后打卡仍在或证据不足")
    return StepResult.NEEDS_REVIEW


def step_level_gift(ui: AdbUIHelper, report: TaskReport, observe: bool) -> StepResult:
    root = ui.dump_ui(require_nodes=True)
    free = ui.find_nodes(root, text_regex=r"无门槛券")
    if not free:
        report.add("level_gift", StepResult.UNAVAILABLE, "未见无门槛券")
        return StepResult.UNAVAILABLE
    if len(free) != 1:
        report.add(
            "level_gift",
            StepResult.NEEDS_REVIEW,
            f"无门槛券候选不唯一 free={len(free)}",
        )
        return StepResult.NEEDS_REVIEW
    # V3 页面把无门槛券和「少拉1人卡」并排放置。只接受同列卡片
    # 内、券名下方的动作；不能按纵向距离跨卡片误点拉人权益。
    target = free[0]
    def same_card_action(n):
        return (
            target["bounds"][0] <= n["center"][0] <= target["bounds"][2]
            and 0 < n["center"][1] - target["center"][1] <= 250
        )
    claims = [
        n for n in ui.find_nodes(root, text_regex=r"^领取$")
        if same_card_action(n)
    ]
    used = [
        n for n in ui.find_nodes(root, text_regex=r"^(去使用|已使用|已领取)$")
        if same_card_action(n)
    ]
    if len(claims) > 1 or (claims and used):
        report.add("level_gift", StepResult.NEEDS_REVIEW, "同一无门槛券卡片状态歧义")
        return StepResult.NEEDS_REVIEW
    if not claims:
        if len(used) == 1:
            report.add("level_gift", StepResult.ALREADY_CLAIMED, f"无门槛券同卡片状态={used[0]['text']}")
            return StepResult.ALREADY_CLAIMED
        report.add("level_gift", StepResult.UNAVAILABLE, "无领取按钮")
        return StepResult.UNAVAILABLE
    best = claims[0]
    if observe:
        report.add("level_gift", StepResult.NEEDS_REVIEW, "observe 仅发现同卡片无门槛券领取候选；未执行领取")
        return StepResult.NEEDS_REVIEW
    before = f"领取@{best['bounds']}"
    ui.tap_node(best, delay=1.5)
    root2 = ui.dump_ui(require_nodes=True)
    after_claim = ui.find_nodes(root2, text_regex=r"^领取$")
    after_use = ui.find_nodes(root2, text_regex=r"^(去使用|已使用|已领取)$")
    same_slot_received = any(n["bounds"] == best["bounds"] for n in after_use)
    if same_slot_received and (
        not any(n["bounds"] == best["bounds"] for n in after_claim)
    ):
        report.add("level_gift", StepResult.NEEDS_REVIEW, "同坐标出现已领状态，但无障碍树未提供可证明同卡片的父容器；拒绝记 verified", before=before)
        return StepResult.NEEDS_REVIEW
    if not any(n["bounds"] == best["bounds"] for n in after_claim):
        report.add("level_gift", StepResult.NEEDS_REVIEW, "领取按钮消失但无同券已领态", before=before)
        return StepResult.NEEDS_REVIEW
    report.add("level_gift", StepResult.NEEDS_REVIEW, "点击后证据不足", before=before)
    return StepResult.NEEDS_REVIEW


def step_dual_claim(ui: AdbUIHelper, report: TaskReport, observe: bool, max_n: int) -> StepResult:
    """双重补贴区：逐张领取（与地区专享同一闭环语义）。"""
    root = ui.dump_ui(require_nodes=True)
    # 若在地区专享，先点双重补贴 Tab
    dual_tabs = ui.find_nodes(root, text_regex=r"^双重补贴$")
    if dual_tabs and not observe:
        top = sorted(dual_tabs, key=lambda t: t["center"][1])[0]
        if top["center"][1] < ui.screen_height * 0.55:
            ui.tap_node(top, delay=1.8)

    if observe:
        root = ui.dump_ui(require_nodes=True)
        n = len(region_mod._claim_candidates(ui, root))
        report.add("dual_claim", StepResult.NEEDS_REVIEW, f"observe 仅发现可领取候选={n}；未执行领取")
        return StepResult.NEEDS_REVIEW

    verified = 0
    for i in range(max_n):
        res = region_mod.claim_one(ui, report, 100 + i)
        # 复用 claim_one 但 step 名在 report 里是 claim[1xx]；额外记 dual
        if res == StepResult.VERIFIED:
            verified += 1
            continue
        if res in (StepResult.UNAVAILABLE, StepResult.ALREADY_CLAIMED):
            region_mod.scroll_coupon_area(ui, horizontal=True)
            time.sleep(0.6)
            res2 = region_mod.claim_one(ui, report, 100 + i + 50)
            if res2 == StepResult.VERIFIED:
                verified += 1
                continue
            if res2 in (StepResult.FAILED, StepResult.NEEDS_REVIEW):
                return res2
            break
        if res in (StepResult.FAILED, StepResult.NEEDS_REVIEW):
            return res
    if verified:
        report.add("dual_claim", StepResult.VERIFIED, f"verified_count={verified}")
        return StepResult.VERIFIED
    report.add("dual_claim", StepResult.UNAVAILABLE, "本轮无新核销")
    return StepResult.UNAVAILABLE


def _scroll_venue_top(ui: AdbUIHelper, rounds: int = 3) -> None:
    w, h = ui.screen_width, ui.screen_height
    for _ in range(rounds):
        ui.swipe(w // 2, int(h * 0.28), w // 2, int(h * 0.78), 420)
        time.sleep(0.35)


def step_light_browse(ui: AdbUIHelper, report: TaskReport, observe: bool, browse_sec: float) -> StepResult:
    root = ui.dump_ui(require_nodes=True)
    sig = page_signals(ui, root)
    if observe:
        result = StepResult.ALREADY_CLAIMED if sig["light_done"] else StepResult.NEEDS_REVIEW if sig["light_available"] else StepResult.UNAVAILABLE
        report.add(
            "light_browse",
            result,
            f"observe light_available={sig['light_available']} light_done={sig['light_done']}",
        )
        return result

    _scroll_venue_top(ui)
    root = ui.dump_ui(require_nodes=True)
    sig = page_signals(ui, root)
    if sig["light_done"]:
        report.add("light_browse", StepResult.ALREADY_CLAIMED, "今日已点亮")
        return StepResult.ALREADY_CLAIMED
    # 顺序闸：仍有可领券时禁止点亮
    if region_mod._claim_candidates(ui, root):
        report.add("light_browse", StepResult.NEEDS_REVIEW, "仍有立即领取，拒绝点亮（顺序闸）")
        return StepResult.NEEDS_REVIEW
    lights = ui.find_nodes(root, text_regex=r"^(立即点亮|解锁点亮)$")
    if not lights:
        _scroll_venue_top(ui, rounds=2)
        root = ui.dump_ui(require_nodes=True)
        lights = ui.find_nodes(root, text_regex=r"^(立即点亮|解锁点亮)$")
    if not lights:
        report.add("light_browse", StepResult.UNAVAILABLE, "无立即点亮/解锁点亮")
        return StepResult.UNAVAILABLE
    if len(lights) > 1:
        report.add("light_browse", StepResult.NEEDS_REVIEW, "点亮按钮歧义")
        return StepResult.NEEDS_REVIEW
    ui.tap_node(lights[0], delay=1.2)
    # 引导「去看看」仅在点亮后短窗口内点一次
    root2 = ui.dump_ui(require_nodes=True)
    go = ui.find_nodes(root2, text_regex=r"去看看")
    if go:
        ui.tap_node(go[0], delay=1.0)
    # 浏览：保持前台并轻滑；被遮挡则 needs_review
    t0 = time.time()
    while time.time() - t0 < browse_sec:
        if ui.foreground_package() != "com.xunmeng.pinduoduo":
            report.add("light_browse", StepResult.NEEDS_REVIEW, "浏览期间离开拼多多前台")
            return StepResult.NEEDS_REVIEW
        ui.swipe_up(0.15)
        time.sleep(1.0)
    # 返回会场并核验「今日已点亮」
    for _ in range(3):
        ui.back(delay=1.0)
        root3 = ui.dump_ui(require_nodes=True)
        sig3 = page_signals(ui, root3)
        if sig3["light_done"]:
            report.add("light_browse", StepResult.VERIFIED, f"浏览{browse_sec}s 后见今日已点亮")
            return StepResult.VERIFIED
        if sig3["venue"]:
            break
    root_f = ui.dump_ui(require_nodes=True)
    if page_signals(ui, root_f)["light_done"]:
        report.add("light_browse", StepResult.VERIFIED, "见今日已点亮")
        return StepResult.VERIFIED
    report.add("light_browse", StepResult.NEEDS_REVIEW, "浏览结束未见今日已点亮（sleep 不算成功）")
    return StepResult.NEEDS_REVIEW


def run_stages(
    serial: str,
    observe: bool,
    stages: list[str],
    browse_sec: float,
    confirm_gkd_off: bool = False,
) -> int:
    report = TaskReport(mode="observe" if observe else "script", serial=serial or "auto")
    try:
        ui = make_helper(serial)
        report.serial = ui.serial
        if "preflight" in stages:
            if not observe:
                assert_script_mode_preflight(ui, confirm_gkd_off=confirm_gkd_off)
        elif not observe:
            # 即使跳过 preflight 阶段，脚本模式仍需硬闸
            assert_script_mode_preflight(ui, confirm_gkd_off=confirm_gkd_off)

        live = runtime_preflight(ui)
        blockers = script_runtime_blockers(live)
        preflight_result = (
            StepResult.FAILED if blockers and not observe
            else StepResult.NEEDS_REVIEW if blockers
            else StepResult.VERIFIED
        )
        report.add(
            "device_preflight",
            preflight_result,
            "; ".join(blockers) if blockers else json.dumps(live, ensure_ascii=False),
        )
        if not observe:
            if blockers:
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return report.exit_code()
        if "preflight" in stages:
            report.add(
                "preflight",
                StepResult.NEEDS_REVIEW if blockers else StepResult.VERIFIED,
                f"fg={ui.foreground_package()} {ui.screen_width}x{ui.screen_height}",
            )

        stop_on = {StepResult.FAILED, StepResult.NEEDS_REVIEW}

        if "member" in stages:
            r = step_checkin(ui, report, observe)
            if r in stop_on and not observe:
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return report.exit_code()

        if "level" in stages:
            r = step_level_gift(ui, report, observe)
            if r in stop_on and not observe:
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return report.exit_code()

        if "venue" in stages:
            code = enter_mod.run(
                ui.serial,
                observe=observe,
                open_subsidy=False,
                allow_fallback=None,
                confirm_gkd_off=confirm_gkd_off,
            )
            # enter 已打印；合并关键记录困难，补一条
            report.add(
                "venue_entry_probe" if observe else "venue_enter",
                StepResult.VERIFIED if code == 0 else StepResult.FAILED if code == 1 else StepResult.NEEDS_REVIEW,
                f"{'entry_probe' if observe else 'enter'}_exit_code={code}",
            )
            if code not in (0,):
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return code

        if "dual" in stages:
            r = step_dual_claim(ui, report, observe, max_n=5)
            if r in stop_on and not observe:
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return report.exit_code()

        if "region" in stages:
            region_start = len(report.records)
            code = region_mod.run(
                ui.serial,
                observe=observe,
                skip_tab=False,
                max_claims=8,
                max_rounds=8,
                confirm_gkd_off=confirm_gkd_off if not observe else False,
                task_report=report,
            )
            region_records = report.records[region_start:]
            region_result = (
                StepResult.VERIFIED
                if any(r.step.startswith("claim[") and r.result == StepResult.VERIFIED for r in region_records)
                else StepResult.NEEDS_REVIEW if observe and any("claimable=" in r.detail and "claimable=0 " not in r.detail for r in region_records)
                else StepResult.UNAVAILABLE if code == 0
                else StepResult.FAILED if code in (1, 3)
                else StepResult.NEEDS_REVIEW
            )
            report.add(
                "region_exclusive",
                region_result,
                f"region_exit_code={code}" + ("; 候选已观察但未执行" if observe and region_result == StepResult.NEEDS_REVIEW else ""),
            )
            if code not in (0,):
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return code

        if "light" in stages:
            r = step_light_browse(ui, report, observe, browse_sec)
            if r in (StepResult.FAILED, StepResult.NEEDS_REVIEW) and not observe:
                # 顺序闸 needs_review 也停，避免未领完却继续
                print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
                return 1 if r == StepResult.FAILED else 2

        print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
        return report.exit_code()
    except AdbError as e:
        report.add("adb", StepResult.FAILED, str(e))
        print(json.dumps(report.summary(), ensure_ascii=False, indent=2))
        return report.exit_code()


def main() -> int:
    ap = argparse.ArgumentParser(description="PDD 领券脚本任务状态机")
    ap.add_argument("--serial", default=SERIAL_DEFAULT)
    ap.add_argument("--observe", action="store_true")
    ap.add_argument(
        "--stages",
        default=",".join(ALL_STAGES),
        help=f"逗号分隔，可选: {','.join(ALL_STAGES)}",
    )
    ap.add_argument("--from-stage", default=None, help="兼容参数：从该阶段起执行到结束；单步验收优先用 --stages 指定一个业务阶段")
    ap.add_argument("--single-stage", action="store_true", help="与 --from-stage 配合，将运行严格限制为单个阶段")
    ap.add_argument("--browse-sec", type=float, default=10.0)
    ap.add_argument(
        "--confirm-gkd-off",
        action="store_true",
        help="确认已停用重叠 GKD 拼多多点击规则（脚本模式必填，或设 PDD_CONFIRM_GKD_OFF=1）",
    )
    args = ap.parse_args()

    if args.single_stage and not args.from_stage:
        ap.error("--single-stage 必须与 --from-stage 配合；也可使用 --stages 仅指定一个业务阶段")

    stages = [s.strip() for s in args.stages.split(",") if s.strip()]
    if args.from_stage:
        if args.from_stage not in ALL_STAGES:
            print(f"未知阶段: {args.from_stage}", file=sys.stderr)
            return 2
        idx = ALL_STAGES.index(args.from_stage)
        stages = [args.from_stage] if args.single_stage else list(ALL_STAGES[idx:])
    for s in stages:
        if s not in ALL_STAGES:
            print(f"未知阶段: {s}", file=sys.stderr)
            return 2
    return run_stages(
        args.serial,
        args.observe,
        stages,
        args.browse_sec,
        confirm_gkd_off=args.confirm_gkd_off,
    )


if __name__ == "__main__":
    raise SystemExit(main())
