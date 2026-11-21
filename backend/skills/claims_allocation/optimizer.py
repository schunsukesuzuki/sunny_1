"""Two independently selectable bounded heuristics; no optimality claim."""
from .feasibility import capacities, slots_for
from .priority import rank_cases
from .scarcity import placement_rank


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
