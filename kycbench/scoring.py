"""Deterministic, risk-weighted scoring for KYC-Bench.

The file note is NOT scored here. It is graded separately by expert or
LLM-judge rubrics (see docs/rubric.md).
"""
from __future__ import annotations

DECISIONS = ("approve", "edd", "reject", "file_str")
RATINGS = ("low", "medium", "high")

# Cost of predicting `pred` when the truth is `truth`, from 0 (fine) to 1 (worst).
# Under-reacting to risk costs far more than over-reacting. That asymmetry is
# the point of this benchmark, so it is written out here in the open.
COST = {
    "approve":  {"approve": 0.0, "edd": 0.2, "reject": 0.5, "file_str": 0.6},
    "edd":      {"approve": 1.0, "edd": 0.0, "reject": 0.3, "file_str": 0.3},
    "reject":   {"approve": 1.0, "edd": 0.4, "reject": 0.0, "file_str": 0.2},
    "file_str": {"approve": 1.0, "edd": 0.5, "reject": 0.4, "file_str": 0.0},
}

WEIGHTS = {"decision": 0.50, "evidence": 0.20, "rules": 0.15, "risk_rating": 0.15}
CRITICAL_MISS_CAP = 0.40


def decision_score(truth: str, pred: str) -> float:
    if pred not in DECISIONS:
        return 0.0
    return 1.0 - COST[truth][pred]


def rating_score(truth: str, pred: str) -> float:
    if pred not in RATINGS:
        return 0.0
    return 1.0 - abs(RATINGS.index(truth) - RATINGS.index(pred)) / (len(RATINGS) - 1)


def _recall(required, found) -> float:
    required, found = set(required), set(found)
    return 1.0 if not required else len(required & found) / len(required)


def _f1(required, found) -> float:
    required, found = set(required), set(found)
    if not required and not found:
        return 1.0
    hit = len(required & found)
    if hit == 0:
        return 0.0
    p, r = hit / len(found), hit / len(required)
    return 2 * p * r / (p + r)


def score_response(truth: dict, response: dict) -> dict:
    """Score one agent response against one ground-truth record."""
    d = decision_score(truth["decision"], response.get("decision", ""))
    rt = rating_score(truth["risk_rating"], response.get("risk_rating", ""))
    ev = _recall(truth["required_evidence"], response.get("evidence", []))
    ru = _f1(truth["required_rules"], response.get("rules", []))

    critical_missed = sorted(
        set(truth.get("critical_evidence", [])) - set(response.get("evidence", []))
    )
    total = (
        WEIGHTS["decision"] * d
        + WEIGHTS["evidence"] * ev
        + WEIGHTS["rules"] * ru
        + WEIGHTS["risk_rating"] * rt
    )
    if critical_missed:
        total = min(total, CRITICAL_MISS_CAP)

    return {
        "case_id": truth["case_id"],
        "decision": round(d, 3),
        "evidence_recall": round(ev, 3),
        "rules_f1": round(ru, 3),
        "risk_rating": round(rt, 3),
        "critical_missed": critical_missed,
        "total": round(total, 3),
    }


def pass_hat_k(scores_by_task: dict, threshold: float = 0.8) -> float:
    """Fraction of tasks where EVERY one of the k runs scored >= threshold.

    This measures reliability, not average accuracy. An agent that gets a task
    right 3 times out of 5 has a good mean but a bad pass^5.
    """
    if not scores_by_task:
        return 0.0
    ok = sum(1 for runs in scores_by_task.values() if runs and min(runs) >= threshold)
    return ok / len(scores_by_task)
