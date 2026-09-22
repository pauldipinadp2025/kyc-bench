"""
KYC-Bench review server.

Two endpoints:
  POST /review          -- run a case (a built-in demo case, or free text)
                            through Claude against the currently active
                            policy, and score the response.
  GET  /policy           -- the currently active policy (text + version).
  POST /policy            -- upload a new policy version. Requires the
                            X-Admin-Key header to match ADMIN_KEY.
  GET  /policy/versions   -- history of uploaded policy versions.

Policy storage: storage/policies.json, a flat JSON file with a list of
versions and which one is "active". This is intentionally simple -- a
real deployment with a large policy manual would swap this file-based
store for a proper database plus a vector index for retrieval, without
changing the shape of these endpoints.
"""

import json
import os
import re
import time
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*")

STORAGE_DIR = Path(__file__).parent / "storage"
POLICY_FILE = STORAGE_DIR / "policies.json"

app = Flask(__name__)
CORS(app, origins=[o.strip() for o in ALLOWED_ORIGINS.split(",")])


# ---------------------------------------------------------------------------
# Demo cases (same content as the toolkit's front end, kept here so /review
# can score a known case without the client having to send ground truth).
# ---------------------------------------------------------------------------

DEMO_CASES = {
    "onb-ind-001": {
        "brief": (
            "Customer: Rohan Mehta Kulkarni, individual, DOB 1991-03-14, Indian "
            "national. Passport SYN-P-00417 valid to 2031-08-02. Utility bill "
            "dated 2026-07-28, same address. Watchlist screen returns a partial "
            "name match to a PEP entry: \"Rohan Mehta\", DOB 1962-11-05, "
            "Canadian nationality."
        ),
        "ground": {
            "decision": "approve",
            "risk_rating": "low",
            "required_evidence": ["passport", "utility bill", "watchlist hit"],
            "critical_evidence": ["watchlist hit"],
            "required_rules": ["P-1.1", "P-1.2", "P-2.1", "P-2.2", "P-5.1"],
        },
    },
    "onb-corp-001": {
        "brief": (
            "Customer: Sahyadri Agro Exports Pvt Ltd. Registry: Sahyadri is 60% "
            "owned by Nirmal Holdings LLP; Nirmal Holdings is 50% owned by Blue "
            "Harbour Ltd (offshore); Blue Harbour's shares are held by a nominee "
            "(Trident Nominee Services Ltd) on behalf of an undisclosed principal "
            "per filing R7. That principal is Karan Vaidya, DOB 1969-09-09, "
            "Indian. Watchlist screen returns a PEP match for Karan Vaidya on "
            "name, DOB and nationality."
        ),
        "ground": {
            "decision": "edd",
            "risk_rating": "high",
            "required_evidence": ["registry chain", "nominee filing", "watchlist hit"],
            "critical_evidence": ["nominee filing", "watchlist hit"],
            "required_rules": ["P-2.1", "P-3.1", "P-3.2", "P-4.1", "P-5.1"],
        },
    },
}

DEFAULT_POLICY_TEXT = """\
P-1.1: Identity must be verified with a valid, unexpired government photo ID.
P-1.2: Address must be confirmed by a document dated within the last 3 months.
P-2.1: Every customer and beneficial owner must be screened against sanctions/PEP lists.
P-2.2: A name match clears as a false positive only if two identifiers (DOB, nationality, ID) differ.
P-3.1: A beneficial owner holds 25%+ directly or indirectly (multiply percentages along the chain).
P-3.2: A nominee or undisclosed principal anywhere in the chain requires Enhanced Due Diligence.
P-4.1: A beneficial owner who is a PEP requires EDD and senior approval.
P-4.2: A confirmed sanctions match means reject.
P-5.1: Risk rating is Low, Medium or High. Any EDD trigger means High.
"""


# ---------------------------------------------------------------------------
# Policy storage
# ---------------------------------------------------------------------------

def _load_policy_store():
    if not POLICY_FILE.exists():
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        seed = {
            "active_id": "seed",
            "versions": [
                {
                    "id": "seed",
                    "title": "Synthetic demo policy (v0.1)",
                    "text": DEFAULT_POLICY_TEXT,
                    "uploaded_at": time.time(),
                }
            ],
        }
        POLICY_FILE.write_text(json.dumps(seed, indent=2), encoding="utf-8")
        return seed
    return json.loads(POLICY_FILE.read_text(encoding="utf-8"))


def _save_policy_store(store):
    POLICY_FILE.write_text(json.dumps(store, indent=2), encoding="utf-8")


def _active_policy_text():
    store = _load_policy_store()
    active_id = store["active_id"]
    for v in store["versions"]:
        if v["id"] == active_id:
            return v["text"], v
    return DEFAULT_POLICY_TEXT, None


# ---------------------------------------------------------------------------
# Claude call
# ---------------------------------------------------------------------------

def _call_claude(prompt: str) -> dict:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set on the server")

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    text = "\n".join(
        block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
    )
    text = re.sub(r"```json|```", "", text).strip()
    return _parse_tolerant(text)


def _parse_tolerant(raw: str) -> dict:
    start = raw.find("{")
    if start == -1:
        raise ValueError("no JSON object found in the reply")
    s = raw[start:]
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        last_close = s.rfind("}")
        if last_close == -1:
            raise ValueError("unrecoverable JSON in the reply")
        attempt = s[: last_close + 1]

        def depth(text):
            d, in_str, esc = 0, False, False
            for ch in text:
                if esc:
                    esc = False
                    continue
                if ch == "\\":
                    esc = True
                    continue
                if ch == '"':
                    in_str = not in_str
                if in_str:
                    continue
                if ch in "{[":
                    d += 1
                if ch in "}]":
                    d -= 1
            return d

        guard = 0
        while depth(attempt) > 0 and guard < 40:
            attempt += "]" if attempt.rfind("[") > attempt.rfind("{") else "}"
            guard += 1
        return json.loads(attempt)


def _build_prompt(policy_text: str, case_brief: str) -> str:
    return (
        "You are reviewing a KYC/AML case for a bank against the policy below. "
        "Reply with ONLY a JSON object, no other text, matching exactly this shape:\n"
        '{"decision":"approve|edd|reject|file_str","risk_rating":"low|medium|high",'
        '"evidence":["short phrases naming what you relied on"],'
        '"rules":["policy rule IDs you applied, e.g. P-2.2"],'
        '"file_note":"a short note an auditor could follow"}\n\n'
        f"POLICY:\n{policy_text}\n\nCASE:\n{case_brief}"
    )


# ---------------------------------------------------------------------------
# Scoring (demo-grade: loose keyword recall, mirrors kycbench/scoring.py's
# cost matrix and critical-miss cap; a deployment using structured case
# files with real evidence IDs should use kycbench/scoring.py directly)
# ---------------------------------------------------------------------------

DECISIONS = ("approve", "edd", "reject", "file_str")
RATINGS = ("low", "medium", "high")
COST = {
    "approve": {"approve": 0.0, "edd": 0.2, "reject": 0.5, "file_str": 0.6},
    "edd": {"approve": 1.0, "edd": 0.0, "reject": 0.3, "file_str": 0.3},
    "reject": {"approve": 1.0, "edd": 0.4, "reject": 0.0, "file_str": 0.2},
    "file_str": {"approve": 1.0, "edd": 0.5, "reject": 0.4, "file_str": 0.0},
}
WEIGHTS = {"decision": 0.50, "evidence": 0.20, "rules": 0.15, "risk_rating": 0.15}


def _decision_score(truth, pred):
    if pred not in DECISIONS:
        return 0.0
    return 1.0 - COST[truth][pred]


def _rating_score(truth, pred):
    if pred not in RATINGS:
        return 0.0
    return 1.0 - abs(RATINGS.index(truth) - RATINGS.index(pred)) / (len(RATINGS) - 1)


def _f1(required, found):
    req = {str(x).lower() for x in required}
    fnd = {str(x).lower() for x in found or []}
    if not req and not fnd:
        return 1.0
    hit = len(req & fnd)
    if hit == 0:
        return 0.0
    p, r = hit / len(fnd), hit / len(req)
    return 2 * p * r / (p + r)


def _keyword_hit(phrase: str, haystack: str) -> bool:
    return phrase.lower() in haystack.lower()


def _score_response(ground: dict, resp: dict) -> dict:
    haystack = " ".join(resp.get("evidence") or []) + " " + (resp.get("file_note") or "")

    d = _decision_score(ground["decision"], resp.get("decision"))
    rt = _rating_score(ground["risk_rating"], resp.get("risk_rating"))
    req_ev = ground["required_evidence"]
    ev_hits = sum(1 for phrase in req_ev if _keyword_hit(phrase, haystack))
    ev = ev_hits / len(req_ev) if req_ev else 1.0
    ru = _f1(ground["required_rules"], resp.get("rules"))

    critical_missed = [
        phrase for phrase in ground["critical_evidence"] if not _keyword_hit(phrase, haystack)
    ]

    total = (
        WEIGHTS["decision"] * d
        + WEIGHTS["evidence"] * ev
        + WEIGHTS["rules"] * ru
        + WEIGHTS["risk_rating"] * rt
    )
    if critical_missed:
        total = min(total, 0.40)

    return {
        "decision": round(d, 3),
        "evidence": round(ev, 3),
        "rules": round(ru, 3),
        "risk_rating": round(rt, 3),
        "critical_missed": critical_missed,
        "total": round(total, 3),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})


@app.route("/review", methods=["POST"])
def review():
    body = request.get_json(silent=True) or {}
    case_id = body.get("case_id")
    custom_brief = body.get("brief")

    if case_id:
        case = DEMO_CASES.get(case_id)
        if not case:
            return jsonify({"error": f"unknown case_id '{case_id}'"}), 400
        brief = case["brief"]
    elif custom_brief:
        case = None
        brief = str(custom_brief)[:4000]
    else:
        return jsonify({"error": "send either case_id or brief"}), 400

    policy_text, _ = _active_policy_text()
    prompt = _build_prompt(policy_text, brief)

    try:
        agent_response = _call_claude(prompt)
    except requests.HTTPError as e:
        # Log the real cause server-side only -- never echo the upstream
        # provider's URL or error body back to the browser.
        app.logger.error("review upstream error: %s", e)
        return jsonify({"error": "The reviewer is temporarily unavailable. Try again shortly."}), 502
    except ValueError as e:
        app.logger.error("review parse error: %s", e)
        return jsonify({"error": "Got an unreadable response. Try again."}), 502
    except Exception as e:  # noqa: BLE001
        app.logger.error("review error: %s", e)
        return jsonify({"error": "Something went wrong running the review. Try again shortly."}), 502

    result = {"response": agent_response}
    if case:
        result["score"] = _score_response(case["ground"], agent_response)
    return jsonify(result)


@app.route("/policy", methods=["GET"])
def get_policy():
    text, meta = _active_policy_text()
    return jsonify({"text": text, "version": meta})


@app.route("/policy/versions", methods=["GET"])
def policy_versions():
    store = _load_policy_store()
    versions = [{k: v[k] for k in ("id", "title", "uploaded_at")} for v in store["versions"]]
    return jsonify({"active_id": store["active_id"], "versions": versions})


@app.route("/policy", methods=["POST"])
def upload_policy():
    if not ADMIN_KEY or request.headers.get("X-Admin-Key") != ADMIN_KEY:
        return jsonify({"error": "missing or invalid X-Admin-Key header"}), 401

    body = request.get_json(silent=True) or {}
    text = body.get("text")
    title = body.get("title") or "Untitled policy"
    if not text or not text.strip():
        return jsonify({"error": "send { text, title } with a non-empty text field"}), 400

    store = _load_policy_store()
    new_id = uuid.uuid4().hex[:12]
    store["versions"].append(
        {"id": new_id, "title": title, "text": text, "uploaded_at": time.time()}
    )
    store["active_id"] = new_id
    _save_policy_store(store)
    return jsonify({"ok": True, "active_id": new_id})


@app.route("/policy/activate/<version_id>", methods=["POST"])
def activate_policy(version_id):
    if not ADMIN_KEY or request.headers.get("X-Admin-Key") != ADMIN_KEY:
        return jsonify({"error": "missing or invalid X-Admin-Key header"}), 401

    store = _load_policy_store()
    ids = [v["id"] for v in store["versions"]]
    if version_id not in ids:
        return jsonify({"error": f"unknown version id '{version_id}'"}), 404
    store["active_id"] = version_id
    _save_policy_store(store)
    return jsonify({"ok": True, "active_id": version_id})


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
