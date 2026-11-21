import json

def load_input():
    with open('/home/user/input.json', 'r') as f:
        return json.load(f)

def save_output(assignments, unassigned_case_ids):
    output = {
        "assignments": assignments,
        "unassigned_case_ids": unassigned_case_ids
    }
    with open('/home/user/output.json', 'w') as f:
        json.dump(output, f, indent=2)

def is_skill_match(case, reviewer):
    return case["required_skill"] in reviewer["skills"]

def can_assign(case, reviewer, day):
    if not is_skill_match(case, reviewer):
        return False
    
    # Check if reviewer has capacity for this day
    if day >= len(reviewer["daily_capacity_hours"]):
        return False
    
    capacity = reviewer["daily_capacity_hours"][day]
    if case["duration_hours"] > capacity:
        return False
    
    return True

def assign_case_to_reviewer(case, reviewers, day, assignments, reviewer_usage):
    # Find all qualified reviewers for this case
    qualified_reviewers = [r for r in reviewers if is_skill_match(case, r)]
    
    # Sort by deadline risk (earlier deadlines first) and then by skill scarcity
    qualified_reviewers.sort(key=lambda r: (
        -sum(1 for a in assignments if a["reviewer_id"] == r["reviewer_id"]),  # Prefer reviewers with fewer cases
        sum(1 for a in assignments if a["reviewer_id"] == r["reviewer_id"])   # Tie-breaker
    ))
    
    # Try to assign to the best reviewer
    for reviewer in qualified_reviewers:
        if can_assign(case, reviewer, day):
            # Check if reviewer has capacity
            if day < len(reviewer["daily_capacity_hours"]):
                capacity = reviewer["daily_capacity_hours"][day]
                if case["duration_hours"] <= capacity:
                    assignments.append({
                        "case_id": case["case_id"],
                        "reviewer_id": reviewer["reviewer_id"],
                        "day": day,
                        "hours": case["duration_hours"]
                    })
                    # Update reviewer usage
                    if reviewer["reviewer_id"] not in reviewer_usage:
                        reviewer_usage[reviewer["reviewer_id"]] = [0] * len(reviewer["daily_capacity_hours"])
                    reviewer_usage[reviewer["reviewer_id"]][day] += case["duration_hours"]
                    return True
    return False

def main():
    data = load_input()
    days = data["days"]
    cases = data["cases"]
    reviewers = data["reviewers"]
    
    # Sort cases by deadline day (earlier deadlines first)
    cases.sort(key=lambda c: c["deadline_day"])
    
    assignments = []
    unassigned_case_ids = []
    reviewer_usage = {}
    
    for case in cases:
        assigned = False
        # Try to assign to any day within the deadline
        for day in range(min(case["deadline_day"] + 1, days)):
            if assign_case_to_reviewer(case, reviewers, day, assignments, reviewer_usage):
                assigned = True
                break
        
        if not assigned:
            unassigned_case_ids.append(case["case_id"])
    
    save_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    main()