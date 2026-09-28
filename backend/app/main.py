from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import Base, engine
from .routers import approvals, assessments, capacity, dependencies, imports, nutanix, planning, reports, waves, workloads

settings = get_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Nutanix Migration Factory API",
    version="0.3.0",
    description=(
        "VMware-to-Nutanix migration inventory, complexity assessment, network mapping, "
        "readiness control, AHV target capacity planning, governance/approvals, dependency-aware "
        "wave planning, runbook generation, reporting and Prism Central discovery."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(imports.router)
app.include_router(workloads.router)
app.include_router(assessments.router)
app.include_router(waves.router)
app.include_router(planning.router)
app.include_router(capacity.router)
app.include_router(approvals.router)
app.include_router(dependencies.router)
app.include_router(reports.router)
app.include_router(nutanix.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "nutanix-migration-factory",
        "version": "0.3.0",
    }
