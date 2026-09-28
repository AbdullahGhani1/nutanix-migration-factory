from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


TERMINAL_STATUSES = {"Succeeded", "RolledBack", "Failed"}
VALID_UAT = {"NotRun", "Passed", "Conditional", "Failed"}


@dataclass(frozen=True)
class TransitionResult:
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    rollback_executed: bool
    uat_status: str
    cutover_duration_minutes: float | None
    validation_summary: str
    rollback_reason: str


def transition_execution(execution, payload, now: datetime | None = None) -> TransitionResult:
    """Validate and calculate a migration execution state transition.

    The function records operator-provided evidence; it does not claim that
    Nutanix Move executed successfully on its own.
    """
    now = now or datetime.utcnow()
    action = (payload.action or "").strip().lower()
    current = execution.status

    if current in TERMINAL_STATUSES:
        raise ValueError(f"Execution is already terminal: {current}")

    if action == "start":
        if current != "Planned":
            raise ValueError("Only Planned executions can be started")
        return TransitionResult(
            status="InProgress",
            started_at=execution.started_at or now,
            completed_at=None,
            rollback_executed=False,
            uat_status=execution.uat_status or "NotRun",
            cutover_duration_minutes=execution.cutover_duration_minutes,
            validation_summary=execution.validation_summary or "",
            rollback_reason="",
        )

    if current != "InProgress":
        raise ValueError("Execution must be InProgress before it can be completed, failed or rolled back")

    if action == "complete":
        uat = (payload.uat_status or "").strip().title()
        if uat not in {"Passed", "Conditional"}:
            raise ValueError("Successful completion requires uat_status Passed or Conditional")
        if payload.cutover_duration_minutes is None:
            raise ValueError("Successful completion requires cutover_duration_minutes")
        if not (payload.validation_summary or "").strip():
            raise ValueError("Successful completion requires validation_summary")
        return TransitionResult(
            status="Succeeded",
            started_at=execution.started_at,
            completed_at=now,
            rollback_executed=False,
            uat_status=uat,
            cutover_duration_minutes=float(payload.cutover_duration_minutes),
            validation_summary=payload.validation_summary.strip(),
            rollback_reason="",
        )

    if action == "rollback":
        reason = (payload.rollback_reason or "").strip()
        if not reason:
            raise ValueError("Rollback requires rollback_reason")
        uat = (payload.uat_status or "Failed").strip().title()
        if uat not in VALID_UAT:
            raise ValueError(f"Invalid uat_status: {uat}")
        return TransitionResult(
            status="RolledBack",
            started_at=execution.started_at,
            completed_at=now,
            rollback_executed=True,
            uat_status=uat,
            cutover_duration_minutes=payload.cutover_duration_minutes,
            validation_summary=(payload.validation_summary or "").strip(),
            rollback_reason=reason,
        )

    if action == "fail":
        summary = (payload.validation_summary or "").strip()
        if not summary:
            raise ValueError("Failed execution requires validation_summary")
        uat = (payload.uat_status or "Failed").strip().title()
        if uat not in VALID_UAT:
            raise ValueError(f"Invalid uat_status: {uat}")
        return TransitionResult(
            status="Failed",
            started_at=execution.started_at,
            completed_at=now,
            rollback_executed=False,
            uat_status=uat,
            cutover_duration_minutes=payload.cutover_duration_minutes,
            validation_summary=summary,
            rollback_reason=(payload.rollback_reason or "").strip(),
        )

    raise ValueError("action must be start, complete, rollback or fail")
