import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import PlanningAudit, TargetCluster, Workload
from ..schemas import (
    CapacityEvaluationResponse,
    ClusterCapacityResult,
    PrismClusterReconciliation,
    PrismReconciliationResponse,
    TargetClusterIn,
    TargetClusterOut,
    WaveDemand as WaveDemandSchema,
)
from ..services.capacity import (
    calculate_wave_demand,
    evaluate_cluster,
    normalize_prism_cluster_inventory,
    reconcile_prism_clusters,
)
from ..services.nutanix import NutanixClient, NutanixNotConfigured

router = APIRouter(prefix="/api/v1/capacity", tags=["capacity"])


@router.get("/clusters", response_model=list[TargetClusterOut])
def list_target_clusters(db: Session = Depends(get_db)):
    return list(db.scalars(select(TargetCluster).order_by(TargetCluster.name)))


@router.post("/clusters", response_model=TargetClusterOut)
def create_target_cluster(payload: TargetClusterIn, db: Session = Depends(get_db)):
    existing = db.scalar(select(TargetCluster).where(TargetCluster.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail=f"Target cluster '{payload.name}' already exists")

    cluster = TargetCluster(**payload.model_dump())
    db.add(cluster)
    db.flush()
    db.add(
        PlanningAudit(
            event_type="target_cluster.created",
            entity=cluster.name,
            detail=json.dumps(payload.model_dump()),
        )
    )
    db.commit()
    db.refresh(cluster)
    return cluster


@router.delete("/clusters/{cluster_id}")
def delete_target_cluster(cluster_id: int, db: Session = Depends(get_db)):
    cluster = db.get(TargetCluster, cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Target cluster not found")
    name = cluster.name
    db.delete(cluster)
    db.add(PlanningAudit(event_type="target_cluster.deleted", entity=name, detail="{}"))
    db.commit()
    return {"deleted": cluster_id, "name": name}


@router.get("/waves/{wave_number}/evaluate", response_model=CapacityEvaluationResponse)
def evaluate_wave_capacity(
    wave_number: int,
    headroom_percent: float = Query(20.0, ge=0, le=50),
    db: Session = Depends(get_db),
):
    workloads = list(db.scalars(select(Workload).where(Workload.wave_number == wave_number)))
    if not workloads:
        raise HTTPException(status_code=404, detail=f"Migration wave {wave_number} does not exist")

    clusters = list(db.scalars(select(TargetCluster).order_by(TargetCluster.name)))
    if not clusters:
        raise HTTPException(status_code=409, detail="No target clusters are configured")

    demand = calculate_wave_demand(wave_number, workloads)
    candidates = [evaluate_cluster(c, demand, headroom_percent) for c in clusters]
    candidates.sort(key=lambda x: (not x["fit"], -x["score"], x["cluster_name"]))

    db.add(
        PlanningAudit(
            event_type="capacity.evaluated",
            entity=f"wave:{wave_number}",
            detail=json.dumps(
                {
                    "headroom_percent": headroom_percent,
                    "demand": demand.to_dict(),
                    "candidates": candidates,
                }
            ),
        )
    )
    db.commit()

    return CapacityEvaluationResponse(
        headroom_percent=headroom_percent,
        demand=WaveDemandSchema(**demand.to_dict()),
        candidates=[ClusterCapacityResult(**x) for x in candidates],
    )


@router.get("/prism-reconcile", response_model=PrismReconciliationResponse)
def prism_reconcile(db: Session = Depends(get_db)):
    try:
        payload = NutanixClient().list_clusters(limit=100)
    except NutanixNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Prism Central request failed: {exc}") from exc

    prism_items = normalize_prism_cluster_inventory(payload)
    local_clusters = list(db.scalars(select(TargetCluster)))
    results = reconcile_prism_clusters(prism_items, local_clusters)
    matched = sum(x["status"] == "Matched" for x in results)

    return PrismReconciliationResponse(
        prism_clusters=len(results),
        matched=matched,
        unmatched=len(results) - matched,
        results=[PrismClusterReconciliation(**x) for x in results],
    )


@router.get("/audit")
def audit(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    rows = list(
        db.scalars(
            select(PlanningAudit)
            .order_by(PlanningAudit.created_at.desc())
            .limit(limit)
        )
    )
    return [
        {
            "id": row.id,
            "event_type": row.event_type,
            "entity": row.entity,
            "detail": row.detail,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
