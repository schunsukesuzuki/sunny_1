"""Deadline and qualification scarcity are separate, interpretable objectives."""


def rank_cases(cases, reviewers):
    skill_supply = {}
    for c in cases:
        s = c['required_skill']
        if s not in skill_supply:
            skill_supply[s] = sum(s in r['skills'] for r in reviewers)
    return sorted(cases, key=lambda c: (
        c['deadline_day'], skill_supply[c['required_skill']],
        -c['duration_hours'], -c.get('business_priority',1),
        c['arrival_order'], c['case_id']))
