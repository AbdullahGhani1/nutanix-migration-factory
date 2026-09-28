from fastapi import APIRouter, HTTPException, Query
from ..services.nutanix import NutanixClient, NutanixNotConfigured

router = APIRouter(prefix="/api/v1/nutanix", tags=["nutanix"])


def _client():
    try:
        return NutanixClient()
    except NutanixNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/clusters")
def clusters(limit: int = Query(50, ge=1, le=100)):
    try:
        return _client().list_clusters(limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Prism Central request failed: {exc}") from exc


@router.get("/vms")
def vms(limit: int = Query(50, ge=1, le=100)):
    try:
        return _client().list_vms(limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Prism Central request failed: {exc}") from exc
