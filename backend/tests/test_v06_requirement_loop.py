"""v0.6: service-design gate, evidence assessment, audit lineage, holdout isolation."""
from __future__ import annotations

from fastapi.testclient import TestClient
from app import main
from app.models import (
    CustomerEvidence, RequirementRefinementProposal, RequirementsDraft,
)
from app.requirements_loop import assess_requirements, fallback_design
from app.sample import SAMPLE_PROJECT
from app.baseline import BASELINE_SOURCE
from app.optimal import OPTIMAL_SOURCE
from app.evaluator import canonical_json, sha256_string
from app.e2b_runner import RawCandidate

REQ = {
    "customer_problem": "講師の配分作業の効率化",
    "target_users": ["講師"],
    "value_hypothesis": "配分作業時間を削減できる",
    "must_have": ["時間上限を守る"],
    "acceptance_criteria": ["1週間の学習配分を生成する", "手動工数を削減する"],
    "unverified_assumptions": ["講師が使いたい"],
    "unanswered_questions": ["作業時間の現状は?"],
    "next_customer_validation": ["実際の講師に時間測定を依頼する"],
}


def evidence(eid, req_id="AC-02", provenance="real_customer", verdict="support", verified=True, source="interview-001"):
    return CustomerEvidence(
        evidence_id=eid, requirement_id=req_id, provenance=provenance,
        verdict=verdict, observation="事後に業務時間を測定した（入力者の申告）",
        source_reference=source, human_verified=verified, reviewer="reviewer",
    )


def test_requirement_evidence_not_inferred_from_synthetic_or_tech_pass():
    requirements = RequirementsDraft.model_validate(REQ)
    check = assess_requirements(requirements, [evidence("E1", provenance="synthetic")], True)
    assert check.implementation_validity == "PASS"
    assert check.requirement_validity == "UNVERIFIED"
    assert check.findings[1].status == "UNVERIFIED"
    assert "E1" in check.findings[1].excluded_evidence_ids


def test_preliminary_and_contradictory_customer_evidence():
    requirements = RequirementsDraft.model_validate(REQ)
    check = assess_requirements(requirements, [evidence("E1"), evidence("E2", verdict="contradict")], True)
    assert check.requirement_validity == "CONFLICTED"
    assert check.findings[1].status == "CONFLICTED"
    assert check.findings[0].status == "UNVERIFIED"
    # Even if all criteria have positive real-customer evidence, no final GO is automated.
    check = assess_requirements(requirements, [evidence("E1", req_id="AC-01"), evidence("E2")], True)
    assert check.requirement_validity == "SUPPORTED_PRELIMINARY"
    assert check.decision == "HUMAN_REVIEW_REQUIRED"


def fake_run(datasets, sources):
    out = {}
    for name, source in sources.items():
        out[name] = []
        for seed, dataset in datasets.items():
            namespace = {"__name__": "test_run"}
            exec(OPTIMAL_SOURCE if name == "generated" else source, namespace)
            result = namespace["solve"](dataset)
            out[name].append(RawCandidate(
                name=name, seed=seed, source_sha256=sha256_string(source),
                sandbox_id="mock-sandbox", output=result,
                output_sha256=sha256_string(canonical_json(result)), elapsed_seconds=0.2,
            ))
    return out


def test_design_run_refine_revision_lineage_and_holdout(monkeypatch, tmp_path):
    monkeypatch.setenv("E2B_API_KEY", "local-test-key")
    monkeypatch.setattr(main, "ARTIFACT_DIR", tmp_path)
    monkeypatch.setattr(main, "run_in_e2b", fake_run)
    client = TestClient(main.app)
    design = fallback_design(RequirementsDraft.model_validate(REQ))

    first = client.post("/api/run", json={
        "project": SAMPLE_PROJECT, "requirements": REQ,
        "service_design": design.model_dump(), "code": "import json\n" * 15,
        "customer_evidence": [evidence("EV-01").model_dump()],
    })
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["requirement_assessment"]["implementation_validity"] == "PASS"
    assert result["requirement_assessment"]["requirement_validity"] == "UNVERIFIED"
    assert result["requirements_revision"] == 0
    assert result["holdout_seeds"] == [10042, 10043]
    root = tmp_path / result["run_id"]
    for name in ("project.json", "service_design.json", "requirement_assessment.json",
                 "customer_evidence.json", "requirement_change_log.json"):
        assert (root / name).is_file(), name
    assert "Requirement Refinement" in (root / "report.md").read_text()
    assert "UNVERIFIED" in (root / "report.md").read_text()

    seen = {}
    async def fake_refine(project, req, service_design, development_summary, evidence_items, prior_run_id):
        seen["keys"] = sorted(development_summary)
        seen["summary"] = str(development_summary)
        return RequirementRefinementProposal(
            prior_run_id=prior_run_id, proposed_requirements=req,
            diagnosis=["要件の妥当性は未検証"], change_reasons=["顧客KPIを確認"],
            unresolved_evidence=["料金受容"], proposed_validation=["顧客実験"],
        )
    monkeypatch.setattr(main, "refine_requirements", fake_refine)
    proposal = client.post("/api/refine", json={"run_id": result["run_id"]})
    assert proposal.status_code == 200, proposal.text
    assert "holdout" not in seen["summary"].lower()
    assert "baseline" in seen["summary"]
    assert len(list(root.glob("proposal_*.json"))) == 1
    assert (root / "requirements.json").is_file()  # proposal never mutates it

    second = client.post("/api/run", json={
        "project": SAMPLE_PROJECT, "requirements": REQ,
        "service_design": design.model_dump(), "code": "import json\n" * 15,
        "parent_run_id": result["run_id"], "requirements_revision": 1,
    })
    assert second.status_code == 200, second.text
    after = second.json()
    assert after["holdout_seeds"] == [20042, 20043]
    assert after["parent_run_id"] == result["run_id"]
    assert after["requirements_revision"] == 1
    assert (tmp_path / after["run_id"] / "requirement_change_log.json").is_file()

    wrong = client.post("/api/run", json={
        "project": SAMPLE_PROJECT, "requirements": REQ,
        "service_design": design.model_dump(), "code": "import json\n" * 15,
        "parent_run_id": result["run_id"], "requirements_revision": 0,
    })
    assert wrong.status_code == 422
