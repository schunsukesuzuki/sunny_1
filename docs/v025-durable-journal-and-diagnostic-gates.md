# v0.25 — durable local approval journal, Dogwood denial tests and diagnostic reliability gate

## Motivation: what v0.24 actually demonstrated

The user's exported `claims_full_run_v024_5ea06547-9d3a-45f2-a5b9-a9aeaccdfd84.zip` showed:

- A real *native Dogwood* engine call with `ALLOW`, bounded replay of **one** saved approval, and successful controlled R1/HOLDOUT. The result is not proof of continuous authorization.
- Qwen3-Coder 30B and ODA-Fin-RL-8B each passed **0/2** fixed independent diagnostic benchmark cases, despite mean assisted rubric score `0.875`. R1 was the reviewed Domain Skill, **not** proof of LLM autonomous repair.
- Consequently, audit completion and synthetic R1 KPI success **must not** be labeled autonomous diagnostic reliability or production readiness.

## What changed

### 1. SQLite authorization journal (Python-side persistence)

- `backend/app/authorization_ledger.py` appends an `APPROVED` event for each saved approved `approval.json` and a `REVOKED` event for a withdrawn approval. Rows are locally append-only via SQLite triggers; verification walks the entire global hash chain, checks event-to-approval linkage and original approval-record SHA256, and rejects altered, duplicated or missing evidence.
- The journal is at `artifacts/authorization_ledger.sqlite3` and persists through the existing Docker host volume (`./artifacts:/app/artifacts`). It is **not put in the public audit ZIP**, because it can include other workflows and actor labels. The workflow audit ZIP includes a scoped `05_authorization_ledger.json` receipt and a separate `revocation.json` in the approval folder when revoked before export. Both are evidence, not signed certificates.
- Optional `AUTH_LEDGER_HMAC_KEY` makes the event chain keyed. Set `AUTH_LEDGER_REQUIRE_HMAC=1` to **fail closed** if no key is provided. The same key must be retained across restarts; rotation invalidates existing chain verification and requires a planned migration. Default unkeyed SHA256 is not tamper-proof against a DB administrator.
- `REVIEWER_API_TOKEN` + `REVIEWER_ID` optionally enforce a fixed local shared-token reviewer claim through the `X-Reviewer-Token` HTTP header. Both `/api/approve` and `/api/full-run/approve-and-continue` accept the header. `POST /api/approvals/{approval_id}/revoke` additionally records a non-reversible cancellation event (the original `approval.json` remains unchanged). Without credentials, UI actor labels are self-reported. A shared local token is **not** external identity verification or suitable for multi-user production.
- All production R1 access paths (standalone generation, standalone evaluation and full-run) require a **verified matching durable journal event** before Dogwood's actual `permit`/`forbid` verdict. A revocation yields a Dogwood `RevokeRevision` replay event and cannot become ALLOW. Missing journal, tamper, mismatched IDs, failed engine/timeout, bad policy hashes, stale approval, etc. fail closed. Offline `DOGWOOD_MODE=off` still skips native engine explicitly; revocation and ledger corruption are never bypassed.

**Important limit:** Dogwood itself still opens a temporary redb store and replays validated event evidence for **each request**. The journal is durable, but it is *not a continuously running Dogwood event store*. We avoid falsely calling it an always-on authorization service. Python enforces the source timestamp's 24h limit because replay events receive new engine timestamps. Neither scheme prevents revocation arriving *during* an already-running E2B job; no global locking/distributed gate is implemented. Revocation blocks future authorization, does not undo prior outputs or archived ZIPs.

**Upgrade note:** an existing v0.24 `approval.json` has no v0.25 SQLite journal event. It intentionally **fails closed** if re-used for R1. Obtain a new approval from the upgraded app; do not fabricate an event just to backfill it.

### 2. Rust denial fixtures

`backend/dogwood_gate/src/main.rs` keeps the known-good v0.24.1 Rust `&principal` and explicit `DurableError` to `io::Error` conversion. The native `cargo test --release` suite now includes:

- Unapproved generation: DENY
- Exact matching approval: ALLOW
- Proposal, workflow or approval ID mismatch: DENY
- Matching revocation: DENY; unrelated revocations cannot cancel the matching approval
- Revocation without approval: DENY
- Malformed identifier, unknown JSON fields and missing required fields: error (fail closed)

The native Rust suite is run during `docker compose build --no-cache api`; it cannot be claimed verified by the Python pytest fixture suite. **Rust/Docker are not installed in the packaging environment.** Python unit tests mock native output; the user must confirm actual Rust compilation and policy fixture behavior in Docker.

### 3. Independent diagnostic reliability gate (after step 08)

`backend/app/diagnostic_reliability.py` adds `diagnostic_reliability_gate.json` for the direct benchmark and `08_diagnostic_reliability_gate.json` for full-run:

- Prespecified conservative *synthetic screen*: **each** model must finish at least 2 independent fixed cases and 2 fresh blind cases with **100% RAW final rubric passes**. Failure/unavailable/blind-disabled -> `HOLD_HUMAN_ADJUDICATION`.
- Assisted evidence-ID binding is reported but cannot turn a raw model failure into PASS. Blind oracle outputs are not used in correction prompts.
- This gate reports *diagnostic generalization*, not the R1 technical KPI or the completion of the workflow. HOLD requires human investigation before claiming trusted autonomous diagnosis, but does not delete valid human-approved technical experimental results.
- Even `PASS_SYNTHETIC_SCREEN` does not prove real-world reliability, automated legal reasoning, customer needs or production authorization. The unconditional field `autonomous_diagnostic_reliability=false` prevents accidental scope inflation.
- Benchmark stage 08 still runs **after** step 06, so this gate is a **post-experiment audit and deployment HOLD**, not a predictive authorization prerequisite for the already human-approved synthetic R1 experiment. Full pre-execution generalization gating would require redesigning the step order.

### 4. Provenance and controls

Each full-run bundle includes its Dogwood policy/schema sources, Dogwood verdict, now a `05_authorization_ledger.json` receipt and diagnostic reliability report; `manifest.json` hashes every included raw file. The full SQLite DB and HMAC secrets are *never bundled*. The UI displays the two distinct gates and offers revoke and optional local reviewer token fields.

## Run locally

```bash
# Keep old .env secrets; only copy the example once.
cp .env.example .env
# Set E2B_API_KEY, models and DOGWOOD_MODE=enforce.
# Recommended for local evidence integrity:
# AUTH_LEDGER_HMAC_KEY=<long private randomly generated stable secret>
# AUTH_LEDGER_REQUIRE_HMAC=1
# Optional for single-reviewer local demo:
# REVIEWER_API_TOKEN=<another secret>
# REVIEWER_ID="Claims Product Owner (demo)"

docker compose build --no-cache api
docker compose up -d --force-recreate
# Run Python tests (native Dogwood is mocked by these tests)
# Run Python tests in a local dev virtual environment (tests are not copied into API image):
# cd backend && pip install -r requirements.txt -r requirements-dev.txt && python -m pytest -q
# Native Rust tests are executed in build stage of `api` Dockerfile.
```

To revoke a local approval (if using the optional token):

```bash
curl -X POST http://127.0.0.1:18000/api/approvals/APPROVAL_UUID/revoke \
  -H 'Content-Type: application/json' \
  -H 'X-Reviewer-Token: YOUR_LOCAL_REVIEWER_TOKEN' \
  -d '{"actor":"Claims Product Owner (demo)","rationale":"Withdraw approval for further R1 execution"}'
```

The UI has a corresponding revoke action under step 05. A subsequent GenerateR1 or EvaluateR1 request using the revoked approval must yield 403 (or 503 on error), with **no new E2B work**.

## Verification matrix

| Control | Python regression | Native Docker required |
| --- | --- | --- |
| Persist/reopen journal; append/revoke; altered snapshot; HMAC key mismatch | ✅ | No |
| No journal, tamper, expired timestamp, invalid IDs, native nonzero/timeout => HOLD | ✅ (subprocess mocked) | No |
| Rust native Dogwood permit/forbid + malformed Rust input | Test fixtures present | **Yes** |
| Frontend TypeScript/Vite build | Not run offline (npm cache lacked React types) | **Yes** |
| Raw vs assisted diagnostic generalization gate | ✅ | No |
| Real identity/production-level legal semantics | **Out of scope** | **Out of scope** |
