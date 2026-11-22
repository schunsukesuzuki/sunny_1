import json
from collections import defaultdict

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

def is_skill_match(case_skill, reviewer_skills):
    return case_skill in reviewer_skills

def can_assign(case, reviewer, day):
    # Check if reviewer has the required skill
    if not is_skill_match(case["required_skill"], reviewer["skills"]):
        return False
    
    # Check if there's enough capacity on the given day
    if day >= len(reviewer["daily_capacity_hours"]):
        return False
    
    capacity = reviewer["daily_capacity_hours"][day]
    if capacity < case["duration_hours"]:
        return False
    
    return True

def assign_case_to_reviewer(case, reviewers, assignments, unassigned_case_ids):
    # Find all eligible reviewers for this case
    eligible_reviewers = []
    for reviewer in reviewers:
        for day in range(len(reviewer["daily_capacity_hours"])):
            if can_assign(case, reviewer, day):
                eligible_reviewers.append((reviewer, day))
    
    # If no eligible reviewers, unassign the case
    if not eligible_reviewers:
        unassigned_case_ids.append(case["case_id"])
        return
    
    # Sort by deadline (earlier deadlines first) and then by arrival order
    eligible_reviewers.sort(key=lambda x: (x[0]["reviewer_id"], x[1]))
    
    # Assign to the first available reviewer with earliest deadline
    best_reviewer, best_day = min(eligible_reviewers, key=lambda x: (x[0]["reviewer_id"], x[1]))
    
    # Update assignments and capacity
    assignment = {
        "case_id": case["case_id"],
        "reviewer_id": best_reviewer["reviewer_id"],
        "day": best_day,
        "hours": case["duration_hours"]
    }
    assignments.append(assignment)
    
    # Deduct capacity
    best_reviewer["daily_capacity_hours"][best_day] -= case["duration_hours"]


def main():
    data = load_input()
    days = data["days"]
    cases = data["cases"]
    reviewers = data["reviewers"]
    
    # Initialize assignments and unassigned cases
    assignments = []
    unassigned_case_ids = []
    
    # Sort cases by deadline (earlier deadlines first) and then by arrival order
    cases.sort(key=lambda x: (x["deadline_day"], x["arrival_order"]))
    
    # Assign each case
    for case in cases:
        assign_case_to_reviewer(case, reviewers, assignments, unassigned_case_ids)
    
    save_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    main()