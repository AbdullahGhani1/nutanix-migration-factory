# Changelog

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
