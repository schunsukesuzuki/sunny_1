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

def is_skill_match(case_skill, reviewer_skills):
    return case_skill in reviewer_skills

def can_assign(case, reviewer, day):
    # Check if reviewer has the required skill
    if not is_skill_match(case["required_skill"], reviewer["skills"]):
        return False
    
    # Check if reviewer has capacity for this day
    if day >= len(reviewer["daily_capacity_hours"]):
        return False
    
    daily_capacity = reviewer["daily_capacity_hours"][day]
    if daily_capacity < case["duration_hours"]:
        return False
    
    return True

def assign_case_to_reviewer(case, reviewers, day):
    # Find a suitable reviewer for the case on the given day
    for reviewer in reviewers:
        if can_assign(case, reviewer, day):
            return reviewer
    return None

def get_deadline_risk_score(case, current_day):
    # Calculate deadline risk: how many days until deadline
    # Lower score means higher risk (closer to deadline)
    return case["deadline_day"] - current_day


def main():
    data = load_input()
    days = data["days"]
    cases = data["cases"]
    reviewers = data["reviewers"]
    
    # Initialize assignments and unassigned cases
    assignments = []
    unassigned_case_ids = []
    
    # Track reviewer capacity usage per day
    reviewer_capacity_used = defaultdict(lambda: [0] * days)
    
    # Sort cases by deadline risk (earlier deadlines first)
    sorted_cases = sorted(cases, key=lambda x: get_deadline_risk_score(x, 0))
    
    for case in sorted_cases:
        assigned = False
        
        # Try to assign the case on each day
        for day in range(days):
            if assigned:
                break
            
            # Find a reviewer who can handle this case on this day
            reviewer = assign_case_to_reviewer(case, reviewers, day)
            
            if reviewer is not None:
                # Check if we have capacity for this reviewer on this day
                if reviewer_capacity_used[reviewer["reviewer_id"]][day] + case["duration_hours"] <= reviewer["daily_capacity_hours"][day]:
                    # Assign the case
                    assignments.append({
                        "case_id": case["case_id"],
                        "reviewer_id": reviewer["reviewer_id"],
                        "day": day,
                        "hours": case["duration_hours"]
                    })
                    
                    # Update capacity usage
                    reviewer_capacity_used[reviewer["reviewer_id"]][day] += case["duration_hours"]
                    
                    assigned = True
                    break
        
        if not assigned:
            unassigned_case_ids.append(case["case_id"])
    
    save_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    main()