from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .capacity import calculate_wave_demand, evaluate_cluster
from .dependencies import dependency_order
from .readiness import evaluate_workload
from .runbooks import build_wave_runbook


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _csv_inventory(workloads) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Wave", "Application Group", "VM", "vCPU", "Memory GB", "Storage GB",
        "OS", "Source Network", "Target Network", "Criticality", "Downtime Minutes", "Owner"
    ])
    for w in workloads:
        writer.writerow([
            w.wave_number or "", w.app_group, w.name, w.cpu, w.memory_gb, w.storage_gb,
            w.os, w.source_network, w.target_network, w.criticality, w.downtime_minutes, w.owner,
        ])
    return output.getvalue().encode("utf-8")


def _table(data, widths=None):
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _cab_pdf(approval, target_cluster, workloads, readiness, capacity, runbook, execution, validations) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"CAB Change Package - {approval.change_ticket or 'No Ticket'}",
        author="Nutanix Migration Factory",
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Nutanix Migration Factory - CAB Change Package", styles["Title"]),
        Paragraph(
            f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} for approved migration wave {approval.wave_number}.",
            styles["Normal"],
        ),
        Spacer(1, 8),
    ]

    story.append(Paragraph("Change summary", styles["Heading2"]))
    story.append(_table([
        ["Change ticket", "Approval", "Wave", "Target cluster", "Workloads", "Headroom"],
        [
            approval.change_ticket or "-",
            approval.status,
            str(approval.wave_number),
            target_cluster.name,
            str(len(workloads)),
            f"{approval.headroom_percent:.0f}%",
        ],
    ]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Readiness snapshot", styles["Heading2"]))
    rows = [["Workload", "Status", "Blockers", "Warnings"]]
    for item in readiness:
        rows.append([item.name, item.status, "; ".join(item.blockers) or "-", "; ".join(item.warnings) or "-"])
    story.append(_table(rows, [38 * mm, 28 * mm, 55 * mm, 63 * mm]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Target capacity snapshot", styles["Heading2"]))
    story.append(_table([
        ["Fit", "Projected vCPU", "Projected RAM", "Projected storage", "Planning result"],
        [
            "Yes" if capacity["fit"] else "No",
            str(capacity["projected_vcpu"]),
            f"{capacity['projected_memory_gb']} GB",
            f"{capacity['projected_storage_gb']} GB",
            "; ".join(capacity["reasons"]),
        ],
    ]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Dependency-aware service sequence", styles["Heading2"]))
    story.append(Paragraph("Stop order: " + " -> ".join(runbook["service_stop_order"]), styles["BodyText"]))
    story.append(Paragraph("Start order: " + " -> ".join(runbook["service_start_order"]), styles["BodyText"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Implementation checklist", styles["Heading2"]))
    for section, items in [
        ("Pre-cutover", runbook["pre_cutover"]),
        ("Cutover", runbook["cutover"]),
        ("Rollback", runbook["rollback"]),
    ]:
        story.append(Paragraph(section, styles["Heading3"]))
        for index, item in enumerate(items, start=1):
            story.append(Paragraph(f"{index}. {item}", styles["BodyText"]))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Evidence status", styles["Heading2"]))
    if execution:
        story.append(Paragraph(
            f"Execution #{execution.id}: {execution.status}; Move plan: {execution.move_plan_name or '-'}; "
            f"measured cutover: {execution.cutover_duration_minutes if execution.cutover_duration_minutes is not None else '-'} minutes; "
            f"UAT: {execution.uat_status}.",
            styles["BodyText"],
        ))
    else:
        story.append(Paragraph("No migration execution record exists yet for this approval.", styles["BodyText"]))

    if validations:
        for v in validations:
            story.append(Paragraph(
                f"Technical validation #{v.id}: {v.status}; tool {v.tool}; hosts {v.hosts_passed}/{v.hosts_total} passed; "
                f"Prism {v.prism_validation}; guest {v.guest_validation}.",
                styles["BodyText"],
            ))
    else:
        story.append(Paragraph("No technical validation record exists yet.", styles["BodyText"]))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Control boundary", styles["Heading2"]))
    story.append(Paragraph(
        "This package is generated from Migration Factory planning and operator evidence. It does not independently certify "
        "Nutanix Move supportability, successful migration execution, application-owner UAT, or production sizing. Final go/no-go, "
        "rollback thresholds, maintenance window and business approval remain controlled by the authorized change process.",
        styles["BodyText"],
    ))

    doc.build(story)
    return buffer.getvalue()


def build_cab_package(*, approval, target_cluster, workloads, dependencies, execution=None, validations=None) -> bytes:
    """Generate an approval-linked enterprise change/CAB handoff package."""
    validations = validations or []
    if approval.status != "Approved":
        raise ValueError("CAB package can only be generated from an Approved migration request")
    if not workloads:
        raise ValueError("Approved migration wave has no workloads")

    workload_ids = {w.id for w in workloads}
    edges = [
        (d.upstream_workload_id, d.downstream_workload_id)
        for d in dependencies
        if d.upstream_workload_id in workload_ids and d.downstream_workload_id in workload_ids
    ]
    ordering = dependency_order(list(workload_ids), edges)
    by_id = {w.id: w.name for w in workloads}
    runbook = build_wave_runbook(
        approval.wave_number,
        workloads,
        start_order=[by_id[x] for x in ordering["start_order"]],
        stop_order=[by_id[x] for x in ordering["stop_order"]],
        dependency_cycle=ordering["has_cycle"],
    )
    readiness = [evaluate_workload(w) for w in workloads]
    demand = calculate_wave_demand(approval.wave_number, workloads)
    capacity = evaluate_cluster(target_cluster, demand, approval.headroom_percent)

    change_request = f'''# Change Request

**Change ticket:** {approval.change_ticket or 'Not recorded'}
**Migration wave:** {approval.wave_number}
**Approval status:** {approval.status}
**Requested by:** {approval.requested_by}
**Approved by:** {approval.decided_by or 'Not recorded'}
**Target AHV cluster:** {target_cluster.name}
**Configured headroom:** {approval.headroom_percent:.0f}%

## Change objective

Execute the approved VMware-to-Nutanix AHV migration wave represented by this package, using the recorded network mappings, dependency sequence, target-cluster capacity policy and change controls.

## Scope

- Workloads: {len(workloads)}
- vCPU: {demand.vcpu}
- Memory: {demand.memory_gb} GB
- Storage: {demand.storage_gb} GB
- Application groups: {', '.join(sorted({w.app_group or 'Ungrouped' for w in workloads}))}

## Control notes

- This package does not certify Nutanix Move compatibility.
- Capacity is a planning envelope, not a production sizing recommendation.
- The maintenance window and final go/no-go must come from the authorized change process.
- Application-owner UAT remains distinct from infrastructure validation.
'''

    implementation = ["# Implementation Plan", "", "## Pre-cutover"]
    implementation += [f"- [ ] {item}" for item in runbook["pre_cutover"]]
    implementation += ["", "## Service stop order", "", " -> ".join(runbook["service_stop_order"])]
    implementation += ["", "## Cutover"]
    implementation += [f"- [ ] {item}" for item in runbook["cutover"]]
    implementation += ["", "## Service start order", "", " -> ".join(runbook["service_start_order"])]
    implementation_md = "\n".join(implementation) + "\n"

    rollback = [
        "# Rollback Plan",
        "",
        "Rollback is an authorized change decision. The checklist below is a technical template and does not invent customer-specific thresholds.",
        "",
        "## Technical rollback sequence",
    ]
    rollback += [f"- [ ] {item}" for item in runbook["rollback"]]
    rollback += [
        "",
        "## Decision evidence to capture",
        "- [ ] Reason rollback was declared",
        "- [ ] Timestamp and approving actor",
        "- [ ] Source/target power state",
        "- [ ] DNS/load-balancer/network restoration state",
        "- [ ] Application/data consistency validation result",
    ]
    rollback_md = "\n".join(rollback) + "\n"

    validation_md = '''# Validation Plan

## Infrastructure validation

- [ ] Prism Central shows the expected target cluster and migrated workload visibility
- [ ] Guest OS boots successfully
- [ ] Expected AHV network attachment is present
- [ ] IP configuration and default gateway are validated
- [ ] DNS forward/reverse behavior is validated where required
- [ ] Linux SSH or Windows WinRM connectivity is validated where authorized
- [ ] Application dependencies are reachable in the documented start order

## Application-owner validation

- [ ] Application smoke tests
- [ ] Business transaction validation
- [ ] Data consistency checks where applicable
- [ ] Application owner UAT decision

## Evidence

- Record measured cutover duration in MigrationExecution.
- Record infrastructure validation separately from application UAT.
- Hash exported validation artifacts with SHA-256 before attaching references.
'''

    approval_json = json.dumps({
        "id": approval.id,
        "wave_number": approval.wave_number,
        "target_cluster_id": approval.target_cluster_id,
        "target_cluster_name": target_cluster.name,
        "status": approval.status,
        "requested_by": approval.requested_by,
        "requested_at": approval.requested_at.isoformat(),
        "decided_by": approval.decided_by,
        "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
        "change_ticket": approval.change_ticket,
        "headroom_percent": approval.headroom_percent,
        "notes": approval.notes,
        "decision_notes": approval.decision_notes,
    }, indent=2, sort_keys=True).encode()

    readiness_json = json.dumps([r.to_dict() for r in readiness], indent=2, sort_keys=True).encode()
    capacity_json = json.dumps({
        "demand": demand.to_dict(),
        "target_cluster": {
            "id": target_cluster.id,
            "name": target_cluster.name,
            "prism_ext_id": target_cluster.prism_ext_id,
        },
        "evaluation": capacity,
        "provenance": "Planning-time capacity envelope; not a Nutanix production sizing recommendation.",
    }, indent=2, sort_keys=True).encode()
    dependency_json = json.dumps({
        "has_cycle": ordering["has_cycle"],
        "start_order": [by_id[x] for x in ordering["start_order"]],
        "stop_order": [by_id[x] for x in ordering["stop_order"]],
        "edges": [
            {
                "upstream": by_id.get(a, str(a)),
                "downstream": by_id.get(b, str(b)),
            }
            for a, b in edges
        ],
    }, indent=2, sort_keys=True).encode()

    evidence_json = json.dumps({
        "execution": None if not execution else {
            "id": execution.id,
            "status": execution.status,
            "operator": execution.operator,
            "move_plan_name": execution.move_plan_name,
            "cutover_duration_minutes": execution.cutover_duration_minutes,
            "uat_status": execution.uat_status,
            "evidence_reference": execution.evidence_reference,
        },
        "technical_validations": [
            {
                "id": v.id,
                "tool": v.tool,
                "status": v.status,
                "hosts_total": v.hosts_total,
                "hosts_passed": v.hosts_passed,
                "hosts_failed": v.hosts_failed,
                "prism_validation": v.prism_validation,
                "guest_validation": v.guest_validation,
                "artifact_sha256": v.artifact_sha256,
                "evidence_reference": v.evidence_reference,
            } for v in validations
        ],
        "provenance": "Operator-recorded evidence; not independently verified by Migration Factory.",
    }, indent=2, sort_keys=True).encode()

    cab_pdf = _cab_pdf(approval, target_cluster, workloads, readiness, capacity, runbook, execution, validations)
    inventory_csv = _csv_inventory(workloads)

    files = {
        "CAB-summary.pdf": cab_pdf,
        "change-request.md": change_request.encode(),
        "implementation-plan.md": implementation_md.encode(),
        "rollback-plan.md": rollback_md.encode(),
        "validation-plan.md": validation_md.encode(),
        "workload-inventory.csv": inventory_csv,
        "approval.json": approval_json,
        "readiness-snapshot.json": readiness_json,
        "capacity-snapshot.json": capacity_json,
        "dependency-map.json": dependency_json,
        "execution-evidence.json": evidence_json,
    }

    manifest = {
        "schema": "nutanix-migration-factory-cab-package/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "approval_id": approval.id,
        "wave_number": approval.wave_number,
        "change_ticket": approval.change_ticket,
        "files": {
            name: {"sha256": _sha256(data), "bytes": len(data)}
            for name, data in sorted(files.items())
        },
        "control_boundary": (
            "Package integrity is verifiable by SHA-256. Source planning/evidence data remains operator-controlled "
            "and is not independently certified by Migration Factory."
        ),
    }
    files["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True).encode()

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()