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
    
    # Track reviewer availability
    reviewer_availability = {}
    for reviewer in reviewers:
        reviewer_id = reviewer['reviewer_id']
        reviewer_availability[reviewer_id] = [
            day_capacity for day_capacity in reviewer['daily_capacity_hours']
        ]
    
    # Process cases in deadline order
    for case in sorted_cases:
        case_id = case['case_id']
        required_skill = case['required_skill']
        duration_hours = case['duration_hours']
        deadline_day = case['deadline_day']
        
        assigned = False
        
        # Find a suitable reviewer
        for reviewer in reviewers:
            reviewer_id = reviewer['reviewer_id']
            skills = reviewer['skills']
            
            # Check if reviewer has required skill
            if required_skill not in skills:
                continue
            
            # Check if reviewer has capacity on any day before or on deadline
            for day in range(min(deadline_day + 1, days)):
                if reviewer_availability[reviewer_id][day] >= duration_hours:
                    # Assign case to this reviewer
                    assignments.append({
                        'case_id': case_id,
                        'reviewer_id': reviewer_id,
                        'day': day,
                        'hours': duration_hours
                    })
                    
                    # Update reviewer availability
                    reviewer_availability[reviewer_id][day] -= duration_hours
                    
                    assigned = True
                    break
            
            if assigned:
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