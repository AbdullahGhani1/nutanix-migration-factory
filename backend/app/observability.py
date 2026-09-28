from __future__ import annotations

import json
import logging
import time
import uuid

from fastapi import Request
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware


HTTP_REQUESTS = Counter(
    "migration_factory_http_requests_total",
    "HTTP requests processed by Migration Factory",
    ["method", "route", "status"],
)
HTTP_DURATION = Histogram(
    "migration_factory_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
)

logger = logging.getLogger("migration_factory.http")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Adds request correlation, structured request logs and Prometheus metrics."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            duration = time.perf_counter() - started
            route = _route_template(request)
            HTTP_REQUESTS.labels(request.method, route, "500").inc()
            HTTP_DURATION.labels(request.method, route).observe(duration)
            logger.exception(
                json.dumps(
                    {
                        "event": "http_request_failed",
                        "request_id": request_id,
                        "method": request.method,
                        "route": route,
                        "duration_ms": round(duration * 1000, 2),
                    }
                )
            )
            raise

        duration = time.perf_counter() - started
        route = _route_template(request)
        HTTP_REQUESTS.labels(request.method, route, str(status_code)).inc()
        HTTP_DURATION.labels(request.method, route).observe(duration)

        response.headers["X-Request-ID"] = request_id
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "route": route,
                    "status": status_code,
                    "duration_ms": round(duration * 1000, 2),
                }
            )
        )
        return response


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path or request.url.path
