import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import MigrationExecution, PlanningAudit, TechnicalValidationRecord
from ..schemas import TechnicalValidationCreate, TechnicalValidationOut
from ..services.technical_validation import normalize_validation_payload

router = APIRouter(prefix="/api/v1/validation", tags=["validation"])


@router.get("", response_model=list[TechnicalValidationOut])
def list_validation_records(db: Session = Depends(get_db)):
    return list(
        db.scalars(
            select(TechnicalValidationRecord).order_by(
                TechnicalValidationRecord.recorded_at.desc()
            )
        )
    )


@router.get("/executions/{execution_id}", response_model=list[TechnicalValidationOut])
def execution_validation_records(execution_id: int, db: Session = Depends(get_db)):
    execution = db.get(MigrationExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Migration execution not found")
    return list(
        db.scalars(
            select(TechnicalValidationRecord)
            .where(TechnicalValidationRecord.execution_id == execution_id)
            .order_by(TechnicalValidationRecord.recorded_at)
        )
    )


@router.post("/executions/{execution_id}", response_model=TechnicalValidationOut)
def record_execution_validation(
    execution_id: int,
    payload: TechnicalValidationCreate,
    db: Session = Depends(get_db),
):
    execution = db.get(MigrationExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Migration execution not found")
    if execution.status == "Planned":
        raise HTTPException(
            status_code=409,
            detail="Technical validation cannot be recorded before migration execution starts",
        )

    try:
        normalized = normalize_validation_payload(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record = TechnicalValidationRecord(
        execution_id=execution.id,
        **normalized,
    )
    db.add(record)
    db.flush()

    db.add(
        PlanningAudit(
            event_type=f"validation.{record.status.lower()}",
            entity=f"validation:{record.id}",
            detail=json.dumps(
                {
                    "execution_id": execution.id,
                    "wave": execution.wave_number,
                    "tool": record.tool,
                    "status": record.status,
                    "hosts_total": record.hosts_total,
                    "hosts_passed": record.hosts_passed,
                    "hosts_failed": record.hosts_failed,
                    "prism_validation": record.prism_validation,
                    "guest_validation": record.guest_validation,
                    "artifact_sha256": record.artifact_sha256,
                    "evidence_reference": record.evidence_reference,
                    "actor": record.actor,
                }
            ),
        )
    )
    db.commit()
    db.refresh(record)
    return record
