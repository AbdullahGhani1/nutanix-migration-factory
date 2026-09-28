# Enterprise CAB / Change Package

Migration Factory can generate a change-management handoff package from a specific **Approved** migration request.

## Endpoint

`GET /api/v1/reports/approvals/{approval_id}/cab-package.zip`

Pending or rejected approvals are refused. The package is tied to the approval's migration wave and selected target AHV cluster.

## Package contents

- `CAB-summary.pdf` — management/change-review summary
- `change-request.md` — approval-linked change scope
- `implementation-plan.md` — pre-cutover, dependency-aware stop order, cutover and start order
- `rollback-plan.md` — technical rollback template and evidence checklist
- `validation-plan.md` — infrastructure validation separated from application-owner UAT
- `workload-inventory.csv` — scoped workload inventory
- `approval.json` — approval/change metadata
- `readiness-snapshot.json` — planning readiness state at package generation
- `capacity-snapshot.json` — approved target-cluster planning envelope
- `dependency-map.json` — application dependency edges and start/stop order
- `execution-evidence.json` — execution/technical-validation evidence if it already exists
- `manifest.json` — SHA-256 digest and size of every package artifact

## Governance boundary

The CAB pack is generated from Migration Factory's current planning/evidence dataset. SHA-256 provides artifact-integrity evidence, but the application does not independently certify source data, Nutanix Move supportability, production sizing, application UAT, change-window authorization or the truth of operator-entered evidence.

Customer-specific maintenance windows, rollback thresholds, stakeholder contacts, communications, regulatory approvals and business go/no-go criteria must remain under the organization's authorized change-management process.