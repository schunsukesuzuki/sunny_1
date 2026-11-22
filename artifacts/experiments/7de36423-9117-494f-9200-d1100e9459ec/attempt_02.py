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

def is_skill_match(case_skills, reviewer_skills):
    return any(skill in reviewer_skills for skill in case_skills)

def assign_cases():
    data = load_input()
    days = data['days']
    cases = data['cases']
    reviewers = data['reviewers']
    
    # Initialize assignments and capacity tracking
    assignments = []
    unassigned_case_ids = []
    reviewer_capacity = defaultdict(lambda: [0] * days)
    
    # Sort cases by deadline (EDD - Earliest Deadline First)
    sorted_cases = sorted(cases, key=lambda x: x['deadline_day'])
    
    for case in sorted_cases:
        case_id = case['case_id']
        required_skills = case['required_skill'] if isinstance(case['required_skill'], list) else [case['required_skill']]
        duration_hours = case['duration_hours']
        deadline_day = case['deadline_day']
        
        assigned = False
        
        # Find a suitable reviewer
        for reviewer in reviewers:
            reviewer_id = reviewer['reviewer_id']
            reviewer_skills = reviewer['skills']
            daily_capacity = reviewer['daily_capacity_hours']
            
            if not is_skill_match(required_skills, reviewer_skills):
                continue
            
            # Try to assign the case to this reviewer
            for day in range(days):
                if day > deadline_day:
                    break  # Cannot assign past deadline
                
                if reviewer_capacity[reviewer_id][day] + duration_hours <= daily_capacity[day]:
                    # Assign case
                    reviewer_capacity[reviewer_id][day] += duration_hours
                    assignments.append({
                        "case_id": case_id,
                        "reviewer_id": reviewer_id,
                        "day": day,
                        "hours": duration_hours
                    })
                    assigned = True
                    break
            
            if assigned:
                break
        
        if not assigned:
            unassigned_case_ids.append(case_id)
    
    # Ensure all cases are assigned or explicitly unassigned
    for case in cases:
        if case['case_id'] not in [a['case_id'] for a in assignments] and case['case_id'] not in unassigned_case_ids:
            unassigned_case_ids.append(case['case_id'])
    
    save_output(assignments, unassigned_case_ids)

if __name__ == "__main__":
    assign_cases()