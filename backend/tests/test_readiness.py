from types import SimpleNamespace

from app.services.readiness import evaluate_workload, summarize_readiness


def vm(**overrides):
    values = dict(
        id=1,
        name="APP-01",
        target_network="AHV-PROD",
        power_state="poweredOn",
        snapshots=0,
        nic_count=1,
        os="Windows Server 2022",
        downtime_minutes=60,
        storage_gb=200,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_ready_workload():
    result = evaluate_workload(vm())
    assert result.status == "Ready"
    assert not result.blockers


def test_unmapped_network_blocks():
    result = evaluate_workload(vm(target_network=""))
    assert result.status == "Blocked"
    assert "Target AHV network is not mapped" in result.blockers


def test_warning_state_and_summary():
    result = evaluate_workload(vm(snapshots=2, downtime_minutes=10))
    assert result.status == "Ready with warnings"
    summary = summarize_readiness([evaluate_workload(vm()), result])
    assert summary == {
        "ready": 1,
        "ready_with_warnings": 1,
        "blocked": 0,
        "total": 2,
    }
