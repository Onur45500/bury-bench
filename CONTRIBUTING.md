# Contributing to bury-bench

Thanks for helping improve a zero-LLM-judge benchmark. By participating you agree
to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## What to work on

- **Rules** — deterministic checks only (no LLM calls inside the scorer)
- **Fixtures** — realistic debug/install/fix/explain/ambiguous prompts (MIT header)
- **Golden cases** — hand-labeled expected rule statuses under `golden/`
- **Ingest adapters** — thin parsers for transcript formats (no vendor SDKs in core)
- **Docs** — README clarity, diagrams under `docs/images/`

## Adding a rule

1. Implement `Rule._check(context)` in `burybench/rules/`.
2. Register in `v1_rules()` and/or `v2_rules()` in `burybench/rules/__init__.py`.
3. Add ≥2 pass, ≥2 fail, and N/A tests when applicable.
4. Prefer `textprep.prose()` for phrase scans; raw markdown for structure only.
5. Document proxy tradeoffs in the README golden table if the check is fuzzy.

## Adding a fixture

1. Create `fixtures/<category>/<id>.yaml` with an MIT header comment.
2. Required: `id`, `category`, `prompt`. Optional: `context`, `notes`, `turns`.
3. Keep prompts realistic (real stderr / package errors / type errors).

## Pull requests

1. Keep changes focused (one concern per PR when practical).
2. Run `pytest` and `bury-bench check-golden` locally.
3. If you change committed sample scores, regenerate:
   `python scripts/generate_samples.py`
   `bury-bench leaderboard samples --out docs/LEADERBOARD.md`
4. Fill out the PR template.

## Security

Do not open public issues for vulnerabilities. See [SECURITY.md](SECURITY.md).

## License

Contributions are licensed under MIT, the same as the project.
