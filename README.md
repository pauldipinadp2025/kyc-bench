# KYC-Bench

An open benchmark for testing whether AI agents can handle KYC/AML case reviews, the work banks do to check who their customers are and whether account activity looks suspicious.

> **Status: early draft (v0.1).** Two example cases, a scoring module and a policy. This is the starting point, not a finished benchmark. Contributions welcome.

## Why this exists

Compliance review is high-volume, expert-heavy work, and it is a hard format for agents. One case means reading several documents, checking registries, applying a rulebook, and writing a note an auditor could follow. Two things make it different from most evals:

- **Mistakes are not equal.** Missing a sanctions match or a hidden owner costs far more than a false alarm. Plain accuracy hides that, so scoring here is risk-weighted.
- **The explanation matters.** A correct decision with a wrong reason is not safe to rely on. We want to check whether the stated reasoning matches the evidence that actually drove the decision.

## How a case works

Each case is a folder with synthetic documents, a watchlist, sometimes a company registry, and a case description. The agent reads the case, uses the mock tools, and returns a JSON response (see `schema/response.schema.json`):

```json
{
  "decision": "approve | edd | reject | file_str",
  "risk_rating": "low | medium | high",
  "evidence": ["D1", "W1"],
  "rules": ["P-2.2"],
  "file_note": "Short note an auditor could follow."
}
```

Cases are graded against an invented bank policy in `policy/`, not against a real regulation. That way the right answer is always known and nobody has to argue about how a real rule should be read.

## What is in the repo

| Path | What it holds |
|------|---------------|
| `cases/` | What the agent sees: documents, watchlist, registry |
| `answers/` | Ground truth. Kept out of the agent's view. |
| `policy/` | The synthetic bank policy every case is graded against |
| `kycbench/` | Scoring, mock tools, CLI |
| `schema/` | JSON schema for agent responses |
| `examples/` | A good response and a bad one, used in tests |
| `docs/` | Design notes and grading rubric |

## Quick start

```bash
pip install -e ".[dev]"
kycbench validate                      # check all cases and ground truth
kycbench score --case onb-corp-001 --response examples/onb-corp-001.missed-pep.json
pytest
```

## How scoring works

Automatic part (`kycbench/scoring.py`):

- **Decision**, weighted by cost. Approving something that needed EDD scores 0. Sending a clean case to EDD only loses a little.
- **Evidence recall** and **rule F1**.
- **Risk rating** distance.
- **Critical-miss cap.** If the agent misses a critical piece of evidence (a PEP match, a nominee filing), the total is capped at 0.40 however good the rest is.
- **pass^k** for reliability: the share of tasks where all k runs scored above a threshold.

Human or LLM-judge part (`docs/rubric.md`): file-note quality and whether the stated reasoning matches the evidence.

## Roadmap

- [ ] Grow to about 40 cases across all four task types
- [ ] Transaction-alert cases (structuring vs seasonal cash flow)
- [ ] Periodic-refresh cases with conflicting evidence
- [ ] Policy variants for India, UK and US style regimes, to test if performance carries over
- [ ] Case generator with controllable traps
- [ ] Faithfulness test: change the planted evidence and check whether the explanation follows
- [ ] Expert review of rubrics and inter-rater agreement
- [ ] Runner for common model APIs
- [ ] Private held-out test split to limit contamination

## Ground rules

- **Everything is synthetic.** No real customer data, no real bank policy documents, no confidential material from any employer. Names, IDs and companies are invented.
- This project is for research on AI evaluation. It is not compliance advice.
- Please do not train on the public ground truth and then report results on the same cases.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Code: MIT. If you add a dataset licence for the case files, note it here (CC BY 4.0 is a common choice).
