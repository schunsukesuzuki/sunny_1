"""Deterministic evaluator and decision logic; not sent to E2B or to the LLM."""
from __future__ import annotations

import hashlib
import json
import math
import statistics
from .models import BusinessInputs, BusinessScenario, CandidateResult, SeedEvidence


def canonical_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_string(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_plans(output: object) -> str | None:
    """Canonicalize allocations without depending on JSON/key/order formatting."""
    if not isinstance(output, dict) or not isinstance(output.get("plans"), list):
        return None
    try:
        items = [(p["student_id"], sorted((a["subject"], a["hours"])
                    for a in p["allocations"])) for p in output["plans"]]
        return canonical_json(sorted(items))
    except (KeyError, TypeError, ValueError):
        return None


def evaluate_output(dataset: dict, output: object) -> tuple[bool, float | None, float, list[str], list[dict]]:
    """Scores a synthetic proxy; never proves teaching or learning effectiveness."""
    violations: list[str] = []
    if not isinstance(output, dict) or not isinstance(output.get("plans"), list):
        return False, None, 0.0, ["output.plans は配列である必要があります。"], []
    plans = output["plans"]
    by_id = {s["student_id"]: s for s in dataset["students"]}
    seen_ids: set[str] = set()
    scores = []
    valid = 0
    for plan in plans:
        if not isinstance(plan, dict) or not isinstance(plan.get("student_id"), str):
            violations.append("生徒IDが不正です。")
            continue
        sid = plan["student_id"]
        if sid in seen_ids:
            violations.append(f"{sid}: 重複した生徒ID")
            continue
        seen_ids.add(sid)
        student = by_id.get(sid)
        if not student:
            violations.append(f"{sid}: 未知の生徒ID")
            continue
        allocations = plan.get("allocations")
        if not isinstance(allocations, list):
            violations.append(f"{sid}: allocations は配列である必要があります。")
            continue
        actual: dict[str, int] = {}
        bad = False
        subjects = {s["name"]: s for s in student["subjects"]}
        for item in allocations:
            if not isinstance(item, dict):
                violations.append(f"{sid}: 配分の要素が不正")
                bad = True
                continue
            sub, hours = item.get("subject"), item.get("hours")
            if not isinstance(sub, str) or sub not in subjects or sub in actual:
                violations.append(f"{sid}: 不正または重複した科目 {str(sub)[:50]}")
                bad = True
                continue
            if type(hours) is not int or hours < 0 or hours > subjects[sub]["max_hours"]:
                violations.append(f"{sid}/{sub}: 時間数・上限の違反")
                bad = True
                continue
            actual[sub] = hours
        if set(actual) != set(subjects):
            violations.append(f"{sid}: すべての科目を出力してください。")
            bad = True
        if sum(actual.values()) != student["available_hours"]:
            violations.append(f"{sid}: 利用可能時間と配分時間が一致しません。")
            bad = True
        if bad:
            continue
        valid += 1
        weight = sum(s["gap"] * s["priority"] for s in student["subjects"])
        utility = sum(s["gap"] * s["priority"] * (1.0 - math.exp(-actual[s["name"]] / 2.5))
                      for s in student["subjects"]) / weight
        scores.append(utility)
    missing = set(by_id) - seen_ids
    if missing:
        violations.append(f"未出力の生徒: {', '.join(sorted(missing))}")
    passed = not violations and valid == len(by_id)
    coverage = valid / len(by_id)
    return passed, (round(statistics.mean(scores), 7) if scores else None), round(coverage, 4), violations[:40], plans[:3]


def summarize_candidate(name: str, algorithm: str, evidence: list[SeedEvidence],
                        source_hash: str) -> CandidateResult:
    valid = [e for e in evidence if e.status == "completed" and e.hard_constraint_pass and e.score is not None]
    all_pass = len(valid) == len(evidence) and bool(evidence)
    # Never silently average only successful seeds and present that as overall performance.
    scores = [e.score for e in valid] if all_pass else []
    return CandidateResult(
        name=name, algorithm=algorithm,
        status="completed" if all_pass else "failed",
        hard_constraint_pass=all_pass,
        score=round(statistics.mean(scores), 7) if scores else None,
        score_std=round(statistics.pstdev(scores), 7) if scores else None,
        min_score=round(min(scores), 7) if scores else None,
        coverage_ratio=round(statistics.mean(e.coverage_ratio for e in evidence), 4),
        elapsed_seconds=round(statistics.mean(e.elapsed_seconds for e in evidence), 3),
        violations=[f"seed {e.seed}: {msg}" for e in evidence for msg in e.violations][:40],
        stdout="\n".join(e.stdout for e in evidence if e.stdout)[-3000:],
        stderr="\n".join(e.stderr for e in evidence if e.stderr)[-3000:],
        source_sha256=source_hash,
        sample_plans=evidence[0].sample_plans if evidence else [],
        passed_seeds=len(valid), total_seeds=len(evidence), per_seed=evidence,
    )


def business_scenario(b: BusinessInputs) -> BusinessScenario:
    monthly_revenue = b.monthly_price_yen * b.paying_schools
    return BusinessScenario(
        monthly_revenue_yen=monthly_revenue,
        monthly_operating_cost_yen=b.monthly_operating_cost_yen,
        monthly_contribution_yen=monthly_revenue - b.monthly_operating_cost_yen,
        hypothetical_customer_value_yen=b.hours_saved_per_school * b.teacher_hourly_cost_yen,
        break_even_schools=math.ceil(b.monthly_operating_cost_yen / b.monthly_price_yen)
        if b.monthly_price_yen else None,
    )


def decide_gates(baseline: CandidateResult, optimal: CandidateResult,
                 generated: CandidateResult, *, optimal_floor: float,
                 improvement_floor: float) -> tuple[str, str, list[str]]:
    if not baseline.hard_constraint_pass or not optimal.hard_constraint_pass:
        return "REVIEW（評価系の異常）", "REVIEW（比較基準無効）", [
            "固定ルールまたは厳密DPの実行に失敗したため、比較判定を停止しました。"
        ]
    if not generated.hard_constraint_pass or generated.score is None:
        return "NO-GO（生成候補の制約違反）", "NO-GO（採用不可）", [
            f"生成候補は全seedの制約を満たせませんでした（合格 {generated.passed_seeds}/{generated.total_seeds}）。",
            "エラーの内容を調査して再実験する必要があります。",
        ]
    if optimal.score is None or baseline.score is None or optimal.score <= 0 or baseline.score <= 0:
        return "REVIEW（採点異常）", "REVIEW（比較不能）", ["代理効用の値が不正です。"]
    ratio_opt = generated.score / optimal.score
    ratio_base = generated.score / baseline.score
    reasons = [
        f"生成候補/厳密DPの平均代理効用比: {ratio_opt:.4f}（要求 ≥ {optimal_floor:.4f}）。",
        f"生成候補/固定ルールの平均代理効用比: {ratio_base:.4f}（改善採用閾値 ≥ {improvement_floor:.4f}）。",
    ]
    if ratio_opt < optimal_floor - 1e-8:
        return "PASS（制約充足）", "HOLD（最適解との品質差）", reasons + [
            "動作可能でも、厳密DPとの差が許容閾値を超えています。"
        ]
    if ratio_base < improvement_floor - 1e-8:
        return "PASS（制約充足）", "HOLD（追加価値未確認）", reasons + [
            "動作可能ですが、静的Greedyに対する十分な改善を確認できませんでした。"
        ]
    return "PASS（制約充足）", "CONDITIONAL GO（追加実証へ）", reasons + [
        "合成データ上の技術比較のみ通過。学習効果・価格受容・工数削減は未検証です。"
    ]


def build_plan_comparisons(
    datasets: dict[int, dict],
    baseline_raw: dict[int, object],
    optimal_raw: dict[int, object],
    generated_raw: dict[int, object],
    *, max_students: int = 3,
) -> list:
    """Customer-facing examples from held-out E2B outputs; never fabricate missing allocations."""
    from .models import PlanComparison, PlanSubjectComparison

    def lookup(raw, student_id: str) -> dict[str, int] | None:
        result = getattr(raw, "output", None)
        if not isinstance(result, dict) or not isinstance(result.get("plans"), list):
            return None
        matches = [p for p in result["plans"]
                   if isinstance(p, dict) and p.get("student_id") == student_id]
        if len(matches) != 1 or not isinstance(matches[0].get("allocations"), list):
            return None
        entries = matches[0]["allocations"]
        names = [e.get("subject") for e in entries if isinstance(e, dict)]
        if len(names) != len(entries) or len(names) != len(set(names)):
            return None
        return {e["subject"]: e.get("hours") for e in entries}

    if not datasets:
        return []
    seed = next(iter(datasets))
    dataset = datasets[seed]
    rows = []
    for student in dataset["students"][:max_students]:
        sid = student["student_id"]
        b = lookup(baseline_raw.get(seed), sid)
        o = lookup(optimal_raw.get(seed), sid)
        g = lookup(generated_raw.get(seed), sid)
        valid_g = (
            g is not None
            and set(g) == {s["name"] for s in student["subjects"]}
            and all(type(g[s["name"]]) is int and 0 <= g[s["name"]] <= s["max_hours"]
                    for s in student["subjects"])
            and sum(g.values()) == student["available_hours"]
        )
        rows.append(PlanComparison(
            seed=seed, student_id=sid, available_hours=student["available_hours"],
            generated_valid=valid_g,
            subjects=[PlanSubjectComparison(
                subject=s["name"], gap=s["gap"], priority=s["priority"],
                max_hours=s["max_hours"],
                baseline_hours=b.get(s["name"]) if b else None,
                optimal_hours=o.get(s["name"]) if o else None,
                generated_hours=g.get(s["name"]) if valid_g else None,
            ) for s in student["subjects"]],
        ))
    return rows
