"""v0.25 durable *local* approval/revocation journal (SQLite).

An append-only, hash-chained evidence trail, not an external identity provider,
not a persistent Dogwood engine, and not a production permission authority.
Database is inside ARTIFACT_DIR to survive Docker container recreation. Every
R1 authorization re-verifies the entire journal and matching approval snapshot;
any missing, tampered or revoked event fails closed. Optional server-side HMAC
requires a stable, secret AUTH_LEDGER_HMAC_KEY. A plain SHA256 chain by itself
is NOT tamper-proof against an attacker who can rewrite the DB.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "AUTH-LEDGER-v0.25.0"
GENESIS = "0" * 64
EVENTS = frozenset({"APPROVED", "REVOKED"})


class LedgerError(RuntimeError):
    pass


def canonical(x: dict) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def record_hash(rec: dict) -> str:
    return hashlib.sha256(canonical(rec).encode("utf-8")).hexdigest()


def _sign(previous: str, body: str) -> str:
    message = (previous + "\n" + body).encode("utf-8")
    secret = os.getenv("AUTH_LEDGER_HMAC_KEY", "")
    if secret:
        return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    if os.getenv("AUTH_LEDGER_REQUIRE_HMAC", "0") == "1":
        raise LedgerError("AUTH_LEDGER_REQUIRE_HMAC is enabled but no HMAC key is configured")
    return hashlib.sha256(message).hexdigest()


def _conn(root: Path) -> sqlite3.Connection:
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / "authorization_ledger.sqlite3", timeout=10)
    try:
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("""CREATE TABLE IF NOT EXISTS events (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            approval_id TEXT NOT NULL,
            body TEXT NOT NULL,
            prev_hash TEXT NOT NULL,
            entry_hash TEXT NOT NULL
        )""")
        db.execute("""CREATE TRIGGER IF NOT EXISTS journal_no_update
            BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'immutable approval journal'); END""")
        db.execute("""CREATE TRIGGER IF NOT EXISTS journal_no_delete
            BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'immutable approval journal'); END""")
        return db
    except Exception:
        db.close()
        raise


def _verify(db: sqlite3.Connection) -> list[dict[str, Any]]:
    previous = GENESIS
    entries = []
    for seq, kind, aid, body, prev_hash, entry_hash in db.execute(
        "SELECT seq,event_type,approval_id,body,prev_hash,entry_hash FROM events ORDER BY seq"
    ):
        try:
            decoded = json.loads(body)
        except (ValueError, TypeError) as exc:
            raise LedgerError("Invalid event JSON") from exc
        if (not isinstance(decoded, dict) or kind not in EVENTS or decoded.get("event_type") != kind
                or decoded.get("approval_id") != aid or prev_hash != previous
                or canonical(decoded) != body or not hmac.compare_digest(_sign(previous, body), entry_hash)):
            raise LedgerError("Hash chain, event identity or signature mismatch")
        previous = entry_hash
        entries.append({"seq": seq, "event": decoded, "prev_hash": prev_hash, "entry_hash": entry_hash})
    return entries


def _append(root: Path, event: dict) -> dict:
    if event.get("event_type") not in EVENTS:
        raise LedgerError("Unsupported journal event")
    db = _conn(root)
    try:
        db.execute("BEGIN IMMEDIATE")
        entries = _verify(db)  # detect modification *before* append
        previous = entries[-1]["entry_hash"] if entries else GENESIS
        body = canonical(event)
        entry_hash = _sign(previous, body)
        aid = event["approval_id"]
        relevant = [r["event"] for r in entries if r["event"]["approval_id"] == aid]
        if event["event_type"] == "APPROVED":
            if relevant:
                raise LedgerError("Approval ID already has journal events")
        else:
            if not any(r["event_type"] == "APPROVED" for r in relevant):
                raise LedgerError("Revocation needs an existing approval")
            if any(r["event_type"] == "REVOKED" for r in relevant):
                raise LedgerError("Already revoked")
        cur = db.execute(
            "INSERT INTO events(event_type,approval_id,body,prev_hash,entry_hash) VALUES(?,?,?,?,?)",
            (event["event_type"], aid, body, previous, entry_hash))
        db.commit()
        return {"seq": cur.lastrowid, "entry_hash": entry_hash}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def approve(root: Path, rec: dict) -> dict:
    if rec.get("decision") != "approved":
        # Rejected proposals have no permit event; rejection remains in decision.json.
        return {"status": "NO_PERMIT_EVENT"}
    event = {
        "version": VERSION, "event_type": "APPROVED",
        "approval_id": rec["approval_id"], "proposal_id": rec["proposal_id"],
        "parent_run_id": rec["parent_run_id"],
        "actor_claim": rec["actor"], "actor_authentication": rec.get("actor_authentication", "SELF_REPORTED"),
        "record_sha256": record_hash(rec), "occurred_at_utc": rec["timestamp_utc"],
    }
    return _append(root, event)


def revoke(root: Path, approval_rec: dict, *, actor: str, rationale: str,
           actor_authentication: str = "SELF_REPORTED") -> dict:
    if approval_rec.get("decision") != "approved":
        raise LedgerError("Only an approved record can be revoked")
    entry = {
        "version": VERSION, "event_type": "REVOKED",
        "approval_id": approval_rec["approval_id"], "proposal_id": approval_rec["proposal_id"],
        "parent_run_id": approval_rec["parent_run_id"],
        "record_sha256": record_hash(approval_rec),
        "actor_claim": actor, "actor_authentication": actor_authentication,
        "reason": rationale, "occurred_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return _append(root, entry)


def audit(root: Path, rec: dict) -> dict[str, Any]:
    """Verify full chain and original approval byte-equivalent canonical content."""
    db = _conn(root)
    try:
        entries = _verify(db)
    finally:
        db.close()
    approval_id = rec.get("approval_id")
    matching = [x for x in entries if x["event"].get("approval_id") == approval_id]
    approved = [x for x in matching if x["event"]["event_type"] == "APPROVED"]
    revoked = [x for x in matching if x["event"]["event_type"] == "REVOKED"]
    if len(approved) != 1 or len(revoked) > 1:
        raise LedgerError("Missing or duplicate approval/revocation evidence")
    approval = approved[0]["event"]
    if (approval.get("proposal_id") != rec.get("proposal_id")
            or approval.get("parent_run_id") != rec.get("parent_run_id")
            or approval.get("record_sha256") != record_hash(rec)
            or approval.get("actor_claim") != rec.get("actor")
            or approval.get("occurred_at_utc") != rec.get("timestamp_utc")):
        raise LedgerError("Persisted approval differs from journal-approved snapshot")
    if revoked and revoked[0]["event"].get("record_sha256") != record_hash(rec):
        raise LedgerError("Revocation references a different approval snapshot")
    return {"version": VERSION, "approval_id": approval_id, "verified": True,
            "journal_total_entries": len(entries), "approval_seq": approved[0]["seq"],
            "approval_event_hash": approved[0]["entry_hash"],
            "revoked": bool(revoked), "revocation_seq": revoked[0]["seq"] if revoked else None,
            "revocation_event_hash": revoked[0]["entry_hash"] if revoked else None,
            "last_chain_hash": entries[-1]["entry_hash"] if entries else GENESIS,
            "approval_record_sha256": record_hash(rec),
            "actor_authentication": approval.get("actor_authentication", "SELF_REPORTED"),
            "integrity": "HMAC_SHA256" if os.getenv("AUTH_LEDGER_HMAC_KEY") else "UNKEYED_SHA256_NOT_TAMPER_PROOF",
            "identity_verification": "LOCAL_SHARED_TOKEN_ONLY" if approval.get("actor_authentication") == "LOCAL_SHARED_TOKEN" else "NONE",
            "dogwood_history_persistent": False,
            "production_authorization": False,
            "note": "SQLite persists local approval evidence; Dogwood replays validated events per decision. No identity provider or continuous Dogwood history."}
