//! Real Dogwood Local Engine; bounded replay from an independently durable local journal.
//! The journal lives in Python/SQLite; this Rust process itself remains ephemeral.
//! Every invocation replays server-validated approval evidence into an isolated, temporary
//! durable Dogwood store. The Python API retains the source of truth and audit trail.
//! See docs/v024-dogwood-approval-gate.md for trust boundaries and limitations.
use std::io::{self, Read};
use dogwood_language::{Event, EventBuilder, Value};
use dogwood_local_engine::{DurableTemporalEngine, Outcome};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

const POLICY: &str = include_str!("../policy/policy.dw");
const SCHEMA: &str = include_str!("../policy/schema.cedarschema");

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Identity {
    workflow_id: String,
    proposal_id: String,
    approval_id: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    // The caller obtains this exclusively from the persisted approval.json and its own
    // current workflow state, never from untrusted generated model text.
    approved_event: Option<Identity>,
    revoked_event: Option<Identity>,
    generate_request: Identity,
}

#[derive(Debug, Serialize)]
struct ResultRecord {
    engine: &'static str,
    execution_mode: &'static str,
    policy_id: &'static str,
    decision: &'static str,
    history_events: usize,
    provenance_scope: &'static str,
    policy_sha256: String,
    schema_sha256: String,
}

fn valid_identifier(value: &str) -> bool {
    !value.is_empty() && value.len() <= 128 && value.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'-' || c == b'_')
}
fn validate_id(id: &Identity) -> Result<(), Box<dyn std::error::Error>> {
    if [&id.workflow_id, &id.proposal_id, &id.approval_id].iter().all(|x| valid_identifier(x)) {
        Ok(())
    } else {
        Err("Identifiers must be nonempty ASCII alphanumerics/underscore/hyphen, <=128 bytes".into())
    }
}
fn event(action: &str, kind: &str, id: &Identity) -> EventBuilder {
    let principal = format!("Claims::Workflow::\"{}\"", id.workflow_id);
    Event::builder(action, kind)
        .principal(&principal)
        .resource("Claims::Service::\"claims-planner\"")
        .field("input", "workflow_id", Value::String(id.workflow_id.clone()))
        .field("input", "proposal_id", Value::String(id.proposal_id.clone()))
        .field("input", "approval_id", Value::String(id.approval_id.clone()))
        .request_context("input", "workflow_id", Value::String(id.workflow_id.clone()))
        .request_context("input", "proposal_id", Value::String(id.proposal_id.clone()))
        .request_context("input", "approval_id", Value::String(id.approval_id.clone()))
}

fn decide(req: Request) -> Result<ResultRecord, Box<dyn std::error::Error>> {
    validate_id(&req.generate_request)?;
    if let Some(ref id) = req.approved_event { validate_id(id)?; }
    if let Some(ref id) = req.revoked_event { validate_id(id)?; }
    // Each request uses a fresh store so the outcome does not depend on whether the
    // process was restarted or the caller retried. The engine genuinely executes
    // Dogwood's temporal authorization rules; it does NOT retain an ongoing history.
    let dir = tempfile::tempdir()?;
    let path = dir.path().join("dogwood.redb");
    let mut engine = DurableTemporalEngine::open(&path, 0)
        .map_err(|e| io::Error::other(format!("Dogwood store open failed: {e:?}")))?;
    engine.install(POLICY, SCHEMA, None, None)
        .map_err(|e| io::Error::other(format!("Dogwood policy installation failed: {e:?}")))?;
    let mut history = 0;
    if let Some(ref id) = req.approved_event {
        let outcome = engine.submit(event("Claims::Action::ApproveRevision", "response", id))
            .map_err(|e| io::Error::other(format!("Dogwood approve event failed: {e:?}")))?;
        if !matches!(outcome.outcome, Outcome::Recorded) {
            return Err("Approval response must be a recorded history event".into());
        }
        history += 1;
    }
    if let Some(ref id) = req.revoked_event {
        let outcome = engine.submit(event("Claims::Action::RevokeRevision", "response", id))
            .map_err(|e| io::Error::other(format!("Dogwood revoke event failed: {e:?}")))?;
        if !matches!(outcome.outcome, Outcome::Recorded) {
            return Err("Revocation response must be a recorded history event".into());
        }
        history += 1;
    }
    let decision = engine.submit(event("Claims::Action::GenerateR1", "request", &req.generate_request))
        .map_err(|e| io::Error::other(format!("Dogwood GenerateR1 request failed: {e:?}")))?;
    let allowed = match decision.outcome {
        Outcome::Decision(verdict) => {
            let errors: Vec<_> = verdict.diagnostics().errors().collect();
            if !errors.is_empty() {
                return Err(format!("Dogwood evaluation diagnostics were nonempty: {errors:?}").into());
            }
            verdict.allowed()
        }
        Outcome::Recorded => return Err("GenerateR1 did not produce a verdict".into()),
    };
    Ok(ResultRecord {
        engine: "dogwood-local-engine",
        execution_mode: "EPHEMERAL_REPLAY_NOT_CONTINUOUS_AUTHORIZATION",
        policy_id: "r1_after_explicit_human_approval+r1_revoked",
        decision: if allowed { "ALLOW" } else { "DENY" },
        history_events: history,
        provenance_scope: "SERVER_PERSISTED_APPROVAL_NOT_AUTHENTICATED_HUMAN_IDENTITY",
        policy_sha256: format!("{:x}", Sha256::digest(POLICY.as_bytes())),
        schema_sha256: format!("{:x}", Sha256::digest(SCHEMA.as_bytes())),
    })
}

fn main() {
    let result = (|| -> Result<(), Box<dyn std::error::Error>> {
        let mut body = String::new();
        io::stdin().take(32_768).read_to_string(&mut body)?;
        let request: Request = serde_json::from_str(&body)?;
        let decision = decide(request)?;
        println!("{}", serde_json::to_string(&decision)?);
        Ok(())
    })();
    if let Err(error) = result {
        eprintln!("Dogwood policy error: {error}");
        std::process::exit(2);  // Python refuses execution on any error.
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn ident(w: &str, p: &str, a: &str) -> Identity {
        Identity { workflow_id: w.into(), proposal_id: p.into(), approval_id: a.into() }
    }
    #[test]
    fn authorization_fixtures() {
        let good = ident("workflow1", "proposal1", "approval1");
        let variants = vec![
            (None, None, good.clone(), false),
            (Some(good.clone()), None, good.clone(), true),
            (Some(good.clone()), None, ident("workflow1", "other", "approval1"), false),
            (Some(good.clone()), None, ident("other", "proposal1", "approval1"), false),
            (Some(good.clone()), None, ident("workflow1", "proposal1", "other"), false),
            (Some(good.clone()), Some(good.clone()), good.clone(), false),
            (Some(good.clone()), Some(ident("workflow1", "other", "approval1")), good.clone(), true),
            (Some(good.clone()), Some(ident("other", "proposal1", "approval1")), good.clone(), true),
            (None, Some(good.clone()), good.clone(), false),
        ];
        for (approved_event, revoked_event, generate_request, expected) in variants {
            let output = decide(Request { approved_event, revoked_event, generate_request }).unwrap();
            assert_eq!(output.decision == "ALLOW", expected);
        }
    }
    #[test]
    fn invalid_identifiers_fail_closed() {
        let long = "a".repeat(129);
        for bad in ["", "a/b", "a:b", "å", " spaced", "a.b", long.as_str()] {
            assert!(!valid_identifier(bad));
        }
        let req = Request { approved_event: Some(ident("workflow1", "proposal1", "approval1")),
            revoked_event: None, generate_request: ident("workflow1", "proposal1", "bad/actor") };
        assert!(decide(req).is_err());
    }

    #[test]
    fn malformed_json_and_unexpected_fields_rejected() {
        assert!(serde_json::from_str::<Request>(r#"{"generate_request":{"workflow_id":"a"}}"#).is_err());
        assert!(serde_json::from_str::<Request>(r#"{"approved_event":null,"revoked_event":null,"generate_request":{"workflow_id":"w","proposal_id":"p","approval_id":"a","permit":true}}"#).is_err());
    }

}
