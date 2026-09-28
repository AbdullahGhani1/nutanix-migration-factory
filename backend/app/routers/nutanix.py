import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import PlanningAudit, PrismEnvironmentEvidence, Workload
from ..schemas import (
    NetworkReconciliationItem,
    NetworkReconciliationResponse,
    PrismEnvironmentSummary,
    PrismEnvironmentEvidenceOut,
    PrismEvidenceCaptureRequest,
)
from ..services.prism_evidence import build_prism_environment_evidence
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
        snapshot = _client().list_all_subnets(max_items=max_items)
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



@router.get("/evidence-snapshots", response_model=list[PrismEnvironmentEvidenceOut])
def list_environment_evidence(db: Session = Depends(get_db)):
    return list(
        db.scalars(
            select(PrismEnvironmentEvidence).order_by(
                PrismEnvironmentEvidence.captured_at.desc()
            )
        )
    )


@router.post("/evidence-snapshots", response_model=PrismEnvironmentEvidenceOut)
def capture_environment_evidence(
    payload: PrismEvidenceCaptureRequest,
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

    snapshot = _prism_call(
        lambda: _client().inventory_snapshot(max_items=max_items)
    )
    evidence = build_prism_environment_evidence(snapshot, target_names)

    record = PrismEnvironmentEvidence(
        status=evidence["status"],
        actor=payload.actor.strip(),
        clusters=evidence["clusters"],
        vms=evidence["vms"],
        subnets=evidence["subnets"],
        target_networks=evidence["target_networks"],
        matched_networks=evidence["matched_networks"],
        missing_networks=evidence["missing_networks"],
        ambiguous_networks=evidence["ambiguous_networks"],
        cluster_inventory_truncated=evidence["cluster_inventory_truncated"],
        vm_inventory_truncated=evidence["vm_inventory_truncated"],
        subnet_inventory_truncated=evidence["subnet_inventory_truncated"],
        snapshot_sha256=evidence["snapshot_sha256"],
        warnings_json=json.dumps(evidence["warnings"], sort_keys=True),
        network_reconciliation_json=json.dumps(
            evidence["network_reconciliation"],
            sort_keys=True,
        ),
        evidence_reference=payload.evidence_reference.strip(),
    )
    db.add(record)
    db.flush()
    db.add(
        PlanningAudit(
            event_type="prism_evidence.captured",
            entity=f"prism_evidence:{record.id}",
            detail=json.dumps(
                {
                    "status": record.status,
                    "actor": record.actor,
                    "clusters": record.clusters,
                    "vms": record.vms,
                    "subnets": record.subnets,
                    "target_networks": record.target_networks,
                    "matched_networks": record.matched_networks,
                    "missing_networks": record.missing_networks,
                    "ambiguous_networks": record.ambiguous_networks,
                    "snapshot_sha256": record.snapshot_sha256,
                    "evidence_reference": record.evidence_reference,
                },
                sort_keys=True,
            ),
        )
    )
    db.commit()
    db.refresh(record)
    return record
