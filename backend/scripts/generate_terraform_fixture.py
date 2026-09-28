from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.terraform_export import build_terraform_pack


def main():
    workloads = [
        SimpleNamespace(
            id=1,
            name="ERP-APP-01",
            wave_number=1,
            cpu=4,
            memory_gb=8,
            storage_gb=120,
            target_network="AHV-PROD-APP",
            app_group="ERP",
            criticality="High",
        )
    ]
    clusters = [
        SimpleNamespace(
            id=1,
            name="AHV-PROD-A",
            prism_ext_id="00000000-0000-0000-0000-000000000001",
            enabled=True,
        )
    ]

    target = Path('/tmp/migration-factory-terraform')
    target.mkdir(parents=True, exist_ok=True)
    payload = build_terraform_pack(workloads, clusters)
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        zf.extractall(target)
    print(target)


if __name__ == '__main__':
    main()