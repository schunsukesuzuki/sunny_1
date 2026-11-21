"""Strict structural contract for the bounded claims-allocation example."""

SKILL_VERSION = "CLAIMS-ALLOCATION-SKILL-v0.20.0"
STRATEGIES = ("deadline_scarcity", "bounded_beam")


def check_input(data):
    if not isinstance(data, dict) or type(data.get('days')) is not int or not 1 <= data['days'] <= 31:
        raise ValueError('days must be an integer in [1,31]')
    cases, reviewers = data.get('cases'), data.get('reviewers')
    if not isinstance(cases, list) or not isinstance(reviewers, list) or len(cases) > 200 or len(reviewers) > 80:
        raise ValueError('Invalid cases/reviewers list or size')
    if len({c['case_id'] for c in cases}) != len(cases) or len({r['reviewer_id'] for r in reviewers}) != len(reviewers):
        raise ValueError('Duplicate case/reviewer IDs')
    for c in cases:
        if not isinstance(c.get('case_id'), str) or not isinstance(c.get('required_skill'), str):
            raise ValueError('Malformed case identifiers/skills')
        if type(c.get('duration_hours')) is not int or c['duration_hours'] <= 0:
            raise ValueError('Invalid duration')
        if type(c.get('deadline_day')) is not int or type(c.get('arrival_order')) is not int:
            raise ValueError('Invalid deadline or arrival order')
    for r in reviewers:
        if not isinstance(r.get('reviewer_id'),str) or not isinstance(r.get('skills'),list):
            raise ValueError('Malformed reviewer')
        caps = r.get('daily_capacity_hours')
        if not isinstance(caps,list) or len(caps) != data['days'] or any(type(x) is not int or x < 0 for x in caps):
            raise ValueError('Malformed reviewer daily capacity')
    return data
