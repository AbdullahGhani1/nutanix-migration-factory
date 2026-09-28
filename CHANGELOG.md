# Changelog

## 0.3.0 — in development

- Added explicit upstream/downstream workload dependency model
- Added dependency graph API with cycle detection
- Added deterministic service start/stop ordering
- Integrated dependency ordering into migration-wave runbooks
- Added dependency planner UI
- Added implementation-planning PDF export using ReportLab
- Added PDF generation tests
- Invalidated stale dependencies and approvals when a new active estate is imported
- Added dependency-aware wave optimizer with VM/vCPU/memory/storage constraints
- Added pilot-first and risk-first sequencing strategies
- Added optional SHA-256 service-key RBAC for viewer/operator/approver/admin roles
- Added Prometheus request metrics, request correlation and structured HTTP logging
- Added /ready database readiness endpoint and API container health checks
- Added optional Prometheus/Grafana Compose profile and provisioned dashboard
- Expanded CI to validate app import, Compose configuration and container builds
- Added Alembic-managed schema migrations and removed implicit create_all startup behavior
- API container now upgrades the schema before startup; CI validates the migration revision
- Added browser session-scoped API-key support for RBAC-enabled deployments and authenticated report downloads

## 0.2.0 — in development

- Added deterministic source-network → AHV subnet mapping with wildcard rules
- Added pre-migration readiness controls and blocker/warning classification
- Added per-wave enterprise cutover/rollback runbook generation
- Added target AHV capacity profiles and per-wave placement evaluation
- Added Prism Central cluster identity reconciliation
- Added migration approval workflow gated by readiness and capacity
- Added planning audit history for governance-relevant events
- Added capacity and governance tests
- Added React target-cluster capacity planning dashboard
- Added tests for network mapping, readiness and runbooks
- Upgraded API metadata to v0.2.0
- Removed repository-local Git bundle artifact from source control

## 0.1.0 — 2026-09-28

- Initial working MVP
- RVTools CSV/XLSX parser
- migration complexity engine
- application-aware wave planner
- CSV report export
- read-only Prism Central v4 cluster/VM inventory connector
- React dashboard
- Docker Compose
- backend tests and GitHub Actions CI
