from types import SimpleNamespace

from app.services.implementation_report import build_implementation_report


def test_pdf_report_is_generated():
    workloads = [
        SimpleNamespace(
            id=1,
            name="DB-01",
            wave_number=1,
            cpu=8,
            memory_gb=32,
            storage_gb=500,
            migration_risk="Medium",
        )
    ]
    clusters = [
        SimpleNamespace(
            name="AHV-PROD-A",
            physical_cpu_cores=64,
            cpu_overcommit_ratio=4.0,
            allocated_vcpu=80,
            used_memory_gb=300,
            total_memory_gb=1024,
            used_storage_gb=6000,
            usable_storage_gb=20000,
        )
    ]
    approvals = [
        SimpleNamespace(
            wave_number=1,
            status="Approved",
            target_cluster_id=1,
            requested_by="migration.engineer",
            change_ticket="CHG-42",
            decided_by="change.manager",
        )
    ]
    dependencies = []

    pdf = build_implementation_report(workloads, clusters, approvals, dependencies)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
