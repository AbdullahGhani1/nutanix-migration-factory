from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Workload, WorkloadDependency
from ..schemas import (
    NetworkMappingRequest,
    NetworkMappingResponse,
    ReadinessResponse,
    ReadinessWorkload,
)
from ..services.dependencies import dependency_order
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

    ids = {w.id for w in workloads}
    edges = list(db.scalars(select(WorkloadDependency)))
    wave_edges = [
        (e.upstream_workload_id, e.downstream_workload_id)
        for e in edges
        if e.upstream_workload_id in ids and e.downstream_workload_id in ids
    ]
    ordering = dependency_order(list(ids), wave_edges)
    by_id = {w.id: w.name for w in workloads}

    return build_wave_runbook(
        wave_number,
        workloads,
        start_order=[by_id[x] for x in ordering["start_order"]],
        stop_order=[by_id[x] for x in ordering["stop_order"]],
        dependency_cycle=ordering["has_cycle"],
    )
