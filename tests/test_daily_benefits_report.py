import pytest

from build_daily_benefits_report import ReportInputError, build_report


def test_report_does_not_invent_coupon_or_points():
    report = build_report({"date": "2026-09-26"})

    assert "不能判断当前账户" in report
    assert "未提供积分余额" in report
    assert "暂无具体购买计划" in report


def test_report_calculates_only_from_complete_purchase_inputs():
    report = build_report({
        "purchase": {
            "baseline_price": 1000,
            "pdd_settlement": 900,
            "membership_fee_allocated": 10,
            "extra_spend": 0,
            "risk_discount": 15,
        }
    })

    assert "估算净节省：75.00" in report
    assert "不触发下单" in report


def test_coupon_fields_are_escaped_for_markdown_table():
    report = build_report({"coupons": [{"name": "A|B", "status": "可领取"}]})

    assert "A&#124;B" in report
    assert "可领取" in report


def test_report_rejects_wrong_shapes_and_non_finite_amounts():
    with pytest.raises(ReportInputError):
        build_report({"coupons": "not-an-array"})
    with pytest.raises(ReportInputError):
        build_report({"purchase": {"baseline_price": float("nan")}})


def test_report_escapes_untrusted_text_and_collapses_newlines():
    report = build_report({"tasks": [{"name": "<script>\n## forged", "status": "ok"}]})

    assert "&lt;script&gt; ## forged" in report
    assert "\n## forged" not in report
