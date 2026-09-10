"""Aggregate result JSON files into a Markdown leaderboard."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


METHODOLOGY = """# bury-bench Leaderboard

Deterministic (zero-LLM-judge) scores for how often coding-agent responses
follow the [i-have-adhd](https://github.com/ayghri/i-have-adhd) output-shaping
rules. Higher **action score** = better (less buried).

## Methodology

- Scoring is 100% reproducible: regex, structure checks, and heuristics only.
  No LLM is called to grade another LLM.
- Rules are derived from the public
  [SKILL.md](https://raw.githubusercontent.com/ayghri/i-have-adhd/main/skills/i-have-adhd/SKILL.md).
- **Rulesets:** `adhd-v1` (single-turn pack) keeps historical scores comparable;
  `adhd-v2` (default) adds multi-turn `restate_state` (rule 5) and
  `visible_wins` (rule 7).
- **Proxy tradeoffs:** `action_first`, `one_next_action`, `numbered_steps`,
  `restate_state`, and `visible_wins` use structural heuristics.
  `no_hedge_filler` uses a density threshold (~1 hedge word per 100 prose words)
  rather than judging “real” uncertainty. See README precision notes.
- Fixtures are MIT-licensed. See the `fixtures/` directory.
- Sample rows under `samples/` are regenerated without live API calls.
- **This project is not affiliated with or endorsed by ayghri/i-have-adhd.**
  It is an independent benchmark inspired by its public rules.

"""


@dataclass
class ModelRow:
    model: str
    provider: str
    overall: float
    debug: float | None
    install: float | None
    fix: float | None
    explain: float | None
    ambiguous: float | None
    worst_rule: str


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _category_means(fixtures: list[dict]) -> dict[str, float | None]:
    by_cat: dict[str, list[float]] = {
        "debug": [],
        "install": [],
        "fix": [],
        "explain": [],
        "ambiguous": [],
    }
    for fx in fixtures:
        cat = fx.get("category")
        if cat in by_cat and "score" in fx:
            by_cat[cat].append(float(fx["score"]))
    return {k: _mean(v) for k, v in by_cat.items()}


def _worst_rule(fixtures: list[dict]) -> str:
    fail_counts: dict[str, int] = {}
    for fx in fixtures:
        for rule in fx.get("rules", []):
            if rule.get("status") == "failed":
                name = rule.get("name", "?")
                fail_counts[name] = fail_counts.get(name, 0) + 1
    if not fail_counts:
        return "—"
    return max(fail_counts.items(), key=lambda kv: kv[1])[0]


def load_result_file(path: Path | str) -> dict:
    path = Path(path)
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def rows_from_results(results: list[dict]) -> list[ModelRow]:
    rows: list[ModelRow] = []
    for data in results:
        fixtures = data.get("fixtures", [])
        cats = _category_means(fixtures)
        overall = data.get("aggregate", {}).get("overall")
        if overall is None:
            scores = [float(fx["score"]) for fx in fixtures if "score" in fx]
            overall = _mean(scores) or 0.0
        model = data.get("model") or "unknown"
        provider = data.get("provider") or "unknown"
        label = f"{provider}/{model}" if provider != "paste" else f"paste/{model}"
        rows.append(
            ModelRow(
                model=label,
                provider=provider,
                overall=float(overall),
                debug=cats.get("debug"),
                install=cats.get("install"),
                fix=cats.get("fix"),
                explain=cats.get("explain"),
                ambiguous=cats.get("ambiguous"),
                worst_rule=_worst_rule(fixtures),
            )
        )
    rows.sort(key=lambda r: r.overall, reverse=True)
    return rows


def render_markdown(rows: list[ModelRow]) -> str:
    lines = [METHODOLOGY.rstrip(), "", "## Scores", ""]
    lines.append(
        "| Rank | Model | Overall | Debug | Install | Fix | Explain | Ambiguous | Most-broken rule |"
    )
    lines.append(
        "|------|-------|---------|-------|---------|-----|---------|-----------|-------------------|"
    )
    for i, row in enumerate(rows, start=1):
        def fmt(v: float | None) -> str:
            return "—" if v is None else f"{v:.1f}"

        lines.append(
            f"| {i} | {row.model} | {row.overall:.1f} | "
            f"{fmt(row.debug)} | {fmt(row.install)} | {fmt(row.fix)} | "
            f"{fmt(row.explain)} | {fmt(row.ambiguous)} | "
            f"{row.worst_rule} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_leaderboard(paths: list[Path | str]) -> str:
    results = [load_result_file(p) for p in paths]
    return render_markdown(rows_from_results(results))


def write_leaderboard(paths: list[Path | str], out: Path | str) -> str:
    md = build_leaderboard(paths)
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    return md
