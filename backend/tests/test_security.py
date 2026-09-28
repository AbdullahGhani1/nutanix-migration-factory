from app.security import hash_api_key, required_role, resolve_role, role_allowed


def test_key_hash_and_role_resolution():
    hashes = {
        "viewer": hash_api_key("viewer-secret"),
        "operator": hash_api_key("operator-secret"),
        "approver": hash_api_key("approver-secret"),
        "admin": hash_api_key("admin-secret"),
    }
    assert resolve_role("operator-secret", hashes) == "operator"
    assert resolve_role("wrong", hashes) is None


def test_required_roles_are_separated():
    assert required_role("GET", "/api/v1/workloads") == "viewer"
    assert required_role("POST", "/api/v1/optimizer/waves") == "operator"
    assert required_role("POST", "/api/v1/approvals/3/decision") == "approver"


def test_approval_and_operator_authority_are_not_accidentally_conflated():
    assert role_allowed("operator", "operator") is True
    assert role_allowed("operator", "approver") is False
    assert role_allowed("approver", "approver") is True
    assert role_allowed("approver", "operator") is False
    assert role_allowed("admin", "operator") is True
    assert role_allowed("admin", "approver") is True
