from app.services.nutanix import (
    NutanixClient,
    normalize_subnets,
    reconcile_target_networks,
)


class FakeClient(NutanixClient):
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def _get(self, path: str, params: dict | None = None):
        params = params or {}
        page = int(params.get("$page", 0))
        self.calls.append((path, page, int(params.get("$limit", 0))))
        return self.pages[page]


def test_normalize_subnets_handles_v4_fields():
    payload = {
        "data": [
            {
                "extId": "subnet-1",
                "name": "AHV-PROD-APP",
                "subnetType": "VLAN",
                "networkId": 120,
                "clusterReference": "cluster-1",
            }
        ]
    }
    assert normalize_subnets(payload) == [
        {
            "ext_id": "subnet-1",
            "name": "AHV-PROD-APP",
            "subnet_type": "VLAN",
            "network_id": 120,
            "cluster_reference": "cluster-1",
        }
    ]


def test_reconcile_target_networks_reports_matched_missing_and_ambiguous():
    subnets = [
        {"ext_id": "1", "name": "AHV-PROD-APP"},
        {"ext_id": "2", "name": "AHV-DEV"},
        {"ext_id": "3", "name": "AHV-DEV"},
    ]
    result = reconcile_target_networks(
        ["AHV-PROD-APP", "AHV-PROD-DB", "AHV-DEV"],
        subnets,
    )
    by_name = {x["target_network"]: x for x in result}
    assert by_name["AHV-PROD-APP"]["status"] == "Matched"
    assert by_name["AHV-PROD-DB"]["status"] == "Missing"
    assert by_name["AHV-DEV"]["status"] == "Ambiguous"


def test_paginated_inventory_respects_max_items_and_marks_truncation():
    pages = [
        {
            "data": [{"extId": str(i)} for i in range(100)],
            "metadata": {"totalAvailableResults": 205},
        },
        {
            "data": [{"extId": str(i)} for i in range(100, 200)],
            "metadata": {"totalAvailableResults": 205},
        },
    ]
    client = FakeClient(pages)
    result = client._list_all("/api/example", page_size=100, max_items=150)
    assert len(result["data"]) == 150
    assert result["metadata"]["truncatedByMigrationFactory"] is True
    assert client.calls == [
        ("/api/example", 0, 100),
        ("/api/example", 1, 100),
    ]


def test_paginated_inventory_not_truncated_when_total_is_fully_returned():
    pages = [
        {
            "data": [{"extId": str(i)} for i in range(2)],
            "metadata": {"totalAvailableResults": 2},
        }
    ]
    client = FakeClient(pages)
    result = client._list_all("/api/example", page_size=100, max_items=1000)
    assert len(result["data"]) == 2
    assert result["metadata"]["truncatedByMigrationFactory"] is False


def test_cluster_inventory_uses_ga_clustermgmt_path(monkeypatch):
    from app.services.nutanix import NutanixClient

    calls = []
    client = NutanixClient.__new__(NutanixClient)
    monkeypatch.setattr(client, "_get", lambda path, params=None: calls.append(path) or {"data": []}, raising=False)
    client.list_clusters()
    assert calls == ["/api/clustermgmt/v4.0/config/clusters"]
