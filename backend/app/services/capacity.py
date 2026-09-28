from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class WaveDemand:
    wave: int
    workloads: int
    vcpu: int
    memory_gb: float
    storage_gb: float

    def to_dict(self) -> dict:
        return asdict(self)


def calculate_wave_demand(wave_number: int, workloads: list) -> WaveDemand:
    return WaveDemand(
        wave=wave_number,
        workloads=len(workloads),
        vcpu=sum(int(w.cpu or 0) for w in workloads),
        memory_gb=round(sum(float(w.memory_gb or 0) for w in workloads), 2),
        storage_gb=round(sum(float(w.storage_gb or 0) for w in workloads), 2),
    )


def evaluate_cluster(cluster, demand: WaveDemand, headroom_percent: float = 20.0) -> dict:
    """Evaluate whether a planned migration wave fits a target cluster envelope.

    CPU is modeled using an explicit planning overcommit ratio:
    physical_cpu_cores * cpu_overcommit_ratio.

    This is capacity-planning logic, not an AHV sizing recommendation. Production
    sizing must still consider measured CPU utilization, HA/N+1 policy, storage
    resiliency, workload reservations, licensing and Nutanix sizing guidance.
    """
    reserve = headroom_percent / 100.0

    effective_vcpu_capacity = float(cluster.physical_cpu_cores) * float(cluster.cpu_overcommit_ratio)
    max_vcpu = effective_vcpu_capacity * (1 - reserve)
    max_memory = float(cluster.total_memory_gb) * (1 - reserve)
    max_storage = float(cluster.usable_storage_gb) * (1 - reserve)

    projected_vcpu = float(cluster.allocated_vcpu) + demand.vcpu
    projected_memory = float(cluster.used_memory_gb) + demand.memory_gb
    projected_storage = float(cluster.used_storage_gb) + demand.storage_gb

    reasons: list[str] = []
    if projected_vcpu > max_vcpu:
        reasons.append(
            f"CPU planning envelope exceeded: projected {projected_vcpu:.1f} vCPU > "
            f"{max_vcpu:.1f} vCPU after {headroom_percent:.0f}% headroom"
        )
    if projected_memory > max_memory:
        reasons.append(
            f"Memory headroom exceeded: projected {projected_memory:.1f} GB > "
            f"{max_memory:.1f} GB after {headroom_percent:.0f}% headroom"
        )
    if projected_storage > max_storage:
        reasons.append(
            f"Storage headroom exceeded: projected {projected_storage:.1f} GB > "
            f"{max_storage:.1f} GB after {headroom_percent:.0f}% headroom"
        )
    if not cluster.enabled:
        reasons.append("Target cluster is disabled for placement")

    fit = not reasons

    # Higher score means more balanced remaining capacity after placement.
    def remaining_ratio(limit: float, projected: float) -> float:
        if limit <= 0:
            return 0.0
        return max(0.0, (limit - projected) / limit)

    score = round(
        100
        * (
            remaining_ratio(max_vcpu, projected_vcpu)
            + remaining_ratio(max_memory, projected_memory)
            + remaining_ratio(max_storage, projected_storage)
        )
        / 3,
        2,
    )

    return {
        "cluster_id": cluster.id,
        "cluster_name": cluster.name,
        "fit": fit,
        "score": score,
        "reasons": reasons or ["Wave fits configured capacity and headroom policy"],
        "effective_vcpu_capacity": round(effective_vcpu_capacity, 2),
        "projected_vcpu": round(projected_vcpu, 2),
        "projected_memory_gb": round(projected_memory, 2),
        "projected_storage_gb": round(projected_storage, 2),
        "max_vcpu_after_headroom": round(max_vcpu, 2),
        "max_memory_after_headroom_gb": round(max_memory, 2),
        "max_storage_after_headroom_gb": round(max_storage, 2),
    }


def normalize_prism_cluster_inventory(payload: dict) -> list[dict]:
    """Normalize cluster identity fields from a Prism Central v4 list response.

    The function intentionally extracts only stable identity fields needed for
    reconciliation and does not infer capacity metrics from undocumented fields.
    """
    data = payload.get("data", []) if isinstance(payload, dict) else []
    normalized = []
    for item in data:
        if not isinstance(item, dict):
            continue
        ext_id = str(item.get("extId") or item.get("ext_id") or "").strip()
        name = str(item.get("name") or "").strip()
        normalized.append({"prism_ext_id": ext_id, "prism_name": name})
    return normalized


def reconcile_prism_clusters(prism_items: list[dict], local_clusters: list) -> list[dict]:
    by_ext = {c.prism_ext_id: c for c in local_clusters if c.prism_ext_id}
    by_name = {c.name.lower(): c for c in local_clusters if c.name}

    results = []
    for item in prism_items:
        ext_id = item.get("prism_ext_id", "")
        name = item.get("prism_name", "")
        local = by_ext.get(ext_id) if ext_id else None
        if local is None and name:
            local = by_name.get(name.lower())
        results.append(
            {
                "prism_ext_id": ext_id,
                "prism_name": name,
                "local_cluster_id": local.id if local else None,
                "local_cluster_name": local.name if local else None,
                "status": "Matched" if local else "Unmatched",
            }
        )
    return results
