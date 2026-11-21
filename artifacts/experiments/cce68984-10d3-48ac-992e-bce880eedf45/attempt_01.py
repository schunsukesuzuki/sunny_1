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

def assign_case_to_reviewer(case, reviewer, day, assignments, unassigned_case_ids):
    # Assign the case to the reviewer on the given day
    assignment = {
        "case_id": case["case_id"],
        "reviewer_id": reviewer["reviewer_id"],
        "day": day,
        "hours": case["duration_hours"]
    }
    assignments.append(assignment)
    
    # Update reviewer's capacity
    reviewer["daily_capacity_hours"][day] -= case["duration_hours"]
    
    # Remove from unassigned list
    if case["case_id"] in unassigned_case_ids:
        unassigned_case_ids.remove(case["case_id"])


def prioritize_by_deadline(cases):
    # Sort cases by deadline day (ascending), then by arrival order (ascending) for ties
    return sorted(cases, key=lambda x: (x["deadline_day"], x["arrival_order"]))

def schedule_cases():
    data = load_input()
    days = data["days"]
    cases = data["cases"]
    reviewers = data["reviewers"]
    
    # Initialize assignments and unassigned list
    assignments = []
    unassigned_case_ids = [case["case_id"] for case in cases]
    
    # Sort cases by deadline priority
    sorted_cases = prioritize_by_deadline(cases)
    
    # Create a copy of reviewers to avoid modifying original data
    reviewers_copy = []
    for reviewer in reviewers:
        reviewers_copy.append({
            "reviewer_id": reviewer["reviewer_id"],
            "skills": reviewer["skills"],
            "daily_capacity_hours": reviewer["daily_capacity_hours"][:]
        })
    
    # For each case, try to assign it to a qualified reviewer
    for case in sorted_cases:
        assigned = False
        
        # Try to find a reviewer who can handle this case
        for day in range(days):
            if assigned:
                break
            
            for reviewer in reviewers_copy:
                if not assigned and can_assign(case, reviewer, day):
                    assign_case_to_reviewer(case, reviewer, day, assignments, unassigned_case_ids)
                    assigned = True
                    break
    
    # If a case couldn't be assigned, it remains in unassigned_case_ids
    save_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    schedule_cases()