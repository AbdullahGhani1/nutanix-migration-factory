from app.services.rvtools import parse_csv


def test_rvtools_csv_normalization():
    raw = b"Name,CPUs,Memory MiB,Provisioned MiB,OS according to config file,Network #1,Criticality,Downtime Minutes,App Group\nERP-01,8,32768,512000,Windows Server 2022,VLAN120,High,30,ERP\n"
    rows = parse_csv(raw)
    assert len(rows) == 1
    row = rows[0]
    assert row["name"] == "ERP-01"
    assert row["cpu"] == 8
    assert row["memory_gb"] == 32
    assert row["storage_gb"] == 500
    assert row["app_group"] == "ERP"
