"""Change-window scheduling for migration waves.

Defaults reflect a typical UAE enterprise change calendar: the Monday-Friday
work week introduced in 2022, cutovers on Friday and Saturday nights so Sunday
remains for hypercare, and Gulf Standard Time (UTC+4, no daylight saving).
Public holidays, Ramadan and regulator/business freezes are supplied as data,
because Islamic holiday dates follow moon sighting and are announced officially.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

GST = timezone(timedelta(hours=4), "GST")
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


@dataclass(frozen=True)
class WindowTemplate:
    weekday: int  # 0 = Monday
    start: time
    duration_minutes: int


@dataclass(frozen=True)
class CalendarPeriod:
    start: date
    end: date  # inclusive
    kind: str  # "blackout" | "restricted"
    reason: str


DEFAULT_WINDOWS = (
    WindowTemplate(weekday=4, start=time(22, 0), duration_minutes=480),  # Friday 22:00 -> Saturday 06:00
    WindowTemplate(weekday=5, start=time(22, 0), duration_minutes=480),  # Saturday 22:00 -> Sunday 06:00
)


def is_high_risk(workloads) -> bool:
    return any(
        (w.migration_risk or "") == "High" or (w.criticality or "").title() == "Critical"
        for w in workloads
    )


def required_minutes(
    workloads,
    parallel_cutovers: int = 5,
    per_vm_cutover_minutes: int = 30,
    precheck_minutes: int = 60,
    validation_minutes: int = 60,
    rollback_reserve_minutes: int = 60,
) -> int:
    """Window length a wave needs: prechecks + batched cutovers + validation + rollback reserve."""
    if parallel_cutovers < 1:
        raise ValueError("parallel_cutovers must be at least 1")
    batches = math.ceil(len(workloads) / parallel_cutovers)
    return precheck_minutes + batches * per_vm_cutover_minutes + validation_minutes + rollback_reserve_minutes


def candidate_windows(start: date, weeks: int, templates, tz=GST):
    windows = []
    for offset in range(weeks * 7):
        day = start + timedelta(days=offset)
        for t in templates:
            if day.weekday() == t.weekday:
                begin = datetime.combine(day, t.start, tzinfo=tz)
                windows.append((begin, begin + timedelta(minutes=t.duration_minutes)))
    return sorted(windows)


def _overlapping(begin: datetime, end: datetime, periods, tz=GST):
    hits = []
    for p in periods:
        p_begin = datetime.combine(p.start, time(0, 0), tzinfo=tz)
        p_end = datetime.combine(p.end + timedelta(days=1), time(0, 0), tzinfo=tz)
        if begin < p_end and p_begin < end:
            hits.append(p)
    return hits


def schedule_waves(
    waves: dict[int, list],
    start: date,
    periods: list[CalendarPeriod] | None = None,
    templates=DEFAULT_WINDOWS,
    weeks: int = 26,
    min_gap_days: int = 7,
    tz=GST,
    **duration_kwargs,
) -> dict:
    periods = periods or []
    for p in periods:
        if p.kind not in {"blackout", "restricted"}:
            raise ValueError(f"Unknown calendar period kind '{p.kind}'")
        if p.end < p.start:
            raise ValueError(f"Calendar period '{p.reason}' ends before it starts")

    windows = candidate_windows(start, weeks, templates, tz)
    earliest = datetime.combine(start, time(0, 0), tzinfo=tz)
    used: set[datetime] = set()
    scheduled, unscheduled = [], []

    for wave_number in sorted(waves):
        workloads = waves[wave_number]
        needed = required_minutes(workloads, **duration_kwargs)
        high_risk = is_high_risk(workloads)
        skipped: list[str] = []
        chosen = None

        for begin, end in windows:
            if begin < earliest or begin in used:
                continue
            length = int((end - begin).total_seconds() // 60)
            label = begin.strftime("%a %d %b %Y %H:%M")
            if length < needed:
                skipped.append(f"{label}: window {length} min < required {needed} min")
                continue
            hits = _overlapping(begin, end, periods, tz)
            blackout = [p for p in hits if p.kind == "blackout"]
            restricted = [p for p in hits if p.kind == "restricted"]
            if blackout:
                skipped.append(f"{label}: blackout ({blackout[0].reason})")
                continue
            if restricted and high_risk:
                skipped.append(f"{label}: restricted period ({restricted[0].reason}) excludes high-risk waves")
                continue
            chosen = (begin, end, restricted)
            break

        if chosen is None:
            unscheduled.append({"wave": wave_number, "required_minutes": needed, "reason": "No eligible window in horizon", "skipped": skipped[:10]})
            continue

        begin, end, restricted = chosen
        used.add(begin)
        earliest = end + timedelta(days=min_gap_days)
        scheduled.append(
            {
                "wave": wave_number,
                "workloads": len(workloads),
                "high_risk": high_risk,
                "required_minutes": needed,
                "window_start_local": begin.isoformat(),
                "window_end_local": end.isoformat(),
                "window_start_utc": begin.astimezone(timezone.utc).isoformat(),
                "day": WEEKDAYS[begin.weekday()],
                "notes": [f"Inside restricted period: {p.reason}" for p in restricted],
                "skipped_windows": skipped[:10],
            }
        )

    return {
        "timezone": str(tz),
        "start": start.isoformat(),
        "horizon_weeks": weeks,
        "min_gap_days": min_gap_days,
        "scheduled": scheduled,
        "unscheduled": unscheduled,
    }
