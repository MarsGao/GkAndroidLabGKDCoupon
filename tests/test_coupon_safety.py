from __future__ import annotations

import xml.etree.ElementTree as ET

import claim_region_exclusive as region
import enter_coupon_venue as enter
import run_pdd_coupon_task as task
import verify_pdd_coupon_venue as verify
from adb_ui_helper import AdbUIHelper
from pdd_common import StepResult, TaskReport, script_runtime_blockers


def _root(*items: tuple[str, str]) -> ET.Element:
    root = ET.Element("hierarchy")
    for index, (text, bounds) in enumerate(items):
        ET.SubElement(
            root,
            "node",
            {
                "index": str(index),
                "text": text,
                "content-desc": "",
                "resource-id": "",
                "class": "android.widget.TextView",
                "bounds": bounds,
                "clickable": "true",
                "visibleToUser": "true",
            },
        )
    return root


class FakeUI:
    serial = "test-device"
    screen_width = 1440
    screen_height = 3200
    parse_bounds = staticmethod(AdbUIHelper.parse_bounds)

    def __init__(self, roots: list[ET.Element]):
        self.roots = roots
        self.actions: list[str] = []

    def dump_ui(self, require_nodes: bool = False) -> ET.Element:
        if len(self.roots) > 1:
            return self.roots.pop(0)
        return self.roots[0]

    def find_nodes(self, root, **kwargs):
        return AdbUIHelper.find_nodes(self, root, **kwargs)

    def foreground_package(self):
        return "com.xunmeng.pinduoduo"

    def tap(self, *args, **kwargs):
        self.actions.append("tap")

    def tap_node(self, *args, **kwargs):
        self.actions.append("tap")

    def swipe(self, *args, **kwargs):
        self.actions.append("swipe")

    def swipe_up(self, *args, **kwargs):
        self.actions.append("swipe")

    def back(self, *args, **kwargs):
        self.actions.append("back")


def test_task_report_requires_review_exit_code():
    report = TaskReport(mode="script", serial="test-device")
    report.add("page", StepResult.NEEDS_REVIEW, "ambiguous")
    assert report.exit_code() == 2


def test_failed_report_exit_code_takes_precedence():
    report = TaskReport(mode="script", serial="test-device")
    report.add("review", StepResult.NEEDS_REVIEW, "ambiguous")
    report.add("adb", StepResult.FAILED, "disconnected")
    assert report.exit_code() == 1


def test_gkd_accessibility_off_is_not_script_blocker():
    live = {
        "foreground": "com.xunmeng.pinduoduo",
        "gkd_accessibility_enabled": False,
        "project_subscription": {"installed": True, "version": 7},
        "expected_subscription_version": 7,
    }
    assert script_runtime_blockers(live) == []


def test_gkd_accessibility_on_blocks_script_executor():
    live = {
        "foreground": "com.xunmeng.pinduoduo",
        "gkd_accessibility_enabled": True,
        "project_subscription": {"installed": True, "version": 7},
        "expected_subscription_version": 7,
    }
    assert "GKD 无障碍服务已启用" in script_runtime_blockers(live)[0]


def test_observe_light_does_not_scroll():
    ui = FakeUI([_root(("消费券", "[0,0][1440,3200]"), ("立即点亮", "[100,300][300,380]"))])
    report = TaskReport(mode="observe", serial=ui.serial)

    result = task.step_light_browse(ui, report, observe=True, browse_sec=10)

    assert result == StepResult.NEEDS_REVIEW
    assert ui.actions == []


def test_region_observe_does_not_switch_or_scroll(monkeypatch):
    ui = FakeUI([
        _root(
            ("消费券", "[0,0][1440,3200]"),
            ("双重补贴", "[100,300][300,380]"),
            ("地区专享", "[400,300][600,380]"),
            ("立即领取", "[800,900][1100,1000]"),
        )
    ])
    monkeypatch.setattr(region, "make_helper", lambda serial: ui)

    code = region.run("test-device", observe=True, skip_tab=False, max_claims=8, max_rounds=8)

    assert code == 0
    assert ui.actions == []


def test_entry_observe_does_not_tap_or_screenshot(monkeypatch):
    ui = FakeUI([_root(("首页", "[0,0][1440,3200]"))])
    monkeypatch.setattr(enter, "make_helper", lambda serial: ui)

    code = enter.run(
        "test-device",
        observe=True,
        open_subsidy=False,
        allow_fallback=None,
    )

    assert code == 2
    assert ui.actions == []


def test_old_subsidy_deeplink_coordinate_is_rejected(monkeypatch):
    ui = FakeUI([_root(("首页", "[0,0][1440,3200]"))])
    monkeypatch.setattr(enter, "make_helper", lambda serial: ui)
    monkeypatch.setattr(enter, "assert_script_mode_preflight", lambda *args, **kwargs: None)
    monkeypatch.setattr(enter, "runtime_preflight", lambda *args, **kwargs: {})
    monkeypatch.setattr(enter, "script_runtime_blockers", lambda *args, **kwargs: [])

    assert enter.run("test-device", observe=False, open_subsidy=True, allow_fallback=None) == 2
    assert ui.actions == []


def test_h5_empty_tree_never_triggers_color_guess(monkeypatch):
    ui = FakeUI([_root(("百亿补贴", "[0,0][1440,3200]"))])
    monkeypatch.setattr(enter, "make_helper", lambda serial: ui)
    monkeypatch.setattr(enter, "assert_script_mode_preflight", lambda *args, **kwargs: None)
    monkeypatch.setattr(enter, "runtime_preflight", lambda *args, **kwargs: {})
    monkeypatch.setattr(enter, "script_runtime_blockers", lambda *args, **kwargs: [])

    assert enter.run("test-device", observe=False, open_subsidy=False, allow_fallback=None) == 2
    assert ui.actions == []


def test_legacy_verify_click_flag_is_rejected_without_touch(monkeypatch):
    ui = FakeUI([_root(("首页", "[0,0][1440,3200]"))])
    monkeypatch.setattr(verify, "make_helper", lambda serial: ui)
    monkeypatch.setattr("sys.argv", ["verify_pdd_coupon_venue.py", "--click-enter"])

    code = verify.main()

    assert code == 2
    assert ui.actions == []


def test_single_stage_without_from_stage_is_rejected(monkeypatch):
    monkeypatch.setattr("sys.argv", ["run_pdd_coupon_task.py", "--single-stage"])

    try:
        task.main()
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("--single-stage without --from-stage must be rejected")


def test_same_slot_received_without_coupon_container_is_needs_review():
    before = _root(
        ("消费券", "[0,0][1440,3200]"),
        ("双重补贴", "[100,300][300,380]"),
        ("地区专享", "[400,300][600,380]"),
        ("立即领取", "[800,900][1100,1000]"),
    )
    after = _root(
        ("消费券", "[0,0][1440,3200]"),
        ("双重补贴", "[100,300][300,380]"),
        ("地区专享", "[400,300][600,380]"),
        ("去使用", "[800,900][1100,1000]"),
    )
    ui = FakeUI([before, after, after])
    report = TaskReport(mode="script", serial=ui.serial)

    result = region.claim_one(ui, report, 2)

    assert result == StepResult.NEEDS_REVIEW


def test_disappearing_coupon_button_is_not_verified():
    before = _root(
        ("消费券", "[0,0][1440,3200]"),
        ("双重补贴", "[100,300][300,380]"),
        ("地区专享", "[400,300][600,380]"),
        ("立即领取", "[800,900][1100,1000]"),
    )
    after = _root(
        ("消费券", "[0,0][1440,3200]"),
        ("双重补贴", "[100,300][300,380]"),
        ("地区专享", "[400,300][600,380]"),
    )
    ui = FakeUI([before, after, after])
    report = TaskReport(mode="script", serial=ui.serial)

    result = region.claim_one(ui, report, 1)

    assert result == StepResult.NEEDS_REVIEW


def test_observe_checkin_candidate_is_not_verified():
    ui = FakeUI([_root(("打卡送积分", "[0,0][1440,300]"), ("打卡", "[100,500][300,600]"))])
    report = TaskReport(mode="observe", serial=ui.serial)

    result = task.step_checkin(ui, report, observe=True)

    assert result == StepResult.NEEDS_REVIEW
    assert report.records[-1].result == StepResult.NEEDS_REVIEW
    assert ui.actions == []


def test_checkin_rejects_button_without_day_reward_binding():
    ui = FakeUI([_root(
        ("百亿补贴会员", "[500,190][900,300]"),
        ("489", "[1106,637][1211,689]"),
        ("积分", "[1214,623][1326,696]"),
        ("打卡送积分", "[91,1221][402,1288]"),
        ("打卡", "[500,1547][598,1613]"),
    )])
    report = TaskReport(mode="script", serial=ui.serial)

    assert task.step_checkin(ui, report, observe=False) == StepResult.NEEDS_REVIEW
    assert ui.actions == []


def test_home_page_is_not_treated_as_member_benefit_unavailable():
    ui = FakeUI([_root(("首页", "[0,0][1440,3200]"))])
    report = TaskReport(mode="observe", serial=ui.serial)

    assert task.step_checkin(ui, report, observe=True) == StepResult.NEEDS_REVIEW
    assert "需先导航" in report.records[-1].detail
    assert ui.actions == []


def test_member_page_next_day_pending_is_already_claimed():
    ui = FakeUI([_root(
        ("百亿补贴会员", "[500,190][900,300]"),
        ("504", "[1106,637][1211,689]"),
        ("积分", "[1214,623][1326,696]"),
        ("打卡送积分", "[91,1221][402,1288]"),
        ("10", "[700,1382][770,1463]"),
        ("待打卡", "[651,1547][794,1613]"),
        ("第4天", "[658,1648][784,1697]"),
    )])
    report = TaskReport(mode="script", serial=ui.serial)

    assert task.step_checkin(ui, report, observe=False) == StepResult.ALREADY_CLAIMED
    assert ui.actions == []


def test_unrelated_done_hint_does_not_verify_member_checkin():
    before = _root(
        ("打卡送积分", "[91,1221][402,1288]"),
        ("打卡", "[500,1547][598,1613]"),
    )
    after = _root(
        ("打卡送积分", "[91,1221][402,1288]"),
        ("今日已签到", "[1000,2000][1300,2100]"),
    )
    ui = FakeUI([before, after])
    report = TaskReport(mode="script", serial=ui.serial)

    assert task.step_checkin(ui, report, observe=False) == StepResult.NEEDS_REVIEW


def test_member_checkin_requires_points_and_next_day_evidence():
    before = _root(
        ("百亿补贴会员", "[500,190][900,300]"),
        ("489", "[1106,637][1211,689]"),
        ("积分", "[1214,623][1326,696]"),
        ("打卡送积分", "[91,1221][402,1288]"),
        ("15", "[528,1382][598,1463]"),
        ("打卡", "[500,1547][598,1613]"),
        ("第3天", "[486,1648][612,1697]"),
    )
    after = _root(
        ("百亿补贴会员", "[500,190][900,300]"),
        ("504", "[1106,637][1211,689]"),
        ("积分", "[1214,623][1326,696]"),
        ("打卡送积分", "[91,1221][402,1288]"),
        ("10", "[700,1382][770,1463]"),
        ("待打卡", "[651,1547][794,1613]"),
        ("第4天", "[658,1648][784,1697]"),
    )
    ui = FakeUI([before, after])
    report = TaskReport(mode="script", serial=ui.serial)

    result = task.step_checkin(ui, report, observe=False)

    assert result == StepResult.VERIFIED
    assert "489→504" in report.records[-1].detail
    assert ui.actions == ["tap"]


def test_member_checkin_missing_points_delta_stays_review():
    before = _root(
        ("百亿补贴会员", "[500,190][900,300]"),
        ("489", "[1106,637][1211,689]"),
        ("积分", "[1214,623][1326,696]"),
        ("打卡送积分", "[91,1221][402,1288]"),
        ("15", "[528,1382][598,1463]"),
        ("打卡", "[500,1547][598,1613]"),
        ("第3天", "[486,1648][612,1697]"),
    )
    after = _root(
        ("百亿补贴会员", "[500,190][900,300]"),
        ("489", "[1106,637][1211,689]"),
        ("积分", "[1214,623][1326,696]"),
        ("打卡送积分", "[91,1221][402,1288]"),
        ("10", "[700,1382][770,1463]"),
        ("待打卡", "[651,1547][794,1613]"),
        ("第4天", "[658,1648][784,1697]"),
    )
    ui = FakeUI([before, after])
    report = TaskReport(mode="script", serial=ui.serial)

    result = task.step_checkin(ui, report, observe=False)

    assert result == StepResult.NEEDS_REVIEW


def test_level_gift_does_not_click_neighbor_referral_card():
    ui = FakeUI([_root(
        ("百亿补贴会员等级", "[0,0][1440,332]"),
        ("无门槛券", "[91,1620][497,1669]"),
        ("已使用", "[129,1676][458,1781]"),
        ("领取", "[567,1680][892,1781]"),
    )])
    report = TaskReport(mode="script", serial=ui.serial)

    result = task.step_level_gift(ui, report, observe=False)

    assert result == StepResult.ALREADY_CLAIMED
    assert ui.actions == []
