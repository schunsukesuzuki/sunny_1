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
    # Check if reviewer has capacity for this day
    if day >= len(reviewer["daily_capacity_hours"]):
        return False
    
    daily_capacity = reviewer["daily_capacity_hours"][day]
    
    # Check if case duration fits within daily capacity
    if case["duration_hours"] > daily_capacity:
        return False
    
    return True

def assign_case_to_reviewer(case, reviewer, day):
    hours = case["duration_hours"]
    assignment = {
        "case_id": case["case_id"],
        "reviewer_id": reviewer["reviewer_id"],
        "day": day,
        "hours": hours
    }
    return assignment

def find_best_assignment(case, reviewers, days):
    best_assignment = None
    best_day = None
    
    # Sort reviewers by skill match and then by deadline priority
    eligible_reviewers = []
    for reviewer in reviewers:
        if is_skill_match(case, reviewer):
            eligible_reviewers.append(reviewer)
    
    # Sort by deadline priority (earlier deadlines first)
    eligible_reviewers.sort(key=lambda r: case["deadline_day"])
    
    # Try to assign to each eligible reviewer
    for reviewer in eligible_reviewers:
        # Check if reviewer has capacity for any day
        for day in range(min(days, len(reviewer["daily_capacity_hours"]))):
            if can_assign(case, reviewer, day):
                if best_assignment is None or day < best_day:
                    best_assignment = assign_case_to_reviewer(case, reviewer, day)
                    best_day = day
    
    return best_assignment

def main():
    data = load_input()
    days = data["days"]
    cases = data["cases"]
    reviewers = data["reviewers"]
    
    assignments = []
    unassigned_case_ids = []
    
    # Sort cases by deadline (earlier deadlines first)
    cases.sort(key=lambda c: c["deadline_day"])
    
    for case in cases:
        assignment = find_best_assignment(case, reviewers, days)
        if assignment:
            assignments.append(assignment)
        else:
            unassigned_case_ids.append(case["case_id"])
    
    save_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    main()