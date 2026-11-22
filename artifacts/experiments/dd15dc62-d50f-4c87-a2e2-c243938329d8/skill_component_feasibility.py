"""Hard feasibility is based on skill, reviewer-day capacity and complete-case duration."""


def slots_for(case, reviewers, remaining, days):
    out=[]
    for day in range(days):
        for reviewer in reviewers:
            rid = reviewer['reviewer_id']
            if case['required_skill'] in reviewer['skills'] and remaining[(rid,day)] >= case['duration_hours']:
                out.append((rid,day))
    return out


def capacities(reviewers, days):
    return {(r['reviewer_id'],day):r['daily_capacity_hours'][day]
            for r in reviewers for day in range(days)}
