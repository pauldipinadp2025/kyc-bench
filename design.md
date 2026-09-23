# Design notes

## Task types

1. **Individual onboarding** (about 30 min expert time): verify documents, screen the name, clear or escalate matches, set a rating.
2. **Corporate onboarding** (about 2 hrs): trace beneficial owners through layers, apply the ownership threshold, catch nominee structures, decide on EDD.
3. **Transaction alert review** (about 2-3 hrs): read months of account activity, separate structuring from normal patterns, decide whether to file a report. *Not built yet.*
4. **Periodic refresh** : reconcile old records against new adverse information. *Not built yet.*

## Traps

Each case lists its traps in `ground_truth.json`. Current ones: `name_near_match`, `layered_ownership`, `nominee_structure`, `hidden_pep`. Planned: `circular_ownership`, `expired_document`, `address_mismatch`, `structuring_pattern`.

## Why a synthetic policy

Real regulations leave room for interpretation, and that would make ground truth arguable. A short invented policy keeps every answer checkable. Later versions can add policy variants modelled on different regimes, so the same case can be judged under different rulebooks.

## Contamination

Public cases can end up in training data. Plan: release a public dev set, keep a private test set, and generate fresh variants of cases (new names, amounts, structures) so scores can be compared across versions.

## Faithfulness check (planned)

For each case, make a version where a key piece of evidence is removed or changed. If the agent's decision changes, its explanation should change in the same direction. If the decision changes but the explanation still cites the old evidence, the stated reasoning is not what drove the answer.

## Cost

Report cost per case (tokens and tool calls) next to expert time per case, so results can be read as economics and not only accuracy.
