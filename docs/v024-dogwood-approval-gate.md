> v0.24.1 build hotfix: fixed Rust `EventBuilder::principal` argument type and `DurableError` propagation. A successful native compile/test has not been established by the authoring environment.

# v0.24 — Dogwood Temporal Approval Gate (bounded, real local engine)

## 1. Why this is not another AI agent

We take the **Dogwood policy language and the genuine Rust `dogwood-local-engine` crate** from the AWS-related open-source project, NOT a Python imitation. An LLM may draft R1; the independent Dogwood runtime decides whether GenerateR1 is allowed. We preserve v0.23's separate Python boundary checks and evaluator because temporal authorization does **not** determine whether a customer's requirement, solver, or economic justification is correct.

References:
- https://github.com/dogwood-policy/dogwood-local-engine
- https://dogwood-policy.github.io/dogwood/guide/00-introduction.html
- https://docs.rs/dogwood-local-engine/latest/dogwood_local_engine/
- https://aws.amazon.com/blogs/opensource/introducing-the-dogwood-local-engine-temporal-governance-for-agent-actions/

This is **not Amazon Bedrock AgentCore** or a managed service and does not require AWS credentials. The Dogwood crates are Apache-2.0. Native compilation requires Rust toolchain & crates.io access in the developer's Docker environment.

## 2. Architecture

```
Saved approval.json (server generated, timestamped)
        │  Python 05→06 lineage / authorization precheck
        ├── refusal if no approved decision / wrong IDs / age >24h
        │
        ▼
Rust claims-dogwood-gate (compiled Dogwood 1.1)
        │  one-shot native DurableTemporalEngine (temporary redb store)
        │  ApproveRevision::response -> GenerateR1::request
        │  permit only for same workflow_id, proposal_id and approval_id
        │  later matching RevokeRevision::response -> forbid
        │
        ├── ALLOW ──> existing GenerateR1 / EvaluateR1 (rechecks independently)
        └── DENY / ERROR / TIMEOUT ──> 06 SKIPPED, 08g HOLD, PARTIAL ZIP

Other boundaries (00b→01, 06→08b/08f/09) remain Python.
```

The Rust program compiles the policy from `backend/dogwood_gate/policy/policy.dw` and the schema from `.../schema.cedarschema`. It returns an actual `Outcome::Decision(verdict)` from the Dogwood Local Engine. The API cross-checks the exact SHA256 of the source policy/schema embedded in the compiled Rust binary. The decision and corresponding source files are saved in the audit ZIP.

### Important distinction from a continuous policy service

Every authorization call opens a **fresh temporary durable Dogwood store**, then replays the server's previously persisted approval into the engine, then submits a GenerateR1 request. This is an intentionally low-operations, replay-oriented use of the *real* local engine. It does NOT observe an append-only stream of every event across restarts or multiple workflows. The 24h horizon is checked against the original persisted `timestamp_utc` by Python **before** the replay because the engine timestamps replay events at the current time. Replays cannot establish the security of the source record.

A production deployment would instead authenticate principals and reviewers, record approvals/revocations in an authoritative event ledger, use a durable long-running engine/gateway with controls on policy updates, and manage parallel action execution and time-of-check/time-of-use races. All those remain out of scope.

## 3. Running on macOS + Docker

```bash
cp .env.example .env    # only if you have no existing .env; do not overwrite secrets
# Edit .env: E2B_API_KEY, OLLAMA models, DOGWOOD_MODE=enforce
# Cargo needs crates.io access; first build may be longer than the earlier Python-only image.
docker compose build --no-cache api
docker compose up -d --force-recreate
# Check native policy and replay fixtures (native Rust tests are run during image build)
docker compose exec -T api sh -c 'test -x /usr/local/bin/claims-dogwood-gate'
```

Native Rust tests cover: missing approval, matching approval, wrong proposal, wrong workflow, wrong approval, and approval followed by revocation. If Cargo compilation or these tests fail, the API image build fails rather than silently falling back to a Python policy. **The authoring environment lacked Cargo/Docker and external network access, so actual Rust image compilation and policy execution have not been verified here.**

The `api` service environment defaults to `DOGWOOD_MODE=enforce`. On a running app, the new `Dogwood 時系列認可` panel shows the verdict and `05_dogwood_authorization.json` in the ZIP. `NOT_ENFORCED` means you explicitly disabled Dogwood for test/dev work; it does not mean ALLOW from the Rust engine.

To run Python-only tests (no Rust binary):
```bash
cd backend
PYTHONPATH=. pytest -q
```

`backend/tests/conftest.py` deliberately sets `DOGWOOD_MODE=off` for this **test process only**, except v0.24 contract tests which override it and mock native subprocess replies. These tests do not substitute for the Docker native compile/test stage.

## 4. Verified and unverified properties

| Question | v0.24 approach |
| --- | --- |
| Did a real Dogwood crate produce ALLOW/DENY? | Intended in the Rust CLI (`DurableTemporalEngine::submit`); Docker native build/runtime **requires user-side verification** |
| Is R1 refused on Dogwood DENY/error/absence? | Python tests verify 06 interception and PARTIAL ZIP with stubbed subprocess |
| Does the stored event belong to the active proposal? | Python ID precheck + Dogwood temporal field correlation |
| Is original approval time within 24h? | Python datetime check; timestamps are **not** inherited by replay events |
| Does a revoked event win? | Dogwood `forbid` fixture; no persisted revocation workflow/UI yet |
| Is the principal authenticated? | **No** — actor labels in local JSON are not identity proofs |
| Does it determine the true customer requirement or legal cause? | **No** |
| Is there an immutable audit chain? | **No** — SHA256 for local bytes, not signed attestations |
| Is ROI or TCO reduction proven? | **No** |

## 5. What to measure next

Compare the v0.23 Python-only handoff with v0.24 enforced Dogwood using the same saved approval fixtures: seeded unauthorized cases detected, allowed normal cases, false blocks, elapsed authorization time and audit overhead. Separate these from LLM diagnosis accuracy, R1 synthetic KPI, and production/customer validity. Do not claim results for the real Rust engine until its compiled `ALLOW/DENY` fixtures pass.
