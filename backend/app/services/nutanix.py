from __future__ import annotations
import httpx
from ..config import get_settings


class NutanixNotConfigured(RuntimeError):
    pass


class NutanixClient:
    """Minimal Prism Central v4 inventory adapter.

    Uses documented GA v4 list endpoints. This client intentionally performs read-only
    inventory operations in the MVP.
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
            response = client.get(f"{self.base}{path}", params=params, headers={"Accept": "application/json"})
            response.raise_for_status()
            return response.json()

    def list_clusters(self, limit: int = 50):
        return self._get("/api/clustermgmt/v4.0/ahv/config/clusters", {"$limit": min(limit, 100)})

    def list_vms(self, limit: int = 50):
        return self._get("/api/vmm/v4.0/ahv/config/vms", {"$limit": min(limit, 100)})
