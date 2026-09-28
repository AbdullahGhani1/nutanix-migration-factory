from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict


CRITICALITY_WEIGHT = {
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Critical": 4,
}


@dataclass(frozen=True)
class GroupDemand:
    key: str
    workload_ids: list[int]
    workload_names: list[str]
    vms: int
    vcpu: int
    memory_gb: float
    storage_gb: float
    max_complexity: int
    max_criticality: int

    def to_dict(self) -> dict:
        return asdict(self)


def _group_key(workload) -> str:
    app = (workload.app_group or "").strip()
    # Treat ungrouped workloads independently so one "Ungrouped" bucket does
    # not accidentally force unrelated VMs into the same migration wave.
    return app if app and app.lower() != "ungrouped" else f"vm:{workload.id}"


def build_group_demands(workloads: list) -> dict[str, GroupDemand]:
    groups: dict[str, list] = defaultdict(list)
    for workload in workloads:
        groups[_group_key(workload)].append(workload)

    result: dict[str, GroupDemand] = {}
    for key, items in groups.items():
        result[key] = GroupDemand(
            key=key,
            workload_ids=sorted(w.id for w in items),
            workload_names=sorted(w.name for w in items),
            vms=len(items),
            vcpu=sum(int(w.cpu or 0) for w in items),
            memory_gb=round(sum(float(w.memory_gb or 0) for w in items), 2),
            storage_gb=round(sum(float(w.storage_gb or 0) for w in items), 2),
            max_complexity=max(int(w.migration_score or 0) for w in items),
            max_criticality=max(CRITICALITY_WEIGHT.get(w.criticality or "Medium", 2) for w in items),
        )
    return result


def build_group_dependency_graph(workloads: list, dependencies: list) -> tuple[dict[str, set[str]], dict[str, int]]:
    workload_group = {w.id: _group_key(w) for w in workloads}
    graph: dict[str, set[str]] = defaultdict(set)
    indegree: dict[str, int] = {key: 0 for key in set(workload_group.values())}

    for dep in dependencies:
        upstream = workload_group.get(dep.upstream_workload_id)
        downstream = workload_group.get(dep.downstream_workload_id)
        if not upstream or not downstream or upstream == downstream:
            continue
        if downstream not in graph[upstream]:
            graph[upstream].add(downstream)
            indegree[downstream] += 1
    return graph, indegree


def _priority(group: GroupDemand, strategy: str) -> tuple:
    if strategy == "risk_first":
        return (-group.max_criticality, -group.max_complexity, group.storage_gb, group.key)
    # Default: choose a low-risk, low-complexity pilot-friendly sequence among
    # dependency-safe groups.
    return (group.max_criticality, group.max_complexity, group.storage_gb, group.key)


def _topological_group_order(
    demands: dict[str, GroupDemand],
    graph: dict[str, set[str]],
    indegree: dict[str, int],
    strategy: str,
) -> tuple[list[str], list[str]]:
    ready = [key for key, degree in indegree.items() if degree == 0]
    ready.sort(key=lambda key: _priority(demands[key], strategy))
    order: list[str] = []
    local_indegree = dict(indegree)

    while ready:
        key = ready.pop(0)
        order.append(key)
        for nxt in sorted(graph.get(key, set())):
            local_indegree[nxt] -= 1
            if local_indegree[nxt] == 0:
                ready.append(nxt)
                ready.sort(key=lambda item: _priority(demands[item], strategy))

    unresolved = sorted(set(demands) - set(order))
    return order, unresolved


def optimize_waves(
    workloads: list,
    dependencies: list,
    *,
    max_vms: int = 20,
    max_vcpu: int = 160,
    max_memory_gb: float = 512.0,
    max_storage_gb: float = 5000.0,
    strategy: str = "pilot_first",
) -> dict:
    if strategy not in {"pilot_first", "risk_first"}:
        raise ValueError("strategy must be pilot_first or risk_first")

    demands = build_group_demands(workloads)
    graph, indegree = build_group_dependency_graph(workloads, dependencies)
    order, unresolved = _topological_group_order(demands, graph, indegree, strategy)
    if unresolved:
        return {
            "has_cycle": True,
            "unresolved_groups": unresolved,
            "waves": [],
            "constraints": {
                "max_vms": max_vms,
                "max_vcpu": max_vcpu,
                "max_memory_gb": max_memory_gb,
                "max_storage_gb": max_storage_gb,
            },
            "strategy": strategy,
        }

    waves: list[dict] = []
    current = {
        "groups": [],
        "workload_ids": [],
        "workload_names": [],
        "vms": 0,
        "vcpu": 0,
        "memory_gb": 0.0,
        "storage_gb": 0.0,
        "warnings": [],
    }

    def exceeds(candidate: GroupDemand, wave: dict) -> bool:
        return (
            wave["vms"] + candidate.vms > max_vms
            or wave["vcpu"] + candidate.vcpu > max_vcpu
            or wave["memory_gb"] + candidate.memory_gb > max_memory_gb
            or wave["storage_gb"] + candidate.storage_gb > max_storage_gb
        )

    def group_violations(group: GroupDemand) -> list[str]:
        violations = []
        if group.vms > max_vms:
            violations.append(f"group has {group.vms} VMs > max {max_vms}")
        if group.vcpu > max_vcpu:
            violations.append(f"group has {group.vcpu} vCPU > max {max_vcpu}")
        if group.memory_gb > max_memory_gb:
            violations.append(f"group has {group.memory_gb:.1f} GB RAM > max {max_memory_gb:.1f}")
        if group.storage_gb > max_storage_gb:
            violations.append(f"group has {group.storage_gb:.1f} GB storage > max {max_storage_gb:.1f}")
        return violations

    def flush():
        nonlocal current
        if current["groups"]:
            current["wave"] = len(waves) + 1
            current["memory_gb"] = round(current["memory_gb"], 2)
            current["storage_gb"] = round(current["storage_gb"], 2)
            waves.append(current)
        current = {
            "groups": [],
            "workload_ids": [],
            "workload_names": [],
            "vms": 0,
            "vcpu": 0,
            "memory_gb": 0.0,
            "storage_gb": 0.0,
            "warnings": [],
        }

    for key in order:
        group = demands[key]
        if current["groups"] and exceeds(group, current):
            flush()

        violations = group_violations(group)
        current["groups"].append(key)
        current["workload_ids"].extend(group.workload_ids)
        current["workload_names"].extend(group.workload_names)
        current["vms"] += group.vms
        current["vcpu"] += group.vcpu
        current["memory_gb"] += group.memory_gb
        current["storage_gb"] += group.storage_gb
        current["warnings"].extend([f"{key}: {v}" for v in violations])

        # Oversized application groups are kept atomic and isolated in their own
        # wave with an explicit warning instead of silently splitting them.
        if violations:
            flush()

    flush()

    # Assign persisted wave numbers.
    by_id = {w.id: w for w in workloads}
    for wave in waves:
        for workload_id in wave["workload_ids"]:
            by_id[workload_id].wave_number = wave["wave"]

    return {
        "has_cycle": False,
        "unresolved_groups": [],
        "waves": waves,
        "constraints": {
            "max_vms": max_vms,
            "max_vcpu": max_vcpu,
            "max_memory_gb": max_memory_gb,
            "max_storage_gb": max_storage_gb,
        },
        "strategy": strategy,
    }
