from types import SimpleNamespace

from app.services.network_mapping import NetworkRule, apply_network_mapping, resolve_target_network


def test_exact_and_wildcard_mapping():
    rules = [
        NetworkRule(source="VLAN120", target="AHV-PROD-APP"),
        NetworkRule(source="DEV-*", target="AHV-DEV"),
    ]
    assert resolve_target_network("VLAN120", rules) == "AHV-PROD-APP"
    assert resolve_target_network("DEV-WEB", rules) == "AHV-DEV"
    assert resolve_target_network("UNKNOWN", rules) is None


def test_apply_mapping_counts():
    workloads = [
        SimpleNamespace(source_network="VLAN120", target_network=""),
        SimpleNamespace(source_network="VLAN999", target_network=""),
    ]
    stats = apply_network_mapping(workloads, [NetworkRule("VLAN120", "AHV-PROD")])
    assert stats == {"mapped": 1, "unmapped": 1}
    assert workloads[0].target_network == "AHV-PROD"
