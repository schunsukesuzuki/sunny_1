# v0.21.1 — Evidence Review (00b) validation guidance

## Root cause of the reported 422

The API returns `Assignment hypothesis must describe an insurance claim delay, deadline, or processing problem.` if `requirement_type=claims_assignment` and the approved hypothesis has no claim delay/deadline/processing wording. v0.21 initialized the UI with `claims_assignment`, even when the user edited the hypothesis to a notification feature. This was a UX mismatch, not a dataset-download or RAG indexing failure.

## Changed

- The frontend starts without a selected feature; approval is disabled until the user chooses one.
- The text is checked against the same feature keywords as the Python classifier for UI hints. A nonmatching feature, mixed feature or missing assignment time/processing context blocks submit with an actionable message. The server remains authoritative.
- Example texts for reviewer assignment and claim progress notification are shown. API 422 errors include a Japanese correction suggestion.
- An LLM-proposed feature is never formally approved by auto-selection; the user must still review the text, selected citations, support assessment, and acknowledgment.

## Expected behavior

- `保険請求の進捗を契約者に通知する` + `claim_progress_updates` maps to the standalone notification prototype, not the R1 assignment KPI.
- `保険請求処理の期限超過を減らすため、資格と容量を考慮して担当者を割り当てる` + `claims_assignment` maps to R1 synthetic allocation evaluation.
- Notification text with assignment selected or vice versa is rejected. A published source's account of claims delays does not validate assignment causality or real customer requirements.

## Limitations

The preview classification is lexical and may not understand synonyms; it is not evidence semantic validation. If the UI preview and backend differ, the backend result is authoritative. No independent end-to-end browser build or real Ollama/E2B/remote-data call is asserted here.
