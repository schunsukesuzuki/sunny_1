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
    
    # Check if case duration exceeds capacity
    if case["duration_hours"] > capacity:
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


def solve_claims_assignment(input_data):
    days = input_data["days"]
    cases = input_data["cases"]
    reviewers = input_data["reviewers"]
    
    # Sort cases by deadline (earlier deadlines first)
    sorted_cases = sorted(cases, key=lambda x: x["deadline_day"])
    
    assignments = []
    unassigned_case_ids = []
    
    # Track reviewer daily usage
    reviewer_daily_usage = defaultdict(lambda: [0] * days)
    
    for case in sorted_cases:
        assigned = False
        
        # Find a suitable reviewer
        for reviewer in reviewers:
            if not is_skill_match(case, reviewer):
                continue
            
            # Try to assign to earliest possible day
            for day in range(days):
                if can_assign(case, reviewer, day) and \
                   reviewer_daily_usage[reviewer["reviewer_id"]][day] + case["duration_hours"] <= reviewer["daily_capacity_hours"][day]:
                    
                    # Assign the case
                    assignment = assign_case_to_reviewer(case, reviewer, day)
                    assignments.append(assignment)
                    
                    # Update reviewer usage
                    reviewer_daily_usage[reviewer["reviewer_id"]][day] += case["duration_hours"]
                    
                    assigned = True
                    break
            
            if assigned:
                break
        
        if not assigned:
            unassigned_case_ids.append(case["case_id"])
    
    return assignments, unassigned_case_ids


def main():
    input_data = load_input()
    assignments, unassigned_case_ids = solve_claims_assignment(input_data)
    save_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    main()