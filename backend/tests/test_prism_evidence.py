from app.services.prism_evidence import build_prism_environment_evidence


def snapshot(*, truncated=False):
    return {
        "clusters": {
            "data": [{"extId": "c1", "name": "AHV-PROD-A"}],
            "metadata": {"truncatedByMigrationFactory": truncated},
        },
        "vms": {
            "data": [{"extId": "v1", "name": "APP-01"}, {"extId": "v2", "name": "DB-01"}],
            "metadata": {"truncatedByMigrationFactory": False},
        },
        "subnets": {
            "data": [
                {"extId": "s1", "name": "AHV-PROD-APP", "subnetType": "VLAN"},
                {"extId": "s2", "name": "AHV-PROD-DB", "subnetType": "VLAN"},
            ],
            "metadata": {"truncatedByMigrationFactory": False},
        },
    }


def test_prism_environment_evidence_captures_counts_and_digest():
    result = build_prism_environment_evidence(
        snapshot(),
        ["AHV-PROD-APP", "AHV-PROD-DB"],
    )
    assert result["status"] == "Captured"
    assert result["clusters"] == 1
    assert result["vms"] == 2
    assert result["subnets"] == 2
    assert result["matched_networks"] == 2
    assert result["missing_networks"] == 0
    assert len(result["snapshot_sha256"]) == 64


def test_prism_environment_evidence_warns_on_missing_network_and_truncation():
    result = build_prism_environment_evidence(
        snapshot(truncated=True),
        ["AHV-PROD-APP", "AHV-MISSING"],
    )
    assert result["status"] == "CapturedWithWarnings"
    assert result["matched_networks"] == 1
    assert result["missing_networks"] == 1
    assert result["cluster_inventory_truncated"] is True
    assert len(result["warnings"]) == 2