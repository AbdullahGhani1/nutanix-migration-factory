from __future__ import annotations


def build_wave_runbook(wave_number: int, workloads: list) -> dict:
    names = [w.name for w in workloads]
    app_groups = sorted({w.app_group or "Ungrouped" for w in workloads})
    source_networks = sorted({w.source_network or "Unknown" for w in workloads})
    target_networks = sorted({w.target_network for w in workloads if w.target_network})

    pre_cutover = [
        "Confirm approved change window and stakeholder bridge",
        "Validate Nutanix target cluster health and capacity",
        "Validate source VM health and application owner sign-off",
        "Confirm source-to-target network mapping",
        "Review/remove stale snapshots where operationally approved",
        "Validate Nutanix Move replication/pre-seed state where used",
        "Capture rollback checkpoints and DNS/load-balancer plan",
    ]
    cutover = [
        "Freeze application changes and confirm business owner go/no-go",
        "Stop application services in documented dependency order",
        "Perform final replication delta / migration cutover",
        "Attach target AHV networks and power on workloads",
        "Validate guest boot, IP configuration, DNS and service dependencies",
        "Execute application smoke tests and owner UAT",
    ]
    rollback = [
        "Declare rollback using predefined decision criteria",
        "Power off target workloads to prevent split-brain",
        "Restore source network/DNS/load-balancer state",
        "Power on source workloads in dependency order",
        "Validate application service and data consistency",
        "Record incident details and reschedule migration after RCA",
    ]

    return {
        "wave": wave_number,
        "workloads": names,
        "application_groups": app_groups,
        "source_networks": source_networks,
        "target_networks": target_networks,
        "pre_cutover": pre_cutover,
        "cutover": cutover,
        "rollback": rollback,
    }
