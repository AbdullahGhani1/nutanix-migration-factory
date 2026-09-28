from __future__ import annotations

import re


ALLOWED_STATUS = {"Passed", "Partial", "Failed"}
ALLOWED_CHECK_STATUS = {"Passed", "Partial", "Failed", "NotRun"}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def normalize_validation_payload(payload) -> dict:
    status = payload.status.strip().title()
    if status not in ALLOWED_STATUS:
        raise ValueError("status must be Passed, Partial or Failed")

    prism = payload.prism_validation.strip().title().replace("Notrun", "NotRun")
    guest = payload.guest_validation.strip().title().replace("Notrun", "NotRun")
    if prism not in ALLOWED_CHECK_STATUS:
        raise ValueError("prism_validation must be Passed, Partial, Failed or NotRun")
    if guest not in ALLOWED_CHECK_STATUS:
        raise ValueError("guest_validation must be Passed, Partial, Failed or NotRun")

    if payload.hosts_passed + payload.hosts_failed > payload.hosts_total:
        raise ValueError("hosts_passed + hosts_failed cannot exceed hosts_total")

    artifact_sha256 = payload.artifact_sha256.strip().lower()
    if artifact_sha256 and not SHA256_RE.fullmatch(artifact_sha256):
        raise ValueError("artifact_sha256 must be a 64-character SHA-256 hex digest")

    if status == "Passed":
        if payload.hosts_failed:
            raise ValueError("Passed validation cannot contain failed hosts")
        if payload.hosts_total and payload.hosts_passed != payload.hosts_total:
            raise ValueError("Passed validation requires all recorded hosts to pass")
        if prism == "Failed" or guest == "Failed":
            raise ValueError("Passed validation cannot include a failed Prism or guest check")

    if status == "Failed" and not (
        payload.hosts_failed > 0 or prism == "Failed" or guest == "Failed"
    ):
        raise ValueError("Failed validation requires at least one failed technical check")

    return {
        "tool": payload.tool.strip() or "Ansible",
        "status": status,
        "actor": payload.actor.strip(),
        "hosts_total": payload.hosts_total,
        "hosts_passed": payload.hosts_passed,
        "hosts_failed": payload.hosts_failed,
        "prism_validation": prism,
        "guest_validation": guest,
        "artifact_sha256": artifact_sha256,
        "evidence_reference": payload.evidence_reference.strip(),
        "summary": payload.summary.strip(),
    }
