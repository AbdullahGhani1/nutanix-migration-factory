import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .observability import ObservabilityMiddleware
from .security import ServiceKeyRBACMiddleware
from .routers import approvals, assessments, capacity, dependencies, executions, imports, nutanix, operations, optimizer, planning, reports, validation, waves, workloads

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI(
    title="Nutanix Migration Factory API",
    version="0.9.0",
    description=(
        "VMware-to-Nutanix migration inventory, complexity assessment, network mapping, "
        "readiness control, AHV target capacity planning, governance/approvals, dependency-aware "
        "wave optimization, execution evidence, runbook generation, Terraform and Ansible automation exports, technical validation evidence, CAB/change-package generation, reporting, observability and Prism Central discovery."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ServiceKeyRBACMiddleware)
app.add_middleware(ObservabilityMiddleware)

app.include_router(imports.router)
app.include_router(workloads.router)
app.include_router(assessments.router)
app.include_router(waves.router)
app.include_router(optimizer.router)
app.include_router(planning.router)
app.include_router(capacity.router)
app.include_router(approvals.router)
app.include_router(dependencies.router)
app.include_router(executions.router)
app.include_router(validation.router)
app.include_router(reports.router)
app.include_router(nutanix.router)
app.include_router(operations.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "nutanix-migration-factory",
        "version": "0.9.0",
        "auth_enabled": settings.auth_enabled,
    }
