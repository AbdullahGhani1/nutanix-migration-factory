# High-Level Design — Nutanix Migration Factory

## Objective
Provide a repeatable assessment and planning layer for VMware-to-Nutanix migrations.

## Components

1. **Web UI** — analyst workflow for imports, assessment and waves.
2. **API** — inventory ingestion, scoring, planning and report generation.
3. **Relational DB** — workload inventory and assessment state.
4. **Prism Central Adapter** — optional read-only target discovery using Nutanix v4 APIs.
5. **Reporting** — migration-plan CSV for engineering review and change planning.

## Design principles

- Explainable scoring; no black-box “AI compatibility” claims.
- Application groups remain intact during automatic wave planning.
- All Nutanix integration is read-only in MVP.
- TLS verification defaults to enabled.
- Source data can be sanitized before import.
- Final supportability is validated using official Nutanix documentation and Move checks.
