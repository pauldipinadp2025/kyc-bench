"""Mock tools an agent can call while reviewing a case. Everything is local
and synthetic. No network access."""
from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class CaseTools:
    def __init__(self, case_dir):
        self.dir = Path(case_dir)
        self.case = _load(self.dir / "case.json")
        wl = self.case.get("watchlist_file")
        rg = self.case.get("registry_file")
        self.watchlist = _load(self.dir / wl) if wl else []
        self.registry = _load(self.dir / rg) if rg else {}

    def get_document(self, doc_id: str) -> dict:
        for d in self.case.get("documents", []):
            if d["id"] == doc_id:
                return d
        return {"error": f"no document {doc_id}"}

    def screen_name(self, name: str, threshold: float = 0.6) -> list:
        """Fuzzy-match a name against the watchlist. Returns candidate hits.
        The tool never says whether a hit is a true match. That is the agent's job."""
        hits = []
        for e in self.watchlist:
            sim = SequenceMatcher(None, name.lower(), e["name"].lower()).ratio()
            if sim >= threshold:
                hits.append({**e, "name_similarity": round(sim, 2)})
        return hits

    def registry_lookup(self, entity_id: str) -> dict:
        return self.registry.get(entity_id, {"error": f"no record for {entity_id}"})
