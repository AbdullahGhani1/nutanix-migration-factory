from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.ansible_export import build_ansible_validation_pack


def main():
    workloads = [
        SimpleNamespace(id=1, name="ERP-APP-01", wave_number=1, os="Windows Server 2022", target_network="AHV-PROD-APP", criticality="High"),
        SimpleNamespace(id=2, name="API-01", wave_number=1, os="Ubuntu Linux", target_network="AHV-PROD-APP", criticality="Medium"),
    ]
    target = Path('/tmp/migration-factory-ansible')
    target.mkdir(parents=True, exist_ok=True)
    payload = build_ansible_validation_pack(workloads)
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        zf.extractall(target)
    print(target)


if __name__ == '__main__':
    main()