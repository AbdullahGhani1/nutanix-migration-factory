"""DR protection planning for AHV target workloads.

Maps each workload's recovery objectives to a Nutanix replication mode and
groups workloads into protection policies that can be created in Prism Central
and attached through categories. The mode thresholds follow the documented
Nutanix replication types (synchronous for zero RPO, NearSync for 1-15 minute
RPO, asynchronous for hourly or longer schedules) but are parameters, because
supported ranges differ between AOS / Prism Central releases and must be
confirmed against the target version.
"""
from __future__ import annotations

import math
from collections import defaultdict

# Planning defaults per business criticality: (RPO minutes, RTO minutes).
TIER_OBJECTIVES = {
    "Critical": (15, 60),
    "High": (60, 240),
    "Medium": (240, 480),
    "Low": (1440, 1440),
}

ASYNC_INTERVALS = (60, 120, 180, 240, 360, 480, 720, 1440)


def objectives(workload) -> tuple[int, int]:
    default_rpo, default_rto = TIER_OBJECTIVES.get((workload.criticality or "Medium").title(), TIER_OBJECTIVES["Medium"])
    rpo = workload.rpo_minutes if getattr(workload, "rpo_minutes", None) is not None else default_rpo
    rto = workload.rto_minutes if getattr(workload, "rto_minutes", None) is not None else default_rto
    return int(rpo), int(rto)


def replication_mode(rpo_minutes: int, nearsync_max_minutes: int = 15) -> tuple[str, int]:
    """Return (mode, snapshot interval in minutes) that meets the RPO."""
    if rpo_minutes < 0:
        raise ValueError("RPO cannot be negative")
    if rpo_minutes == 0:
        return "Synchronous", 0
    if rpo_minutes < 60:
        return "NearSync", max(1, min(rpo_minutes, nearsync_max_minutes))
    interval = max(i for i in ASYNC_INTERVALS if i <= rpo_minutes)
    return "Async", interval


def policy_name(mode: str, interval: int) -> str:
    if mode == "Synchronous":
        return "PP-SYNC-RPO0"
    if interval >= 60 and interval % 60 == 0:
        return f"PP-{mode.upper()}-{interval // 60}H"
    return f"PP-{mode.upper()}-{interval}M"


def replication_mbps(storage_gb: float, daily_change_rate_percent: float) -> float:
    """Average replication bandwidth for the daily changed data, in Mbps.

    Uses decimal units (1 GB = 8,000 Mb) and ignores compression/dedup, so it is
    an upper-bound planning figure, not a WAN sizing guarantee.
    """
    changed_gb = storage_gb * daily_change_rate_percent / 100
    return changed_gb * 8000 / 86400


def plan_protection(
    workloads,
    site_rtt_ms: float | None = None,
    sync_max_rtt_ms: float = 5.0,
    daily_change_rate_percent: float = 5.0,
    nearsync_max_minutes: int = 15,
    available_bandwidth_mbps: float | None = None,
    peak_factor: float = 2.0,
) -> dict:
    items = []
    blockers: list[str] = []
    warnings: list[str] = []
    policies: dict[str, dict] = defaultdict(lambda: {"workloads": [], "storage_gb": 0.0, "avg_mbps": 0.0})

    for w in workloads:
        rpo, rto = objectives(w)
        mode, interval = replication_mode(rpo, nearsync_max_minutes)
        name = policy_name(mode, interval)
        mbps = replication_mbps(w.storage_gb, daily_change_rate_percent)
        notes: list[str] = []

        if mode == "Synchronous":
            if site_rtt_ms is None:
                notes.append("RPO 0 requires synchronous replication; inter-site RTT not supplied")
            elif site_rtt_ms > sync_max_rtt_ms:
                blockers.append(
                    f"{w.name}: RPO 0 needs synchronous replication but site RTT {site_rtt_ms} ms exceeds {sync_max_rtt_ms} ms"
                )
        if rto <= 60:
            notes.append("RTO <= 60 min: use a Prism Central recovery plan with boot order and network mapping, and rehearse failover")
        if rto < rpo and mode != "Synchronous":
            notes.append("RTO is shorter than RPO; confirm objectives with the application owner")

        policy = policies[name]
        policy["mode"] = mode
        policy["snapshot_interval_minutes"] = interval
        policy["category"] = f"DR-Tier:{name}"
        policy["workloads"].append(w.name)
        policy["storage_gb"] += w.storage_gb
        policy["avg_mbps"] += mbps

        items.append(
            {
                "workload_id": w.id,
                "name": w.name,
                "criticality": w.criticality,
                "rpo_minutes": rpo,
                "rto_minutes": rto,
                "mode": mode,
                "snapshot_interval_minutes": interval,
                "protection_policy": name,
                "category": f"DR-Tier:{name}",
                "avg_replication_mbps": round(mbps, 2),
                "notes": notes,
            }
        )

    total_mbps = sum(p["avg_mbps"] for p in policies.values())
    recommended_mbps = math.ceil(total_mbps * peak_factor) if total_mbps else 0
    if available_bandwidth_mbps is not None:
        if total_mbps > available_bandwidth_mbps:
            blockers.append(
                f"Average replication demand {total_mbps:.1f} Mbps exceeds available DR link bandwidth {available_bandwidth_mbps} Mbps"
            )
        elif recommended_mbps > available_bandwidth_mbps:
            warnings.append(
                f"DR link {available_bandwidth_mbps} Mbps covers the average but not the {peak_factor}x peak estimate ({recommended_mbps} Mbps)"
            )
    if any(p["mode"] == "Synchronous" for p in policies.values()) and site_rtt_ms is None:
        warnings.append("Synchronous replication planned without a measured inter-site RTT")

    policy_list = [
        {
            "name": name,
            "mode": p["mode"],
            "snapshot_interval_minutes": p["snapshot_interval_minutes"],
            "category": p["category"],
            "workload_count": len(p["workloads"]),
            "workloads": sorted(p["workloads"]),
            "storage_gb": round(p["storage_gb"], 2),
            "avg_replication_mbps": round(p["avg_mbps"], 2),
        }
        for name, p in sorted(policies.items(), key=lambda kv: (kv[1]["snapshot_interval_minutes"], kv[0]))
    ]

    return {
        "status": "Blocked" if blockers else "Ready",
        "assumptions": {
            "site_rtt_ms": site_rtt_ms,
            "sync_max_rtt_ms": sync_max_rtt_ms,
            "daily_change_rate_percent": daily_change_rate_percent,
            "nearsync_max_minutes": nearsync_max_minutes,
            "available_bandwidth_mbps": available_bandwidth_mbps,
            "peak_factor": peak_factor,
        },
        "total_avg_replication_mbps": round(total_mbps, 2),
        "recommended_link_mbps": recommended_mbps,
        "policies": policy_list,
        "workloads": items,
        "blockers": blockers,
        "warnings": warnings,
    }
