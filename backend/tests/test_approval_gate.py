from types import SimpleNamespace

from app.services.capacity import calculate_wave_demand, evaluate_cluster
from app.services.readiness import evaluate_workload


def workload(**overrides):
    values = dict(
        id=1,
        name="APP-01",
        cpu=4,
        memory_gb=8,
        storage_gb=100,
        target_network="AHV-PROD",
        power_state="poweredOn",
        snapshots=0,
        nic_count=1,
        os="Windows Server 2022",
        downtime_minutes=60,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def cluster(**overrides):
    values = dict(
        id=1,
        name="AHV-PROD-A",
        physical_cpu_cores=64,
        cpu_overcommit_ratio=4.0,
        allocated_vcpu=80,
        total_memory_gb=1024,
        used_memory_gb=300,
        usable_storage_gb=20000,
        used_storage_gb=6000,
        enabled=True,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_governance_gate_requires_readiness_and_capacity():
    workloads = [workload(), workload(id=2, name="DB-01", cpu=8, memory_gb=32, storage_gb=500)]
    readiness = [evaluate_workload(w) for w in workloads]
    assert all(r.status != "Blocked" for r in readiness)

    demand = calculate_wave_demand(1, workloads)
    placement = evaluate_cluster(cluster(), demand, 20)
    assert placement["fit"] is True


def test_unmapped_workload_would_block_approval():
    result = evaluate_workload(workload(target_network=""))
    assert result.status == "Blocked"
