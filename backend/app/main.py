from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .db import Base, engine
from .routers import imports, workloads, assessments, waves, reports, nutanix

settings = get_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Nutanix Migration Factory API",
    version="0.1.0",
    description="Migration inventory, assessment, wave planning and Prism Central discovery API.",
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
app.include_router(reports.router)
app.include_router(nutanix.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "nutanix-migration-factory", "version": "0.1.0"}
