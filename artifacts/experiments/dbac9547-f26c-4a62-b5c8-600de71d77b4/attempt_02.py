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
    if daily_capacity < case["duration_hours"]:
        return False
    
    # Check if reviewer has skill match
    if not is_skill_match(case, reviewer):
        return False
    
    return True

def assign_case_to_reviewer(case, reviewers, day):
    # Find a reviewer who can handle this case on the given day
    for reviewer in reviewers:
        if can_assign(case, reviewer, day):
            # Check if reviewer has capacity for this day
            if day < len(reviewer["daily_capacity_hours"]):
                daily_capacity = reviewer["daily_capacity_hours"][day]
                if daily_capacity >= case["duration_hours"]:
                    return reviewer
    return None

def prioritize_cases(cases, reviewers):
    # Sort cases by deadline day (earlier deadlines first)
    sorted_cases = sorted(cases, key=lambda x: x["deadline_day"])
    return sorted_cases

def schedule_assignments(input_data):
    days = input_data["days"]
    cases = input_data["cases"]
    reviewers = input_data["reviewers"]
    
    # Initialize assignments and unassigned cases
    assignments = []
    unassigned_case_ids = []
    
    # Track reviewer daily capacity usage
    reviewer_daily_usage = {}
    for reviewer in reviewers:
        reviewer_daily_usage[reviewer["reviewer_id"]] = [0] * days
    
    # Sort cases by deadline day (earlier deadlines first)
    sorted_cases = prioritize_cases(cases, reviewers)
    
    # Assign cases to reviewers
    for case in sorted_cases:
        assigned = False
        
        # Try to assign the case on its deadline day or earlier
        for day in range(case["deadline_day"] + 1):
            if not assigned:
                reviewer = assign_case_to_reviewer(case, reviewers, day)
                if reviewer:
                    # Check if reviewer has capacity for this day
                    if day < len(reviewer["daily_capacity_hours"]):
                        daily_capacity = reviewer["daily_capacity_hours"][day]
                        if daily_capacity >= case["duration_hours"]:
                            # Assign the case
                            assignments.append({
                                "case_id": case["case_id"],
                                "reviewer_id": reviewer["reviewer_id"],
                                "day": day,
                                "hours": case["duration_hours"]
                            })
                            
                            # Update reviewer capacity
                            reviewer_daily_usage[reviewer["reviewer_id"]][day] += case["duration_hours"]
                            assigned = True
                            break
        
        if not assigned:
            unassigned_case_ids.append(case["case_id"])
    
    return assignments, unassigned_case_ids

# Main execution
if __name__ == "__main__":
    input_data = load_input()
    assignments, unassigned_case_ids = schedule_assignments(input_data)
    save_output(assignments, unassigned_case_ids)