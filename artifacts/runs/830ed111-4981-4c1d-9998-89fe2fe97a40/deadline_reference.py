from collections import defaultdict
import json

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

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

if __name__ == '__main__':
    with open('/home/user/input.json', encoding='utf-8') as f: dataset=json.load(f)
    output=allocate(dataset, policy='deadline')
    with open('/home/user/output.json','w',encoding='utf-8') as f: json.dump(output,f,ensure_ascii=False)
