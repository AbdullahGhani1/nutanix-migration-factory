import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import MigrationApproval, PlanningAudit, TargetCluster, Workload
from ..schemas import ApprovalDecision, ApprovalOut, ApprovalRequest
from ..services.capacity import calculate_wave_demand, evaluate_cluster
from ..services.readiness import evaluate_workload

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalOut])
def list_approvals(db: Session = Depends(get_db)):
    return list(db.scalars(select(MigrationApproval).order_by(MigrationApproval.requested_at.desc())))


@router.post("/waves/{wave_number}/request", response_model=ApprovalOut)
def request_approval(
    wave_number: int,
    payload: ApprovalRequest,
    db: Session = Depends(get_db),
):
    workloads = list(db.scalars(select(Workload).where(Workload.wave_number == wave_number)))
    if not workloads:
        raise HTTPException(status_code=404, detail=f"Migration wave {wave_number} does not exist")

    target = db.get(TargetCluster, payload.target_cluster_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target cluster not found")

    blocked = [r for r in (evaluate_workload(w) for w in workloads) if r.status == "Blocked"]
    if blocked:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Wave cannot enter approval while readiness blockers remain",
                "blocked": [{"name": r.name, "blockers": r.blockers} for r in blocked],
            },
        )

    demand = calculate_wave_demand(wave_number, workloads)
    placement = evaluate_cluster(target, demand, payload.headroom_percent)
    if not placement["fit"]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Selected target cluster does not satisfy capacity policy",
                "cluster": target.name,
                "reasons": placement["reasons"],
            },
        )

    existing = db.scalar(
        select(MigrationApproval).where(
            MigrationApproval.wave_number == wave_number,
            MigrationApproval.status == "Pending",
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Wave {wave_number} already has a pending approval")

    approval = MigrationApproval(
        wave_number=wave_number,
        target_cluster_id=target.id,
        requested_by=payload.requested_by,
        change_ticket=payload.change_ticket,
        notes=payload.notes,
        headroom_percent=payload.headroom_percent,
        status="Pending",
    )
    db.add(approval)
    db.flush()
    db.add(
        PlanningAudit(
            event_type="approval.requested",
            entity=f"approval:{approval.id}",
            detail=json.dumps(
                {
                    "wave": wave_number,
                    "target_cluster": target.name,
                    "requested_by": payload.requested_by,
                    "change_ticket": payload.change_ticket,
                    "headroom_percent": payload.headroom_percent,
                }
            ),
        )
    )
    db.commit()
    db.refresh(approval)
    return approval


@router.post("/{approval_id}/decision", response_model=ApprovalOut)
def decide_approval(
    approval_id: int,
    payload: ApprovalDecision,
    db: Session = Depends(get_db),
):
    approval = db.get(MigrationApproval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if approval.status != "Pending":
        raise HTTPException(status_code=409, detail=f"Approval is already {approval.status}")

    decision = payload.decision.strip().title()
    if decision not in {"Approved", "Rejected"}:
        raise HTTPException(status_code=400, detail="decision must be Approved or Rejected")

    approval.status = decision
    approval.decided_by = payload.decided_by
    approval.decided_at = datetime.utcnow()
    approval.decision_notes = payload.notes

    db.add(
        PlanningAudit(
            event_type=f"approval.{decision.lower()}",
            entity=f"approval:{approval.id}",
            detail=json.dumps(
                {
                    "wave": approval.wave_number,
                    "decided_by": payload.decided_by,
                    "notes": payload.notes,
                }
            ),
        )
    )
    db.commit()
    db.refresh(approval)
    return approval
