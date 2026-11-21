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

def assign_case_to_reviewer(case, reviewers, assignments, unassigned_case_ids):
    # Find all eligible reviewers for this case
    eligible_reviewers = []
    for reviewer in reviewers:
        if is_skill_match(case, reviewer):
            # Check if reviewer can handle the case on any day
            for day in range(len(reviewer["daily_capacity_hours"])):
                if can_assign(case, reviewer, day):
                    eligible_reviewers.append((reviewer, day))
    
    if not eligible_reviewers:
        unassigned_case_ids.append(case["case_id"])
        return
    
    # Sort by deadline (earlier deadlines first) and then by priority
    eligible_reviewers.sort(key=lambda x: (x[1], -case["business_priority"]))
    
    # Assign to the reviewer with earliest deadline and highest priority
    reviewer, day = eligible_reviewers[0]
    
    # Check if reviewer has capacity for this day
    if day >= len(reviewer["daily_capacity_hours"]):
        unassigned_case_ids.append(case["case_id"])
        return
    
    hours = case["duration_hours"]
    if reviewer["daily_capacity_hours"][day] < hours:
        unassigned_case_ids.append(case["case_id"])
        return
    
    # Assign the case
    assignments.append({
        "case_id": case["case_id"],
        "reviewer_id": reviewer["reviewer_id"],
        "day": day,
        "hours": hours
    })
    
    # Update reviewer's capacity
    reviewer["daily_capacity_hours"][day] -= hours


def main():
    data = load_input()
    days = data["days"]
    cases = data["cases"]
    reviewers = data["reviewers"]
    
    assignments = []
    unassigned_case_ids = []
    
    # Sort cases by deadline day (earlier deadlines first)
    cases.sort(key=lambda x: x["deadline_day"])
    
    for case in cases:
        assign_case_to_reviewer(case, reviewers, assignments, unassigned_case_ids)
    
    save_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    main()