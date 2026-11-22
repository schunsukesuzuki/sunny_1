"""Protect specialists needed by other cases, without changing hard constraints."""


def placement_rank(case, reviewer_id, day, reviewers, remaining_cases):
    r = next(r for r in reviewers if r['reviewer_id']==reviewer_id)
    sole_specialist = sum(1 for pending in remaining_cases
        if pending['case_id']!=case['case_id']
        and pending['required_skill'] in r['skills']
        and sum(pending['required_skill'] in rr['skills'] for rr in reviewers)==1
        and pending['deadline_day']>=day)
    # Meeting the due date dominates all soft skill preferences.
    late = int(day > case['deadline_day'])
    tardiness = max(0, day-case['deadline_day'])
    return (late, tardiness, sole_specialist, len(r['skills']), day, reviewer_id)
