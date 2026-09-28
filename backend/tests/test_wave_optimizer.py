from types import SimpleNamespace

from app.services.wave_optimizer import optimize_waves


def vm(
    id,
    name,
    app_group,
    cpu=4,
    memory_gb=8,
    storage_gb=100,
    score=10,
    criticality="Medium",
):
    return SimpleNamespace(
        id=id,
        name=name,
        app_group=app_group,
        cpu=cpu,
        memory_gb=memory_gb,
        storage_gb=storage_gb,
        migration_score=score,
        criticality=criticality,
        wave_number=None,
    )


def dep(upstream, downstream):
    return SimpleNamespace(
        upstream_workload_id=upstream,
        downstream_workload_id=downstream,
    )


def test_optimizer_preserves_application_groups_and_dependencies():
    workloads = [
        vm(1, "DB-01", "ERP", cpu=8, memory_gb=32),
        vm(2, "APP-01", "ERP", cpu=8, memory_gb=16),
        vm(3, "WEB-01", "Portal", score=5, criticality="Low"),
    ]
    result = optimize_waves(
        workloads,
        [dep(1, 3)],
        max_vms=2,
        max_vcpu=32,
        max_memory_gb=64,
        max_storage_gb=1000,
    )
    assert result["has_cycle"] is False
    erp_wave = workloads[0].wave_number
    assert workloads[1].wave_number == erp_wave
    assert erp_wave <= workloads[2].wave_number


def test_optimizer_keeps_oversized_group_atomic_and_warns():
    workloads = [
        vm(1, "DB-01", "ERP", memory_gb=200),
        vm(2, "APP-01", "ERP", memory_gb=200),
    ]
    result = optimize_waves(
        workloads,
        [],
        max_vms=20,
        max_vcpu=160,
        max_memory_gb=256,
        max_storage_gb=5000,
    )
    assert len(result["waves"]) == 1
    assert result["waves"][0]["warnings"]
    assert workloads[0].wave_number == workloads[1].wave_number == 1


def test_pilot_first_prefers_lower_risk_when_dependency_safe():
    workloads = [
        vm(1, "LEGACY-01", "Legacy", score=70, criticality="Critical"),
        vm(2, "WEB-01", "Web", score=5, criticality="Low"),
    ]
    result = optimize_waves(
        workloads,
        [],
        max_vms=1,
        max_vcpu=160,
        max_memory_gb=512,
        max_storage_gb=5000,
        strategy="pilot_first",
    )
    assert result["waves"][0]["workload_names"] == ["WEB-01"]
    assert result["waves"][1]["workload_names"] == ["LEGACY-01"]
