# Low-Level Design

## Data model

### Workload
- identity: name
- sizing: cpu, memory_gb, storage_gb
- source: os, source_network, power_state, snapshots, nic_count
- business: criticality, downtime_minutes, app_group, owner
- target: target_network
- derived: migration_score, migration_risk, migration_reasons, wave_number

## Complexity policy

The initial scoring policy is deterministic and unit tested. It increases complexity for:
- business-critical workloads
- low downtime tolerance
- large CPU/RAM/storage footprint
- many snapshots
- multi-NIC network mapping
- guest OS values needing manual verification

The score is explicitly not a compatibility decision.

## Wave policy

1. Group by application group.
2. Sort groups by maximum complexity score.
3. Pack intact groups into waves subject to configurable VM and storage ceilings.
4. Assign wave numbers to workloads.
5. Export for human review.
