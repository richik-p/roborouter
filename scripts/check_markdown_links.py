from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {".git", ".next", ".venv", "node_modules"}
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


def markdown_files() -> list[Path]:
    return sorted(path for path in ROOT.rglob("*.md") if not IGNORED_PARTS.intersection(path.parts))


def local_target(raw: str) -> str | None:
    value = raw.strip().strip("<>")
    if " " in value and not value.startswith("<"):
        value = value.split(" ", 1)[0]
    if not value or value.startswith(("#", "http://", "https://", "mailto:")):
        return None
    return unquote(value.split("#", 1)[0])


def main() -> None:
    failures: list[str] = []
    for document in markdown_files():
        for match in LINK.finditer(document.read_text()):
            target = local_target(match.group(1))
            if target is None:
                continue
            resolved = (document.parent / target).resolve()
            if not resolved.exists():
                failures.append(f"{document.relative_to(ROOT)} -> {target}")
    if failures:
        raise SystemExit("Broken local Markdown links:\n" + "\n".join(failures))
    print(f"Checked local links in {len(markdown_files())} Markdown files.")


if __name__ == "__main__":
    main()
