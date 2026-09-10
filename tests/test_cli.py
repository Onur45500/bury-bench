"""CLI and end-to-end tests."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from burybench.cli import app
from burybench.leaderboard import build_leaderboard, write_leaderboard
from burybench.providers.local_paste import PasteProvider

runner = CliRunner()
FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


GOOD_RESPONSE = """Run `pip install fastapi`.

1. Create a virtualenv
2. Install fastapi and uvicorn
3. Run `uvicorn main:app --reload`

Next: open http://127.0.0.1:8000/docs.
"""

BURIED_RESPONSE = """Great question! Let me think about this carefully.

First you should maybe look at the docs, then perhaps try a few options
after that you might circle back to the install.

By the way, your README is also stale.

Hope this helps! Let me know if you need anything else.
"""


def test_list_rules() -> None:
    result = runner.invoke(app, ["list-rules"])
    assert result.exit_code == 0
    assert "action_first" in result.stdout
    assert "no_preamble" in result.stdout
    assert "restate_state" in result.stdout
    assert "visible_wins" in result.stdout


def test_list_rules_v1_excludes_multiturn() -> None:
    result = runner.invoke(app, ["list-rules", "--ruleset", "adhd-v1"])
    assert result.exit_code == 0
    assert "action_first" in result.stdout
    assert "restate_state" not in result.stdout


def test_paste_provider_scripted() -> None:
    lines = iter([*GOOD_RESPONSE.splitlines(), "END"])
    provider = PasteProvider(input_fn=lambda: next(lines), output_fn=lambda _s: None)
    text = provider.send("How do I install FastAPI?")
    assert "pip install fastapi" in text


def test_run_paste_e2e(tmp_path: Path) -> None:
    fixture = FIXTURES_ROOT / "install" / "install-001.yaml"
    out = tmp_path / "result.json"
    pasted = "\n".join([*GOOD_RESPONSE.splitlines(), "END"]) + "\n"

    result = runner.invoke(
        app,
        ["run", "--provider", "paste", "--fixtures", str(fixture), "--out", str(out)],
        input=pasted,
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["provider"] == "paste"
    assert len(data["fixtures"]) == 1
    assert data["fixtures"][0]["id"] == "install-001"
    assert "score" in data["fixtures"][0]
    assert data["aggregate"]["overall"] == data["fixtures"][0]["score"]


def test_score_command(tmp_path: Path) -> None:
    responses = {
        "model": "demo",
        "provider": "precollected",
        "responses": [
            {
                "id": "install-001",
                "category": "install",
                "response_text": GOOD_RESPONSE,
            },
            {
                "id": "debug-001",
                "category": "debug",
                "response_text": BURIED_RESPONSE,
            },
        ],
    }
    inp = tmp_path / "responses.json"
    out = tmp_path / "scored.json"
    inp.write_text(json.dumps(responses), encoding="utf-8")

    result = runner.invoke(app, ["score", "--responses", str(inp), "--out", str(out)])
    assert result.exit_code == 0, result.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["fixtures"]) == 2
    assert data["fixtures"][0]["score"] > data["fixtures"][1]["score"]


def test_leaderboard_from_two_results(tmp_path: Path) -> None:
    good = {
        "model": "good-model",
        "provider": "paste",
        "fixtures": [
            {
                "id": "a",
                "category": "debug",
                "score": 95.0,
                "rules": [{"name": "no_preamble", "status": "passed"}],
            },
            {
                "id": "b",
                "category": "install",
                "score": 90.0,
                "rules": [{"name": "no_closer", "status": "failed"}],
            },
            {
                "id": "c",
                "category": "fix",
                "score": 92.0,
                "rules": [{"name": "no_closer", "status": "failed"}],
            },
        ],
        "aggregate": {"overall": 92.33},
    }
    bad = {
        "model": "bad-model",
        "provider": "openai",
        "fixtures": [
            {
                "id": "a",
                "category": "debug",
                "score": 40.0,
                "rules": [{"name": "no_preamble", "status": "failed"}],
            },
            {
                "id": "b",
                "category": "install",
                "score": 35.0,
                "rules": [{"name": "no_preamble", "status": "failed"}],
            },
            {
                "id": "c",
                "category": "fix",
                "score": 30.0,
                "rules": [{"name": "no_preamble", "status": "failed"}],
            },
        ],
        "aggregate": {"overall": 35.0},
    }
    p1 = tmp_path / "good.json"
    p2 = tmp_path / "bad.json"
    p1.write_text(json.dumps(good), encoding="utf-8")
    p2.write_text(json.dumps(bad), encoding="utf-8")

    out = tmp_path / "LEADERBOARD.md"
    md = write_leaderboard([p1, p2], out)
    assert out.exists()
    assert "good-model" in md
    assert "bad-model" in md
    assert "zero-LLM-judge" in md or "Zero-LLM-judge" in md or "zero-LLM-judge" in md.lower() or "Deterministic" in md
    # good model ranks first
    good_pos = md.index("good-model")
    bad_pos = md.index("bad-model")
    assert good_pos < bad_pos

    result = runner.invoke(app, ["leaderboard", str(p1), str(p2), "--out", str(out)])
    assert result.exit_code == 0


def test_build_leaderboard_empty_worst_rule() -> None:
    data = {
        "model": "x",
        "provider": "paste",
        "fixtures": [
            {"id": "a", "category": "debug", "score": 100.0, "rules": []},
        ],
        "aggregate": {"overall": 100.0},
    }
    md = build_leaderboard([])  # no files — handled by caller; smoke via rows
    # just ensure function exists; empty list yields methodology + empty table header
    from burybench.leaderboard import render_markdown, rows_from_results

    md = render_markdown(rows_from_results([data]))
    assert "Most-broken rule" in md
    assert "—" in md
