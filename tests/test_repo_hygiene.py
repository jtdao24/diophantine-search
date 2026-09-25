"""Repository text-file hygiene tests."""

from pathlib import Path


def test_maintained_files_end_with_exactly_one_newline():
    root = Path(__file__).parents[1]
    files = [
        root / "README.md",
        root / "pyproject.toml",
        root / ".editorconfig",
        root / ".gitattributes",
    ]
    suffixes = {".py", ".md", ".toml", ".json"}
    excluded = {"__pycache__", ".pytest_cache"}

    for directory in ("docs", "src", "tests"):
        files.extend(
            path
            for path in (root / directory).rglob("*")
            if path.is_file()
            and path.suffix in suffixes
            and not excluded.intersection(path.parts)
        )

    for path in files:
        content = path.read_bytes()
        assert content, f"{path} is empty"
        assert b"\r" not in content, f"{path} contains a carriage return"
        assert content.endswith(b"\n"), f"{path} lacks a final newline"
        assert not content.endswith(b"\n\n"), f"{path} has extra final newlines"
