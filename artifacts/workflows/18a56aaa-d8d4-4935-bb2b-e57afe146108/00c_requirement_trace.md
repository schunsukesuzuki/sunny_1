# Evidence → Requirement → Feature → Acceptance Trace (v0.19)

- Public evidence: PUB-006
- Requirement: Insurers must identify and adapt communication for vulnerable consumers early in the claims process
- Type: `claim_progress_updates` / Feature: `FEATURE-CLAIM-PROGRESS-NOTIFICATION`
- Human template mapping: `TEMPLATE_MAPPED_HUMAN_SELECTED`
- Target: `separate_deterministic_notification_prototype` (not the same as the published source)
- Reviewer: Technical reviewer (demo)

## KPI and acceptance tests

- KPI: `notification_coverage_pct`
- KPI: `maximum_status_update_delay_hours`
- KPI: `no_wrong_recipient`
- Acceptance test: `NOTIFY-ON-STATUS-CHANGE`
- Acceptance test: `NOTIFY-WITHIN-THRESHOLD`
- Acceptance test: `NOTIFY-CORRECT-RECIPIENT`
- Acceptance test: `NEGATIVE-CONTROL-NO-UPDATE`

## Proof boundary

- Citation exists ≠ citation supports claim ≠ requirement is correct.
- Public issue does not prove FIFO causality or customer-approved SLA.
- Scheduling R1 cannot satisfy a claim-progress notification requirement.
- The notification prototype is separate and not deployed or connected to customers.
