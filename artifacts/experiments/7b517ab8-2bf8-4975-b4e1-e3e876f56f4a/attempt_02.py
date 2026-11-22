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
    # If same deadline, prioritize by business priority (higher first)
    # If same priority, prioritize by arrival order (earlier first)
    cases.sort(key=lambda x: (x['deadline_day'], -x['business_priority'], x['arrival_order']))
    
    for case in cases:
        assigned = False
        best_reviewer = None
        best_day = None
        best_hours = None
        
        # Find the best reviewer for this case
        for r in reviewer_capacity:
            # Check if reviewer has required skill
            if case['required_skill'] in r['skills']:
                # Try to assign to earliest possible day
                for day in range(days):
                    if day < len(r['daily_capacity_hours']) and r['daily_capacity_hours'][day] >= case['duration_hours']:
                        # Check if this is better than previous best (earlier day, or same day but earlier in reviewer list)
                        if not assigned or day < best_day or (day == best_day and 
                            (best_reviewer is None or r['reviewer_id'] < best_reviewer['reviewer_id'])):
                            best_reviewer = r
                            best_day = day
                            best_hours = case['duration_hours']
                            assigned = True
        
        if assigned:
            # Assign the case
            assignments.append({
                'case_id': case['case_id'],
                'reviewer_id': best_reviewer['reviewer_id'],
                'day': best_day,
                'hours': best_hours
            })
            
            # Update reviewer capacity
            best_reviewer['daily_capacity_hours'][best_day] -= best_hours
            best_reviewer['total_capacity'] -= best_hours
        else:
            unassigned_case_ids.append(case['case_id'])
    
    # Write output
    output = {
        'assignments': assignments,
        'unassigned_case_ids': unassigned_case_ids
    }
    
    with open('/home/user/output.json', 'w') as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    main()