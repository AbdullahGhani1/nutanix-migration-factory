from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile


def _safe_host(name: str, fallback: str) -> str:
    value = re.sub(r"[^0-9A-Za-z_.-]+", "-", (name or "").strip()).strip("-")
    return value or fallback


def _is_windows(os_name: str) -> bool:
    return "windows" in (os_name or "").lower()


def build_ansible_validation_pack(workloads) -> bytes:
    """Build a no-secret post-migration validation pack.

    The pack validates Prism visibility and guest reachability after an approved
    migration. Host addresses and credentials remain placeholders because the
    planner must not invent production IPs or embed customer secrets.
    """
    linux_hosts = []
    windows_hosts = []
    inventory_records = []

    for index, w in enumerate(workloads, start=1):
        alias = _safe_host(w.name, f"workload-{index}")
        record = {
            "alias": alias,
            "name": w.name,
            "wave": w.wave_number,
            "os": w.os or "Unknown",
            "target_network": w.target_network or "",
            "criticality": w.criticality or "Medium",
            "ansible_host": "REPLACE_WITH_MIGRATED_GUEST_IP",
        }
        inventory_records.append(record)
        (windows_hosts if _is_windows(w.os) else linux_hosts).append(record)

    def host_block(records):
        if not records:
            return "      {}\n"
        lines = []
        for item in records:
            lines.extend([
                f"      {json.dumps(item['alias'])}:",
                f"        ansible_host: {json.dumps(item['ansible_host'])}",
                f"        migration_name: {json.dumps(item['name'])}",
                f"        migration_wave: {json.dumps(item['wave'])}",
                f"        expected_target_network: {json.dumps(item['target_network'])}",
                f"        migration_criticality: {json.dumps(item['criticality'])}",
            ])
        return "\n".join(lines) + "\n"

    inventory = (
        "all:\n"
        "  children:\n"
        "    linux_migrated:\n"
        "      hosts:\n" + host_block(linux_hosts) +
        "    windows_migrated:\n"
        "      hosts:\n" + host_block(windows_hosts)
    )

    requirements = '''---
collections:
  - name: nutanix.ncp
    version: "2.6.0"
  - name: ansible.windows
'''

    prism_playbook = '''---
- name: Validate Prism Central visibility after migration
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Require Prism Central connection variables
      ansible.builtin.assert:
        that:
          - lookup('env', 'NUTANIX_ENDPOINT') | length > 0
          - lookup('env', 'NUTANIX_USERNAME') | length > 0
          - lookup('env', 'NUTANIX_PASSWORD') | length > 0
        fail_msg: "Set NUTANIX_ENDPOINT, NUTANIX_USERNAME and NUTANIX_PASSWORD outside source control."

    - name: Query clusters through Nutanix v4-backed Ansible collection
      nutanix.ncp.ntnx_clusters_info_v2:
        nutanix_host: "{{ lookup('env', 'NUTANIX_ENDPOINT') }}"
        nutanix_username: "{{ lookup('env', 'NUTANIX_USERNAME') }}"
        nutanix_password: "{{ lookup('env', 'NUTANIX_PASSWORD') }}"
        validate_certs: "{{ (lookup('env', 'NUTANIX_VALIDATE_CERTS') | default('true', true)) | bool }}"
        limit: 100
      register: prism_clusters
      no_log: true

    - name: Confirm Prism returned cluster inventory
      ansible.builtin.assert:
        that:
          - prism_clusters is defined
          - prism_clusters.failed is not defined or not prism_clusters.failed
        fail_msg: "Prism cluster discovery failed. Review connectivity, RBAC and TLS settings."
'''

    linux_playbook = '''---
- name: Validate migrated Linux guests
  hosts: linux_migrated
  gather_facts: true
  serial: 10
  tasks:
    - name: Wait for SSH/Ansible connectivity
      ansible.builtin.wait_for_connection:
        timeout: 180

    - name: Validate basic guest facts
      ansible.builtin.assert:
        that:
          - ansible_facts.hostname is defined
          - ansible_facts.os_family is defined
        fail_msg: "Guest facts are incomplete after migration."

    - name: Capture hostname
      ansible.builtin.command: hostname
      register: hostname_result
      changed_when: false

    - name: Record post-migration Linux validation summary
      ansible.builtin.debug:
        msg:
          workload: "{{ migration_name }}"
          wave: "{{ migration_wave }}"
          expected_network: "{{ expected_target_network }}"
          hostname: "{{ hostname_result.stdout }}"
          default_ipv4: "{{ ansible_facts.default_ipv4.address | default('not-detected') }}"
'''

    windows_playbook = '''---
- name: Validate migrated Windows guests
  hosts: windows_migrated
  gather_facts: false
  serial: 10
  tasks:
    - name: Wait for WinRM/Ansible connectivity
      ansible.builtin.wait_for_connection:
        timeout: 180

    - name: Validate Windows connectivity
      ansible.windows.win_ping:

    - name: Capture Windows hostname
      ansible.windows.win_shell: hostname
      register: hostname_result
      changed_when: false

    - name: Record post-migration Windows validation summary
      ansible.builtin.debug:
        msg:
          workload: "{{ migration_name }}"
          wave: "{{ migration_wave }}"
          expected_network: "{{ expected_target_network }}"
          hostname: "{{ hostname_result.stdout | trim }}"
'''

    site_playbook = '''---
- import_playbook: validate_prism.yml
- import_playbook: validate_linux.yml
- import_playbook: validate_windows.yml
'''

    ansible_cfg = '''[defaults]
inventory = inventory/hosts.yml
host_key_checking = True
retry_files_enabled = False
stdout_callback = default
interpreter_python = auto_silent

[ssh_connection]
pipelining = True
'''

    readme = '''# Nutanix Migration Factory - Ansible Validation Pack

This pack is generated from the current migration estate for **post-migration
validation**. It does not execute Nutanix Move and it does not contain guest or
Prism credentials.

## What it validates

1. Prism Central connectivity and cluster visibility using `nutanix.ncp` v2 modules.
2. Linux guest reachability/facts after migration.
3. Windows guest reachability using WinRM.
4. Hostname and expected target-network metadata for operator evidence.

## Install collections

ansible-galaxy collection install -r collections/requirements.yml

## Configure Prism credentials outside source control

export NUTANIX_ENDPOINT="prism-central.example.com"
export NUTANIX_USERNAME="automation-user"
export NUTANIX_PASSWORD="<secret>"
export NUTANIX_VALIDATE_CERTS="true"

## Configure guest access

Replace every `REPLACE_WITH_MIGRATED_GUEST_IP` in `inventory/hosts.yml` with
the actual post-migration guest address. Configure SSH/WinRM credentials using
Ansible Vault, your secret manager, or runtime environment; do not write them
into this generated pack.

## Run

ansible-playbook site.yml --check
ansible-playbook site.yml

Application-specific UAT remains separate. A successful ping/hostname check is
not proof that the business application is healthy.
'''

    records_json = json.dumps(
        {
            "workloads": inventory_records,
            "provenance": "Generated from Migration Factory planning data; guest addresses are intentionally placeholders.",
        },
        indent=2,
        sort_keys=True,
    )

    files = {
        "README.md": readme.encode(),
        "ansible.cfg": ansible_cfg.encode(),
        "site.yml": site_playbook.encode(),
        "playbooks/validate_prism.yml": prism_playbook.encode(),
        "playbooks/validate_linux.yml": linux_playbook.encode(),
        "playbooks/validate_windows.yml": windows_playbook.encode(),
        "inventory/hosts.yml": inventory.encode(),
        "collections/requirements.yml": requirements.encode(),
        "workloads.json": records_json.encode(),
    }

    manifest = {
        name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        for name, data in sorted(files.items())
    }
    files["manifest.json"] = json.dumps(
        {
            "files": manifest,
            "notes": [
                "No credentials are included.",
                "Guest IP addresses are placeholders.",
                "Application-specific UAT is outside the scope of this validation pack.",
            ],
        },
        indent=2,
        sort_keys=True,
    ).encode()

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return output.getvalue()