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
    
    # Check if case duration fits within daily capacity
    if case["duration_hours"] > daily_capacity:
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

def get_deadline_risk_score(case):
    # Higher score means higher risk of missing deadline
    # We prioritize cases with earlier deadlines (closer to 0)
    return case["deadline_day"]

def get_scarcity_score(case, reviewers):
    # Count how many reviewers can handle this case
    qualified_reviewers = [r for r in reviewers if is_skill_match(case, r)]
    return len(qualified_reviewers)

def prioritize_cases(cases, reviewers):
    # Create list of (case, risk_score, scarcity_score) tuples
    prioritized = []
    for case in cases:
        risk_score = get_deadline_risk_score(case)
        scarcity_score = get_scarcity_score(case, reviewers)
        # Combine scores: prioritize by deadline risk first, then by scarcity
        # Lower score is better (earlier deadline, fewer reviewers)
        combined_score = (risk_score * 1000) + scarcity_score
        prioritized.append((case, combined_score))
    
    # Sort by combined score (ascending)
    prioritized.sort(key=lambda x: x[1])
    return [item[0] for item in prioritized]

def main():
    data = load_input()
    days = data["days"]
    cases = data["cases"]
    reviewers = data["reviewers"]
    
    # Initialize assignments and unassigned cases
    assignments = []
    unassigned_case_ids = []
    
    # Sort cases by deadline risk and scarcity
    sorted_cases = prioritize_cases(cases, reviewers)
    
    # Track reviewer usage per day
    reviewer_usage = {}
    for reviewer in reviewers:
        reviewer_usage[reviewer["reviewer_id"]] = [0] * days
    
    # Assign cases
    for case in sorted_cases:
        assigned = False
        
        # Try to assign to a qualified reviewer
        for reviewer in reviewers:
            if not is_skill_match(case, reviewer):
                continue
            
            # Try each day
            for day in range(days):
                if can_assign(case, reviewer, day) and \
                   reviewer_usage[reviewer["reviewer_id"]][day] + case["duration_hours"] <= reviewer["daily_capacity_hours"][day]:
                    
                    # Assign the case
                    assignment = assign_case_to_reviewer(case, reviewer, day)
                    assignments.append(assignment)
                    
                    # Update reviewer usage
                    reviewer_usage[reviewer["reviewer_id"]][day] += case["duration_hours"]
                    
                    assigned = True
                    break
            
            if assigned:
                break
        
        if not assigned:
            unassigned_case_ids.append(case["case_id"])
    
    save_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    main()