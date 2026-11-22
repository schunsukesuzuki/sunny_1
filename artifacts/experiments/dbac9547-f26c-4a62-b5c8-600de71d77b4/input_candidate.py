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
    
    # Create a list of cases sorted by deadline (earliest first)
    # For ties, sort by arrival order (FIFO)
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
        assigned = False
        
        # Find a suitable reviewer
        for reviewer in reviewer_capacity:
            # Check if reviewer has the required skill
            if case['required_skill'] in reviewer['skills']:
                # Try to assign the case to this reviewer
                for day in range(days):
                    if day < len(reviewer['daily_capacity_hours']) and \
                       reviewer['daily_capacity_hours'][day] >= case['duration_hours']:
                        # Assign the case
                        assignments.append({
                            'case_id': case['case_id'],
                            'reviewer_id': reviewer['reviewer_id'],
                            'day': day,
                            'hours': case['duration_hours']
                        })
                        
                        # Update reviewer's capacity
                        reviewer['daily_capacity_hours'][day] -= case['duration_hours']
                        
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