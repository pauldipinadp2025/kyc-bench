from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .scoring import DECISIONS, RATINGS, score_response

ROOT = Path.cwd()


def _cases():
    return sorted(p.parent.name for p in (ROOT / "cases").glob("*/case.json"))


def cmd_validate(_args) -> int:
    """Check every case has ground truth and that ground truth is well formed."""
    problems = []
    for cid in _cases():
        gt_path = ROOT / "answers" / cid / "ground_truth.json"
        if not gt_path.exists():
            problems.append(f"{cid}: missing ground_truth.json")
            continue
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        if gt.get("decision") not in DECISIONS:
            problems.append(f"{cid}: bad decision")
        if gt.get("risk_rating") not in RATINGS:
            problems.append(f"{cid}: bad risk_rating")
        for key in ("required_evidence", "required_rules", "critical_evidence"):
            if key not in gt:
                problems.append(f"{cid}: missing {key}")
        crit, req = set(gt.get("critical_evidence", [])), set(gt.get("required_evidence", []))
        if not crit <= req:
            problems.append(f"{cid}: critical_evidence must be a subset of required_evidence")
    for p in problems:
        print("PROBLEM:", p)
    print(f"{len(_cases())} cases checked, {len(problems)} problems")
    return 1 if problems else 0


def cmd_score(args) -> int:
    gt = json.loads((ROOT / "answers" / args.case / "ground_truth.json").read_text(encoding="utf-8"))
    resp = json.loads(Path(args.response).read_text(encoding="utf-8"))
    print(json.dumps(score_response(gt, resp), indent=2))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="kycbench")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate", help="check cases and ground truth").set_defaults(fn=cmd_validate)
    sc = sub.add_parser("score", help="score one response file")
    sc.add_argument("--case", required=True)
    sc.add_argument("--response", required=True)
    sc.set_defaults(fn=cmd_score)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
