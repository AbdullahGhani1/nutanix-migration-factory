"""Data classification and data residency controls.

UAE enterprises commonly operate under in-country hosting obligations that come
from sector regulators and internal policy (for example UAE PDPL, the UAE
Information Assurance standards, DESC ISR for Dubai government entities,
ADHICS for Abu Dhabi healthcare and CBUAE requirements for licensed financial
institutions). Which obligation applies is a legal/compliance decision, so this
module does not encode any regulation. It enforces an explicit, configurable
policy: classification -> allowed hosting countries, with optional per-workload
overrides, and checks both the primary and the DR placement against it.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

CLASSIFICATIONS = ("Public", "Internal", "Confidential", "Secret")

CLASSIFICATION_ALIASES = {
    "open": "Public",
    "public": "Public",
    "internal": "Internal",
    "official": "Internal",
    "sensitive": "Confidential",
    "confidential": "Confidential",
    "restricted": "Secret",
    "secret": "Secret",
}

GCC_COUNTRIES = frozenset({"AE", "SA", "QA", "KW", "BH", "OM"})

# Conservative starting point, not legal advice: anything Confidential or above
# stays in the UAE. Organizations replace this with their approved policy.
DEFAULT_RESIDENCY_POLICY: dict[str, list[str] | None] = {
    "Public": None,
    "Internal": None,
    "Confidential": ["AE"],
    "Secret": ["AE"],
}


def load_policy(raw: str | None) -> dict[str, list[str] | None]:
    """Parse a JSON residency policy, falling back to the default when empty."""
    if not raw or not raw.strip():
        return dict(DEFAULT_RESIDENCY_POLICY)
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Residency policy must be a JSON object")
    policy: dict[str, list[str] | None] = dict(DEFAULT_RESIDENCY_POLICY)
    for key, value in data.items():
        countries = parse_countries(value)
        policy[normalize_classification(key)] = sorted(countries) if countries is not None else None
    return policy


def normalize_classification(value: str | None) -> str:
    key = (value or "").strip().lower()
    if not key:
        return "Internal"
    if key not in CLASSIFICATION_ALIASES:
        raise ValueError(f"Unknown data classification '{value}'; expected one of {', '.join(CLASSIFICATIONS)}")
    return CLASSIFICATION_ALIASES[key]


def parse_countries(value: str | list[str] | None) -> frozenset[str] | None:
    """Parse "AE", "AE,SA", "GCC" or "ANY" into a set of ISO country codes.

    None means unrestricted.
    """
    if value is None:
        return None
    tokens = value if isinstance(value, list) else value.replace(";", ",").split(",")
    countries: set[str] = set()
    for token in (t.strip().upper() for t in tokens):
        if not token:
            continue
        if token == "ANY":
            return None
        if token == "GCC":
            countries |= GCC_COUNTRIES
        elif len(token) == 2 and token.isalpha():
            countries.add(token)
        else:
            raise ValueError(f"Invalid country code '{token}'; use ISO 3166 alpha-2, GCC or ANY")
    return frozenset(countries) if countries else None


def allowed_countries(workload, policy: dict[str, list[str] | None] | None = None) -> frozenset[str] | None:
    override = (getattr(workload, "residency", "") or "").strip()
    if override:
        return parse_countries(override)
    classification = normalize_classification(getattr(workload, "data_classification", ""))
    rules = policy if policy is not None else DEFAULT_RESIDENCY_POLICY
    return parse_countries(rules.get(classification))


@dataclass(frozen=True)
class ResidencyResult:
    workload_id: int
    name: str
    classification: str
    allowed_countries: list[str] | None
    status: str
    violations: list[str]
    warnings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _placement_issue(role: str, cluster, allowed: frozenset[str]) -> tuple[str, str] | None:
    country = (getattr(cluster, "country_code", "") or "").strip().upper()
    if not country:
        return "unverified", f"{role} cluster '{cluster.name}' has no country_code; residency cannot be verified"
    if country not in allowed:
        return "violation", (
            f"{role} cluster '{cluster.name}' is in {country}; data is restricted to {', '.join(sorted(allowed))}"
        )
    return None


def evaluate_residency(workload, primary_cluster, dr_cluster=None, policy=None) -> ResidencyResult:
    classification = normalize_classification(getattr(workload, "data_classification", ""))
    allowed = allowed_countries(workload, policy)
    violations: list[str] = []
    warnings: list[str] = []
    unverified = False

    if allowed is not None:
        for role, cluster in (("Primary", primary_cluster), ("DR", dr_cluster)):
            if cluster is None:
                continue
            issue = _placement_issue(role, cluster, allowed)
            if issue is None:
                continue
            kind, message = issue
            if kind == "violation":
                violations.append(message)
            else:
                unverified = True
                warnings.append(message)

    if classification == "Secret":
        warnings.append("Secret data: confirm data-at-rest encryption and key-management evidence on the target cluster")
    if classification in {"Confidential", "Secret"} and dr_cluster is None:
        warnings.append("No DR cluster supplied; DR copy location is not verified")

    status = "Violation" if violations else "Unverified" if unverified else "Compliant"
    return ResidencyResult(
        workload_id=workload.id,
        name=workload.name,
        classification=classification,
        allowed_countries=sorted(allowed) if allowed is not None else None,
        status=status,
        violations=violations,
        warnings=warnings,
    )


def summarize_residency(results: list[ResidencyResult]) -> dict[str, int]:
    return {
        "total": len(results),
        "compliant": sum(r.status == "Compliant" for r in results),
        "unverified": sum(r.status == "Unverified" for r in results),
        "violations": sum(r.status == "Violation" for r in results),
    }
