"""PINNED Domain Skill; not an LLM-generated candidate."""
import json

# --- schemas.py ---
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

# --- priority.py ---
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

# --- feasibility.py ---
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

# --- scarcity.py ---
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

# --- optimizer.py ---
"""Two independently selectable bounded heuristics; no optimality claim."""


def greedy_schedule(dataset):
    reviewers=dataset['reviewers']; days=dataset['days']
    remain=capacities(reviewers,days)
    ordered=rank_cases(dataset['cases'], reviewers)
    assigned=[]; unassigned=[]
    for i,c in enumerate(ordered):
        slots=slots_for(c,reviewers,remain,days)
        if not slots:
            unassigned.append(c['case_id']);continue
        rid, day = min(slots, key=lambda x:placement_rank(c,x[0],x[1],reviewers,ordered[i+1:]))
        remain[(rid,day)] -= c['duration_hours']
        assigned.append({'case_id':c['case_id'],'reviewer_id':rid,'day':day,'hours':c['duration_hours']})
    return {'assignments':assigned,'unassigned_case_ids':unassigned}


def bounded_beam_schedule(dataset, beam_width=24):
    """Finite beam search over complete-case assignments. Not an exact solver.

    A bounded beam can miss better solutions and is intentionally labeled as such.
    """
    if type(beam_width) is not int or not 1 <= beam_width <= 64:
        raise ValueError('beam_width must be between 1 and 64')
    reviewers=dataset['reviewers']; days=dataset['days']
    ordered=rank_cases(dataset['cases'],reviewers)
    # (cost, assigned_hours, ordered_assignments, unassigned_ids, remaining)
    states=[(0,0,[],[],capacities(reviewers,days))]
    for i,c in enumerate(ordered):
        candidates=[]
        for score,hours,assign,unassigned,remain in states:
            slots=slots_for(c,reviewers,remain,days)
            # Mark dropping a claim as expensive; retains a complete partition.
            candidates.append((score+5000+c['duration_hours']*40, hours, assign,
                unassigned+[c['case_id']], remain))
            for rid,day in slots:
                nr=remain.copy();nr[(rid,day)]-=c['duration_hours']
                late=max(0,day-c['deadline_day'])
                rank=placement_rank(c,rid,day,reviewers,ordered[i+1:])
                penalty=(1000 if late else 0)+late*200 + rank[2]*2 + rank[3] + day
                candidates.append((score+penalty,hours+c['duration_hours'],
                    assign+[{'case_id':c['case_id'],'reviewer_id':rid,'day':day,'hours':c['duration_hours']}],
                    unassigned,nr))
        # Stable deterministic tie-breaker; output is not a proof of minimum cost.
        candidates.sort(key=lambda s:(s[0],-s[1],len(s[3]),
            tuple((a['case_id'],a['reviewer_id'],a['day']) for a in s[2])))
        states=candidates[:beam_width]
    _, _, assign, missing, _=states[0]
    return {'assignments':assign,'unassigned_case_ids':missing}

# --- validators.py ---
"""Skill-owned internal sanity check ONLY, never the independent acceptance grader."""


def structural_check(dataset,output):
    if not isinstance(output,dict) or not isinstance(output.get('assignments'),list) or not isinstance(output.get('unassigned_case_ids'),list):
        raise ValueError('Missing output arrays')
    input_ids={c['case_id'] for c in dataset['cases']}
    assigned=[x['case_id'] for x in output['assignments']]
    missing=output['unassigned_case_ids']
    if len(assigned)+len(missing)!=len(input_ids) or len(set(assigned+missing))!=len(input_ids) or set(assigned+missing)!=input_ids:
        raise ValueError('Incomplete or duplicated output partition')
    return True

# --- runner.py ---
"""Only allowed deterministic entry point for the Domain Skill."""


def schedule(dataset, strategy='deadline_scarcity'):
    check_input(dataset)
    if strategy == 'deadline_scarcity':
        output=greedy_schedule(dataset)
    elif strategy == 'bounded_beam':
        output=bounded_beam_schedule(dataset)
    else:
        raise ValueError('Unapproved skill strategy')
    structural_check(dataset,output)
    return output

if __name__ == "__main__":
    with open("/home/user/input.json", encoding="utf-8") as f: dataset=json.load(f)
    output=schedule(dataset, strategy='bounded_beam')
    with open("/home/user/output.json", "w", encoding="utf-8") as f: json.dump(output,f,ensure_ascii=False)
