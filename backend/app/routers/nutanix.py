from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Workload
from ..schemas import (
    NetworkReconciliationItem,
    NetworkReconciliationResponse,
    PrismEnvironmentSummary,
)
from ..services.nutanix import (
    NutanixClient,
    NutanixNotConfigured,
    normalize_subnets,
    reconcile_target_networks,
)

router = APIRouter(prefix="/api/v1/nutanix", tags=["nutanix"])


def _client():
    try:
        return NutanixClient()
    except NutanixNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _prism_call(fn):
    try:
        return fn()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Prism Central request failed: {exc}") from exc


@router.get("/connection-test")
def connection_test():
    def run():
        client = _client()
        clusters = client.list_clusters(limit=1)
        subnets = client.list_subnets(limit=1)
        return {
            "connected": True,
            "cluster_endpoint": "ok",
            "subnet_endpoint": "ok",
            "clusters_returned": len(clusters.get("data", [])),
            "subnets_returned": len(subnets.get("data", [])),
        }

    return _prism_call(run)


@router.get("/clusters")
def clusters(limit: int = Query(50, ge=1, le=100)):
    return _prism_call(lambda: _client().list_clusters(limit))


@router.get("/vms")
def vms(limit: int = Query(50, ge=1, le=100)):
    return _prism_call(lambda: _client().list_vms(limit))


@router.get("/subnets")
def subnets(limit: int = Query(100, ge=1, le=100)):
    return _prism_call(lambda: _client().list_subnets(limit))


@router.get("/environment-summary", response_model=PrismEnvironmentSummary)
def environment_summary(max_items: int = Query(1000, ge=1, le=10000)):
    def run():
        snapshot = _client().inventory_snapshot(max_items=max_items)
        return PrismEnvironmentSummary(
            connected=True,
            clusters=len(snapshot["clusters"].get("data", [])),
            vms=len(snapshot["vms"].get("data", [])),
            subnets=len(snapshot["subnets"].get("data", [])),
            cluster_inventory_truncated=bool(
                snapshot["clusters"].get("metadata", {}).get("truncatedByMigrationFactory")
            ),
            vm_inventory_truncated=bool(
                snapshot["vms"].get("metadata", {}).get("truncatedByMigrationFactory")
            ),
            subnet_inventory_truncated=bool(
                snapshot["subnets"].get("metadata", {}).get("truncatedByMigrationFactory")
            ),
        )

    return _prism_call(run)


@router.get("/network-reconcile", response_model=NetworkReconciliationResponse)
def network_reconcile(
    max_items: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    target_names = list(
        db.scalars(
            select(Workload.target_network)
            .where(Workload.target_network != "")
            .distinct()
        )
    )

    def run():
        snapshot = _client()._list_all(
            "/api/networking/v4.0/config/subnets",
            max_items=max_items,
        )
        normalized = normalize_subnets(snapshot)
        results = reconcile_target_networks(target_names, normalized)
        return NetworkReconciliationResponse(
            targets=len(results),
            matched=sum(x["status"] == "Matched" for x in results),
            missing=sum(x["status"] == "Missing" for x in results),
            ambiguous=sum(x["status"] == "Ambiguous" for x in results),
            results=[NetworkReconciliationItem(**x) for x in results],
        )

    return _prism_call(run)
