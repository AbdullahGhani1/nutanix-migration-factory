from __future__ import annotations

import httpx

from ..config import get_settings


class NutanixNotConfigured(RuntimeError):
    pass


def _metadata_total(payload: dict) -> int | None:
    metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
    for key in ("totalAvailableResults", "total_available_results", "totalAvailableResult"):
        value = metadata.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
    return None


def normalize_subnets(payload: dict) -> list[dict]:
    result: list[dict] = []
    for item in payload.get("data", []) if isinstance(payload, dict) else []:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "ext_id": str(item.get("extId") or item.get("ext_id") or "").strip(),
                "name": str(item.get("name") or "").strip(),
                "subnet_type": str(item.get("subnetType") or item.get("subnet_type") or "").strip(),
                "network_id": item.get("networkId", item.get("network_id")),
                "cluster_reference": str(
                    item.get("clusterReference") or item.get("cluster_reference") or ""
                ).strip(),
            }
        )
    return result


def reconcile_target_networks(target_names: list[str], subnets: list[dict]) -> list[dict]:
    by_name: dict[str, list[dict]] = {}
    for subnet in subnets:
        name = (subnet.get("name") or "").strip()
        if name:
            by_name.setdefault(name.lower(), []).append(subnet)

    results = []
    for target in sorted({x.strip() for x in target_names if x and x.strip()}):
        matches = by_name.get(target.lower(), [])
        if len(matches) == 1:
            status = "Matched"
        elif len(matches) > 1:
            status = "Ambiguous"
        else:
            status = "Missing"

        results.append(
            {
                "target_network": target,
                "status": status,
                "matches": matches,
            }
        )
    return results


class NutanixClient:
    """Read-only Prism Central v4 inventory adapter.

    Current endpoints use the GA v4 API family. The adapter does not perform
    mutations against Prism Central.
    """

    def __init__(self):
        settings = get_settings()
        if not (settings.nutanix_pc_url and settings.nutanix_username and settings.nutanix_password):
            raise NutanixNotConfigured("Prism Central connection is not configured")
        self.base = settings.nutanix_pc_url.rstrip("/")
        self.auth = (settings.nutanix_username, settings.nutanix_password)
        self.verify = settings.nutanix_verify_tls

    def _get(self, path: str, params: dict | None = None):
        with httpx.Client(auth=self.auth, verify=self.verify, timeout=30.0) as client:
            response = client.get(
                f"{self.base}{path}",
                params=params,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()

    def _list_all(self, path: str, *, page_size: int = 100, max_items: int = 1000) -> dict:
        page_size = max(1, min(page_size, 100))
        max_items = max(1, max_items)
        page = 0
        collected: list[dict] = []
        last_metadata: dict = {}
        last_total: int | None = None
        last_page_size = 0

        while len(collected) < max_items:
            payload = self._get(path, {"$page": page, "$limit": page_size})
            data = payload.get("data", []) if isinstance(payload, dict) else []
            last_metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
            last_total = _metadata_total(payload)
            last_page_size = len(data)
            if not data:
                break

            remaining = max_items - len(collected)
            collected.extend(data[:remaining])

            total = last_total
            if total is not None and len(collected) >= min(total, max_items):
                break
            if len(data) < page_size:
                break
            page += 1

        if last_total is not None:
            truncated = last_total > len(collected)
        else:
            truncated = len(collected) >= max_items and last_page_size >= page_size

        return {
            "data": collected,
            "metadata": {
                **last_metadata,
                "returnedByMigrationFactory": len(collected),
                "truncatedByMigrationFactory": truncated,
            },
        }

    def list_clusters(self, limit: int = 50):
        return self._get(
            "/api/clustermgmt/v4.0/ahv/config/clusters",
            {"$limit": min(limit, 100)},
        )

    def list_vms(self, limit: int = 50):
        return self._get(
            "/api/vmm/v4.0/ahv/config/vms",
            {"$limit": min(limit, 100)},
        )

    def list_subnets(self, limit: int = 100):
        return self._get(
            "/api/networking/v4.0/config/subnets",
            {"$limit": min(limit, 100)},
        )

    def list_all_subnets(self, max_items: int = 1000) -> dict:
        return self._list_all(
            "/api/networking/v4.0/config/subnets",
            max_items=max_items,
        )

    def inventory_snapshot(self, max_items: int = 1000) -> dict:
        clusters = self._list_all(
            "/api/clustermgmt/v4.0/ahv/config/clusters",
            max_items=max_items,
        )
        vms = self._list_all(
            "/api/vmm/v4.0/ahv/config/vms",
            max_items=max_items,
        )
        subnets = self.list_all_subnets(max_items=max_items)
        return {
            "clusters": clusters,
            "vms": vms,
            "subnets": subnets,
        }
