import json
import sys
from collections import defaultdict

def read_input():
    with open('/home/user/input.json', 'r') as f:
        return json.load(f)

def write_output(assignments, unassigned_case_ids):
    output = {
        "assignments": assignments,
        "unassigned_case_ids": unassigned_case_ids
    }
    with open('/home/user/output.json', 'w') as f:
        json.dump(output, f, indent=2)

def is_skill_match(case_skill, reviewer_skills):
    return case_skill in reviewer_skills

def can_assign_case(case, reviewer, day):
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
        if can_assign_case(case, reviewer, day):
            # Check if reviewer has capacity for this day
            if day < len(reviewer["daily_capacity_hours"]):
                daily_capacity = reviewer["daily_capacity_hours"][day]
                if daily_capacity >= case["duration_hours"]:
                    return reviewer
    return None

def prioritize_cases(cases, reviewers):
    # Sort cases by deadline day (earlier deadlines first)
    # If same deadline, prioritize by business priority (higher first)
    # If same deadline and priority, prioritize by arrival order (earlier first)
    sorted_cases = sorted(cases, key=lambda x: (x["deadline_day"], -x["business_priority"], x["arrival_order"]))
    return sorted_cases


def assign_cases_to_reviewers(cases, reviewers, days):
    assignments = []
    unassigned_case_ids = []
    
    # Track reviewer capacity usage per day
    reviewer_capacity_usage = defaultdict(lambda: [0] * days)
    
    # Sort cases by deadline priority
    sorted_cases = prioritize_cases(cases, reviewers)
    
    for case in sorted_cases:
        assigned = False
        
        # Try to assign the case on its deadline day first
        for day in range(case["deadline_day"], days):
            reviewer = assign_case_to_reviewer(case, reviewers, day)
            if reviewer is not None:
                # Check if this reviewer has capacity for this day
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
                        
                        # Update capacity usage
                        reviewer_capacity_usage[reviewer["reviewer_id"]][day] += case["duration_hours"]
                        assigned = True
                        break
        
        if not assigned:
            unassigned_case_ids.append(case["case_id"])
    
    return assignments, unassigned_case_ids


def main():
    data = read_input()
    days = data["days"]
    cases = data["cases"]
    reviewers = data["reviewers"]
    
    assignments, unassigned_case_ids = assign_cases_to_reviewers(cases, reviewers, days)
    
    write_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    main()