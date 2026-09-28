from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import ImportBatch, MigrationApproval, Workload, WorkloadDependency
from ..schemas import ImportResult
from ..services.rvtools import parse_inventory

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])


@router.post("/rvtools", response_model=ImportResult)
async def import_rvtools(file: UploadFile = File(...), db: Session = Depends(get_db)):
    data = await file.read()
    try:
        rows = parse_inventory(file.filename or "inventory.csv", data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not rows:
        raise HTTPException(status_code=400, detail="Inventory contains no workload rows")

    batch = ImportBatch(filename=file.filename or "inventory", row_count=len(rows))
    db.add(batch)
    db.flush()

    # Each import becomes the active estate. Planning artifacts tied to the prior
    # workload IDs/waves are invalidated before the new inventory is persisted.
    db.execute(delete(WorkloadDependency))
    db.execute(delete(MigrationApproval))
    db.execute(delete(Workload))
    for row in rows:
        db.add(Workload(batch_id=batch.id, **row))
    db.commit()
    return ImportResult(batch_id=batch.id, filename=batch.filename, imported=len(rows))
