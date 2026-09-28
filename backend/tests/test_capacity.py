from types import SimpleNamespace

from app.services.capacity import calculate_wave_demand, evaluate_cluster


def workload(cpu=4, memory_gb=8, storage_gb=100):
    return SimpleNamespace(cpu=cpu, memory_gb=memory_gb, storage_gb=storage_gb)


def cluster(**overrides):
    values = dict(
        id=1,
        name="AHV-PROD-A",
        physical_cpu_cores=64,
        cpu_overcommit_ratio=4.0,
        allocated_vcpu=100,
        total_memory_gb=1024,
        used_memory_gb=300,
        usable_storage_gb=20000,
        used_storage_gb=6000,
        enabled=True,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_wave_demand_aggregation():
    demand = calculate_wave_demand(2, [workload(), workload(cpu=8, memory_gb=16, storage_gb=300)])
    assert demand.wave == 2
    assert demand.workloads == 2
    assert demand.vcpu == 12
    assert demand.memory_gb == 24
    assert demand.storage_gb == 400


def test_cluster_fit_with_headroom():
    demand = calculate_wave_demand(1, [workload(cpu=20, memory_gb=100, storage_gb=500)])
    result = evaluate_cluster(cluster(), demand, 20)
    assert result["fit"] is True
    assert result["score"] > 0


def test_cluster_rejected_when_memory_headroom_exceeded():
    demand = calculate_wave_demand(1, [workload(cpu=2, memory_gb=300, storage_gb=20)])
    result = evaluate_cluster(cluster(total_memory_gb=512, used_memory_gb=200), demand, 20)
    assert result["fit"] is False
    assert any("Memory headroom exceeded" in x for x in result["reasons"])
