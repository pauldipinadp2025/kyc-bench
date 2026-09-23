# Contributing

Thanks for helping. The most useful contributions right now are new cases and expert review.

## Adding a case

1. Make a folder `cases/<id>/` with `case.json` and any watchlist or registry files. Look at `onb-corp-001` for the format.
2. Make `answers/<id>/ground_truth.json` with the decision, risk rating, required and critical evidence, required rules and traps.
3. Every ground-truth answer must follow from `policy/synthetic_bank_policy.md`. If it needs a rule that is not there, propose the rule in the same pull request.
4. Run `kycbench validate` and `pytest`.

## Hard rules

- **Synthetic only.** No real people, customers, accounts or company records. No text copied from a real bank's policy or from any employer's internal material.
- No real personal data of any kind, including yours.
- Do not put ground truth or answer hints inside `cases/`.

## Expert reviewers

If you work in compliance, the best thing you can do is read a case and its ground truth and tell us where a working analyst would disagree. Open an issue with the label `expert-review`.
