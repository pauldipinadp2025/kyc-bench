import json
from pathlib import Path

from kycbench.scoring import score_response, pass_hat_k, decision_score
from kycbench.tools import CaseTools

ROOT = Path(__file__).resolve().parent.parent


def _gt(cid):
    return json.loads((ROOT / "answers" / cid / "ground_truth.json").read_text())


def test_perfect_response_scores_one():
    gt = _gt("onb-ind-001")
    resp = json.loads((ROOT / "examples" / "onb-ind-001.good.json").read_text())
    assert score_response(gt, resp)["total"] == 1.0


def test_missed_pep_is_capped_and_flagged():
    gt = _gt("onb-corp-001")
    resp = json.loads((ROOT / "examples" / "onb-corp-001.missed-pep.json").read_text())
    out = score_response(gt, resp)
    assert out["total"] <= 0.4
    assert "W1" in out["critical_missed"]


def test_cost_is_asymmetric():
    assert decision_score("edd", "approve") < decision_score("approve", "edd")


def test_pass_hat_k_rewards_consistency():
    assert pass_hat_k({"a": [0.9, 0.9, 0.9], "b": [0.9, 0.2, 0.9]}) == 0.5


def test_screen_name_returns_candidate_not_verdict():
    tools = CaseTools(ROOT / "cases" / "onb-ind-001")
    hits = tools.screen_name("Rohan Mehta Kulkarni")
    assert any(h["entry_id"] == "W1" for h in hits)
    assert not any(h["entry_id"] == "W2" for h in hits)
