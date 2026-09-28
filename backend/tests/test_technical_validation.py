from types import SimpleNamespace

import pytest

from app.services.technical_validation import normalize_validation_payload


def payload(**overrides):
    values = dict(
        tool="Ansible",
        status="Passed",
        actor="migration.engineer",
        hosts_total=3,
        hosts_passed=3,
        hosts_failed=0,
        prism_validation="Passed",
        guest_validation="Passed",
        artifact_sha256="a" * 64,
        evidence_reference="CHG-42/validation-01",
        summary="All technical validation checks passed.",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_passed_validation_normalizes():
    result = normalize_validation_payload(payload())
    assert result["status"] == "Passed"
    assert result["artifact_sha256"] == "a" * 64


def test_passed_validation_rejects_failed_hosts():
    with pytest.raises(ValueError):
        normalize_validation_payload(payload(hosts_passed=2, hosts_failed=1))


def test_failed_validation_requires_failure_evidence():
    with pytest.raises(ValueError):
        normalize_validation_payload(
            payload(
                status="Failed",
                hosts_total=0,
                hosts_passed=0,
                hosts_failed=0,
                prism_validation="NotRun",
                guest_validation="NotRun",
            )
        )


def test_invalid_digest_rejected():
    with pytest.raises(ValueError):
        normalize_validation_payload(payload(artifact_sha256="abc"))
