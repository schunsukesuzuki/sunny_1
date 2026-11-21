import json

def main():
    # Read input
    with open('/home/user/input.json', 'r') as f:
        data = json.load(f)
    
    days = data['days']
    cases = data['cases']
    reviewers = data['reviewers']
    
    # Initialize assignments and unassigned cases
    assignments = []
    unassigned_case_ids = []
    
    # Create a copy of reviewers with remaining capacity
    reviewer_capacity = []
    for r in reviewers:
        reviewer_capacity.append({
            'reviewer_id': r['reviewer_id'],
            'skills': r['skills'],
            'daily_capacity_hours': r['daily_capacity_hours'][:],  # Copy the list
            'total_capacity': sum(r['daily_capacity_hours'])
        })
    
    # Sort cases by deadline day (earlier deadlines first)
    sorted_cases = sorted(cases, key=lambda x: x['deadline_day'])
    
    # Process each case in order of deadline
    for case in sorted_cases:
        assigned = False
        
        # Find a suitable reviewer
        for r in reviewer_capacity:
            # Check if reviewer has the required skill
            if case['required_skill'] in r['skills']:
                # Check if reviewer has capacity on the deadline day
                deadline_day = case['deadline_day']
                if 0 <= deadline_day < days and r['daily_capacity_hours'][deadline_day] >= case['duration_hours']:
                    # Assign the case
                    assignments.append({
                        'case_id': case['case_id'],
                        'reviewer_id': r['reviewer_id'],
                        'day': deadline_day,
                        'hours': case['duration_hours']
                    })
                    
                    # Update reviewer capacity
                    r['daily_capacity_hours'][deadline_day] -= case['duration_hours']
                    r['total_capacity'] -= case['duration_hours']
                    
                    assigned = True
                    break
        
        if not assigned:
            unassigned_case_ids.append(case['case_id'])
    
    # Write output
    output = {
        'assignments': assignments,
        'unassigned_case_ids': unassigned_case_ids
    }
    
    with open('/home/user/output.json', 'w') as f:
        json.dump(output, f, indent=2)

if __name__ == '__main__':
    main()