from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class ReadinessResult:
    workload_id: int
    name: str
    status: str
    blockers: list[str]
    warnings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_workload(workload) -> ReadinessResult:
    """Perform planning-time pre-migration readiness checks.

    This is not a Nutanix Move compatibility certification. Product
    supportability must still be validated against the target environment.
    """
    blockers: list[str] = []
    warnings: list[str] = []

    if not (workload.target_network or "").strip():
        blockers.append("Target AHV network is not mapped")

    if (workload.power_state or "").lower() not in {"poweredon", "powered on", "on"}:
        warnings.append("Source VM is not currently reported as powered on")

    if workload.snapshots > 0:
        warnings.append(f"{workload.snapshots} source snapshot(s) require review before migration")

    if workload.nic_count > 4:
        warnings.append("VM has more than four NICs; validate network mapping and target design")

    if (workload.os or "Unknown").strip().lower() == "unknown":
        blockers.append("Guest OS is unknown and requires manual supportability verification")

    if workload.downtime_minutes <= 15:
        warnings.append("Very low downtime tolerance requires cutover rehearsal and rollback validation")

    if workload.storage_gb >= 4096:
        warnings.append("Large storage footprint; validate replication/pre-seed duration and cutover delta")

    status = "Blocked" if blockers else "Ready with warnings" if warnings else "Ready"
    return ReadinessResult(
        workload_id=workload.id,
        name=workload.name,
        status=status,
        blockers=blockers,
        warnings=warnings,
    )


def summarize_readiness(results: list[ReadinessResult]) -> dict[str, int]:
    return {
        "ready": sum(r.status == "Ready" for r in results),
        "ready_with_warnings": sum(r.status == "Ready with warnings" for r in results),
        "blocked": sum(r.status == "Blocked" for r in results),
        "total": len(results),
    }
