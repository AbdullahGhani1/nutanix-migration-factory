from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Workload
from ..schemas import (
    NetworkMappingRequest,
    NetworkMappingResponse,
    ReadinessResponse,
    ReadinessWorkload,
)
from ..services.network_mapping import NetworkRule, apply_network_mapping
from ..services.readiness import evaluate_workload, summarize_readiness
from ..services.runbooks import build_wave_runbook

router = APIRouter(prefix="/api/v1/planning", tags=["planning"])


@router.post("/network-map", response_model=NetworkMappingResponse)
def map_networks(payload: NetworkMappingRequest, db: Session = Depends(get_db)):
    workloads = list(db.scalars(select(Workload)))
    rules = [
        NetworkRule(source=r.source, target=r.target, description=r.description or "")
        for r in payload.rules
    ]
    stats = apply_network_mapping(workloads, rules)
    db.commit()
    return NetworkMappingResponse(total=len(workloads), **stats)


@router.get("/readiness", response_model=ReadinessResponse)
def readiness(db: Session = Depends(get_db)):
    workloads = list(db.scalars(select(Workload)))
    results = [evaluate_workload(w) for w in workloads]
    summary = summarize_readiness(results)
    return ReadinessResponse(
        **summary,
        workloads=[ReadinessWorkload(**r.to_dict()) for r in results],
    )


@router.get("/waves/{wave_number}/runbook")
def wave_runbook(wave_number: int, db: Session = Depends(get_db)):
    workloads = list(
        db.scalars(
            select(Workload)
            .where(Workload.wave_number == wave_number)
            .order_by(Workload.app_group, Workload.name)
        )
    )
    if not workloads:
        raise HTTPException(status_code=404, detail=f"Migration wave {wave_number} does not exist")
    return build_wave_runbook(wave_number, workloads)
