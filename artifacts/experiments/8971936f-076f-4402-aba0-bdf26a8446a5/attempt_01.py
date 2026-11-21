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

def is_skill_match(case, reviewer):
    return case["required_skill"] in reviewer["skills"]

def can_assign(case, reviewer, day):
    # Check if reviewer has capacity for this day
    if day >= len(reviewer["daily_capacity_hours"]):
        return False
    
    capacity = reviewer["daily_capacity_hours"][day]
    if capacity < case["duration_hours"]:
        return False
    
    # Check if reviewer has skill match
    if not is_skill_match(case, reviewer):
        return False
    
    return True

def assign_case_to_reviewer(case, reviewer, day, assignments, unassigned_case_ids):
    # Check if case is already assigned
    for assignment in assignments:
        if assignment["case_id"] == case["case_id"]:
            return False
    
    # Check if reviewer has capacity
    if not can_assign(case, reviewer, day):
        return False
    
    # Assign the case
    assignment = {
        "case_id": case["case_id"],
        "reviewer_id": reviewer["reviewer_id"],
        "day": day,
        "hours": case["duration_hours"]
    }
    
    assignments.append(assignment)
    return True

def get_reviewer_capacity(reviewer, day):
    if day >= len(reviewer["daily_capacity_hours"]):
        return 0
    return reviewer["daily_capacity_hours"][day]

def prioritize_cases(cases):
    # Sort by deadline day (earlier deadlines first)
    # For same deadline, sort by arrival order (FIFO)
    return sorted(cases, key=lambda x: (x["deadline_day"], x["arrival_order"]))

def schedule_assignments(input_data):
    days = input_data["days"]
    cases = input_data["cases"]
    reviewers = input_data["reviewers"]
    
    # Sort cases by deadline day and arrival order
    sorted_cases = prioritize_cases(cases)
    
    assignments = []
    unassigned_case_ids = []
    
    # Create a copy of reviewers with remaining capacity
    reviewer_capacity = []
    for reviewer in reviewers:
        reviewer_copy = {
            "reviewer_id": reviewer["reviewer_id"],
            "skills": reviewer["skills"],
            "daily_capacity_hours": reviewer["daily_capacity_hours"][:]
        }
        reviewer_capacity.append(reviewer_copy)
    
    # Process cases in deadline priority order
    for case in sorted_cases:
        assigned = False
        
        # Try to assign to a reviewer with sufficient capacity and skill match
        for day in range(days):
            if assigned:
                break
            
            # Sort reviewers by available capacity (ascending) to use scarce resources efficiently
            sorted_reviewers = sorted(reviewer_capacity, key=lambda r: get_reviewer_capacity(r, day))
            
            for reviewer in sorted_reviewers:
                if not is_skill_match(case, reviewer):
                    continue
                
                # Check if reviewer has capacity on this day
                if day < len(reviewer["daily_capacity_hours"]):
                    if reviewer["daily_capacity_hours"][day] >= case["duration_hours"]:
                        # Assign the case
                        assignment = {
                            "case_id": case["case_id"],
                            "reviewer_id": reviewer["reviewer_id"],
                            "day": day,
                            "hours": case["duration_hours"]
                        }
                        
                        assignments.append(assignment)
                        
                        # Update reviewer capacity
                        reviewer["daily_capacity_hours"][day] -= case["duration_hours"]
                        
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