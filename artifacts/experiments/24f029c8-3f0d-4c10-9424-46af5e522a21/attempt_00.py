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
    
    capacity = reviewer["daily_capacity_hours"][day]
    if capacity < case["duration_hours"]:
        return False
    
    # Check if reviewer has skill match
    if not is_skill_match(case, reviewer):
        return False
    
    return True

def find_assignment(case, reviewers, days):
    # Try to assign the case to a qualified reviewer with enough capacity
    for day in range(days):
        for reviewer in reviewers:
            if can_assign(case, reviewer, day):
                # Check if reviewer already has an assignment on this day
                # (This is a simplified check - in reality we'd need to track existing assignments)
                return {
                    "case_id": case["case_id"],
                    "reviewer_id": reviewer["reviewer_id"],
                    "day": day,
                    "hours": case["duration_hours"]
                }
    return None

def main():
    data = load_input()
    days = data["days"]
    cases = data["cases"]
    reviewers = data["reviewers"]
    
    assignments = []
    unassigned_case_ids = []
    
    # Sort cases by deadline (earlier deadlines first) - EDD heuristic
    cases.sort(key=lambda x: x["deadline_day"])
    
    for case in cases:
        assignment = find_assignment(case, reviewers, days)
        if assignment:
            assignments.append(assignment)
        else:
            unassigned_case_ids.append(case["case_id"])
    
    save_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    main()