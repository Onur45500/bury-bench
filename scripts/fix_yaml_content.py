"""Fix fixture/golden YAML lines where content: has unquoted colons."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    changed = False
    for line in lines:
        raw = line.rstrip("\n\r")
        match = re.match(r"^(\s*)content:\s+(.+)$", raw)
        if (
            match
            and ":" in match.group(2)
            and not match.group(2).startswith("|")
            and not match.group(2).startswith(">")
        ):
            indent, val = match.group(1), match.group(2)
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            out.append(f"{indent}content: |\n")
            out.append(f"{indent}  {val}\n")
            changed = True
            continue
        out.append(line if line.endswith("\n") else line + "\n")
    if changed:
        path.write_text("".join(out), encoding="utf-8")
    return changed


def main() -> None:
    changed: list[str] = []
    for root in (Path("fixtures"), Path("golden")):
        for path in root.rglob("*.yaml"):
            if fix_file(path):
                changed.append(str(path))
    print(f"fixed {len(changed)}")
    bad: list[tuple[str, str]] = []
    for root in (Path("fixtures"), Path("golden")):
        for path in root.rglob("*.yaml"):
            try:
                yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                bad.append((str(path), str(exc).splitlines()[0]))
    print(f"remaining bad {len(bad)}")
    for item in bad:
        print(item)


if __name__ == "__main__":
    main()
