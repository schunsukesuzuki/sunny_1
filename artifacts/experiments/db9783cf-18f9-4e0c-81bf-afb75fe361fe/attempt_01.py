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

def is_skill_match(case, reviewer):
    return case["required_skill"] in reviewer["skills"]

def can_assign(case, reviewer, day, assignments_by_reviewer, assignments_by_day):
    # Check if reviewer has skill
    if not is_skill_match(case, reviewer):
        return False
    
    # Check if reviewer has capacity
    current_hours = sum(a["hours"] for a in assignments_by_reviewer.get(reviewer["reviewer_id"], []))
    if current_hours + case["duration_hours"] > reviewer["daily_capacity_hours"][day]:
        return False
    
    # Check if case is already assigned
    if any(a["case_id"] == case["case_id"] for a in assignments_by_reviewer.get(reviewer["reviewer_id"], [])):
        return False
    
    return True

def assign_cases():
    data = load_input()
    days = data["days"]
    cases = data["cases"]
    reviewers = data["reviewers"]
    
    # Initialize data structures
    assignments = []
    unassigned_case_ids = []
    assignments_by_reviewer = defaultdict(list)
    assignments_by_day = defaultdict(list)
    
    # Sort cases by deadline day (earlier deadlines first)
    sorted_cases = sorted(cases, key=lambda x: x["deadline_day"])
    
    for case in sorted_cases:
        assigned = False
        
        # Try to assign to a reviewer with the required skill
        for reviewer in reviewers:
            if not is_skill_match(case, reviewer):
                continue
            
            # Check if we can assign this case to this reviewer on any day
            for day in range(days):
                if can_assign(case, reviewer, day, assignments_by_reviewer, assignments_by_day):
                    # Assign the case
                    assignment = {
                        "case_id": case["case_id"],
                        "reviewer_id": reviewer["reviewer_id"],
                        "day": day,
                        "hours": case["duration_hours"]
                    }
                    assignments.append(assignment)
                    assignments_by_reviewer[reviewer["reviewer_id"]].append(assignment)
                    assignments_by_day[day].append(assignment)
                    assigned = True
                    break
            
        if not assigned:
            unassigned_case_ids.append(case["case_id"])
    
    # Ensure all cases are assigned exactly once or explicitly unassigned
    case_ids = {case["case_id"] for case in cases}
    assigned_case_ids = {a["case_id"] for a in assignments}
    
    if not (assigned_case_ids <= case_ids):
        raise ValueError("Some assignments reference non-existent cases")
    
    # Check that all cases are either assigned or unassigned
    all_assigned_or_unassigned = assigned_case_ids.union(set(unassigned_case_ids)) == case_ids
    if not all_assigned_or_unassigned:
        raise ValueError("Some cases are neither assigned nor unassigned")
    
    save_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    assign_cases()