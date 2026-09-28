import json
from datetime import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import PlanningAudit, TargetCluster, Workload
from ..schemas import (
    ChangeCalendarRequest,
    DRPlanRequest,
    ResidencyRequest,
    ResidencyResponse,
    ResidencyWorkload,
)
from ..services.change_calendar import DEFAULT_WINDOWS, CalendarPeriod, WindowTemplate, schedule_waves
from ..services.dr_planner import plan_protection
from ..services.residency import evaluate_residency, load_policy, summarize_residency

router = APIRouter(prefix="/api/v1/controls", tags=["enterprise-controls"])


def residency_policy():
    try:
        return load_policy(get_settings().residency_policy_json)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid RESIDENCY_POLICY_JSON: {exc}") from exc


def _cluster(db: Session, cluster_id: int | None, label: str):
    if cluster_id is None:
        return None
    cluster = db.get(TargetCluster, cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail=f"{label} cluster {cluster_id} not found")
    return cluster


def _workloads(db: Session, wave: int | None):
    query = select(Workload).order_by(Workload.name)
    if wave is not None:
        query = query.where(Workload.wave_number == wave)
    workloads = list(db.scalars(query))
    if not workloads:
        raise HTTPException(
            status_code=404,
            detail=f"Migration wave {wave} does not exist" if wave is not None else "No workloads are loaded",
        )
    return workloads


@router.get("/residency/policy")
def get_residency_policy():
    return residency_policy()


@router.post("/residency", response_model=ResidencyResponse)
def check_residency(payload: ResidencyRequest, db: Session = Depends(get_db)):
    primary = _cluster(db, payload.cluster_id, "Primary")
    dr = _cluster(db, payload.dr_cluster_id, "DR")
    if dr is not None and dr.id == primary.id:
        raise HTTPException(status_code=400, detail="DR cluster must differ from the primary cluster")

    policy = residency_policy()
    results = [evaluate_residency(w, primary, dr, policy) for w in _workloads(db, payload.wave)]
    summary = summarize_residency(results)
    db.add(
        PlanningAudit(
            event_type="residency.evaluated",
            entity=f"wave:{payload.wave}" if payload.wave is not None else "estate",
            detail=json.dumps({"cluster": primary.name, "dr_cluster": dr.name if dr else None, **summary}),
        )
    )
    db.commit()
    return ResidencyResponse(
        cluster=primary.name,
        dr_cluster=dr.name if dr else None,
        **summary,
        workloads=[ResidencyWorkload(**r.to_dict()) for r in results],
    )


@router.post("/dr-plan")
def dr_plan(payload: DRPlanRequest, db: Session = Depends(get_db)):
    workloads = _workloads(db, payload.wave)
    primary = _cluster(db, payload.primary_cluster_id, "Primary")
    dr = _cluster(db, payload.dr_cluster_id, "DR")

    result = plan_protection(
        workloads,
        site_rtt_ms=payload.site_rtt_ms,
        sync_max_rtt_ms=payload.sync_max_rtt_ms,
        daily_change_rate_percent=payload.daily_change_rate_percent,
        nearsync_max_minutes=payload.nearsync_max_minutes,
        available_bandwidth_mbps=payload.available_bandwidth_mbps,
        peak_factor=payload.peak_factor,
    )

    if dr is not None:
        policy = residency_policy()
        for w in workloads:
            check = evaluate_residency(w, primary, dr, policy)
            result["blockers"].extend(f"{w.name}: {v}" for v in check.violations if v.startswith("DR "))
            if check.status == "Unverified":
                result["warnings"].extend(f"{w.name}: {x}" for x in check.warnings if "country_code" in x)
        result["warnings"] = sorted(set(result["warnings"]))
        if result["blockers"]:
            result["status"] = "Blocked"

    result["primary_cluster"] = primary.name if primary else None
    result["dr_cluster"] = dr.name if dr else None
    db.add(
        PlanningAudit(
            event_type="dr.planned",
            entity=f"wave:{payload.wave}" if payload.wave is not None else "estate",
            detail=json.dumps(
                {
                    "status": result["status"],
                    "policies": [p["name"] for p in result["policies"]],
                    "total_avg_replication_mbps": result["total_avg_replication_mbps"],
                    "dr_cluster": result["dr_cluster"],
                }
            ),
        )
    )
    db.commit()
    return result


@router.post("/change-calendar/schedule")
def change_calendar(payload: ChangeCalendarRequest, db: Session = Depends(get_db)):
    planned = list(db.scalars(select(Workload).where(Workload.wave_number.is_not(None))))
    if not planned:
        raise HTTPException(status_code=409, detail="No migration waves are planned")
    waves: dict[int, list] = {}
    for w in planned:
        waves.setdefault(w.wave_number, []).append(w)

    templates = DEFAULT_WINDOWS
    if payload.windows:
        templates = tuple(
            WindowTemplate(weekday=x.weekday, start=time.fromisoformat(x.start), duration_minutes=x.duration_minutes)
            for x in payload.windows
        )
    periods = [CalendarPeriod(start=p.start, end=p.end, kind=p.kind, reason=p.reason) for p in payload.periods]

    try:
        result = schedule_waves(
            waves,
            payload.start_date,
            periods=periods,
            templates=templates,
            weeks=payload.weeks,
            min_gap_days=payload.min_gap_days,
            parallel_cutovers=payload.parallel_cutovers,
            per_vm_cutover_minutes=payload.per_vm_cutover_minutes,
            precheck_minutes=payload.precheck_minutes,
            validation_minutes=payload.validation_minutes,
            rollback_reserve_minutes=payload.rollback_reserve_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.add(
        PlanningAudit(
            event_type="change_calendar.scheduled",
            entity=f"start:{payload.start_date.isoformat()}",
            detail=json.dumps(
                {
                    "scheduled": [(s["wave"], s["window_start_local"]) for s in result["scheduled"]],
                    "unscheduled": [u["wave"] for u in result["unscheduled"]],
                    "periods": len(periods),
                }
            ),
        )
    )
    db.commit()
    return result
