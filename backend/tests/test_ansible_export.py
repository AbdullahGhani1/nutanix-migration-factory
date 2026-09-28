import io
import json
import zipfile
from types import SimpleNamespace

from app.services.ansible_export import build_ansible_validation_pack


def test_ansible_validation_pack_groups_linux_and_windows_without_secrets():
    workloads = [
        SimpleNamespace(id=1, name="ERP-APP-01", wave_number=1, os="Windows Server 2022", target_network="AHV-PROD-APP", criticality="High"),
        SimpleNamespace(id=2, name="API-01", wave_number=1, os="Ubuntu Linux", target_network="AHV-PROD-APP", criticality="Medium"),
    ]

    payload = build_ansible_validation_pack(workloads)
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        names = set(zf.namelist())
        assert {
            "README.md",
            "ansible.cfg",
            "site.yml",
            "playbooks/validate_prism.yml",
            "playbooks/validate_linux.yml",
            "playbooks/validate_windows.yml",
            "inventory/hosts.yml",
            "collections/requirements.yml",
            "workloads.json",
            "manifest.json",
        } <= names

        inventory = zf.read("inventory/hosts.yml").decode()
        requirements = zf.read("collections/requirements.yml").decode()
        prism = zf.read("playbooks/validate_prism.yml").decode()
        manifest = json.loads(zf.read("manifest.json"))

        assert "ERP-APP-01" in inventory
        assert "API-01" in inventory
        assert "REPLACE_WITH_MIGRATED_GUEST_IP" in inventory
        assert "nutanix.ncp" in requirements
        assert 'version: "2.6.0"' in requirements
        assert "ntnx_clusters_info_v2" in prism
        assert "password:" not in inventory.lower()
        assert manifest["files"]["site.yml"]["sha256"]


def test_unknown_os_defaults_to_linux_style_validation_group():
    workloads = [
        SimpleNamespace(id=1, name="LEGACY-01", wave_number=2, os="Unknown", target_network="AHV-LEGACY", criticality="High")
    ]
    payload = build_ansible_validation_pack(workloads)
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        inventory = zf.read("inventory/hosts.yml").decode()
        linux_section = inventory.split("windows_migrated:")[0]
        assert "LEGACY-01" in linux_section