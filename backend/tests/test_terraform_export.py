import io
import json
import zipfile
from types import SimpleNamespace

from app.services.terraform_export import build_terraform_pack


def test_terraform_pack_is_safe_and_complete():
    workloads = [
        SimpleNamespace(
            id=1,
            name="ERP APP 01",
            wave_number=2,
            cpu=4,
            memory_gb=8,
            storage_gb=120,
            target_network="AHV-PROD-APP",
            app_group="ERP",
            criticality="High",
        )
    ]
    clusters = [
        SimpleNamespace(id=1, name="AHV-PROD-A", prism_ext_id="cluster-ext-id", enabled=True)
    ]

    payload = build_terraform_pack(workloads, clusters)
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        names = set(zf.namelist())
        assert {
            "README.md",
            "versions.tf",
            "provider.tf",
            "variables.tf",
            "locals.tf",
            "workloads.json",
            "planned_vms.tf",
            "outputs.tf",
            "terraform.tfvars.example",
            "inventory.json",
            "manifest.json",
        } <= names

        planned = zf.read("planned_vms.tf").decode()
        variables = zf.read("variables.tf").decode()
        tfvars = zf.read("terraform.tfvars.example").decode()
        inventory = zf.read("inventory.json").decode()
        manifest = json.loads(zf.read("manifest.json"))

        assert 'resource "nutanix_virtual_machine_v2" "planned"' in planned
        assert "var.enable_vm_creation ? local.workloads : {}" in planned
        assert "default     = false" in variables
        assert "DO-NOT-COMMIT" in tfvars
        assert "password" not in inventory.lower()
        assert "api_key" not in inventory.lower()
        assert manifest["files"]["planned_vms.tf"]["sha256"]


def test_duplicate_sanitized_workload_names_remain_unique():
    workloads = [
        SimpleNamespace(id=1, name="APP 01", wave_number=1, cpu=1, memory_gb=1, storage_gb=1, target_network="", app_group="", criticality="Low"),
        SimpleNamespace(id=2, name="APP-01", wave_number=1, cpu=1, memory_gb=1, storage_gb=1, target_network="", app_group="", criticality="Low"),
    ]
    payload = build_terraform_pack(workloads, [])
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        workloads_json = json.loads(zf.read("workloads.json"))
        assert "APP-01" in workloads_json
        assert "APP-01-2" in workloads_json