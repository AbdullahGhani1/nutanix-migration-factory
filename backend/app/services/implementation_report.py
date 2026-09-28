from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _table(data, widths=None):
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def build_implementation_report(workloads, clusters, approvals, dependencies) -> bytes:
    """Build a sanitized implementation-planning PDF from persisted project data."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Nutanix Migration Factory - Implementation Planning Report",
        author="Nutanix Migration Factory",
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Nutanix Migration Factory - Implementation Planning Report", styles["Title"]))
    story.append(
        Paragraph(
            f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} from the current migration-planning dataset.",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 8))

    waves = defaultdict(list)
    for w in workloads:
        waves[w.wave_number or 0].append(w)

    total_vcpu = sum(int(w.cpu or 0) for w in workloads)
    total_memory = sum(float(w.memory_gb or 0) for w in workloads)
    total_storage = sum(float(w.storage_gb or 0) for w in workloads)

    story.append(Paragraph("Executive summary", styles["Heading2"]))
    story.append(
        _table(
            [
                ["Workloads", "Migration waves", "vCPU", "Memory GB", "Storage TB", "Target clusters"],
                [
                    str(len(workloads)),
                    str(len([x for x in waves if x])),
                    str(total_vcpu),
                    f"{total_memory:.1f}",
                    f"{total_storage / 1024:.2f}",
                    str(len(clusters)),
                ],
            ]
        )
    )
    story.append(Spacer(1, 10))

    story.append(Paragraph("Migration waves", styles["Heading2"]))
    wave_rows = [["Wave", "VMs", "vCPU", "Memory GB", "Storage GB", "High complexity"]]
    for wave_no in sorted(x for x in waves if x):
        items = waves[wave_no]
        wave_rows.append(
            [
                str(wave_no),
                str(len(items)),
                str(sum(int(w.cpu or 0) for w in items)),
                f"{sum(float(w.memory_gb or 0) for w in items):.1f}",
                f"{sum(float(w.storage_gb or 0) for w in items):.1f}",
                str(sum((w.migration_risk or "") == "High" for w in items)),
            ]
        )
    if len(wave_rows) == 1:
        wave_rows.append(["-", "0", "0", "0", "0", "0"])
    story.append(_table(wave_rows))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Target AHV capacity profiles", styles["Heading2"]))
    cluster_rows = [["Cluster", "CPU cores", "CPU ratio", "Allocated vCPU", "Memory used/total", "Storage used/usable"]]
    for c in clusters:
        cluster_rows.append(
            [
                c.name,
                str(c.physical_cpu_cores),
                f"{c.cpu_overcommit_ratio:.1f}x",
                str(c.allocated_vcpu),
                f"{c.used_memory_gb:.1f}/{c.total_memory_gb:.1f} GB",
                f"{c.used_storage_gb / 1024:.2f}/{c.usable_storage_gb / 1024:.2f} TB",
            ]
        )
    if len(cluster_rows) == 1:
        cluster_rows.append(["No target clusters configured", "-", "-", "-", "-", "-"])
    story.append(_table(cluster_rows))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Migration governance", styles["Heading2"]))
    approval_rows = [["Wave", "Status", "Target cluster ID", "Requested by", "Change ticket", "Decision by"]]
    for a in approvals:
        approval_rows.append(
            [
                str(a.wave_number),
                a.status,
                str(a.target_cluster_id),
                a.requested_by,
                a.change_ticket or "-",
                a.decided_by or "-",
            ]
        )
    if len(approval_rows) == 1:
        approval_rows.append(["-", "No approvals recorded", "-", "-", "-", "-"])
    story.append(_table(approval_rows))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Application dependencies", styles["Heading2"]))
    by_id = {w.id: w.name for w in workloads}
    dependency_rows = [["Upstream", "Downstream", "Type", "Notes"]]
    for d in dependencies:
        dependency_rows.append(
            [
                by_id.get(d.upstream_workload_id, str(d.upstream_workload_id)),
                by_id.get(d.downstream_workload_id, str(d.downstream_workload_id)),
                d.dependency_type,
                d.notes or "-",
            ]
        )
    if len(dependency_rows) == 1:
        dependency_rows.append(["No dependencies recorded", "-", "-", "-"])
    story.append(_table(dependency_rows, [42 * mm, 42 * mm, 25 * mm, 55 * mm]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Engineering boundaries", styles["Heading2"]))
    story.append(
        Paragraph(
            "Migration complexity, readiness and capacity results in this report are planning controls. "
            "They do not certify Nutanix Move or AHV supportability and do not replace production sizing. "
            "Final implementation must be validated against the authorized target environment, current "
            "Nutanix product documentation, measured utilization, HA/N+1 requirements and customer change controls.",
            styles["BodyText"],
        )
    )

    doc.build(story)
    return buffer.getvalue()
