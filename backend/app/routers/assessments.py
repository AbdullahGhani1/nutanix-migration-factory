import json
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Workload
from ..schemas import AssessmentSummary
from ..services.scoring import score_workload

router = APIRouter(prefix="/api/v1/assessments", tags=["assessments"])


@router.post("/run", response_model=AssessmentSummary)
def run_assessment(db: Session = Depends(get_db)):
    workloads = list(db.scalars(select(Workload)))
    counts = {"Low": 0, "Medium": 0, "High": 0}
    for w in workloads:
        score, risk, reasons = score_workload(w)
        w.migration_score = score
        w.migration_risk = risk
        w.migration_reasons = json.dumps(reasons)
        counts[risk] += 1
    db.commit()
    return AssessmentSummary(assessed=len(workloads), low=counts["Low"], medium=counts["Medium"], high=counts["High"])
