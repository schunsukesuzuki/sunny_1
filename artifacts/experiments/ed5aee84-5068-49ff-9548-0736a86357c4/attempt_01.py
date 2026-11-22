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

def is_valid_day(day, days):
    return 0 <= day < days

def can_assign(case, reviewer, day, days):
    # Check if reviewer has skill
    if case["required_skill"] not in reviewer["skills"]:
        return False
    
    # Check if day is valid
    if not is_valid_day(day, days):
        return False
    
    # Check capacity
    if reviewer["daily_capacity_hours"][day] < case["duration_hours"]:
        return False
    
    return True

def assign_case(case, reviewer, day, days, assignments, unassigned_case_ids):
    # Check if case is already assigned
    for assignment in assignments:
        if assignment["case_id"] == case["case_id"]:
            return False
    
    # Check if reviewer can handle this case on this day
    if not can_assign(case, reviewer, day, days):
        return False
    
    # Assign the case
    assignments.append({
        "case_id": case["case_id"],
        "reviewer_id": reviewer["reviewer_id"],
        "day": day,
        "hours": case["duration_hours"]
    })
    
    # Update reviewer capacity
    reviewer["daily_capacity_hours"][day] -= case["duration_hours"]
    
    return True

def prioritize_by_deadline_and_skill(cases, reviewers, days):
    # Sort cases by deadline (earlier first) and then by business priority (higher first)
    sorted_cases = sorted(cases, key=lambda x: (x["deadline_day"], -x["business_priority"]))
    
    # Create a copy of reviewers to avoid modifying original
    reviewers_copy = []
    for reviewer in reviewers:
        reviewers_copy.append({
            "reviewer_id": reviewer["reviewer_id"],
            "skills": reviewer["skills"],
            "daily_capacity_hours": reviewer["daily_capacity_hours"][:]
        })
    
    assignments = []
    unassigned_case_ids = []
    
    for case in sorted_cases:
        assigned = False
        
        # Try to assign the case to a qualified reviewer
        for day in range(days):
            if assigned:
                break
            
            for reviewer in reviewers_copy:
                if assigned:
                    break
                
                if can_assign(case, reviewer, day, days):
                    assign_case(case, reviewer, day, days, assignments, unassigned_case_ids)
                    assigned = True
                    
        # If not assigned, add to unassigned list
        if not assigned:
            unassigned_case_ids.append(case["case_id"])
    
    return assignments, unassigned_case_ids

def main():
    data = load_input()
    days = data["days"]
    cases = data["cases"]
    reviewers = data["reviewers"]
    
    assignments, unassigned_case_ids = prioritize_by_deadline_and_skill(cases, reviewers, days)
    
    save_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    main()