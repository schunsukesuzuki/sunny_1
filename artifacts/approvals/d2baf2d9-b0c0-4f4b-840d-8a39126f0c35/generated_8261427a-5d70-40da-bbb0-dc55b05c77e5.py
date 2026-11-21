import json

def load_input(input_path):
    with open(input_path, 'r') as f:
        return json.load(f)

def save_output(output_path, output_data):
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

def is_skill_match(case, reviewer):
    return case['required_skill'] in reviewer['skills']

def can_assign_case(case, reviewer, day):
    # Check if reviewer has capacity for this case on the given day
    if day >= len(reviewer['daily_capacity_hours']):
        return False
    
    capacity = reviewer['daily_capacity_hours'][day]
    if capacity < case['duration_hours']:
        return False
    
    # Check if reviewer has skill match
    if not is_skill_match(case, reviewer):
        return False
    
    return True

def find_best_assignment(case, reviewers, days):
    best_reviewer = None
    best_day = None
    
    for reviewer in reviewers:
        # Check if reviewer has skill match
        if not is_skill_match(case, reviewer):
            continue
        
        # Try to assign case on each day
        for day in range(min(days, len(reviewer['daily_capacity_hours']))):
            if can_assign_case(case, reviewer, day):
                # Prefer earlier days and reviewers with less workload
                if best_reviewer is None or day < best_day or (day == best_day and 
                    sum(reviewer['daily_capacity_hours'][i] for i in range(days) if i < day) < 
                    sum(best_reviewer['daily_capacity_hours'][i] for i in range(days) if i < best_day)):
                    best_reviewer = reviewer
                    best_day = day
    
    return best_reviewer, best_day

def assign_cases(cases, reviewers, days):
    assignments = []
    unassigned_case_ids = []
    
    # Create a copy of reviewers with updated capacities
    active_reviewers = []
    for reviewer in reviewers:
        active_reviewers.append({
            'reviewer_id': reviewer['reviewer_id'],
            'skills': reviewer['skills'],
            'daily_capacity_hours': reviewer['daily_capacity_hours'][:]
        })
    
    # Sort cases by deadline day (earlier deadlines first)
    sorted_cases = sorted(cases, key=lambda x: x['deadline_day'])
    
    for case in sorted_cases:
        best_reviewer, best_day = find_best_assignment(case, active_reviewers, days)
        
        if best_reviewer is not None and best_day is not None:
            # Assign the case
            assignment = {
                'case_id': case['case_id'],
                'reviewer_id': best_reviewer['reviewer_id'],
                'day': best_day,
                'hours': case['duration_hours']
            }
            assignments.append(assignment)
            
            # Update reviewer's capacity
            active_reviewers[active_reviewers.index(best_reviewer)]['daily_capacity_hours'][best_day] -= case['duration_hours']
        else:
            unassigned_case_ids.append(case['case_id'])
    
    return assignments, unassigned_case_ids

# Main execution
if __name__ == "__main__":
    input_data = load_input('/home/user/input.json')
    
    days = input_data['days']
    cases = input_data['cases']
    reviewers = input_data['reviewers']
    
    assignments, unassigned_case_ids = assign_cases(cases, reviewers, days)
    
    output_data = {
        'assignments': assignments,
        'unassigned_case_ids': unassigned_case_ids
    }
    
    save_output('/home/user/output.json', output_data)