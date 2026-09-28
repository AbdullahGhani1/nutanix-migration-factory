# Prism Central Environment Evidence

This feature bridges the portfolio software to a real authorized Nutanix environment without making destructive changes.

## Capture

```http
POST /api/v1/nutanix/evidence-snapshots?max_items=1000
Content-Type: application/json

{
  "actor": "migration.engineer",
  "evidence_reference": "CHG-2026-0042/pre-change"
}
```

The server uses the existing read-only Prism Central v4 inventory connector to collect clusters, AHV VMs and subnets.

## Persisted evidence

The database stores:

- capture actor and timestamp
- status: `Captured` or `CapturedWithWarnings`
- observed cluster / VM / subnet counts
- planned target-network count
- matched / missing / ambiguous network totals
- per-inventory truncation flags
- SHA-256 digest of the full in-memory snapshot
- sanitized evidence reference

The raw Prism payload is intentionally not persisted by this record.

## What the digest means

The SHA-256 value is calculated from the canonical JSON representation of the inventory snapshot observed during capture. It is useful as an integrity/provenance checkpoint for the captured observation.

It does **not** prove:

- Nutanix Move compatibility
- production sizing correctness
- workload supportability
- application health
- successful migration execution

## Authorized use

Only run this capture against Prism Central environments you are authorized to access. The connector remains read-only.
