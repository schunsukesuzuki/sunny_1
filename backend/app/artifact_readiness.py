"""Fail-closed checks for partly written R1 experiment artifacts (v0.22).

A started marker is a trace of an attempted execution, NOT an experiment result.
This module is intentionally read-only and never turns an error into a PASS.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

RECORD_FIELDS = ("experiment_id", "r0_run_id", "proposal_id", "approval_id")
VALID_RECORD_STATES = ("READY", "NO_SELECTED_R1")


def inspect_experiment(artifact_root: Path, experiment_id: str | None) -> dict:
    """Return the diagnostic and trustworthy record, if present.

    The returned record is for application logic; use public_view() for audit files.
    No exception from a missing, malformed, or invalid artifact should propagate.
    """
    result = {"experiment_id": experiment_id, "status": "NOT_LINKED",
              "record": None, "reason": "No experiment ID was linked to this workflow",
              "available_files": []}
    if not experiment_id:
        return result
    try:
        if not isinstance(experiment_id, str) or str(uuid.UUID(experiment_id)) != experiment_id:
            raise ValueError("Invalid UUID")
    except (ValueError, TypeError, AttributeError):
        return {**result, "status": "INVALID_ID", "reason": "Experiment ID is not a canonical UUID"}
    folder = artifact_root / "experiments" / experiment_id
    if not folder.is_dir():
        return {**result, "status": "MISSING_FOLDER", "reason": "Experiment folder does not exist"}
    result["available_files"] = sorted(p.name for p in folder.iterdir() if p.is_file() and not p.is_symlink())[:150]
    record_path = folder / "experiment.json"
    if not record_path.is_file():
        status = "FAILED_WITHOUT_RESULT" if (folder / "error.json").is_file() else "STARTED_ONLY"
        return {**result, "status": status,
                "reason": "No completed experiment.json; started marker is not a result"}
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return {**result, "status": "CORRUPT_RESULT", "reason": f"Cannot decode experiment.json ({type(exc).__name__})"}
    if not isinstance(record, dict):
        return {**result, "status": "CORRUPT_RESULT", "reason": "Experiment result must be a JSON object"}
    result["record"] = record
    if record.get("status") in {"FAILED", "ERROR"} or (folder / "error.json").is_file():
        return {**result, "status": "FAILED", "reason": "Experiment records an upstream evaluation failure"}
    missing = [key for key in RECORD_FIELDS if not record.get(key)]
    if missing:
        return {**result, "status": "INCOMPLETE_RESULT", "reason": "Missing required experiment fields: " + ", ".join(missing)}
    if record["experiment_id"] != experiment_id:
        return {**result, "status": "ID_MISMATCH", "reason": "Experiment ID mismatches its containing folder"}
    if not record.get("selected_code_sha256"):
        return {**result, "status": "NO_SELECTED_R1", "reason": "No DEV-eligible R1 source selected"}
    code_path = folder / "selected_r1.py"
    if not code_path.is_file():
        return {**result, "status": "SELECTED_CODE_MISSING", "reason": "Selected source hash is set but selected_r1.py is missing"}
    try:
        actual = hashlib.sha256(code_path.read_bytes()).hexdigest()
    except OSError as exc:
        return {**result, "status": "SELECTED_CODE_UNREADABLE", "reason": type(exc).__name__}
    if actual != record["selected_code_sha256"]:
        return {**result, "status": "SELECTED_CODE_HASH_MISMATCH", "reason": "Selected source does not match recorded SHA256"}
    if not record.get("holdout_executed"):
        return {**result, "status": "INCOMPLETE_RESULT", "reason": "Selected R1 has not completed the declared HOLDOUT"}
    return {**result, "status": "READY", "reason": "Experiment result and selected code are complete and integrity-checked"}


def public_view(inspection: dict) -> dict:
    """A small immutable audit description; never duplicate arbitrary R1 payloads."""
    return {key: inspection.get(key) for key in ("experiment_id", "status", "reason", "available_files")}


def record_is_complete(inspection: dict) -> bool:
    return inspection.get("status") in VALID_RECORD_STATES


def ready_for_policy(inspection: dict) -> bool:
    return inspection.get("status") == "READY"
