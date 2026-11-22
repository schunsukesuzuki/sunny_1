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

def is_skill_match(case_skill, reviewer_skills):
    return case_skill in reviewer_skills

def can_assign(case, reviewer, day):
    # Check if reviewer has the required skill
    if not is_skill_match(case["required_skill"], reviewer["skills"]):
        return False
    
    # Check if case duration fits within daily capacity
    if case["duration_hours"] > reviewer["daily_capacity_hours"][day]:
        return False
    
    return True

def assign_cases():
    data = load_input()
    days = data["days"]
    cases = data["cases"]
    reviewers = data["reviewers"]
    
    # Initialize assignments and unassigned cases
    assignments = []
    unassigned_case_ids = []
    
    # Track reviewer daily usage
    reviewer_daily_usage = [[0 for _ in range(days)] for _ in range(len(reviewers))]
    
    # Sort cases by deadline (earliest first) to prioritize deadline risk
    sorted_cases = sorted(cases, key=lambda x: x["deadline_day"])
    
    # Assign each case
    for case in sorted_cases:
        assigned = False
        
        # Find a suitable reviewer
        for i, reviewer in enumerate(reviewers):
            # Try to assign to earliest possible day
            for day in range(case["deadline_day"] + 1):  # Can only assign on or before deadline
                if can_assign(case, reviewer, day) and \
                   reviewer_daily_usage[i][day] + case["duration_hours"] <= reviewer["daily_capacity_hours"][day]:
                    
                    # Assign the case
                    assignments.append({
                        "case_id": case["case_id"],
                        "reviewer_id": reviewer["reviewer_id"],
                        "day": day,
                        "hours": case["duration_hours"]
                    })
                    
                    # Update daily usage
                    reviewer_daily_usage[i][day] += case["duration_hours"]
                    
                    assigned = True
                    break
            
            if assigned:
                break
        
        if not assigned:
            unassigned_case_ids.append(case["case_id"])
    
    return assignments, unassigned_case_ids

# Run the assignment logic
assignments, unassigned_case_ids = assign_cases()

# Save output
save_output(assignments, unassigned_case_ids)