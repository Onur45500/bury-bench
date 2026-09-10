"""bury-bench CLI."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from burybench import __version__
from burybench.fixtures import load_fixtures
from burybench.golden import evaluate_golden, load_golden_dir
from burybench.ingest import ingest
from burybench.leaderboard import write_leaderboard
from burybench.providers import get_provider
from burybench.rules import DEFAULT_RULESET, rules_for
from burybench.rules.base import Turn
from burybench.scorer import Scorer
from burybench.validate import RESULT_SCHEMA, validate_result_file

app = typer.Typer(
    name="bury-bench",
    help="Zero-LLM-judge benchmark for answer-burial in coding-agent responses.",
    no_args_is_help=True,
)
console = Console()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _aggregate(fixture_results: list[dict]) -> dict:
    scores = [float(fx["score"]) for fx in fixture_results]
    overall = round(sum(scores) / len(scores), 2) if scores else 0.0

    per_category: dict[str, list[float]] = {}
    per_rule_fail: dict[str, int] = {}
    for fx in fixture_results:
        per_category.setdefault(fx["category"], []).append(float(fx["score"]))
        for rule in fx.get("rules", []):
            if rule.get("status") == "failed":
                name = rule["name"]
                per_rule_fail[name] = per_rule_fail.get(name, 0) + 1

    return {
        "overall": overall,
        "per_category": {
            cat: round(sum(vals) / len(vals), 2) for cat, vals in sorted(per_category.items())
        },
        "per_rule_fail_counts": dict(sorted(per_rule_fail.items(), key=lambda kv: -kv[1])),
    }


def _turns_from_item(item: dict | object) -> list[Turn]:
    if hasattr(item, "turns"):
        raw = getattr(item, "turns")
    else:
        raw = item.get("turns") if isinstance(item, dict) else None  # type: ignore[union-attr]
    if not raw:
        return []
    turns: list[Turn] = []
    for t in raw:
        if isinstance(t, Turn):
            turns.append(t)
        elif isinstance(t, dict):
            turns.append(Turn(role=str(t["role"]), content=str(t["content"])))
        else:
            turns.append(Turn(role=t.role, content=t.content))
    return turns


def _score_response(
    scorer: Scorer,
    response: str,
    fixture_id: str,
    category: str,
    *,
    turns: list[Turn] | None = None,
) -> dict:
    result = scorer.score(response, turns=turns or [])
    return {
        "id": fixture_id,
        "category": category,
        "response_text": response,
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


@app.command("list-rules")
def list_rules(
    ruleset: str = typer.Option(DEFAULT_RULESET, "--ruleset", help="adhd-v1 | adhd-v2"),
) -> None:
    """Print all active rules with descriptions."""
    table = Table(title=f"bury-bench rules ({ruleset})")
    table.add_column("Name", style="cyan")
    table.add_column("Weight", justify="right")
    table.add_column("Multi-turn", justify="center")
    table.add_column("Description")
    for rule in rules_for(ruleset):
        table.add_row(
            rule.name,
            f"{rule.weight:g}",
            "yes" if rule.multi_turn_only else "",
            rule.description,
        )
    console.print(table)


@app.command()
def run(
    fixtures: Path = typer.Option(
        Path("fixtures"),
        "--fixtures",
        help="Fixture file or directory",
        exists=True,
    ),
    provider: str = typer.Option("paste", "--provider", "-p", help="paste | openai | anthropic"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model id (required for API providers)"),
    out: Path = typer.Option(Path("results/run.json"), "--out", "-o", help="Output JSON path"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Override API base URL"),
    ruleset: str = typer.Option(DEFAULT_RULESET, "--ruleset", help="adhd-v1 | adhd-v2"),
) -> None:
    """Send fixture prompts to a provider and score the responses."""
    loaded = load_fixtures(fixtures)
    adapter = get_provider(provider, model=model, base_url=base_url)
    scorer = Scorer.from_ruleset(ruleset)
    model_label = model or ("pasted" if adapter.name == "paste" else "unknown")

    console.print(
        f"[bold]bury-bench[/bold] v{__version__} — {len(loaded)} fixture(s) "
        f"via {adapter.name} [{ruleset}]"
    )

    fixture_results: list[dict] = []
    for fx in loaded:
        console.print(f"\n[cyan]-> {fx.id}[/cyan] ({fx.category})")
        response = adapter.send(fx.full_prompt())
        scored = _score_response(
            scorer,
            response,
            fx.id,
            fx.category,
            turns=list(fx.transcript_turns()),
        )
        fixture_results.append(scored)
        console.print(f"  action score: [green]{scored['score']}[/green]")

    payload = {
        "model": model_label,
        "provider": adapter.name,
        "ruleset": ruleset,
        "timestamp": _utc_now(),
        "fixtures": fixture_results,
        "aggregate": _aggregate(fixture_results),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    console.print(f"\nWrote [bold]{out}[/bold] — overall {payload['aggregate']['overall']}")


@app.command()
def score(
    responses: Path = typer.Option(
        ...,
        "--responses",
        "-r",
        help="JSON file of already-collected responses",
        exists=True,
    ),
    out: Path = typer.Option(Path("results/scored.json"), "--out", "-o"),
    ruleset: str = typer.Option(DEFAULT_RULESET, "--ruleset", help="adhd-v1 | adhd-v2"),
) -> None:
    """Score already-collected responses without calling a provider."""
    raw = json.loads(responses.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        items = raw
        model_label = "unknown"
        provider_label = "precollected"
    else:
        items = raw.get("responses") or raw.get("fixtures") or []
        model_label = raw.get("model", "unknown")
        provider_label = raw.get("provider", "precollected")
        if raw.get("ruleset"):
            ruleset = str(raw["ruleset"])

    if not items:
        raise typer.BadParameter("No responses found in input JSON")

    scorer = Scorer.from_ruleset(ruleset)
    fixture_results = [
        _score_response(
            scorer,
            item["response_text"],
            item["id"],
            item.get("category", "debug"),
            turns=_turns_from_item(item),
        )
        for item in items
    ]
    payload = {
        "model": model_label,
        "provider": provider_label,
        "ruleset": ruleset,
        "timestamp": _utc_now(),
        "fixtures": fixture_results,
        "aggregate": _aggregate(fixture_results),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    console.print(f"Wrote [bold]{out}[/bold] — overall {payload['aggregate']['overall']}")


@app.command("ingest")
def ingest_cmd(
    path: Path = typer.Argument(..., exists=True, help="Transcript file to ingest"),
    fmt: str = typer.Option("jsonl", "--format", "-f", help="jsonl | cursor-export | markdown"),
    out: Path = typer.Option(Path("results/ingested.json"), "--out", "-o"),
    category: str = typer.Option("debug", "--category", "-c"),
    ruleset: str = typer.Option(DEFAULT_RULESET, "--ruleset"),
    score_after: bool = typer.Option(True, "--score/--no-score", help="Score after ingest"),
) -> None:
    """Normalize agent transcripts, then optionally score them (no API keys)."""
    transcripts = ingest(path, fmt=fmt, default_category=category)
    items = [t.to_score_item() for t in transcripts]
    model_label = path.stem

    if not score_after:
        payload = {
            "model": model_label,
            "provider": f"ingest:{fmt}",
            "ruleset": ruleset,
            "timestamp": _utc_now(),
            "responses": items,
        }
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        console.print(f"Wrote {len(items)} transcript(s) to [bold]{out}[/bold]")
        return

    scorer = Scorer.from_ruleset(ruleset)
    fixture_results = [
        _score_response(
            scorer,
            item["response_text"],
            item["id"],
            item["category"],
            turns=_turns_from_item(item),
        )
        for item in items
    ]
    payload = {
        "model": model_label,
        "provider": f"ingest:{fmt}",
        "ruleset": ruleset,
        "timestamp": _utc_now(),
        "fixtures": fixture_results,
        "aggregate": _aggregate(fixture_results),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    console.print(
        f"Ingested+scored {len(fixture_results)} transcript(s) -> [bold]{out}[/bold] "
        f"(overall {payload['aggregate']['overall']})"
    )


@app.command("validate-results")
def validate_results(
    results: list[Path] = typer.Argument(..., help="Result JSON file(s) or directories"),
) -> None:
    """Validate result JSON files against the bury-bench result contract."""
    paths: list[Path] = []
    for entry in results:
        if entry.is_dir():
            paths.extend(sorted(entry.glob("*.json")))
        else:
            paths.append(entry)
    if not paths:
        raise typer.BadParameter("No result JSON files found")

    failed = 0
    for path in paths:
        errors = validate_result_file(path)
        if errors:
            failed += 1
            console.print(f"[red]FAIL[/red] {path}")
            for err in errors:
                console.print(f"  - {err}")
        else:
            console.print(f"[green]OK[/green]   {path}")
    if failed:
        raise typer.Exit(code=1)


@app.command("check-golden")
def check_golden(
    golden_dir: Path = typer.Option(Path("golden"), "--golden", exists=True),
) -> None:
    """Run golden regression cases (expected per-rule statuses)."""
    cases = load_golden_dir(golden_dir)
    failed = 0
    for case in cases:
        mismatches = evaluate_golden(case)
        if mismatches:
            failed += 1
            console.print(f"[red]FAIL[/red] {case.id}")
            for msg in mismatches:
                console.print(f"  - {msg}")
        else:
            console.print(f"[green]OK[/green]   {case.id}")
    if failed:
        raise typer.Exit(code=1)
    console.print(f"\n{len(cases)} golden case(s) passed")


@app.command()
def leaderboard(
    results: list[Path] = typer.Argument(..., help="One or more result JSON files"),
    out: Path = typer.Option(Path("docs/LEADERBOARD.md"), "--out", "-o"),
) -> None:
    """Aggregate result files into a Markdown leaderboard table."""
    paths: list[Path] = []
    for entry in results:
        if entry.is_dir():
            paths.extend(sorted(entry.glob("*.json")))
        else:
            paths.append(entry)
    if not paths:
        raise typer.BadParameter("No result JSON files found")

    md = write_leaderboard(paths, out)
    console.print(md)
    console.print(f"\nWrote [bold]{out}[/bold]")


@app.command("show-schema")
def show_schema() -> None:
    """Print the result JSON schema."""
    console.print_json(data=RESULT_SCHEMA)


@app.callback()
def main_callback() -> None:
    """bury-bench CLI entry."""


if __name__ == "__main__":
    app()
