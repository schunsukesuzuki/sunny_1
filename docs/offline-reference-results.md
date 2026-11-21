# v0.8 Synthetic reference benchmark (local deterministic check)

> These results come from local deterministic Python references, **not** from E2B/Qwen runs. R1 Qwen candidate is not scored here.

| seed | FIFO missed | Deadline-first missed | FIFO worked hours | Deadline-first worked hours | all constraints pass |
|---:|---:|---:|---:|---:|---|
|42|3|0|28|28|True|
|43|4|0|31|31|True|
|44|4|0|28|28|True|
|10042|3|0|33|33|True|
|10043|5|0|31|31|True|
|142|4|0|31|31|True|
|143|4|0|32|32|True|
|20142|3|0|31|31|True|
|20143|5|0|31|31|True|

Each seed changes case durations, deadlines and EUR amounts. The fixed reviewer-day capacity is identical between both methods.

This benchmark is a controlled counterexample: FIFO can perfectly implement R0 while missing deadlines. It is not proof of customer benefit or robustness to real claims distributions.

To evaluate a generated R1 implementation, run the UI workflow with actual E2B and macOS Ollama.
