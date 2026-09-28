from types import SimpleNamespace

from app.services.capacity import normalize_prism_cluster_inventory, reconcile_prism_clusters


def test_normalize_and_reconcile_by_ext_id_then_name():
    payload = {
        "data": [
            {"extId": "abc-123", "name": "AHV-PROD-A"},
            {"extId": "def-456", "name": "AHV-DR-A"},
        ]
    }
    prism = normalize_prism_cluster_inventory(payload)
    local = [
        SimpleNamespace(id=1, name="local-name", prism_ext_id="abc-123"),
        SimpleNamespace(id=2, name="AHV-DR-A", prism_ext_id=""),
    ]
    result = reconcile_prism_clusters(prism, local)
    assert result[0]["status"] == "Matched"
    assert result[0]["local_cluster_id"] == 1
    assert result[1]["status"] == "Matched"
    assert result[1]["local_cluster_id"] == 2
