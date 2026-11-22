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
    
    # Check if reviewer has skill
    if not is_skill_match(case, reviewer):
        return False
    
    return True

def assign_case_to_reviewer(case, reviewers, day, assignments, unassigned_case_ids):
    # Find the best reviewer based on deadline priority and skill scarcity
    best_reviewer = None
    min_deadline = float('inf')
    
    for reviewer in reviewers:
        if can_assign(case, reviewer, day):
            # Check if this reviewer has the required skill
            if is_skill_match(case, reviewer):
                # Calculate deadline priority (lower day is better)
                deadline_priority = case["deadline_day"]
                
                # Prefer reviewers with fewer assignments
                reviewer_assignments = [a for a in assignments if a["reviewer_id"] == reviewer["reviewer_id"]]
                
                if best_reviewer is None or deadline_priority < min_deadline:
                    best_reviewer = reviewer
                    min_deadline = deadline_priority
                elif deadline_priority == min_deadline and len(reviewer_assignments) < len([a for a in assignments if a["reviewer_id"] == best_reviewer["reviewer_id"]]):
                    # Tie-break: prefer reviewer with fewer assignments
                    best_reviewer = reviewer
    
    if best_reviewer:
        # Assign the case
        assignment = {
            "case_id": case["case_id"],
            "reviewer_id": best_reviewer["reviewer_id"],
            "day": day,
            "hours": case["duration_hours"]
        }
        assignments.append(assignment)
        
        # Update reviewer's capacity
        best_reviewer["daily_capacity_hours"][day] -= case["duration_hours"]
        return True
    else:
        unassigned_case_ids.append(case["case_id"])
        return False


def main():
    data = load_input()
    
    days = data["days"]
    cases = data["cases"]
    reviewers = data["reviewers"]
    
    assignments = []
    unassigned_case_ids = []
    
    # Sort cases by deadline day (earlier deadlines first)
    cases.sort(key=lambda x: x["deadline_day"])
    
    for day in range(days):
        # For each day, assign cases
        for case in cases:
            if case["case_id"] not in unassigned_case_ids:
                assign_case_to_reviewer(case, reviewers, day, assignments, unassigned_case_ids)
    
    save_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    main()