from types import SimpleNamespace

import pytest

from app.services.residency import (
    allowed_countries,
    evaluate_residency,
    load_policy,
    normalize_classification,
    parse_countries,
    summarize_residency,
)


def vm(**overrides):
    values = dict(id=1, name="CRM-DB-01", data_classification="Confidential", residency="")
    values.update(overrides)
    return SimpleNamespace(**values)


def cluster(name="DXB-AHV-01", country_code="AE"):
    return SimpleNamespace(name=name, country_code=country_code)


def test_classification_aliases_and_rejects_unknown():
    assert normalize_classification("restricted") == "Secret"
    assert normalize_classification("") == "Internal"
    with pytest.raises(ValueError):
        normalize_classification("TopSecret")


def test_gcc_and_any_country_tokens():
    assert "SA" in parse_countries("GCC")
    assert parse_countries("AE,ANY") is None
    with pytest.raises(ValueError):
        parse_countries("UAE")


def test_confidential_in_uae_is_compliant():
    result = evaluate_residency(vm(), cluster(), cluster("AUH-AHV-DR", "AE"))
    assert result.status == "Compliant"
    assert result.allowed_countries == ["AE"]


def test_dr_outside_uae_is_violation():
    result = evaluate_residency(vm(), cluster(), cluster("EU-DR", "DE"))
    assert result.status == "Violation"
    assert result.violations[0].startswith("DR cluster 'EU-DR' is in DE")


def test_cluster_without_country_is_unverified_for_restricted_data():
    result = evaluate_residency(vm(), cluster(country_code=""))
    assert result.status == "Unverified"


def test_internal_data_is_unrestricted_by_default():
    result = evaluate_residency(vm(data_classification="Internal"), cluster(country_code="DE"))
    assert result.status == "Compliant"
    assert result.allowed_countries is None


def test_workload_override_beats_policy():
    workload = vm(data_classification="Public", residency="AE")
    assert allowed_countries(workload) == frozenset({"AE"})
    assert evaluate_residency(workload, cluster(country_code="SA")).status == "Violation"


def test_custom_policy_and_summary():
    policy = load_policy('{"Confidential": "GCC"}')
    assert "SA" in policy["Confidential"]
    results = [
        evaluate_residency(vm(), cluster(country_code="SA"), policy=policy),
        evaluate_residency(vm(id=2, name="X"), cluster(country_code="GB"), policy=policy),
    ]
    assert summarize_residency(results) == {"total": 2, "compliant": 1, "unverified": 0, "violations": 1}
