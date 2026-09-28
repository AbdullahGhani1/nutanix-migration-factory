# UAE Enterprise Controls

Three planning controls that UAE infrastructure teams (banking, government,
healthcare, telecom) usually require before a VMware → Nutanix AHV wave can be
approved. They sit between wave planning and the approval gate.

> These are engineering controls with configurable policy. They do not interpret
> any law or regulation. Which obligations apply (for example UAE PDPL, UAE
> Information Assurance standards, DESC ISR, ADHICS or CBUAE requirements) must be
> decided by the organization's compliance function and then encoded as policy.

## 1. Data residency

**Why:** Many UAE organizations must keep sensitive data, and every copy of it,
in the UAE. Migration programs often break this by accident through the DR
site, not the primary site.

**Inputs**

| Source | Field | Notes |
|---|---|---|
| Inventory | `Data Classification` | Public, Internal, Confidential, Secret (aliases: Restricted → Secret, Sensitive → Confidential) |
| Inventory | `Residency` | Optional per-VM override: `AE`, `AE,SA`, `GCC`, `ANY` |
| Target cluster | `country_code`, `site_name` | ISO 3166 alpha-2, e.g. `AE` / `DXB-DC1` |
| Environment | `RESIDENCY_POLICY_JSON` | Classification → allowed countries; default keeps Confidential and Secret in `AE` |

**Result per workload**

- `Compliant`: the primary and DR clusters are in allowed countries
- `Violation`: a cluster is outside the allowed countries
- `Unverified`: restricted data, but the cluster has no `country_code`

The approval workflow rejects a wave when any workload is `Violation` or
`Unverified` for the chosen target cluster.

## 2. DR protection planning

**Why:** A common UAE design is a Dubai primary site and an Abu Dhabi DR site
(or the reverse). The team must decide which replication type each application
needs, and whether the link can carry it.

**Rules**

| RPO | Mode | Snapshot interval |
|---|---|---|
| 0 | Synchronous | n/a; blocked when measured site RTT > `sync_max_rtt_ms` (default 5 ms) |
| 1–59 min | NearSync | RPO, capped at `nearsync_max_minutes` (default 15) |
| ≥ 60 min | Async | the largest standard interval ≤ RPO (1, 2, 3, 4, 6, 8, 12, 24 h) |

If a workload has no RPO/RTO, defaults come from its business criticality:
Critical 15/60, High 60/240, Medium 240/480, Low 1440/1440 minutes.

Workloads are grouped into protection policies (`PP-NEARSYNC-15M`,
`PP-ASYNC-4H`, …), each with a category (`DR-Tier:<policy>`) so they can be
attached in Prism Central by category. Thresholds are parameters because
supported ranges depend on AOS / Prism Central version. Check them against the
target release.

**Bandwidth:** `storage × daily change % × 8000 / 86400` Mbps per VM (decimal
units, before compression and dedup), multiplied by `peak_factor` (default 2)
for the recommended link size. If average demand is above the supplied link, the
plan is blocked. If only the peak is above it, the plan gets a warning.

When a DR cluster is supplied, residency is checked for the DR copy too.

## 3. Change calendar (GST)

**Why:** Cutovers must fit approved change windows and avoid national holidays,
Ramadan working hours and business freezes.

- Timezone: Gulf Standard Time (UTC+4, no daylight saving)
- Default windows: Friday 22:00 → Saturday 06:00 and Saturday 22:00 → Sunday 06:00
  (UAE Monday–Friday work week; Sunday stays free for hypercare)
- `blackout` periods: no cutovers
- `restricted` periods: only waves with no High-risk or Critical workloads
- Required window = prechecks + ⌈VMs / parallel cutovers⌉ × per-VM cutover +
  validation + rollback reserve (all configurable)
- Waves keep their order and are separated by `min_gap_days` (default 7) of hypercare

Islamic holiday dates depend on moon sighting. The dates in
`samples/uae_change_calendar_2026_2027.json` are estimates. Replace them with the
official announcement before use.

## Audit

Every evaluation writes a `PlanningAudit` event: `residency.evaluated`,
`dr.planned`, `change_calendar.scheduled`.
