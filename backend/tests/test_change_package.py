import io
import json
import zipfile
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.services.change_package import build_cab_package


def workload(id, name, app_group, network):
    return SimpleNamespace(
        id=id, name=name, wave_number=1, app_group=app_group, cpu=4, memory_gb=8,
        storage_gb=100, os="Ubuntu Linux", source_network="VLAN120",
        target_network=network, criticality="High", downtime_minutes=60,
        owner="app.owner", power_state="PoweredOn", snapshots=0, nic_count=1,
    )


def approved(status="Approved"):
    return SimpleNamespace(
        id=7, wave_number=1, target_cluster_id=3, status=status,
        requested_by="migration.engineer", requested_at=datetime(2026, 9, 28, 9, 0),
        decided_by="change.manager", decided_at=datetime(2026, 9, 28, 10, 0),
        change_ticket="CHG-2026-0042", headroom_percent=20.0,
        notes="Pilot production wave", decision_notes="CAB approved",
    )


def cluster():
    return SimpleNamespace(
        id=3, name="AHV-PROD-A", prism_ext_id="cluster-ext-id",
        physical_cpu_cores=64, cpu_overcommit_ratio=4.0, allocated_vcpu=40,
        total_memory_gb=1024, used_memory_gb=300,
        usable_storage_gb=20000, used_storage_gb=6000, enabled=True,
    )


def test_cab_package_contains_change_control_artifacts_and_manifest():
    workloads = [
        workload(1, "ERP-DB-01", "ERP", "AHV-PROD-DB"),
        workload(2, "ERP-APP-01", "ERP", "AHV-PROD-APP"),
    ]
    deps = [SimpleNamespace(upstream_workload_id=1, downstream_workload_id=2)]
    execution = SimpleNamespace(
        id=11, status="Succeeded", operator="migration.engineer",
        move_plan_name="ERP-WAVE-01", cutover_duration_minutes=14,
        uat_status="Passed", evidence_reference="CHG-2026-0042/run-01",
    )
    validations = [SimpleNamespace(
        id=21, tool="Ansible", status="Passed", hosts_total=2, hosts_passed=2,
        hosts_failed=0, prism_validation="Passed", guest_validation="Passed",
        artifact_sha256="a" * 64, evidence_reference="CHG-2026-0042/validation-01",
    )]

    payload = build_cab_package(
        approval=approved(), target_cluster=cluster(), workloads=workloads,
        dependencies=deps, execution=execution, validations=validations,
    )

    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        names = set(zf.namelist())
        assert {
            "CAB-summary.pdf",
            "change-request.md",
            "implementation-plan.md",
            "rollback-plan.md",
            "validation-plan.md",
            "workload-inventory.csv",
            "approval.json",
            "readiness-snapshot.json",
            "capacity-snapshot.json",
            "dependency-map.json",
            "execution-evidence.json",
            "manifest.json",
        } <= names

        assert zf.read("CAB-summary.pdf").startswith(b"%PDF")
        implementation = zf.read("implementation-plan.md").decode()
        dependency = json.loads(zf.read("dependency-map.json"))
        capacity = json.loads(zf.read("capacity-snapshot.json"))
        evidence = json.loads(zf.read("execution-evidence.json"))
        manifest = json.loads(zf.read("manifest.json"))

        assert "ERP-APP-01 -> ERP-DB-01" in implementation
        assert "ERP-DB-01 -> ERP-APP-01" in implementation
        assert dependency["has_cycle"] is False
        assert dependency["start_order"] == ["ERP-DB-01", "ERP-APP-01"]
        assert capacity["evaluation"]["fit"] is True
        assert evidence["execution"]["status"] == "Succeeded"
        assert evidence["technical_validations"][0]["artifact_sha256"] == "a" * 64
        assert manifest["schema"] == "nutanix-migration-factory-cab-package/v1"
        assert manifest["change_ticket"] == "CHG-2026-0042"
        assert manifest["files"]["change-request.md"]["sha256"]


def test_cab_package_rejects_non_approved_request():
    with pytest.raises(ValueError, match="Approved"):
        build_cab_package(
            approval=approved("Pending"),
            target_cluster=cluster(),
            workloads=[workload(1, "APP-01", "APP", "AHV-PROD-APP")],
            dependencies=[],
        )