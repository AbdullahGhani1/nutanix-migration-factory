from __future__ import annotations

from dataclasses import dataclass
import fnmatch


@dataclass(frozen=True)
class NetworkRule:
    source: str
    target: str
    description: str = ""


def resolve_target_network(source_network: str, rules: list[NetworkRule]) -> str | None:
    """Resolve a source VMware network to an AHV subnet.

    Rules are evaluated in order. The source field supports shell-style
    wildcards such as PROD-*, which keeps mappings deterministic and readable.
    """
    source = (source_network or "").strip()
    for rule in rules:
        pattern = (rule.source or "").strip()
        if pattern and fnmatch.fnmatchcase(source.lower(), pattern.lower()):
            return rule.target.strip() or None
    return None


def apply_network_mapping(workloads, rules: list[NetworkRule]) -> dict[str, int]:
    mapped = 0
    unmapped = 0
    for workload in workloads:
        target = resolve_target_network(workload.source_network, rules)
        workload.target_network = target or ""
        if target:
            mapped += 1
        else:
            unmapped += 1
    return {"mapped": mapped, "unmapped": unmapped}
