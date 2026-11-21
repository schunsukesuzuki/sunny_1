"""Explicitly separate, deterministic claim-progress-notification prototype.

Only fake event fixtures. The candidate function implements an example policy;
it is NOT derived from an LLM or the public documents and NOT integrated to R1.
"""
from __future__ import annotations

VERSION='CLAIM-NOTIFICATION-PROTOTYPE-v0.19.0'
EVENTS=[
  {'event_id':'EV-001','claim_id':'C-001','policyholder_id':'P-001','changed_at_hour':0,'status':'RECEIVED'},
  {'event_id':'EV-002','claim_id':'C-001','policyholder_id':'P-001','changed_at_hour':9,'status':'IN_REVIEW'},
  {'event_id':'EV-003','claim_id':'C-002','policyholder_id':'P-002','changed_at_hour':2,'status':'RECEIVED'},
  {'event_id':'EV-004','claim_id':'C-002','policyholder_id':'P-002','changed_at_hour':23,'status':'NEEDS_DOCUMENT'},
]


def prototype_notifications(events:list[dict])->list[dict]:
    """Prototype behavior under test: dispatch each status-change at +1 hour."""
    return [{'event_id':e['event_id'], 'claim_id':e['claim_id'],
             'recipient_id':e['policyholder_id'],'sent_at_hour':e['changed_at_hour']+1,
             'status':e['status']} for e in events]


def evaluate_notifications(events:list[dict], notices:list[dict], *,max_delay_hours:int,
                           min_coverage_pct:int)->dict:
    """Independent deterministic oracle; rejects duplicates, recipient errors and late/missing notices."""
    event_by={e['event_id']:e for e in events}
    ids=[n.get('event_id') for n in notices]
    errors=[]
    if len(event_by)!=len(events):errors.append('Duplicate fixture event IDs')
    if len(ids)!=len(set(ids)): errors.append('Duplicate notifications for same event')
    if any(i not in event_by for i in ids): errors.append('Notification refers to non-existent event')
    on_time=0;correct_recipient=True;accurate_status=True;all_sent_timely=True
    for n in notices:
        e=event_by.get(n.get('event_id'))
        if not e:continue
        if n.get('recipient_id')!=e['policyholder_id'] or n.get('claim_id')!=e['claim_id']:
            correct_recipient=False
        if n.get('status')!=e['status']:accurate_status=False
        delay=n.get('sent_at_hour',-100)-e['changed_at_hour']
        if isinstance(delay,(int,float)) and 0<=delay<=max_delay_hours:on_time+=1
        else:all_sent_timely=False
    cov=100*on_time/len(events) if events else 0
    tests={
      'notifications_correspond_to_status_changes':bool(ids) and set(ids).issubset(set(event_by)),
      'all_sent_within_max_delay':all_sent_timely,
      'coverage_threshold':cov>=min_coverage_pct,
      'correct_policyholder':correct_recipient,
      'status_matches_event':accurate_status,
      'no_duplicate_or_spurious_notices':not errors,
    }
    return {'synthetic_pass':all(tests.values()),'checks':tests,'errors':errors,
            'coverage_pct':round(cov,2),'event_count':len(events),'notice_count':len(notices),
            'max_delay_hours':max_delay_hours,'min_coverage_pct':min_coverage_pct}


def evaluate_prototype(*, max_delay_hours:int=24,min_coverage_pct:int=100)->dict:
    candidate=prototype_notifications(EVENTS)
    res=evaluate_notifications(EVENTS,candidate,max_delay_hours=max_delay_hours,
                                min_coverage_pct=min_coverage_pct)
    # Negative controls prove the oracle rejects broken coverage and wrong recipient.
    no_notice=evaluate_notifications(EVENTS,[],max_delay_hours=max_delay_hours,
                                      min_coverage_pct=min_coverage_pct)
    wrong=[dict(x) for x in candidate];wrong[0]['recipient_id']='WRONG-PERSON'
    wrong_result=evaluate_notifications(EVENTS,wrong,max_delay_hours=max_delay_hours,
                                        min_coverage_pct=min_coverage_pct)
    oracle_controls={'missing_notices_rejected':not no_notice['synthetic_pass'],
                     'wrong_recipient_rejected':not wrong_result['synthetic_pass']}
    passed=bool(res['synthetic_pass'] and all(oracle_controls.values()))
    return {'version':VERSION,'status':'SUPPORTED_SYNTHETIC_PROTOTYPE' if passed else 'HOLD',
            'synthetic_pass':passed,'prototype_source':'app.notification_demo.prototype_notifications',
            'implementation_origin':'PREBUILT_DETERMINISTIC_EXAMPLE_NOT_LLM_GENERATED',
            'events':EVENTS,'candidate_notifications':candidate,'evaluation':res,
            'negative_controls':oracle_controls,
            'scope':'STANDALONE_SYNTHETIC_NOTIFICATION_PROTOTYPE',
            'is_R1_assignment_implementation':False,'customer_integration':'NOT_IMPLEMENTED',
            'customer_acceptance':'NOT_OBTAINED','production_go':False,
            'note':'A deterministic prototype can pass its own independent acceptance oracle; it does not evaluate generated R1 or prove real-world service delivery.'}
