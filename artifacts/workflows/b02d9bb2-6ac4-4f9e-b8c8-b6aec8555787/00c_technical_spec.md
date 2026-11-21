# Human-configured evidence-to-experiment test contract — v0.18

## Scope and origin
- Published problem context is not a customer-approved requirement.
- Human-edited hypothesis: Insurers must provide clear and timely updates on claim progress
- Public evidence pointers: PUB-003, PUB-006
- Executable target: fixed synthetic insurance claims assignment, **not** the published case.
- Data model, assignment code, and oracle are NOT generated from the natural-language hypothesis.

## Decision criteria (human-selected, machine-checked)

- Total missed deadlines INCLUDING unassigned cases <= **0**
- Reduction against FIFO >= **50%**
- Require synthetic behavioral probes: **True**
- Enforce assigned hours equality, valid reviewer qualifications and capacity constraints.

## Known uncertainty

Topic relevance ≠ evidence support ≠ requirements correctness.
No public source proves that the above scheduling thresholds or FIFO assumptions describe real customer operations.
An independent real-data evaluation contract requires customer datasets, agreed acceptance tests and additional validators.
