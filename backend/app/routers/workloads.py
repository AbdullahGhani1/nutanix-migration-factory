from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Workload
from ..schemas import WorkloadOut

router = APIRouter(prefix="/api/v1/workloads", tags=["workloads"])


@router.get("", response_model=list[WorkloadOut])
def list_workloads(db: Session = Depends(get_db)):
    return list(db.scalars(select(Workload).order_by(Workload.name)))
