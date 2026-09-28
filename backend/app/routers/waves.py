from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Workload
from ..schemas import WaveSummary
from ..services.scoring import score_workload
from ..services.waves import plan_waves
import json

router = APIRouter(prefix="/api/v1/waves", tags=["waves"])


@router.post("/plan", response_model=WaveSummary)
def create_plan(
    max_vms: int = Query(20, ge=1, le=200),
    max_storage_gb: float = Query(5000, ge=1),
    db: Session = Depends(get_db),
):
    workloads = list(db.scalars(select(Workload)))
    for w in workloads:
        if w.migration_score is None:
            score, risk, reasons = score_workload(w)
            w.migration_score = score
            w.migration_risk = risk
            w.migration_reasons = json.dumps(reasons)
    waves = plan_waves(workloads, max_vms=max_vms, max_storage_gb=max_storage_gb)
    db.commit()
    return WaveSummary(waves=len(waves), workloads=len(workloads))
