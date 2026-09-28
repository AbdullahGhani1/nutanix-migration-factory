import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import PlanningAudit, Workload, WorkloadDependency
from ..schemas import (
    DependencyCreate,
    DependencyGraphEdge,
    DependencyGraphNode,
    DependencyGraphResponse,
    DependencyOut,
)
from ..services.dependencies import dependency_order

router = APIRouter(prefix="/api/v1/dependencies", tags=["dependencies"])


@router.get("", response_model=list[DependencyOut])
def list_dependencies(db: Session = Depends(get_db)):
    return list(db.scalars(select(WorkloadDependency).order_by(WorkloadDependency.id)))


@router.post("", response_model=DependencyOut)
def create_dependency(payload: DependencyCreate, db: Session = Depends(get_db)):
    if payload.upstream_workload_id == payload.downstream_workload_id:
        raise HTTPException(status_code=400, detail="A workload cannot depend on itself")

    upstream = db.get(Workload, payload.upstream_workload_id)
    downstream = db.get(Workload, payload.downstream_workload_id)
    if not upstream or not downstream:
        raise HTTPException(status_code=404, detail="One or both workloads do not exist")

    existing = db.scalar(
        select(WorkloadDependency).where(
            WorkloadDependency.upstream_workload_id == payload.upstream_workload_id,
            WorkloadDependency.downstream_workload_id == payload.downstream_workload_id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Dependency already exists")

    edge = WorkloadDependency(**payload.model_dump())
    db.add(edge)
    db.flush()

    # Validate the complete graph before committing a dependency that would
    # introduce a circular application dependency.
    all_edges = list(db.scalars(select(WorkloadDependency)))
    node_ids = list(db.scalars(select(Workload.id)))
    graph = dependency_order(
        node_ids,
        [(x.upstream_workload_id, x.downstream_workload_id) for x in all_edges],
    )
    if graph["has_cycle"]:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Dependency would introduce a cycle",
                "unresolved_workload_ids": graph["unresolved"],
            },
        )

    db.add(
        PlanningAudit(
            event_type="dependency.created",
            entity=f"{upstream.name}->{downstream.name}",
            detail=json.dumps(payload.model_dump()),
        )
    )
    db.commit()
    db.refresh(edge)
    return edge


@router.delete("/{dependency_id}")
def delete_dependency(dependency_id: int, db: Session = Depends(get_db)):
    edge = db.get(WorkloadDependency, dependency_id)
    if not edge:
        raise HTTPException(status_code=404, detail="Dependency not found")
    db.delete(edge)
    db.add(
        PlanningAudit(
            event_type="dependency.deleted",
            entity=f"dependency:{dependency_id}",
            detail="{}",
        )
    )
    db.commit()
    return {"deleted": dependency_id}


@router.get("/graph", response_model=DependencyGraphResponse)
def graph(db: Session = Depends(get_db)):
    workloads = list(db.scalars(select(Workload).order_by(Workload.name)))
    edges = list(db.scalars(select(WorkloadDependency).order_by(WorkloadDependency.id)))
    ordered = dependency_order(
        [w.id for w in workloads],
        [(e.upstream_workload_id, e.downstream_workload_id) for e in edges],
    )
    return DependencyGraphResponse(
        nodes=[
            DependencyGraphNode(id=w.id, name=w.name, wave_number=w.wave_number)
            for w in workloads
        ],
        edges=[
            DependencyGraphEdge(
                id=e.id,
                upstream_workload_id=e.upstream_workload_id,
                downstream_workload_id=e.downstream_workload_id,
                dependency_type=e.dependency_type,
            )
            for e in edges
        ],
        has_cycle=ordered["has_cycle"],
        start_order=ordered["start_order"],
        stop_order=ordered["stop_order"],
    )


@router.get("/waves/{wave_number}/order")
def wave_order(wave_number: int, db: Session = Depends(get_db)):
    workloads = list(db.scalars(select(Workload).where(Workload.wave_number == wave_number)))
    if not workloads:
        raise HTTPException(status_code=404, detail=f"Migration wave {wave_number} does not exist")

    ids = {w.id for w in workloads}
    edges = list(
        db.scalars(
            select(WorkloadDependency).where(
                or_(
                    WorkloadDependency.upstream_workload_id.in_(ids),
                    WorkloadDependency.downstream_workload_id.in_(ids),
                )
            )
        )
    )
    in_wave_edges = [
        (e.upstream_workload_id, e.downstream_workload_id)
        for e in edges
        if e.upstream_workload_id in ids and e.downstream_workload_id in ids
    ]
    ordered = dependency_order(list(ids), in_wave_edges)
    by_id = {w.id: w.name for w in workloads}
    return {
        "wave": wave_number,
        "has_cycle": ordered["has_cycle"],
        "start_order": [by_id[x] for x in ordered["start_order"]],
        "stop_order": [by_id[x] for x in ordered["stop_order"]],
        "unresolved": [by_id[x] for x in ordered["unresolved"]],
    }
