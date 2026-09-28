import csv
import io
import json

from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    MigrationApproval,
    MigrationExecution,
    TargetCluster,
    TechnicalValidationRecord,
    Workload,
    WorkloadDependency,
)
from ..services.ansible_export import build_ansible_validation_pack
from ..services.evidence_bundle import build_evidence_bundle
from ..services.implementation_report import build_implementation_report
from ..services.terraform_export import build_terraform_pack

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _migration_plan_csv_bytes(workloads: list[Workload]) -> bytes:
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
    return output.getvalue().encode("utf-8")


def _execution_json_bytes(executions: list[MigrationExecution]) -> bytes:
    data = []
    for e in executions:
        data.append(
            {
                "id": e.id,
                "approval_id": e.approval_id,
                "wave_number": e.wave_number,
                "target_cluster_id": e.target_cluster_id,
                "status": e.status,
                "operator": e.operator,
                "move_plan_name": e.move_plan_name,
                "change_ticket": e.change_ticket,
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                "cutover_duration_minutes": e.cutover_duration_minutes,
                "uat_status": e.uat_status,
                "rollback_executed": e.rollback_executed,
                "validation_summary": e.validation_summary,
                "rollback_reason": e.rollback_reason,
                "evidence_reference": e.evidence_reference,
                "notes": e.notes,
                "created_at": e.created_at.isoformat(),
                "provenance": "Operator-entered execution evidence; not independently verified by Migration Factory.",
            }
        )
    return json.dumps(data, indent=2, sort_keys=True).encode("utf-8")


def _technical_validation_json_bytes(records: list[TechnicalValidationRecord]) -> bytes:
    data = []
    for row in records:
        data.append(
            {
                "id": row.id,
                "execution_id": row.execution_id,
                "tool": row.tool,
                "status": row.status,
                "actor": row.actor,
                "hosts_total": row.hosts_total,
                "hosts_passed": row.hosts_passed,
                "hosts_failed": row.hosts_failed,
                "prism_validation": row.prism_validation,
                "guest_validation": row.guest_validation,
                "artifact_sha256": row.artifact_sha256,
                "evidence_reference": row.evidence_reference,
                "summary": row.summary,
                "recorded_at": row.recorded_at.isoformat(),
                "provenance": (
                    "Operator-recorded technical validation evidence. The referenced "
                    "Ansible/Prism results are not independently verified by Migration Factory."
                ),
            }
        )
    return json.dumps(data, indent=2, sort_keys=True).encode("utf-8")


def _estate(db: Session):
    workloads = list(
        db.scalars(
            select(Workload).order_by(
                Workload.wave_number,
                Workload.app_group,
                Workload.name,
            )
        )
    )
    clusters = list(db.scalars(select(TargetCluster).order_by(TargetCluster.name)))
    approvals = list(
        db.scalars(
            select(MigrationApproval).order_by(MigrationApproval.requested_at)
        )
    )
    dependencies = list(
        db.scalars(
            select(WorkloadDependency).order_by(WorkloadDependency.id)
        )
    )
    executions = list(
        db.scalars(
            select(MigrationExecution).order_by(MigrationExecution.created_at)
        )
    )
    validations = list(
        db.scalars(
            select(TechnicalValidationRecord).order_by(
                TechnicalValidationRecord.recorded_at
            )
        )
    )
    return workloads, clusters, approvals, dependencies, executions, validations


@router.get("/migration-plan.csv")
def migration_plan_csv(db: Session = Depends(get_db)):
    workloads = list(
        db.scalars(
            select(Workload).order_by(
                Workload.wave_number,
                Workload.app_group,
                Workload.name,
            )
        )
    )
    content = _migration_plan_csv_bytes(workloads)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=migration-plan.csv"},
    )


@router.get("/implementation-report.pdf")
def implementation_report_pdf(db: Session = Depends(get_db)):
    workloads, clusters, approvals, dependencies, executions, validations = _estate(db)
    pdf = build_implementation_report(
        workloads,
        clusters,
        approvals,
        dependencies,
        executions,
        validations,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=nutanix-implementation-report.pdf"
        },
    )


@router.get("/evidence-bundle.zip")
def evidence_bundle_zip(db: Session = Depends(get_db)):
    workloads, clusters, approvals, dependencies, executions = _estate(db)
    pdf = build_implementation_report(
        workloads,
        clusters,
        approvals,
        dependencies,
        executions,
    )
    migration_csv = _migration_plan_csv_bytes(workloads)
    execution_json = _execution_json_bytes(executions)
    validation_json = _technical_validation_json_bytes(validations)

    bundle = build_evidence_bundle(
        implementation_pdf=pdf,
        migration_plan_csv=migration_csv,
        executions_json=execution_json,
        technical_validations_json=validation_json,
        metadata={
            "workloads": len(workloads),
            "target_clusters": len(clusters),
            "approvals": len(approvals),
            "dependencies": len(dependencies),
            "executions": len(executions),
            "technical_validations": len(validations),
        },
    )
    return Response(
        content=bundle,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=nutanix-migration-evidence-bundle.zip"
        },
    )


@router.get("/terraform-pack.zip")
def terraform_pack_zip(db: Session = Depends(get_db)):
    workloads = list(
        db.scalars(
            select(Workload).order_by(
                Workload.wave_number,
                Workload.app_group,
                Workload.name,
            )
        )
    )
    clusters = list(db.scalars(select(TargetCluster).order_by(TargetCluster.name)))
    bundle = build_terraform_pack(workloads, clusters)
    return Response(
        content=bundle,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=nutanix-terraform-pack.zip"
        },
    )


@router.get("/ansible-validation-pack.zip")
def ansible_validation_pack_zip(db: Session = Depends(get_db)):
    workloads = list(
        db.scalars(
            select(Workload).order_by(
                Workload.wave_number,
                Workload.app_group,
                Workload.name,
            )
        )
    )
    bundle = build_ansible_validation_pack(workloads)
    return Response(
        content=bundle,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=nutanix-ansible-validation-pack.zip"
        },
    )
