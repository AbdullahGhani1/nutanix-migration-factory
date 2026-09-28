import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import PlanningAudit, Workload, WorkloadDependency
from ..services.scoring import score_workload
from ..services.wave_optimizer import optimize_waves

router = APIRouter(prefix="/api/v1/optimizer", tags=["optimizer"])


@router.post("/waves")
def optimize_migration_waves(
    max_vms: int = Query(20, ge=1, le=200),
    max_vcpu: int = Query(160, ge=1),
    max_memory_gb: float = Query(512, gt=0),
    max_storage_gb: float = Query(5000, gt=0),
    strategy: str = Query("pilot_first"),
    db: Session = Depends(get_db),
):
    workloads = list(db.scalars(select(Workload).order_by(Workload.name)))
    if not workloads:
        raise HTTPException(status_code=409, detail="No workloads are loaded")

    for workload in workloads:
        if workload.migration_score is None:
            score, risk, reasons = score_workload(workload)
            workload.migration_score = score
            workload.migration_risk = risk
            workload.migration_reasons = json.dumps(reasons)

    dependencies = list(db.scalars(select(WorkloadDependency).order_by(WorkloadDependency.id)))

    try:
        result = optimize_waves(
            workloads,
            dependencies,
            max_vms=max_vms,
            max_vcpu=max_vcpu,
            max_memory_gb=max_memory_gb,
            max_storage_gb=max_storage_gb,
            strategy=strategy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result["has_cycle"]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Cannot optimize migration waves while application dependency cycles exist",
                "unresolved_groups": result["unresolved_groups"],
            },
        )

    db.add(
        PlanningAudit(
            event_type="waves.optimized",
            entity=f"strategy:{strategy}",
            detail=json.dumps(result),
        )
    )
    db.commit()
    return result
