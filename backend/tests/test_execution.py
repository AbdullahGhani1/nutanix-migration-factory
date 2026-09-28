from datetime import datetime
from types import SimpleNamespace

import pytest

from app.services.execution import transition_execution


def execution(status="Planned", **overrides):
    values = dict(
        status=status,
        started_at=None,
        completed_at=None,
        rollback_executed=False,
        uat_status="NotRun",
        cutover_duration_minutes=None,
        validation_summary="",
        rollback_reason="",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def payload(action, **overrides):
    values = dict(
        action=action,
        actor="engineer",
        cutover_duration_minutes=None,
        uat_status=None,
        validation_summary="",
        rollback_reason="",
        evidence_reference=None,
        notes="",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_execution_happy_path_records_measured_result():
    started = datetime(2026, 9, 28, 10, 0)
    completed = datetime(2026, 9, 28, 10, 12)

    start = transition_execution(execution(), payload("start"), now=started)
    assert start.status == "InProgress"
    assert start.started_at == started

    current = execution(status="InProgress", started_at=start.started_at)
    done = transition_execution(
        current,
        payload(
            "complete",
            cutover_duration_minutes=12,
            uat_status="Passed",
            validation_summary="Guest boot, DNS and application smoke test passed.",
        ),
        now=completed,
    )
    assert done.status == "Succeeded"
    assert done.cutover_duration_minutes == 12
    assert done.uat_status == "Passed"
    assert done.completed_at == completed


def test_success_requires_uat_duration_and_validation():
    with pytest.raises(ValueError):
        transition_execution(
            execution(status="InProgress", started_at=datetime.utcnow()),
            payload("complete", uat_status="Passed"),
        )


def test_rollback_requires_reason_and_marks_rollback():
    current = execution(status="InProgress", started_at=datetime.utcnow())
    result = transition_execution(
        current,
        payload(
            "rollback",
            rollback_reason="Application health check failed",
            validation_summary="Target service did not pass smoke test",
        ),
    )
    assert result.status == "RolledBack"
    assert result.rollback_executed is True
    assert result.rollback_reason == "Application health check failed"


def test_terminal_execution_cannot_be_changed():
    with pytest.raises(ValueError):
        transition_execution(execution(status="Succeeded"), payload("start"))
