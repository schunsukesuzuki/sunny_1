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
    
    # Check if reviewer is qualified
    if not is_skill_match(case, reviewer):
        return False
    
    return True

def assign_case_to_reviewer(case, reviewer, day, assignments, unassigned_case_ids):
    # Check if case is already assigned
    for assignment in assignments:
        if assignment["case_id"] == case["case_id"]:
            return False
    
    # Check if reviewer has capacity
    if not can_assign(case, reviewer, day):
        return False
    
    # Assign the case
    assignment = {
        "case_id": case["case_id"],
        "reviewer_id": reviewer["reviewer_id"],
        "day": day,
        "hours": case["duration_hours"]
    }
    assignments.append(assignment)
    return True

def prioritize_deadline_and_scarcity(cases, reviewers, days):
    # Sort cases by deadline (earlier deadlines first)
    sorted_cases = sorted(cases, key=lambda x: x["deadline_day"])
    
    # Create a list of assignments and unassigned cases
    assignments = []
    unassigned_case_ids = []
    
    # For each case, try to assign it to the most suitable reviewer
    for case in sorted_cases:
        assigned = False
        
        # Try to find a reviewer with sufficient capacity and skill match
        for day in range(days):
            if assigned:
                break
            
            # Sort reviewers by skill match and then by available capacity
            eligible_reviewers = []
            for reviewer in reviewers:
                if is_skill_match(case, reviewer) and can_assign(case, reviewer, day):
                    eligible_reviewers.append((reviewer, reviewer["daily_capacity_hours"][day]))
            
            # Sort by available capacity (ascending) to use the most constrained reviewer first
            eligible_reviewers.sort(key=lambda x: x[1])
            
            for reviewer, capacity in eligible_reviewers:
                if assign_case_to_reviewer(case, reviewer, day, assignments, unassigned_case_ids):
                    assigned = True
                    break
        
        if not assigned:
            unassigned_case_ids.append(case["case_id"])
    
    return assignments, unassigned_case_ids

def main():
    data = load_input()
    days = data["days"]
    cases = data["cases"]
    reviewers = data["reviewers"]
    
    assignments, unassigned_case_ids = prioritize_deadline_and_scarcity(cases, reviewers, days)
    save_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    main()