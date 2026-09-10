"""Load and validate fixture YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml

from burybench.fixtures.schema import Fixture, validate_fixture_dict


def load_fixture(path: Path | str) -> Fixture:
    path = Path(path)
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return validate_fixture_dict(data, source=str(path))


def load_fixtures(path: Path | str) -> list[Fixture]:
    """Load a single YAML file or all ``*.yaml`` / ``*.yml`` under a directory."""
    path = Path(path)
    if path.is_file():
        return [load_fixture(path)]
    if not path.is_dir():
        raise FileNotFoundError(f"Fixtures path not found: {path}")

    files = sorted(path.rglob("*.yaml")) + sorted(path.rglob("*.yml"))
    # de-dupe while preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for f in files:
        resolved = f.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(f)

    if not unique:
        raise FileNotFoundError(f"No fixture YAML files under {path}")

    fixtures = [load_fixture(f) for f in unique]
    ids = [fx.id for fx in fixtures]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise ValueError(f"Duplicate fixture ids: {dupes}")
    return fixtures
