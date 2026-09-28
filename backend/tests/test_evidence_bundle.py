import hashlib
import io
import json
import zipfile

from app.services.evidence_bundle import build_evidence_bundle


def test_evidence_bundle_contains_hash_manifest():
    pdf = b"%PDF-demo"
    csv = b"Wave,VM\n1,APP-01\n"
    executions = b'[{"id":1,"status":"Succeeded"}]'

    bundle = build_evidence_bundle(
        implementation_pdf=pdf,
        migration_plan_csv=csv,
        executions_json=executions,
        metadata={"workloads": 1},
    )

    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        assert set(archive.namelist()) == {
            "implementation-report.pdf",
            "migration-plan.csv",
            "executions.json",
            "manifest.json",
        }
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["schema"] == "nutanix-migration-factory-evidence-bundle/v1"
        assert manifest["metadata"]["workloads"] == 1
        assert manifest["files"]["migration-plan.csv"]["sha256"] == hashlib.sha256(csv).hexdigest()
        assert archive.read("implementation-report.pdf") == pdf
