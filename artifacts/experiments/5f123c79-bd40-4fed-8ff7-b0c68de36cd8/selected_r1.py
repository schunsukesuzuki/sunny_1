import json

def assign_cases(input_data):
    days = input_data['days']
    cases = input_data['cases']
    reviewers = input_data['reviewers']

    # Initialize assignments and unassigned cases
    assignments = []
    unassigned_case_ids = []

    # Create a list of reviewers with their available capacity per day
    reviewer_capacity = []
    for reviewer in reviewers:
        reviewer_id = reviewer['reviewer_id']
        skills = reviewer['skills']
        daily_capacity = reviewer['daily_capacity_hours']
        reviewer_capacity.append({
            'reviewer_id': reviewer_id,
            'skills': skills,
            'daily_capacity': daily_capacity,
            'available_hours': [0] * days  # Track available hours per day
        })

    # Sort cases by deadline (earlier deadlines first) and then by business priority (higher first)
    cases.sort(key=lambda x: (x['deadline_day'], -x['business_priority']))

    # Assign each case
    for case in cases:
        case_id = case['case_id']
        required_skill = case['required_skill']
        duration_hours = case['duration_hours']
        deadline_day = case['deadline_day']

        assigned = False
        best_reviewer = None
        best_day = None

        # Find the best reviewer for this case
        for reviewer in reviewer_capacity:
            if required_skill in reviewer['skills']:
                # Check if reviewer has capacity on any day before or on deadline
                for day in range(min(deadline_day + 1, days)):
                    if reviewer['available_hours'][day] + duration_hours <= reviewer['daily_capacity'][day]:
                        if best_reviewer is None or day < best_day:
                            best_reviewer = reviewer
                            best_day = day
                            assigned = True

        if assigned:
            # Assign the case to the reviewer
            best_reviewer['available_hours'][best_day] += duration_hours
            assignments.append({
                'case_id': case_id,
                'reviewer_id': best_reviewer['reviewer_id'],
                'day': best_day,
                'hours': duration_hours
            })
        else:
            unassigned_case_ids.append(case_id)

    return {
        'assignments': assignments,
        'unassigned_case_ids': unassigned_case_ids
    }


def main():
    # Read input file
    with open('/home/user/input.json', 'r') as f:
        input_data = json.load(f)

    # Assign cases
    output_data = assign_cases(input_data)

    # Write output file
    with open('/home/user/output.json', 'w') as f:
        json.dump(output_data, f, indent=2)

if __name__ == '__main__':
    main()