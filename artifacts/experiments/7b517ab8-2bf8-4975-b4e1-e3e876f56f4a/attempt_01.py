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
    required_hours = case["duration_hours"]
    
    # Check if reviewer can handle the case duration within capacity
    return required_hours <= daily_capacity


def assign_cases():
    data = load_input()
    days = data["days"]
    cases = data["cases"]
    reviewers = data["reviewers"]
    
    # Sort cases by deadline (earlier deadlines first)
    sorted_cases = sorted(cases, key=lambda x: x["deadline_day"])
    
    assignments = []
    unassigned_case_ids = []
    
    # Track reviewer usage per day
    reviewer_usage = [[0 for _ in range(days)] for _ in reviewers]
    
    for case in sorted_cases:
        assigned = False
        
        # Find a suitable reviewer
        for i, reviewer in enumerate(reviewers):
            if not is_skill_match(case, reviewer):
                continue
            
            # Try to assign to earliest possible day
            for day in range(days):
                if can_assign(case, reviewer, day) and reviewer_usage[i][day] + case["duration_hours"] <= reviewer["daily_capacity_hours"][day]:
                    # Assign the case
                    assignments.append({
                        "case_id": case["case_id"],
                        "reviewer_id": reviewer["reviewer_id"],
                        "day": day,
                        "hours": case["duration_hours"]
                    })
                    
                    # Update usage
                    reviewer_usage[i][day] += case["duration_hours"]
                    assigned = True
                    break
            
            if assigned:
                break
        
        if not assigned:
            unassigned_case_ids.append(case["case_id"])
    
    save_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    assign_cases()