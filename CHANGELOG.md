# Changelog

## 0.5.0 — in development

- Added migration execution records linked to approved change requests
- Added Planned / InProgress / Succeeded / RolledBack / Failed execution lifecycle
- Added measured cutover duration and UAT status fields
- Added explicit validation summary and rollback reason requirements
- Added Nutanix Move plan name and sanitized evidence-reference fields
- Added execution audit events and standalone evidence endpoint
- Added migration execution evidence to implementation PDF
- Added migration execution dashboard and controls
- Added Alembic revision 0002 for execution evidence
- Added ZIP evidence bundle containing implementation PDF, migration CSV, execution JSON and SHA-256 manifest
- Active-estate replacement now invalidates stale execution records before approvals/workloads

## 0.4.0 — in development

- Added read-only Prism Central connection-test endpoint
- Added GA v4 subnet discovery via networking namespace
- Added paginated cluster, VM and subnet inventory collection
- Added explicit inventory truncation metadata
- Added planned target-network to live Prism subnet reconciliation
- Added Matched / Missing / Ambiguous network states
- Added React Prism discovery and network reconciliation dashboard
- Added tests for v4 subnet normalization, reconciliation and pagination behavior
- Bumped API service version to 0.4.0

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
