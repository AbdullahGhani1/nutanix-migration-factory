import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import MigrationApproval, MigrationExecution, PlanningAudit
from ..schemas import ExecutionCreate, ExecutionOut, ExecutionTransition
from ..services.execution import transition_execution

router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


@router.get("", response_model=list[ExecutionOut])
def list_executions(db: Session = Depends(get_db)):
    return list(
        db.scalars(
            select(MigrationExecution).order_by(MigrationExecution.created_at.desc())
        )
    )


@router.post("", response_model=ExecutionOut)
def create_execution(payload: ExecutionCreate, db: Session = Depends(get_db)):
    approval = db.get(MigrationApproval, payload.approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Migration approval not found")
    if approval.status != "Approved":
        raise HTTPException(
            status_code=409,
            detail="Migration execution can only be created from an Approved request",
        )

    existing = db.scalar(
        select(MigrationExecution).where(
            MigrationExecution.approval_id == approval.id
        )
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Approval {approval.id} already has execution record {existing.id}",
        )

    execution = MigrationExecution(
        approval_id=approval.id,
        wave_number=approval.wave_number,
        target_cluster_id=approval.target_cluster_id,
        status="Planned",
        operator=payload.operator,
        move_plan_name=payload.move_plan_name,
        change_ticket=approval.change_ticket,
        evidence_reference=payload.evidence_reference,
        notes=payload.notes,
    )
    db.add(execution)
    db.flush()
    db.add(
        PlanningAudit(
            event_type="execution.created",
            entity=f"execution:{execution.id}",
            detail=json.dumps(
                {
                    "approval_id": approval.id,
                    "wave": approval.wave_number,
                    "operator": payload.operator,
                    "move_plan_name": payload.move_plan_name,
                    "change_ticket": approval.change_ticket,
                }
            ),
        )
    )
    db.commit()
    db.refresh(execution)
    return execution


@router.post("/{execution_id}/transition", response_model=ExecutionOut)
def transition(
    execution_id: int,
    payload: ExecutionTransition,
    db: Session = Depends(get_db),
):
    execution = db.get(MigrationExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Migration execution not found")

    try:
        result = transition_execution(execution, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    before = execution.status
    execution.status = result.status
    execution.started_at = result.started_at
    execution.completed_at = result.completed_at
    execution.rollback_executed = result.rollback_executed
    execution.uat_status = result.uat_status
    execution.cutover_duration_minutes = result.cutover_duration_minutes
    execution.validation_summary = result.validation_summary
    execution.rollback_reason = result.rollback_reason

    if payload.evidence_reference is not None:
        execution.evidence_reference = payload.evidence_reference.strip()
    if payload.notes:
        execution.notes = (
            f"{execution.notes}\n{payload.notes}".strip()
            if execution.notes
            else payload.notes.strip()
        )

    db.add(
        PlanningAudit(
            event_type=f"execution.{result.status.lower()}",
            entity=f"execution:{execution.id}",
            detail=json.dumps(
                {
                    "from": before,
                    "to": result.status,
                    "actor": payload.actor,
                    "wave": execution.wave_number,
                    "cutover_duration_minutes": result.cutover_duration_minutes,
                    "uat_status": result.uat_status,
                    "rollback_executed": result.rollback_executed,
                    "evidence_reference": execution.evidence_reference,
                }
            ),
        )
    )
    db.commit()
    db.refresh(execution)
    return execution


@router.get("/{execution_id}/evidence")
def execution_evidence(execution_id: int, db: Session = Depends(get_db)):
    execution = db.get(MigrationExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Migration execution not found")

    return {
        "execution_id": execution.id,
        "approval_id": execution.approval_id,
        "wave_number": execution.wave_number,
        "target_cluster_id": execution.target_cluster_id,
        "status": execution.status,
        "operator": execution.operator,
        "move_plan_name": execution.move_plan_name,
        "change_ticket": execution.change_ticket,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "cutover_duration_minutes": execution.cutover_duration_minutes,
        "uat_status": execution.uat_status,
        "rollback_executed": execution.rollback_executed,
        "validation_summary": execution.validation_summary,
        "rollback_reason": execution.rollback_reason,
        "evidence_reference": execution.evidence_reference,
        "notes": execution.notes,
        "recorded_at": execution.created_at.isoformat(),
        "provenance": (
            "Operator-recorded execution evidence. This record does not independently "
            "verify Nutanix Move, Prism Central or application-owner systems."
        ),
    }
