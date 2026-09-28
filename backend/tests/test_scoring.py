from types import SimpleNamespace
from app.services.scoring import score_workload


def workload(**overrides):
    data = dict(
        criticality="Medium", downtime_minutes=60, cpu=4, memory_gb=8,
        storage_gb=200, snapshots=0, nic_count=1, os="Ubuntu Linux"
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def test_low_complexity_workload():
    score, risk, reasons = score_workload(workload())
    assert risk == "Low"
    assert score < 25
    assert reasons


def test_high_complexity_workload():
    score, risk, reasons = score_workload(workload(
        criticality="Critical", downtime_minutes=10, cpu=32, memory_gb=256,
        storage_gb=6000, snapshots=9, nic_count=6, os="Unknown appliance"
    ))
    assert risk == "High"
    assert score >= 55
    assert len(reasons) >= 6
