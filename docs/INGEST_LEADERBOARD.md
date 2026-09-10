# bury-bench Leaderboard

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

## Scores

| Rank | Model | Overall | Debug | Install | Fix | Explain | Ambiguous | Most-broken rule |
|------|-------|---------|-------|---------|-----|---------|-----------|-------------------|
| 1 | ingest:jsonl/chat | 76.9 | 76.9 | — | — | — | — | action_first |
| 2 | ingest:jsonl/chat-buried | 7.9 | 7.9 | — | — | — | — | action_first |
