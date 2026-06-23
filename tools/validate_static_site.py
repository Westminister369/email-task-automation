"""Validate the static dashboard before deploying to GitHub Pages.

The checks intentionally use only the Python standard library so they can run in
CI or on a contributor machine without installing frontend tooling.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = ["index.html", "style.css", "script.js", "README.md"]
CONFLICT_MARKERS = ("<" * 7, "=" * 7, ">" * 7)


class AssetParser(HTMLParser):
    """Collect stylesheet and script references from index.html."""

    def __init__(self) -> None:
        super().__init__()
        self.stylesheets: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "link" and attributes.get("rel") == "stylesheet":
            href = attributes.get("href")
            if href:
                self.stylesheets.append(href)
        if tag == "script":
            src = attributes.get("src")
            if src:
                self.scripts.append(src)


def read_text(path: Path) -> str:
    """Read a project file as UTF-8 text."""
    return path.read_text(encoding="utf-8")


def assert_required_files_exist() -> None:
    """Ensure GitHub Pages entrypoint and assets are present."""
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    if missing:
        raise AssertionError(f"Missing required file(s): {', '.join(missing)}")


def assert_no_conflict_markers() -> None:
    """Fail fast if unresolved merge conflict markers are committed."""
    checked_suffixes = {".html", ".css", ".js", ".md", ".py", ".txt"}
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or not path.is_file() or path.suffix not in checked_suffixes:
            continue
        text = read_text(path)
        for marker in CONFLICT_MARKERS:
            if marker in text:
                raise AssertionError(f"Found conflict marker {marker!r} in {path.relative_to(ROOT)}")


def assert_index_assets_exist() -> None:
    """Verify index.html references local assets that exist in the repo."""
    parser = AssetParser()
    parser.feed(read_text(ROOT / "index.html"))
    referenced_assets = parser.stylesheets + parser.scripts
    missing = [asset for asset in referenced_assets if not (ROOT / asset).is_file()]
    if missing:
        raise AssertionError(f"Missing referenced asset(s): {', '.join(missing)}")


def main() -> None:
    """Run all static dashboard validation checks."""
    assert_required_files_exist()
    assert_no_conflict_markers()
    assert_index_assets_exist()
    print("Static dashboard validation passed.")


if __name__ == "__main__":
    main()
