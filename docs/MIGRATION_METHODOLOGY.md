# VMware → Nutanix Migration Methodology

## 1. Discover
Collect RVTools/vCenter inventory, owners, criticality, dependency data, network mappings, backup status and downtime constraints.

## 2. Assess
Use this application to normalize the estate and expose complexity factors. Separately validate Nutanix Move and target-platform supportability using current official documentation.

## 3. Design target
Confirm AHV cluster placement, target subnets, IP strategy, DNS, security controls, capacity headroom and recovery requirements.

## 4. Plan waves
Keep application dependencies together. Include pilot workloads before business-critical migrations. Define freeze periods and validation owners.

## 5. Pre-cutover
- Verify backups and rollback criteria.
- Confirm application shutdown/start sequence.
- Confirm source/target network mappings.
- Run Move preparation/pre-seeding as appropriate.
- Confirm UAT and business-owner availability.

## 6. Cutover
Execute approved runbook, record timestamps and decisions, validate application and infrastructure health, and invoke rollback when acceptance criteria are not met.

## 7. Stabilize and hand over
Monitor, close defects, reconcile CMDB/documentation, decommission source only after approval, and capture lessons learned.
