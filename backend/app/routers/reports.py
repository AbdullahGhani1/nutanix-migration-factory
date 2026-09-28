import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Workload

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/migration-plan.csv")
def migration_plan_csv(db: Session = Depends(get_db)):
    workloads = list(db.scalars(select(Workload).order_by(Workload.wave_number, Workload.app_group, Workload.name)))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Wave", "App Group", "VM", "CPU", "Memory GB", "Storage GB", "OS", "Source Network",
        "Target Network", "Criticality", "Downtime Minutes", "Complexity Score", "Risk", "Reasons", "Owner"
    ])
    for w in workloads:
        writer.writerow([
            w.wave_number or "", w.app_group, w.name, w.cpu, w.memory_gb, w.storage_gb, w.os,
            w.source_network, w.target_network, w.criticality, w.downtime_minutes,
            w.migration_score or "", w.migration_risk or "", w.migration_reasons or "", w.owner,
        ])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=migration-plan.csv"
    })
