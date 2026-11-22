"""v0.28 DEV-only multi-scenario robustness selection and stability audit.

Inputs are the *predeclared* DEV seeds and policy stress scenarios (never
HOLDOUT or 08f).  A deterministic leave-one-stress-out sensitivity check is
reported as an instability diagnostic, NOT a confidence interval or an
estimate of real-world generalization.
"""
from __future__ import annotations
from . import dev_robustness_fixtures as fixtures

VERSION = 'PRESELECTION-DEV-ROBUSTNESS-v0.28.0'
EXPECTED_STRESS_SEEDS = frozenset((910000, 910001, 910002, 910003))


def _as_nonnegative_int(value):
    return value if type(value) is int and value >= 0 else None


def _stress_rows(candidate: dict) -> dict[int, dict]:
    out = {}
    for row in candidate.get('stress_checks') or []:
        if not isinstance(row, dict):
            continue
        seed = row.get('seed')
        proposed = row.get('generated') or {}
        baseline = row.get('deadline') or {}
        if (type(seed) is not int or seed in out or
                not proposed.get('valid') or not baseline.get('valid')):
            return {}
        misses = _as_nonnegative_int(proposed.get('missed'))
        unassigned = _as_nonnegative_int(proposed.get('unassigned'))
        ref_misses = _as_nonnegative_int(baseline.get('missed'))
        ref_unassigned = _as_nonnegative_int(baseline.get('unassigned'))
        if None in (misses, unassigned, ref_misses, ref_unassigned):
            return {}
        out[seed] = {'seed': seed, 'scenario': str(row.get('scenario') or seed),
                     'missed': misses, 'unassigned': unassigned,
                     'reference_missed': ref_misses, 'reference_unassigned': ref_unassigned,
                     'regret_missed': misses-ref_misses,
                     'regret_unassigned': unassigned-ref_unassigned}
    return out


def _extra_rows(candidate: dict) -> dict[int,dict]:
    out={}
    for row in candidate.get('extra_dev_metrics') or []:
        if not isinstance(row,dict):
            return {}
        seed=row.get('seed')
        missed=_as_nonnegative_int(row.get('missed_deadlines'))
        unassigned=_as_nonnegative_int(row.get('unassigned_cases'))
        if (type(seed) is not int or seed in out or row.get('valid') is not True or
                missed is None or unassigned is None):
            return {}
        out[seed]={'seed':seed,'missed':missed,'unassigned':unassigned,
                   'valid':True}
    return out


def _base_rows(candidate: dict) -> list[dict]:
    return [{'seed':x.get('seed'), 'missed':x.get('missed_deadlines'),
             'unassigned':x.get('unassigned_cases'), 'valid':x.get('valid')}
            for x in (candidate.get('dev_case_metrics') or []) if isinstance(x,dict)]


def _candidate_score(candidate: dict, usable_stress: bool,
                     usable_extra: bool = False, omit_seed: int | None = None,
                     omit_extra_seed: int | None = None) -> tuple:
    base = candidate.get('dev_score') or [10**9,10**9]
    score=(base[0],base[1])
    if usable_extra:
        extra=[r for seed,r in _extra_rows(candidate).items() if seed!=omit_extra_seed]
        score+=(max((r['missed'] for r in extra),default=0),
                sum(r['missed'] for r in extra),
                sum(r['unassigned'] for r in extra))
    if usable_stress:
        cases=[r for seed,r in _stress_rows(candidate).items() if seed!=omit_seed]
        score+=(max((r['missed'] for r in cases),default=0),
                sum(r['missed'] for r in cases),
                sum(r['unassigned'] for r in cases))
    return score


def choose(candidates: list[dict]) -> dict:
    eligible = [(i,c) for i,c in enumerate(candidates) if c.get('eligible') is True]
    profiles = [_stress_rows(c) for _,c in eligible]
    comparable = bool(eligible) and all(set(x) == EXPECTED_STRESS_SEEDS for x in profiles)
    if comparable:
        for seed in EXPECTED_STRESS_SEEDS:
            # Reference scenario identity must agree for every candidate.
            reference = {(rows[seed]['reference_missed'], rows[seed]['reference_unassigned'],
                          rows[seed]['scenario']) for rows in profiles}
            if len(reference) != 1:
                comparable = False
                break
    # A wholly missing cohort (legacy artifacts) cannot establish robustness.
    # If only SOME candidates have the new cohort, don't reward their missing
    # data: disable this dimension for ALL candidates and flag the mismatch.
    extra_present=any(c.get('extra_dev_metrics') for _,c in eligible)
    extra_profiles=[_extra_rows(c) for _,c in eligible]
    extra_comparable=bool(extra_present and eligible) and all(
        set(x)==set(fixtures.SEEDS) for x in extra_profiles)
    def ranking(omit_seed: int | None = None, omit_extra_seed: int | None = None):
        return sorted(eligible, key=lambda pair:(
            *_candidate_score(pair[1],comparable,extra_comparable,omit_seed,omit_extra_seed),pair[0]))
    ordered = ranking()
    winner = ordered[0][1] if ordered else None
    top_score = _candidate_score(winner,comparable,extra_comparable) if winner else None
    runner_up_score = _candidate_score(ordered[1][1],comparable,extra_comparable) if len(ordered)>1 else None
    unresolved_tie = bool(top_score is not None and top_score==runner_up_score)
    leave_one_out=[]
    if comparable and winner:
        for seed in sorted(EXPECTED_STRESS_SEEDS):
            lo=ranking(seed)[0][1]
            leave_one_out.append({'omitted_stress_seed':seed,
                                  'winner_candidate_id':lo['candidate_id'],
                                  'changed_winner':lo['candidate_id']!=winner['candidate_id']})
    leave_one_extra_out=[]
    if extra_comparable and winner:
        for seed in fixtures.SEEDS:
            lo=ranking(omit_extra_seed=seed)[0][1]
            leave_one_extra_out.append({'omitted_extra_dev_seed':seed,
                'winner_candidate_id':lo['candidate_id'],
                'changed_winner':lo['candidate_id']!=winner['candidate_id']})
    scenario_sensitivity=any(r['changed_winner'] for r in leave_one_out+leave_one_extra_out)
    incomplete_extra=extra_present and not extra_comparable
    profiles_by_candidate=[]
    for i,c in eligible:
        stress=_stress_rows(c)
        extra=_extra_rows(c)
        profiles_by_candidate.append({
            'candidate_id':c['candidate_id'],'engine':c['engine'],
            'source_sha256':c.get('source_sha256'),
            'dev_score':c.get('dev_score'), 'dev_case_metrics':_base_rows(c),
            'stress_scenarios':[stress[s] for s in sorted(stress)],
            'extra_dev_scenarios':[extra[s] for s in sorted(extra)],
            'robust_rank_key':list(_candidate_score(c,comparable,extra_comparable)),
            'input_complete':set(stress)==EXPECTED_STRESS_SEEDS,
            'extra_dev_input_complete':set(extra)==set(fixtures.SEEDS),
            'source_order':i,
        })
    return {
        'version':VERSION,
        'status':('NO_ELIGIBLE_CANDIDATE' if not eligible else
                  'INCOMPLETE_COMPARABLE_STRESS_FALLBACK' if not comparable else
                  'INCOMPLETE_EXTRA_DEV_COHORT' if incomplete_extra else
                  ('SENSITIVE_TO_DEV_SCENARIO' if extra_comparable else 'SENSITIVE_TO_STRESS_SCENARIO') if scenario_sensitivity else
                  'TIE_UNRESOLVED_BY_DEV' if unresolved_tie else
                  'DEV_MULTICOHORT_ALIGNED' if extra_comparable else
                  'DEV_STRESS_SCENARIOS_ALIGNED'),
        'selection_uncertainty':('NO_ELIGIBLE_CANDIDATE' if not eligible else
                  'INCOMPLETE_COMPARABLE_STRESS' if not comparable else
                  'INCOMPLETE_EXTRA_DEV_COHORT' if incomplete_extra else
                  'SCENARIO_SENSITIVE' if scenario_sensitivity else
                  'TIED_WITH_ANOTHER_ELIGIBLE_CANDIDATE' if unresolved_tie else
                  'NO_SENSITIVITY_DETECTED_IN_SMALL_FIXTURES'),
        'requires_human_review_of_selection':not eligible or unresolved_tie or not comparable or incomplete_extra or scenario_sensitivity,
        'top_rank_score':list(top_score) if top_score is not None else None,
        'runner_up_rank_score':list(runner_up_score) if runner_up_score is not None else None,
        'selected_candidate_id':winner['candidate_id'] if winner else None,
        'selected_engine':winner['engine'] if winner else None,
        'selected_source_sha256':winner.get('source_sha256') if winner else None,
        'eligible_ranking':[c['candidate_id'] for _,c in ordered],
        'profiles':profiles_by_candidate,
        'comparable_stress':comparable,'stress_seeds':sorted(EXPECTED_STRESS_SEEDS),
        'extra_dev_cohort_present':extra_present,'extra_dev_comparable':extra_comparable,
        'extra_dev_seeds':list(fixtures.SEEDS),
        'leave_one_stress_out':leave_one_out,'leave_one_extra_dev_out':leave_one_extra_out,
        'dev_selection_only':True,'holdout_used_for_selection':False,
        '08f_used_for_selection':False,'post_selection_feedback_used':False,
        'policy':'Gate first. Rank eligible candidates by DEV missed, DEV unassigned, then extra DEV cohort worst missed, total missed, total unassigned, then pinned stress worst missed, total missed, total unassigned, stable order. Incomplete cohorts are excluded equally across candidates.',
        'limitations':'Four additional synthetic DEV cases plus four fixed stress cases; leave-one-out is sensitivity, NOT statistical confidence or real-world generalization. DEV case scoring is not a production SLA guarantee.'
    }
