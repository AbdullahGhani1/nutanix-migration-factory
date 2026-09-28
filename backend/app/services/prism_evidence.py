from __future__ import annotations

import hashlib
import json

from .nutanix import normalize_subnets, reconcile_target_networks


def build_prism_environment_evidence(snapshot: dict, target_names: list[str]) -> dict:
    clusters = snapshot.get("clusters", {}) if isinstance(snapshot, dict) else {}
    vms = snapshot.get("vms", {}) if isinstance(snapshot, dict) else {}
    subnets = snapshot.get("subnets", {}) if isinstance(snapshot, dict) else {}

    cluster_data = clusters.get("data", []) if isinstance(clusters, dict) else []
    vm_data = vms.get("data", []) if isinstance(vms, dict) else []
    subnet_data = subnets.get("data", []) if isinstance(subnets, dict) else []

    normalized_subnets = normalize_subnets(subnets)
    reconciliation = reconcile_target_networks(target_names, normalized_subnets)

    truncation = {
        "clusters": bool(clusters.get("metadata", {}).get("truncatedByMigrationFactory")),
        "vms": bool(vms.get("metadata", {}).get("truncatedByMigrationFactory")),
        "subnets": bool(subnets.get("metadata", {}).get("truncatedByMigrationFactory")),
    }

    matched = sum(item["status"] == "Matched" for item in reconciliation)
    missing = sum(item["status"] == "Missing" for item in reconciliation)
    ambiguous = sum(item["status"] == "Ambiguous" for item in reconciliation)

    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()

    warnings = []
    if any(truncation.values()):
        warnings.append("One or more Prism inventory collections were truncated by the configured Migration Factory cap")
    if missing:
        warnings.append(f"{missing} planned target network(s) are missing from Prism subnet inventory")
    if ambiguous:
        warnings.append(f"{ambiguous} planned target network(s) match multiple Prism subnets")

    return {
        "status": "CapturedWithWarnings" if warnings else "Captured",
        "clusters": len(cluster_data),
        "vms": len(vm_data),
        "subnets": len(subnet_data),
        "target_networks": len(reconciliation),
        "matched_networks": matched,
        "missing_networks": missing,
        "ambiguous_networks": ambiguous,
        "cluster_inventory_truncated": truncation["clusters"],
        "vm_inventory_truncated": truncation["vms"],
        "subnet_inventory_truncated": truncation["subnets"],
        "snapshot_sha256": digest,
        "warnings": warnings,
        "network_reconciliation": [
            {
                "target_network": item["target_network"],
                "status": item["status"],
                "match_count": len(item.get("matches", [])),
            }
            for item in reconciliation
        ],
    }