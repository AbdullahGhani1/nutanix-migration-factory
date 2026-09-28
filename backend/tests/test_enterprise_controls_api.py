from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app

INVENTORY = (
    "Name,CPUs,Memory GB,Storage GB,OS,Network #1,Powerstate,Criticality,App Group,Target Network,Data Classification,RPO Minutes\n"
    "CBS-DB-01,8,64,2000,RHEL 9,VLAN10,poweredOn,Critical,CoreBanking,AHV-DB,Secret,0\n"
    "CBS-APP-01,4,16,200,RHEL 9,VLAN11,poweredOn,High,CoreBanking,AHV-APP,Confidential,\n"
    "INTRANET-01,2,8,100,Windows Server 2022,VLAN12,poweredOn,Low,Intranet,AHV-WEB,Internal,\n"
)


def cluster(name, country, cores=64):
    return {
        "name": name,
        "country_code": country,
        "site_name": name.split("-")[0],
        "physical_cpu_cores": cores,
        "cpu_overcommit_ratio": 4,
        "allocated_vcpu": 0,
        "total_memory_gb": 2048,
        "used_memory_gb": 0,
        "usable_storage_gb": 100000,
        "used_storage_gb": 0,
    }


def make_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def test_uae_controls_end_to_end():
    client = make_client()
    try:
        r = client.post("/api/v1/imports/rvtools", files={"file": ("inv.csv", INVENTORY, "text/csv")})
        assert r.status_code == 200, r.text
        workloads = {w["name"]: w for w in client.get("/api/v1/workloads").json()}
        assert workloads["CBS-DB-01"]["data_classification"] == "Secret"
        assert workloads["CBS-DB-01"]["rpo_minutes"] == 0

        assert client.post("/api/v1/waves/plan").status_code == 200
        dxb = client.post("/api/v1/capacity/clusters", json=cluster("DXB-AHV-01", "ae")).json()
        auh = client.post("/api/v1/capacity/clusters", json=cluster("AUH-AHV-DR", "AE")).json()
        eu = client.post("/api/v1/capacity/clusters", json=cluster("FRA-AHV-01", "DE")).json()
        assert dxb["country_code"] == "AE"

        ok = client.post("/api/v1/controls/residency", json={"cluster_id": dxb["id"], "dr_cluster_id": auh["id"]}).json()
        assert ok["violations"] == 0 and ok["compliant"] == 3

        bad = client.post("/api/v1/controls/residency", json={"cluster_id": eu["id"]}).json()
        assert bad["violations"] == 2  # Secret + Confidential; Internal is unrestricted

        dr = client.post(
            "/api/v1/controls/dr-plan",
            json={"primary_cluster_id": dxb["id"], "dr_cluster_id": auh["id"], "site_rtt_ms": 2.5},
        ).json()
        assert dr["status"] == "Ready"
        assert "PP-SYNC-RPO0" in [p["name"] for p in dr["policies"]]

        offshore_dr = client.post(
            "/api/v1/controls/dr-plan",
            json={"primary_cluster_id": dxb["id"], "dr_cluster_id": eu["id"], "site_rtt_ms": 2.5},
        ).json()
        assert offshore_dr["status"] == "Blocked"

        calendar = client.post(
            "/api/v1/controls/change-calendar/schedule",
            json={
                "start_date": "2026-11-30",
                "periods": [{"start": "2026-12-01", "end": "2026-12-06", "kind": "blackout", "reason": "National Day + freeze"}],
            },
        ).json()
        assert calendar["scheduled"][0]["window_start_local"].startswith("2026-12-11T22:00")

        planned = {w["name"]: w for w in client.get("/api/v1/workloads").json()}
        wave = planned["CBS-DB-01"]["wave_number"]
        assert wave is not None
        blocked = client.post(
            f"/api/v1/approvals/waves/{wave}/request",
            json={"target_cluster_id": eu["id"], "requested_by": "ops", "change_ticket": "CHG-1"},
        )
        assert blocked.status_code == 409
        assert "data residency" in blocked.json()["detail"]["message"]

        allowed = client.post(
            f"/api/v1/approvals/waves/{wave}/request",
            json={"target_cluster_id": dxb["id"], "requested_by": "ops", "change_ticket": "CHG-1"},
        )
        assert allowed.status_code == 200, allowed.text
    finally:
        app.dependency_overrides.clear()
