"""Claims Operations Planner: independent, deterministic synthetic insurance-domain evaluator.

All claims are an incoming backlog snapshot at the start of a four-day horizon.
One claim occupies one qualified reviewer on one day, in integer-hour blocks.
All figures and customer comments are synthetic; these are NOT claim decisions.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict
from copy import deepcopy

DAYS = 4
SKILLS = ("motor", "property", "liability")
CONTRACT_R0 = {
    "id": "REQ-QUEUE-001", "version": "CLAIMS-R0-FIFO-v1",
    "rule": "Process cases in ascending arrival_order (FIFO), selecting earliest feasible qualified reviewer-day",
    "target": "Implement FIFO exactly; do not guarantee fewer deadline breaches",
    "fixed": ["reviewer eligibility", "duration", "daily hours", "no overtime", "human claims decisions"],
}
CONTRACT_R1 = {
    "id": "REQ-QUEUE-001", "version": "CLAIMS-R1-SLA-v1",
    "rule": "Prioritize deadline risk and scarce qualified reviewers rather than arrival order",
    "target": "Reduce missed deadlines without increasing planned or actual reviewer hours",
    "fixed": ["reviewer eligibility", "duration", "daily hours", "no overtime", "human claims decisions"],
}
SERVICE_R0 = {
    "actors": ["Claims Operations Manager", "Claims Reviewer"],
    "use_cases": ["Upload claims backlog", "Build FIFO work schedule", "Human reviews assignments"],
    "entities": ["Claim", "Reviewer", "DailyCapacity", "Assignment", "Deadline"],
    "data_contract": "input.json contains days, cases[], reviewers[]; output.json contains assignments[], unassigned_case_ids[]",
    "hard_constraints": ["one assignment maximum per claim", "qualified reviewer", "no hours beyond daily capacity", "duration unchanged", "nonnegative integer day"],
    "acceptance": ["R0 FIFO matching reference", "no hard constraint violations"],
    "out_of_scope": ["claim payment decisions", "fraud scoring", "medical/health personal records"],
}
SERVICE_R1 = {
    **SERVICE_R0,
    "use_cases": ["Assess deadline exposure", "Schedule skilled reviewers by due date", "Escalate unassigned/late cases to manager"],
    "acceptance": ["independent R1 validity", "missed deadline count vs R0", "no growth in actual reviewer-hours", "human approval of policy"],
    "source": "predeclared_experiment_specification_not_llm_generated",
}
SIMULATED_EVIDENCE = {
    "evidence_id": "SIM-SLA-001", "requirement_id": "REQ-QUEUE-001",
    "provenance": "synthetic", "verdict": "contradict", "human_verified": False,
    "source_reference": "fixtures/claims_fifo_deadline_counterexample_v1",
    "observation": "架空のClaims Operations Manager: FIFOでは期限の長い高額案件が先に処理され、後着の短納期案件が期限超過する。総稼働時間を増やさず期限超過件数を減らしたい。",
}


def canonical(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(obj: object) -> str:
    raw = obj if isinstance(obj, str) else canonical(obj)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def make_dataset(seed: int) -> dict:
    """Synthetic, deterministic, diverse durations/deadlines/costs/skills.

    Strictly snapshots cases available at day 0, not production arrival-time modeling.
    """
    r = random.Random(seed)
    reviewers = [
        {"reviewer_id": "R-A", "skills": ["motor", "property"], "daily_capacity_hours": [5, 5, 5, 5]},
        {"reviewer_id": "R-B", "skills": ["motor"], "daily_capacity_hours": [5, 5, 5, 5]},
        {"reviewer_id": "R-C", "skills": ["liability", "property"], "daily_capacity_hours": [5, 5, 5, 5]},
    ]
    # Large, nonurgent claims arrive early. Urgent cases later in intake order.
    # FIFO is valid under R0, but typically poor for deadline adherence.
    specifications = [
        ("motor", 3, 3), ("property", 3, 3), ("liability", 3, 3),
        ("motor", 2, 3), ("property", 2, 2), ("liability", 2, 3),
        ("motor", 1, 0), ("property", 1, 0), ("liability", 1, 0),
        ("motor", 2, 0), ("property", 2, 1), ("liability", 1, 1),
        ("motor", 1, 1), ("property", 2, 2), ("liability", 2, 2),
        ("motor", 1, 0), ("property", 1, 1), ("liability", 1, 0),
    ]
    cases = []
    for i, (skill, hours, due) in enumerate(specifications):
        # Vary operational cases across seeds, not only display-only amounts.
        hours = max(1, min(3, hours + r.choice((-1, 0, 0, 1))))
        if due in (0, 1) and r.random() < 0.18:
            due = min(3, due + 1)
        cases.append({
            "case_id": f"C{i+1:03d}", "arrival_order": i + 1,
            "required_skill": skill, "duration_hours": hours,
            "deadline_day": due,
            "amount_eur": (500 + r.randrange(100, 28000) // 100 * 100),
            "business_priority": r.randint(1, 5),
        })
    return {"schema_version": "claims-0.8", "seed": seed, "days": DAYS, "cases": cases,
            "reviewers": reviewers, "scenario": "synthetic_backlog_snapshot", "currency": "EUR"}


def allocate(dataset: dict, *, policy: str) -> dict:
    """Independent deterministic references: FIFO and EDD/skill-aware (not an oracle)."""
    cases = list(dataset["cases"])
    reviewers = dataset["reviewers"]
    skills = {r["reviewer_id"]: set(r["skills"]) for r in reviewers}
    remaining = {(r["reviewer_id"], day): r["daily_capacity_hours"][day]
                 for r in reviewers for day in range(dataset["days"])}
    if policy == "fifo":
        cases.sort(key=lambda c: c["arrival_order"])
    elif policy == "deadline":
        # Qualification scarcity as second criterion: preserve scarce specialist capacity.
        cases.sort(key=lambda c: (c["deadline_day"], sum(c["required_skill"] in k for k in skills.values()),
                                  -c["duration_hours"], c["arrival_order"]))
    else:
        raise ValueError("Unknown reference scheduling policy")
    assignments, unassigned = [], []
    for case in cases:
        feasible = []
        for day in range(dataset["days"]):
            for rev in reviewers:
                reviewer = rev["reviewer_id"]
                if case["required_skill"] in skills[reviewer] and remaining[(reviewer, day)] >= case["duration_hours"]:
                    flexibility = len(skills[reviewer]); free = remaining[(reviewer, day)]
                    feasible.append((day, flexibility, free, reviewer))
        if not feasible:
            unassigned.append(case["case_id"])
            continue
        day, _, _, reviewer = min(feasible)
        remaining[(reviewer, day)] -= case["duration_hours"]
        assignments.append({"case_id": case["case_id"], "reviewer_id": reviewer,
                            "day": day, "hours": case["duration_hours"]})
    return {"assignments": assignments, "unassigned_case_ids": unassigned}


def validate(dataset: dict, output: object, *, policy: str = "r1") -> dict:
    """The evaluator never executes/model-trusts generated scorer code."""
    errors = []
    if not isinstance(output, dict) or not isinstance(output.get("assignments"), list) or not isinstance(output.get("unassigned_case_ids"), list):
        return {"valid": False, "violations": ["Expected assignments[] and unassigned_case_ids[]"],
                "missed_deadlines": None, "completed": None, "assigned_hours": None, "on_time": None,
                "total_cases": len(dataset["cases"]), "planned_capacity_hours": sum(sum(r["daily_capacity_hours"]) for r in dataset["reviewers"])}
    expected = {c["case_id"]: c for c in dataset["cases"]}
    reviewers = {r["reviewer_id"]: r for r in dataset["reviewers"]}
    allocations = defaultdict(int)
    seen = set(); valid_assignments = {}
    for row in output["assignments"]:
        if not isinstance(row, dict):
            errors.append("Invalid assignment object"); continue
        cid = row.get("case_id"); reviewer = row.get("reviewer_id"); day = row.get("day"); hours = row.get("hours")
        if not isinstance(cid, str) or cid not in expected or cid in seen:
            errors.append(f"Unknown/duplicate claim: {str(cid)[:40]}"); continue
        seen.add(cid)
        if not isinstance(reviewer, str) or reviewer not in reviewers or type(day) is not int or not 0 <= day < dataset["days"] or type(hours) is not int or hours != expected[cid]["duration_hours"]:
            errors.append(f"Invalid reviewer/day/hours for {cid}"); continue
        if expected[cid]["required_skill"] not in reviewers[reviewer]["skills"]:
            errors.append(f"Reviewer lacks required skill for {cid}")
        allocations[(reviewer, day)] += hours
        valid_assignments[cid] = (reviewer, day, hours)
    missing_ids = set(); unassigned = output["unassigned_case_ids"]
    for cid in unassigned:
        if not isinstance(cid, str) or cid not in expected or cid in seen or cid in missing_ids:
            errors.append(f"Invalid unassigned claim: {str(cid)[:40]}")
        else:
            missing_ids.add(cid)
    if seen | missing_ids != set(expected):
        errors.append("Each case must be assigned exactly once or explicitly unassigned")
    for (rev, day), hours in allocations.items():
        if hours > reviewers[rev]["daily_capacity_hours"][day]:
            errors.append(f"Capacity exceeded: {rev}/day{day}: {hours}")
    if policy == "r0":
        # Strict old requirement: adherence to deterministic FIFO reference (not just some valid schedule).
        if canonical(output) != canonical(allocate(dataset, policy="fifo")):
            errors.append("R0 does not implement the specified deterministic FIFO schedule")
    missed = sum(1 for cid, c in expected.items() if cid not in valid_assignments or valid_assignments[cid][1] > c["deadline_day"])
    assigned_hours = sum(v[2] for v in valid_assignments.values())
    return {"valid": not errors, "violations": errors[:25], "missed_deadlines": missed,
            "on_time": len(expected) - missed, "completed": len(valid_assignments),
            "assigned_hours": assigned_hours, "total_cases": len(expected),
            "planned_capacity_hours": sum(sum(r["daily_capacity_hours"]) for r in dataset["reviewers"]),
            "unassigned_cases": len(missing_ids),
            "deadline_hit_rate": round((len(expected)-missed)/len(expected), 5) if expected else None}


def common_score(m: dict) -> float | None:
    if not m.get("valid"): return None
    # Fixed BEFORE generation; observable KPI rather than model-selected proxy.
    return round(m["on_time"] / m["total_cases"], 6)


def get_reference_sources() -> tuple[str, str]:
    """Standalone sandbox programs kept independent of application imports."""
    import inspect
    parts = [
        "from collections import defaultdict\nimport json\n",
        f"def canonical(obj):\n    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))\n",
        inspect.getsource(allocate),
    ]
    # Reuse exact reference algorithm source to make R0 fidelity deterministic.
    # Return FIFO and deadline-first wrappers separately for E2B.
    base = "\n".join(parts)
    def wrap(policy: str) -> str:
        return base + f"\nif __name__ == '__main__':\n    with open('/home/user/input.json', encoding='utf-8') as f: dataset=json.load(f)\n    output=allocate(dataset, policy='{policy}')\n    with open('/home/user/output.json','w',encoding='utf-8') as f: json.dump(output,f,ensure_ascii=False)\n"
    return wrap("fifo"), wrap("deadline")
