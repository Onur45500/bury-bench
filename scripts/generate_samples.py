"""Generate samples/*.json for CI leaderboard (no API calls)."""

from __future__ import annotations

import json
from pathlib import Path

from burybench.rules.base import Turn
from burybench.scorer import Scorer

GOOD = """Run `pip install fastapi`.

1. Create a virtualenv
2. Install fastapi and uvicorn
3. Run `uvicorn main:app --reload`

Next: open http://127.0.0.1:8000/docs.
"""

BURIED = """Great question! Let me think about this carefully.

First maybe look at the logs, then perhaps restart after that circle back.

By the way, your README is stale.

Hope this helps! Let me know if you need anything else.
"""


def pack(model: str, provider: str, pairs: list) -> dict:
    scorer = Scorer.from_ruleset("adhd-v2")
    fixtures = []
    for fid, cat, text, turns in pairs:
        result = scorer.score(text, turns=turns)
        fixtures.append(
            {
                "id": fid,
                "category": cat,
                "response_text": text,
                "score": result.score,
                "rules": [
                    {
                        "name": r.name,
                        "status": r.status,
                        "evidence": r.evidence,
                        "weight": r.weight,
                    }
                    for r in result.rules
                ],
            }
        )
    scores = [f["score"] for f in fixtures]
    per_cat: dict[str, list[float]] = {}
    fail_counts: dict[str, int] = {}
    for fx in fixtures:
        per_cat.setdefault(fx["category"], []).append(fx["score"])
        for rule in fx["rules"]:
            if rule["status"] == "failed":
                fail_counts[rule["name"]] = fail_counts.get(rule["name"], 0) + 1
    return {
        "model": model,
        "provider": provider,
        "ruleset": "adhd-v2",
        "timestamp": "2026-09-10T00:00:00+00:00",
        "fixtures": fixtures,
        "aggregate": {
            "overall": round(sum(scores) / len(scores), 2),
            "per_category": {
                k: round(sum(v) / len(v), 2) for k, v in sorted(per_cat.items())
            },
            "per_rule_fail_counts": dict(
                sorted(fail_counts.items(), key=lambda kv: -kv[1])
            ),
        },
    }


def main() -> None:
    turns = [Turn(role="assistant", content="Step 2 of 4 done: schema updated.")]
    root = Path("samples")
    root.mkdir(exist_ok=True)
    good = pack(
        "sample-good",
        "paste",
        [
            ("debug-001", "debug", GOOD, []),
            ("install-001", "install", GOOD, []),
            ("fix-001", "fix", GOOD, []),
            ("explain-001", "explain", GOOD, []),
            (
                "debug-mt-001",
                "debug",
                "Step 2 of 4 done: schema updated. Next: run backfill.",
                turns,
            ),
        ],
    )
    buried = pack(
        "sample-buried",
        "openai",
        [
            ("debug-001", "debug", BURIED, []),
            ("install-001", "install", BURIED, []),
            ("fix-001", "fix", BURIED, []),
            ("ambiguous-001", "ambiguous", BURIED, []),
            ("debug-mt-001", "debug", "Done. Ready for the next part?", turns),
        ],
    )
    (root / "sample-good.json").write_text(json.dumps(good, indent=2), encoding="utf-8")
    (root / "sample-buried.json").write_text(
        json.dumps(buried, indent=2), encoding="utf-8"
    )
    print("good", good["aggregate"]["overall"], "buried", buried["aggregate"]["overall"])


if __name__ == "__main__":
    main()
