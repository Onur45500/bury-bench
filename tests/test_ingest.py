"""Ingest + validate-results CLI tests."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from burybench.cli import app
from burybench.ingest import ingest, parse_jsonl, parse_markdown
from burybench.validate import validate_result_dict

runner = CliRunner()


THREE_TURN_JSONL = (
    json.dumps(
        {
            "id": "sample-mt-001",
            "category": "debug",
            "messages": [
                {"role": "user", "content": "Migration failed."},
                {
                    "role": "assistant",
                    "content": "Step 1 of 3 done: added column in `migrations/002.sql`.",
                },
                {"role": "user", "content": "continue"},
                {
                    "role": "assistant",
                    "content": (
                        "Step 1 of 3 done: schema updated. "
                        "Next: run `python backfill.py`."
                    ),
                },
            ],
        }
    )
    + "\n"
)


def test_parse_jsonl_three_turn(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    path.write_text(THREE_TURN_JSONL, encoding="utf-8")
    items = parse_jsonl(path)
    assert len(items) == 1
    assert items[0].id == "sample-mt-001"
    assert "Step 1 of 3" in items[0].response_text
    assert len(items[0].turns) == 3


def test_parse_markdown(tmp_path: Path) -> None:
    path = tmp_path / "chat.md"
    path.write_text(
        "User:\nHello\n\nAssistant:\nRun `npm test`.\n\nUser:\nok\n\nAssistant:\nDone.\n",
        encoding="utf-8",
    )
    items = parse_markdown(path)
    assert items[0].response_text.strip() == "Done."
    assert items[0].turns[-1]["role"] == "user"


def test_ingest_cli_scores(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    path.write_text(THREE_TURN_JSONL, encoding="utf-8")
    out = tmp_path / "out.json"
    result = runner.invoke(
        app,
        ["ingest", str(path), "--format", "jsonl", "--out", str(out)],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["provider"] == "ingest:jsonl"
    assert data["model"] == path.stem
    assert len(data["fixtures"]) == 1
    assert "score" in data["fixtures"][0]
    statuses = {r["name"]: r["status"] for r in data["fixtures"][0]["rules"]}
    assert statuses["restate_state"] == "passed"


def test_validate_results_ok(tmp_path: Path) -> None:
    payload = {
        "model": "x",
        "provider": "paste",
        "fixtures": [
            {
                "id": "a",
                "category": "debug",
                "score": 90.0,
                "rules": [{"name": "no_preamble", "status": "passed"}],
            }
        ],
        "aggregate": {"overall": 90.0},
    }
    assert validate_result_dict(payload) == []
    path = tmp_path / "ok.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    result = runner.invoke(app, ["validate-results", str(path)])
    assert result.exit_code == 0


def test_validate_results_fail(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"model": "x"}), encoding="utf-8")
    result = runner.invoke(app, ["validate-results", str(path)])
    assert result.exit_code == 1


def test_cursor_export_ingest(tmp_path: Path) -> None:
    path = tmp_path / "cursor.json"
    path.write_text(
        json.dumps(
            {
                "conversations": [
                    {
                        "id": "c1",
                        "messages": [
                            {"role": "user", "content": "hi"},
                            {"role": "assistant", "content": "Run `echo hi`."},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    items = ingest(path, fmt="cursor-export")
    assert items[0].id == "c1"
    assert items[0].response_text.startswith("Run")
