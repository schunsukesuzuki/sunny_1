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
    
    # Check if reviewer has enough capacity
    capacity = reviewer["daily_capacity_hours"][day]
    if capacity < case["duration_hours"]:
        return False
    
    # Check if reviewer has the required skill
    if not is_skill_match(case, reviewer):
        return False
    
    return True

def assign_case_to_reviewer(case, reviewer, day, assignments, unassigned_case_ids):
    # Update reviewer's capacity
    reviewer["daily_capacity_hours"][day] -= case["duration_hours"]
    
    # Add assignment
    assignment = {
        "case_id": case["case_id"],
        "reviewer_id": reviewer["reviewer_id"],
        "day": day,
        "hours": case["duration_hours"]
    }
    assignments.append(assignment)
    
    # Remove from unassigned
    if case["case_id"] in unassigned_case_ids:
        unassigned_case_ids.remove(case["case_id"])


def main():
    data = load_input()
    days = data["days"]
    cases = data["cases"]
    reviewers = data["reviewers"]
    
    # Initialize assignments and unassigned cases
    assignments = []
    unassigned_case_ids = [case["case_id"] for case in cases]
    
    # Sort cases by deadline (earlier deadlines first)
    cases.sort(key=lambda x: x["deadline_day"])
    
    # For each day
    for day in range(days):
        # Create a copy of reviewers to avoid modifying original during iteration
        day_reviewers = []
        for reviewer in reviewers:
            day_reviewers.append({
                "reviewer_id": reviewer["reviewer_id"],
                "skills": reviewer["skills"],
                "daily_capacity_hours": reviewer["daily_capacity_hours"][:]
            })
        
        # Sort cases for this day by deadline (earlier deadlines first)
        day_cases = [case for case in cases if case["deadline_day"] == day]
        
        # Assign cases to reviewers
        for case in day_cases:
            assigned = False
            
            # Find a suitable reviewer
            for reviewer in day_reviewers:
                if can_assign(case, reviewer, day):
                    assign_case_to_reviewer(case, reviewer, day, assignments, unassigned_case_ids)
                    assigned = True
                    break
            
            # If no reviewer found, try to assign to any reviewer with capacity
            if not assigned:
                for reviewer in day_reviewers:
                    if is_skill_match(case, reviewer) and reviewer["daily_capacity_hours"][day] >= case["duration_hours"]:
                        assign_case_to_reviewer(case, reviewer, day, assignments, unassigned_case_ids)
                        assigned = True
                        break
    
    # Assign remaining cases (those with deadlines in the future or no capacity)
    for case in cases:
        if case["case_id"] in unassigned_case_ids:
            # Try to assign to any reviewer with capacity
            for reviewer in reviewers:
                if is_skill_match(case, reviewer):
                    # Find a day where this reviewer has capacity
                    for day in range(len(reviewer["daily_capacity_hours"])):
                        if reviewer["daily_capacity_hours"][day] >= case["duration_hours"]:
                            assign_case_to_reviewer(case, reviewer, day, assignments, unassigned_case_ids)
                            break
    
    save_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    main()