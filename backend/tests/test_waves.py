from types import SimpleNamespace
from app.services.waves import plan_waves


def w(name, app, storage, score):
    return SimpleNamespace(name=name, app_group=app, storage_gb=storage, migration_score=score, wave_number=None)


def test_group_is_not_split_when_capacity_allows():
    items = [w("ERP-APP", "ERP", 500, 30), w("ERP-DB", "ERP", 800, 50), w("WEB", "WEB", 100, 10)]
    waves = plan_waves(items, max_vms=10, max_storage_gb=2000)
    assert len(waves) == 1
    assert {x.wave_number for x in items} == {1}


def test_capacity_creates_multiple_waves():
    items = [w("A", "APP-A", 2000, 50), w("B", "APP-B", 2000, 20)]
    waves = plan_waves(items, max_vms=10, max_storage_gb=2500)
    assert len(waves) == 2
