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
    
    # Create a list of cases sorted by deadline (earliest first), then by arrival order
    sorted_cases = sorted(cases, key=lambda x: (x['deadline_day'], x['arrival_order']))
    
    # Create a copy of reviewers with remaining capacity
    reviewer_capacity = []
    for reviewer in reviewers:
        reviewer_copy = {
            'reviewer_id': reviewer['reviewer_id'],
            'skills': reviewer['skills'],
            'daily_capacity_hours': reviewer['daily_capacity_hours'][:],  # Copy the list
            'total_capacity': sum(reviewer['daily_capacity_hours'])
        }
        reviewer_capacity.append(reviewer_copy)
    
    # Process each case in deadline order
    for case in sorted_cases:
        case_id = case['case_id']
        required_skill = case['required_skill']
        duration_hours = case['duration_hours']
        deadline_day = case['deadline_day']
        
        # Find a suitable reviewer
        assigned = False
        for reviewer in reviewer_capacity:
            # Check if reviewer has the required skill
            if required_skill in reviewer['skills']:
                # Check if reviewer has capacity on the deadline day
                if deadline_day < len(reviewer['daily_capacity_hours']) and \
                   reviewer['daily_capacity_hours'][deadline_day] >= duration_hours:
                    # Assign the case
                    assignments.append({
                        'case_id': case_id,
                        'reviewer_id': reviewer['reviewer_id'],
                        'day': deadline_day,
                        'hours': duration_hours
                    })
                    
                    # Update reviewer capacity
                    reviewer['daily_capacity_hours'][deadline_day] -= duration_hours
                    assigned = True
                    break
                
        if not assigned:
            unassigned_case_ids.append(case_id)
    
    # Write output
    output = {
        'assignments': assignments,
        'unassigned_case_ids': unassigned_case_ids
    }
    
    with open('/home/user/output.json', 'w') as f:
        json.dump(output, f, indent=2)

if __name__ == '__main__':
    main()