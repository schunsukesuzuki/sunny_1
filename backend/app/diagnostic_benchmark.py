"""Fixed synthetic benchmark fixtures. Labels/oracles are NEVER passed to either model."""
from __future__ import annotations
import copy

FIXTURE_VERSION = "CLAIMS-DIAG-FIXTURES-v0.10.1"

FIXTURES = {
    "fifo_sla_conflict": {
        "title":"Correct FIFO conflicts with deadline-oriented business goal",
        "input": {
            "contract":"R0: assign claims strictly in arrival_order, earliest feasible qualified reviewer/day.",
            "independent_implementation_test":"PASS: R0 matches specified FIFO, reviewer qualifications, capacities, case durations.",
            "business_goal":"Reduce missed deadlines without increasing total staffed hours.",
            "synthetic_dev_observation":"On identical synthetic cases and 87 reviewer-hours, FIFO misses 11 deadlines; independent deadline-priority reference misses 0. Reference is a heuristic, not proven optimal.",
            "evidence":[{"evidence_id":"SIM-SLA-001", "provenance":"synthetic", "observation":"Later arriving urgent claim can be missed under FIFO while an earlier arrival with a later deadline is scheduled first."}],
            "real_customer_interviews":[], "legal_source_material":[],
        },
        "oracle":{"classification":"requirement_mismatch","implementation_assessment":"correct",
                  "synthetic_requirement_fit":"mismatch","expected_evidence_ids":["SIM-SLA-001"]},
    },
    "correct_fifo_no_customer_evidence": {
        "title":"Correct FIFO but unknown customer business validity",
        "input": {
            "contract":"R0: assign cases strictly in arrival order, earliest feasible qualified reviewer/day.",
            "independent_implementation_test":"PASS: implementation matches FIFO requirements and fixed technical constraints.",
            "business_goal":"Unspecified; the customer has not prioritized deadlines, costs or fairness.",
            "synthetic_dev_observation":"No comparative business KPI was measured.",
            "evidence":[], "real_customer_interviews":[], "legal_source_material":[],
        },
        "oracle":{"classification":"insufficient_evidence","implementation_assessment":"correct",
                  "synthetic_requirement_fit":"unverified","expected_evidence_ids":[]},
    },
    "actual_fifo_implementation_bug": {
        "title":"Implementation violates a correctly specified FIFO requirement",
        "input": {
            "contract":"R0: strictly process arrival_order; earliest eligible qualified reviewer/day.",
            "independent_implementation_test":"FAIL: independent deterministic order check shows R0 implementation violates FIFO.",
            "business_goal":"Follow the stated FIFO queue for this test. No deadline-reduction requirement was supplied.",
            "synthetic_dev_observation":"Reviewer R-A can process both cases on day 0. C001 arrival_order=1, C002 arrival_order=2, but code schedules C002 before C001 solely because C002 has a larger amount. Both are otherwise equally feasible.",
            "evidence":[{"evidence_id":"SIM-BUG-001","provenance":"synthetic_implementation_trace","observation":"Generated schedule inverted two feasible FIFO cases."}],
            "real_customer_interviews":[], "legal_source_material":[],
        },
        "oracle":{"classification":"implementation_bug","implementation_assessment":"incorrect",
                  "synthetic_requirement_fit":"unverified","expected_evidence_ids":["SIM-BUG-001"]},
    },
    "conflicting_stakeholder_notes": {
        "title":"Conflicting synthetic stakeholder requirements without an objective comparator",
        "input": {
            "contract":"R0: assign claims in arrival_order; no validated business KPI hierarchy.",
            "independent_implementation_test":"PASS: FIFO is implemented according to contract.",
            "business_goal":"The ordering preference across departments is unknown.",
            "synthetic_dev_observation":"No controlled comparison of SLA, cost or fairness. Evidence is conflicting hypothetical comments, not verified customer research.",
            "evidence":[
                {"evidence_id":"SIM-STAKE-001","provenance":"synthetic", "observation":"One imaginary claims manager wants urgent deadlines first."},
                {"evidence_id":"SIM-STAKE-002","provenance":"synthetic", "observation":"Another imaginary claims manager insists on FIFO to avoid discretionary priority."},
            ],
            "real_customer_interviews":[], "legal_source_material":[],
        },
        "oracle":{"classification":"insufficient_evidence","implementation_assessment":"correct",
                  "synthetic_requirement_fit":"unverified","expected_evidence_ids":["SIM-STAKE-001","SIM-STAKE-002"]},
    },
}


def public_cases():
    return [{"id":i, "title":x["title"],"input":copy.deepcopy(x["input"])} for i,x in FIXTURES.items()]
