from __future__ import annotations

KNOWN_OS_HINTS = (
    "windows", "rhel", "red hat", "ubuntu", "centos", "rocky", "alma", "suse", "debian", "oracle linux"
)


def score_workload(workload) -> tuple[int, str, list[str]]:
    score = 0
    reasons: list[str] = []

    criticality = (workload.criticality or "Medium").lower()
    if criticality == "critical":
        score += 25; reasons.append("Business critical workload")
    elif criticality == "high":
        score += 18; reasons.append("High business criticality")

    if workload.downtime_minutes <= 15:
        score += 18; reasons.append("Very low downtime tolerance")
    elif workload.downtime_minutes <= 30:
        score += 10; reasons.append("Low downtime tolerance")

    if workload.cpu > 16:
        score += 10; reasons.append("High vCPU count")
    elif workload.cpu > 8:
        score += 5; reasons.append("Moderate vCPU count")

    if workload.memory_gb > 128:
        score += 12; reasons.append("Very large memory footprint")
    elif workload.memory_gb > 64:
        score += 7; reasons.append("Large memory footprint")

    if workload.storage_gb > 4096:
        score += 15; reasons.append("Very large storage footprint")
    elif workload.storage_gb > 2048:
        score += 10; reasons.append("Large storage footprint")
    elif workload.storage_gb > 1024:
        score += 5; reasons.append("Moderate storage footprint")

    if workload.snapshots > 5:
        score += 10; reasons.append("Many source snapshots require cleanup/review")
    elif workload.snapshots > 0:
        score += 3; reasons.append("Source snapshots present")

    if workload.nic_count > 4:
        score += 8; reasons.append("Multiple NICs require network mapping review")
    elif workload.nic_count > 2:
        score += 4; reasons.append("More than two NICs")

    os_name = (workload.os or "Unknown").lower()
    if os_name == "unknown" or not any(hint in os_name for hint in KNOWN_OS_HINTS):
        score += 12; reasons.append("Guest OS requires manual supportability verification")

    score = min(score, 100)
    risk = "High" if score >= 55 else "Medium" if score >= 25 else "Low"
    if not reasons:
        reasons.append("No complexity factors triggered by current scoring policy")
    return score, risk, reasons
