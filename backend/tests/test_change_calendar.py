from datetime import date, datetime
from types import SimpleNamespace

import pytest

from app.services.change_calendar import CalendarPeriod, required_minutes, schedule_waves


def vm(i, risk="Low", criticality="Medium"):
    return SimpleNamespace(id=i, name=f"VM-{i}", migration_risk=risk, criticality=criticality)


def test_required_minutes_batches_cutovers():
    # 60 precheck + ceil(12/5)=3 batches * 30 + 60 validation + 60 rollback reserve
    assert required_minutes([vm(i) for i in range(12)]) == 270


def test_waves_land_on_friday_night_gst_with_hypercare_gap():
    # 2026-10-01 is a Thursday.
    result = schedule_waves({1: [vm(1)], 2: [vm(2)]}, date(2026, 10, 1))
    first, second = result["scheduled"]
    assert first["day"] == "Friday"
    assert first["window_start_local"] == "2026-10-02T22:00:00+04:00"
    assert first["window_start_utc"] == "2026-10-02T18:00:00+00:00"
    gap = datetime.fromisoformat(second["window_start_local"]) - datetime.fromisoformat(first["window_end_local"])
    assert gap.days >= 7


def test_blackout_is_skipped():
    national_day = CalendarPeriod(date(2026, 12, 1), date(2026, 12, 3), "blackout", "Commemoration & National Day")
    # 2026-11-30 is a Monday; the Friday window on 4 Dec starts the evening after the blackout ends.
    freeze = CalendarPeriod(date(2026, 12, 4), date(2026, 12, 6), "blackout", "Year-end freeze")
    result = schedule_waves({1: [vm(1)]}, date(2026, 11, 30), periods=[national_day, freeze])
    assert result["scheduled"][0]["window_start_local"].startswith("2026-12-11")
    assert any("Year-end freeze" in s for s in result["scheduled"][0]["skipped_windows"])


def test_restricted_period_only_allows_low_risk_waves():
    ramadan = CalendarPeriod(date(2027, 2, 8), date(2027, 3, 9), "restricted", "Ramadan (estimated)")
    low = schedule_waves({1: [vm(1)]}, date(2027, 2, 10), periods=[ramadan])
    assert low["scheduled"][0]["window_start_local"].startswith("2027-02-12")
    assert low["scheduled"][0]["notes"] == ["Inside restricted period: Ramadan (estimated)"]

    high = schedule_waves({1: [vm(1, criticality="Critical")]}, date(2027, 2, 10), periods=[ramadan])
    assert high["scheduled"][0]["window_start_local"] >= "2027-03-10"


def test_oversized_wave_is_reported_unscheduled():
    result = schedule_waves({1: [vm(i) for i in range(200)]}, date(2026, 10, 1), weeks=2)
    assert result["scheduled"] == []
    assert result["unscheduled"][0]["wave"] == 1


def test_invalid_period_rejected():
    with pytest.raises(ValueError):
        schedule_waves({1: [vm(1)]}, date(2026, 10, 1), periods=[CalendarPeriod(date(2026, 10, 5), date(2026, 10, 1), "blackout", "x")])
