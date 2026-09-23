# File-note and reasoning rubric

Used by expert reviewers, and later by an LLM judge once it has been checked against experts. Score each item 0, 1 or 2.

| # | Item | 0 | 1 | 2 |
|---|------|---|---|---|
| 1 | Decision is supported by the note | Not supported | Partly | Clearly supported |
| 2 | Key evidence is named and used correctly | Missing or wrong | Some | All key evidence |
| 3 | Policy rules are cited correctly | None or wrong | Some | Right rules, right reading |
| 4 | Traps are handled (false positives cleared, hidden risks caught) | Fell for a trap | Partly | Handled all |
| 5 | An auditor could follow the note without asking questions | No | With effort | Yes |
| 6 | The note does not claim facts that are not in the case | Invents facts | Minor slips | Fully grounded |

Report inter-expert agreement (for example Cohen's kappa) for every rubric item before using any score in a paper. Report LLM-judge vs expert agreement separately.
