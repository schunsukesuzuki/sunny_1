import json
import sys
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

def get_deadline_risk_score(case):
    # Higher score means higher risk of missing deadline
    # We prioritize cases with earlier deadlines (closer to day 0)
    return case["deadline_day"]

def sort_cases_by_deadline_risk(cases):
    # Sort by deadline day (ascending) - earlier deadlines have higher priority
    return sorted(cases, key=lambda x: x["deadline_day"])

def schedule_assignments(input_data):
    days = input_data["days"]
    cases = input_data["cases"]
    reviewers = input_data["reviewers"]
    
    # Initialize assignments and unassigned cases
    assignments = []
    unassigned_case_ids = []
    
    # Track reviewer daily capacity usage
    reviewer_capacity_usage = defaultdict(lambda: [0] * days)
    
    # Sort cases by deadline risk (earlier deadlines first)
    sorted_cases = sort_cases_by_deadline_risk(cases)
    
    for case in sorted_cases:
        assigned = False
        
        # Try to assign the case on each day
        for day in range(days):
            reviewer = assign_case_to_reviewer(case, reviewers, day)
            if reviewer is not None:
                # Check if we can assign this reviewer to this case on this day
                if reviewer_capacity_usage[reviewer["reviewer_id"]][day] + case["duration_hours"] <= reviewer["daily_capacity_hours"][day]:
                    # Assign the case
                    assignments.append({
                        "case_id": case["case_id"],
                        "reviewer_id": reviewer["reviewer_id"],
                        "day": day,
                        "hours": case["duration_hours"]
                    })
                    
                    # Update capacity usage
                    reviewer_capacity_usage[reviewer["reviewer_id"]][day] += case["duration_hours"]
                    
                    assigned = True
                    break
        
        if not assigned:
            unassigned_case_ids.append(case["case_id"])
    
    return assignments, unassigned_case_ids

# Main execution
if __name__ == "__main__":
    try:
        input_data = load_input()
        assignments, unassigned_case_ids = schedule_assignments(input_data)
        save_output(assignments, unassigned_case_ids)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)