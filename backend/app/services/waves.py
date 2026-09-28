from __future__ import annotations
from collections import defaultdict


def plan_waves(workloads, max_vms: int = 20, max_storage_gb: float = 5000.0):
    groups = defaultdict(list)
    for w in workloads:
        groups[w.app_group or "Ungrouped"].append(w)

    # Higher complexity groups first so they are visible and can be manually moved to pilot/later waves.
    ordered_groups = sorted(
        groups.items(),
        key=lambda item: max((w.migration_score or 0) for w in item[1]),
        reverse=True,
    )

    waves: list[list] = []
    current: list = []
    current_storage = 0.0

    for _, group in ordered_groups:
        group_storage = sum(w.storage_gb for w in group)
        if current and (len(current) + len(group) > max_vms or current_storage + group_storage > max_storage_gb):
            waves.append(current)
            current = []
            current_storage = 0.0
        current.extend(group)
        current_storage += group_storage

    if current:
        waves.append(current)

    for idx, wave in enumerate(waves, start=1):
        for w in wave:
            w.wave_number = idx
    return waves
