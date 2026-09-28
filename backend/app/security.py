from __future__ import annotations

import hashlib
import hmac

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .config import get_settings


ROLE_ORDER = {
    "viewer": 1,
    "operator": 2,
    "approver": 3,
    "admin": 4,
}

PUBLIC_PATHS = {
    "/health",
    "/ready",
    "/metrics",
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
}


def hash_api_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def resolve_role(api_key: str, role_hashes: dict[str, str]) -> str | None:
    if not api_key:
        return None
    presented = hash_api_key(api_key)
    for role, configured_hash in role_hashes.items():
        if configured_hash and hmac.compare_digest(presented, configured_hash.strip().lower()):
            return role
    return None


def required_role(method: str, path: str) -> str:
    if method.upper() in {"GET", "HEAD", "OPTIONS"}:
        return "viewer"
    if path.startswith("/api/v1/approvals/") and path.endswith("/decision"):
        return "approver"
    return "operator"


def role_allowed(role: str | None, required: str) -> bool:
    if role is None:
        return False
    if role == "admin":
        return True
    # Approvers can inspect and decide approvals but should not implicitly gain
    # every operator mutation. Keep approval authority separate.
    if required == "approver":
        return role == "approver"
    if required == "operator":
        return role == "operator"
    return ROLE_ORDER.get(role, 0) >= ROLE_ORDER["viewer"]


class ServiceKeyRBACMiddleware(BaseHTTPMiddleware):
    """Optional service-key RBAC for self-hosted deployments.

    This deliberately does not claim to be enterprise SSO. It provides a
    dependency-free control for demos/private deployments while leaving OIDC
    integration as the preferred production identity architecture.
    """

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if not settings.auth_enabled or request.url.path in PUBLIC_PATHS:
            request.state.role = "auth-disabled" if not settings.auth_enabled else "public"
            return await call_next(request)

        role_hashes = {
            "viewer": settings.viewer_api_key_sha256,
            "operator": settings.operator_api_key_sha256,
            "approver": settings.approver_api_key_sha256,
            "admin": settings.admin_api_key_sha256,
        }
        api_key = request.headers.get("X-API-Key", "")
        role = resolve_role(api_key, role_hashes)
        if role is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Valid X-API-Key required"},
                headers={"WWW-Authenticate": "ApiKey"},
            )

        required = required_role(request.method, request.url.path)
        if not role_allowed(role, required):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": f"Role '{role}' is not permitted; required role: {required}",
                },
            )

        request.state.role = role
        return await call_next(request)
