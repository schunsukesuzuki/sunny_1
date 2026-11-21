import json
from collections import defaultdict

def load_input(input_path):
    with open(input_path, 'r') as f:
        return json.load(f)

def save_output(output_path, output_data):
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

def is_skill_match(case, reviewer):
    return case['required_skill'] in reviewer['skills']

def can_assign_case(case, reviewer, day, assignments_by_reviewer, assignments_by_day):
    # Check if reviewer has skill
    if not is_skill_match(case, reviewer):
        return False
    
    # Check if reviewer has capacity
    current_hours = sum(assignments_by_reviewer[reviewer['reviewer_id']][day] for day in range(len(reviewer['daily_capacity_hours'])))
    if current_hours + case['duration_hours'] > reviewer['daily_capacity_hours'][day]:
        return False
    
    # Check if case is already assigned
    for assignment in assignments_by_reviewer[reviewer['reviewer_id']].values():
        if any(a['case_id'] == case['case_id'] for a in assignment):
            return False
    
    return True

def assign_cases(input_data):
    days = input_data['days']
    cases = input_data['cases']
    reviewers = input_data['reviewers']
    
    # Initialize data structures
    assignments_by_reviewer = defaultdict(lambda: defaultdict(list))
    assignments_by_day = defaultdict(list)
    unassigned_cases = []
    
    # Sort cases by deadline day (earlier deadlines first) and then by arrival order
    sorted_cases = sorted(cases, key=lambda x: (x['deadline_day'], x['arrival_order']))
    
    for case in sorted_cases:
        assigned = False
        best_reviewer = None
        best_day = None
        
        # Find the best reviewer for this case
        for reviewer in reviewers:
            if not is_skill_match(case, reviewer):
                continue
            
            # Try to assign to earliest possible day
            for day in range(days):
                if can_assign_case(case, reviewer, day, assignments_by_reviewer, assignments_by_day):
                    if best_reviewer is None or (day < best_day) or (day == best_day and 
                        (not best_reviewer or 
                         len(reviewer['skills']) > len(best_reviewer['skills']))):
                        best_reviewer = reviewer
                        best_day = day
                        assigned = True
        
        if assigned:
            # Assign the case
            assignment = {
                'case_id': case['case_id'],
                'reviewer_id': best_reviewer['reviewer_id'],
                'day': best_day,
                'hours': case['duration_hours']
            }
            
            assignments_by_reviewer[best_reviewer['reviewer_id']][best_day].append(assignment)
            assignments_by_day[best_day].append(assignment)
        else:
            unassigned_cases.append(case['case_id'])
    
    # Flatten assignments
    all_assignments = []
    for reviewer_id, days_assignments in assignments_by_reviewer.items():
        for day, assignments in days_assignments.items():
            all_assignments.extend(assignments)
    
    return {
        'assignments': all_assignments,
        'unassigned_case_ids': unassigned_cases
    }

def main():
    input_data = load_input('/home/user/input.json')
    output_data = assign_cases(input_data)
    save_output('/home/user/output.json', output_data)

if __name__ == '__main__':
    main()