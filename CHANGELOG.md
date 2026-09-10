# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Open-source docs: CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, issue/PR templates
- README diagrams under `docs/images/`

### Changed

- `no_hedge_filler`: hybrid gate (density **or** opening cluster/spam); short single hedge allowed; diagnostic-sentence allowlist
- `restate_state`: state card with commands, checklist items, progress paraphrases; empty-continuer fail; artifact can satisfy without echoing step id
- Expanded golden set for the hedge/restate failure modes

## [0.2.0] - 2026-09-10

### Added

- Multi-turn fixture schema (`turns`) and scoring context
- Rules `restate_state` (rule 5) and `visible_wins` (rule 7)
- Rulesets `adhd-v1` and `adhd-v2` (`--ruleset`)
- `bury-bench ingest` for `jsonl`, `cursor-export`, and `markdown`
- Golden regression suite (`golden/`, `bury-bench check-golden`)
- `bury-bench validate-results` and result JSON contract
- Categories `explain` and `ambiguous`; corpus expanded to ~88 fixtures
- GitHub Actions CI (pytest, golden, sample leaderboard freshness)
- Sample transcripts `samples/chat.jsonl` and `samples/chat-buried.jsonl`

### Changed

- Default ruleset is `adhd-v2`
- Ingest result `model` label uses the input filename stem

## [0.1.0] - 2026-09-10

### Added

- Initial zero-LLM-judge harness with 11 single-turn rules
- CLI: `list-rules`, `run`, `score`, `leaderboard`
- Paste / OpenAI-compatible / Anthropic providers
- Fixtures for debug / install / fix
- MIT license

[Unreleased]: https://github.com/Onur45500/bury-bench/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Onur45500/bury-bench/releases/tag/v0.2.0
[0.1.0]: https://github.com/Onur45500/bury-bench/releases/tag/v0.1.0
