from types import SimpleNamespace

import pytest

from app.services.dr_planner import plan_protection, replication_mode, replication_mbps


def vm(**overrides):
    values = dict(id=1, name="APP-01", criticality="Medium", storage_gb=1000, rpo_minutes=None, rto_minutes=None)
    values.update(overrides)
    return SimpleNamespace(**values)


def test_replication_mode_thresholds():
    assert replication_mode(0) == ("Synchronous", 0)
    assert replication_mode(5) == ("NearSync", 5)
    assert replication_mode(45) == ("NearSync", 15)
    assert replication_mode(60) == ("Async", 60)
    assert replication_mode(300) == ("Async", 240)
    with pytest.raises(ValueError):
        replication_mode(-1)


def test_bandwidth_estimate_uses_decimal_units():
    # 1,000 GB at 5% daily change = 50 GB/day = 400,000 Mb / 86,400 s
    assert round(replication_mbps(1000, 5), 2) == 4.63


def test_policies_group_by_mode_and_use_tier_defaults():
    plan = plan_protection([vm(criticality="Critical"), vm(id=2, name="APP-02", criticality="Low")])
    names = [p["name"] for p in plan["policies"]]
    assert names == ["PP-NEARSYNC-15M", "PP-ASYNC-24H"]
    critical = plan["workloads"][0]
    assert critical["category"] == "DR-Tier:PP-NEARSYNC-15M"
    assert any("recovery plan" in n for n in critical["notes"])


def test_sync_blocked_when_rtt_too_high():
    plan = plan_protection([vm(rpo_minutes=0)], site_rtt_ms=12)
    assert plan["status"] == "Blocked"
    assert "exceeds 5.0 ms" in plan["blockers"][0]


def test_sync_allowed_on_low_latency_metro_link():
    plan = plan_protection([vm(rpo_minutes=0)], site_rtt_ms=2)
    assert plan["status"] == "Ready"
    assert plan["policies"][0]["name"] == "PP-SYNC-RPO0"


def test_link_bandwidth_checks():
    workloads = [vm(storage_gb=20000)]  # ~92.6 Mbps average
    assert plan_protection(workloads, available_bandwidth_mbps=50)["status"] == "Blocked"
    thin = plan_protection(workloads, available_bandwidth_mbps=100)
    assert thin["status"] == "Ready"
    assert thin["recommended_link_mbps"] == 186
    assert "peak estimate" in thin["warnings"][0]
