from types import SimpleNamespace

from app.services.runbooks import build_wave_runbook


def test_wave_runbook_contains_operational_controls():
    workloads = [
        SimpleNamespace(
            name="ERP-DB-01",
            app_group="ERP",
            source_network="VLAN121",
            target_network="AHV-DB",
        ),
        SimpleNamespace(
            name="ERP-APP-01",
            app_group="ERP",
            source_network="VLAN120",
            target_network="AHV-APP",
        ),
    ]
    runbook = build_wave_runbook(2, workloads)
    assert runbook["wave"] == 2
    assert runbook["workloads"] == ["ERP-DB-01", "ERP-APP-01"]
    assert any("rollback" in step.lower() for step in runbook["pre_cutover"])
    assert any("split-brain" in step.lower() for step in runbook["rollback"])
