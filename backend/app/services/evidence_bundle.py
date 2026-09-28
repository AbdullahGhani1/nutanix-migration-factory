from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_evidence_bundle(
    *,
    implementation_pdf: bytes,
    migration_plan_csv: bytes,
    executions_json: bytes,
    technical_validations_json: bytes | None = None,
    prism_environment_evidence_json: bytes | None = None,
    metadata: dict | None = None,
) -> bytes:
    """Package migration artifacts with a SHA-256 manifest.

    The manifest establishes integrity of the exported files at bundle creation
    time. It does not independently verify the truth of operator-entered data.
    """
    files = {
        "implementation-report.pdf": implementation_pdf,
        "migration-plan.csv": migration_plan_csv,
        "executions.json": executions_json,
    }
    if technical_validations_json is not None:
        files["technical-validations.json"] = technical_validations_json
    if prism_environment_evidence_json is not None:
        files["prism-environment-evidence.json"] = prism_environment_evidence_json

    manifest = {
        "schema": "nutanix-migration-factory-evidence-bundle/v3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provenance": (
            "Artifacts exported from Migration Factory. Prism environment snapshots are captured "
            "through the configured read-only connector; execution and technical validation "
            "records may contain operator-entered measurements and references."
        ),
        "metadata": metadata or {},
        "files": {
            name: {
                "sha256": sha256_bytes(content),
                "bytes": len(content),
            }
            for name, content in files.items()
        },
    }
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")

    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
        archive.writestr("manifest.json", manifest_bytes)

    return output.getvalue()
