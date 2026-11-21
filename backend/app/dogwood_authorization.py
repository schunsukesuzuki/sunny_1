"""v0.24 Dogwood Local Engine gate: verified local approval -> temporal policy.

The Rust program uses *the actual* dogwood-local-engine crate. It replays only
server-persisted approval evidence into an isolated temporary store; this is not
an authenticated identity service or an always-on multi-agent event monitor.
No engine available / unexpected output / timeout / policy DENY => no R1 work.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

VERSION = "DOGWOOD-APPROVAL-GATE-v0.24.0"
DEFAULT_BINARY = "/usr/local/bin/claims-dogwood-gate"
POLICY_PATH = Path(__file__).resolve().parent.parent / "dogwood_gate/policy/policy.dw"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "dogwood_gate/policy/schema.cedarschema"
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def configured_mode() -> str:
    return os.getenv("DOGWOOD_MODE", "enforce").strip().lower()


def _sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _record(decision: str, reason: str, workflow_id: str, expected_proposal_id: str,
            expected_approval_id: str, *, elapsed_ms: int = 0, engine: str | None = None,
            history_events: int = 0, mode: str | None = None) -> dict[str, Any]:
    return {
        "version": VERSION, "status": decision, "decision": decision, "reason": reason[:500],
        "workflow_id": workflow_id, "proposal_id": expected_proposal_id,
        "approval_id": expected_approval_id, "configured_mode": mode or configured_mode(),
        "engine": engine, "history_events": history_events, "elapsed_ms": elapsed_ms,
        "policy_sha256": _sha(POLICY_PATH), "schema_sha256": _sha(SCHEMA_PATH),
        "scope": "EPHEMERAL_REPLAY_OF_LOCAL_APPROVAL; NO_AUTHENTICATED_IDENTITY_OR_CONTINUOUS_HISTORY",
        "production_authorization": False,
    }


def check(workflow_id: str, expected_proposal_id: str, expected_approval_id: str,
          approval_record: dict | None, *, revoked: bool = False) -> dict[str, Any]:
    """Checks local lineage and makes a *real Rust Dogwood authorization call*.

    This is synchronous and safe to run from an async FastAPI handler because
    the CLI is bounded and returns immediately for a tiny policy. Not a claim
    that the caller is an authenticated human or that approval evidence is signed.
    """
    start = time.monotonic()
    mode = configured_mode()
    ids = (workflow_id, expected_proposal_id, expected_approval_id)
    def base(status: str, reason: str, **kwargs: Any) -> dict:
        return _record(status, reason, *ids,
                       elapsed_ms=round((time.monotonic()-start)*1000), mode=mode, **kwargs)
    if mode not in ("enforce", "off"):
        return base("ERROR", "Invalid DOGWOOD_MODE; valid values are enforce or off")
    if not all(isinstance(x, str) and _IDENTIFIER.fullmatch(x) for x in ids):
        return base("DENY", "Missing or malformed workflow/proposal/approval ID")
    if not isinstance(approval_record, dict):
        return base("DENY", "No persisted approval.json")
    if (approval_record.get("approval_id") != expected_approval_id
            or approval_record.get("proposal_id") != expected_proposal_id):
        return base("DENY", "Approval record ID/proposal ID differs from active workflow")
    if approval_record.get("decision") != "approved":
        return base("DENY", "Approval not approved or explicitly revoked")
    # Authoritative evidence is the server's persisted timestamp, not a fresh
    # replay timestamp. Dogwood assigns *now* to the replay event, so check the
    # 24h policy horizon independently before constructing the event history.
    stamp = approval_record.get("timestamp_utc")
    try:
        ts = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            raise ValueError("timezone missing")
        age = datetime.now(timezone.utc) - ts.astimezone(timezone.utc)
        if not (-timedelta(minutes=2) <= age <= timedelta(hours=24)):
            return base("DENY", "Approval outside accepted 24h window")
    except (AttributeError, TypeError, ValueError, OverflowError):
        return base("DENY", "Invalid or missing approval timestamp")
    if mode == "off":
        return base("NOT_ENFORCED", "Explicit test/development bypass. NO Dogwood authorization executed")

    binary = os.getenv("DOGWOOD_BINARY", DEFAULT_BINARY)
    if not Path(binary).is_file():
        return base("ERROR", "Dogwood binary missing; refusing to generate R1")
    if _sha(POLICY_PATH) is None or _sha(SCHEMA_PATH) is None:
        return base("ERROR", "Auditable Dogwood policy or schema file unavailable")
    # Do not trust the LLM or browser to supply past events. The event is built
    # exclusively from already-validated approval.json plus workflow identifiers.
    request = {
        "approved_event": {"workflow_id": workflow_id, "proposal_id": expected_proposal_id,
                           "approval_id": expected_approval_id},
        "revoked_event": {"workflow_id": workflow_id, "proposal_id": expected_proposal_id,
                          "approval_id": expected_approval_id} if revoked else None,
        "generate_request": {"workflow_id": workflow_id, "proposal_id": expected_proposal_id,
                             "approval_id": expected_approval_id},
    }
    try:
        completed = subprocess.run([binary], input=json.dumps(request), text=True,
                                   capture_output=True, check=False, timeout=8)
        if completed.returncode != 0:
            return base("ERROR", f"Dogwood exited {completed.returncode}: {completed.stderr[:200]}")
        result = json.loads(completed.stdout)
        if (not isinstance(result, dict) or result.get("engine") != "dogwood-local-engine"
                or result.get("execution_mode") != "EPHEMERAL_REPLAY_NOT_CONTINUOUS_AUTHORIZATION"
                or result.get("policy_id") != "r1_after_explicit_human_approval+r1_revoked"
                or result.get("decision") not in ("ALLOW", "DENY")
                or result.get("history_events") != (2 if revoked else 1)
                or result.get("policy_sha256") != _sha(POLICY_PATH)
                or result.get("schema_sha256") != _sha(SCHEMA_PATH)):
            return base("ERROR", "Unexpected Dogwood response schema; rejecting")
        return base(result["decision"], "Dogwood temporal policy verdict",
                    engine=result["engine"], history_events=result["history_events"])
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError) as exc:
        return base("ERROR", f"Dogwood invocation failed: {type(exc).__name__}: {str(exc)[:140]}")


def admitted(record: dict) -> bool:
    return record.get("status") == "ALLOW" or (
        configured_mode() == "off" and record.get("status") == "NOT_ENFORCED")


def boundary_gate(record: dict) -> dict:
    """Wrap a Dogwood verdict in the existing EAIR-style boundary contract."""
    safe = admitted(record)
    issues = [] if safe else [{"code": "DOGWOOD_AUTHORIZATION_DENIED",
        "evidence_paths": ["approvals/<id>/approval.json", "05_dogwood_authorization.json"],
        "detail": record["reason"],
        "suggested_repair": "Recheck approval and Dogwood policy/service, then obtain a new explicit human approval; no fallback"}]
    return {"version": VERSION, "boundary": "05_to_06_dogwood",
            "status": "PASS" if safe else "HOLD", "violations": issues,
            "checks_performed": ["dogwood_temporal_approval"], "authorization": record,
            "semantic_validity": "NOT_PROVEN", "production_authorization": False}
