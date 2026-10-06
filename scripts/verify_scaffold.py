"""Check scaffold consistency offline; this is not a product test suite."""

import ast
import csv
import json
import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
AGENTS = (
    "architect",
    "explore",
    "data-engineer",
    "mcp-engineer",
    "reviewer",
    "verifier",
    "teacher",
)
COMMANDS = ("teacher", "plan", "review", "verify", "checkpoint")
SKILLS = (
    "cms-data-discovery",
    "cms-source-validation",
    "healthcare-data-modeling",
    "mcp-tool-design",
    "data-validation",
    "mcp-testing",
    "provenance",
)
GENERATED = {".git", ".venv", "dist", "build", "__pycache__", ".mypy_cache", ".ruff_cache"}


def verify() -> list[str]:
    errors: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    required = [
        "README.md",
        "AGENTS.md",
        "PROJECT_STATE.md",
        "pyproject.toml",
        ".env.example",
        ".gitignore",
        ".cursor/rules/project.md",
        ".cursor/rules/project.mdc",
        "src/cms_mcp/__init__.py",
        "src/cms_mcp/py.typed",
        "tests/README.md",
        "tests/unit/README.md",
        "tests/integration/README.md",
        "tests/fixtures/catalog_entry.json",
        "tests/evals/scenarios.json",
        "data/cache/README.md",
        "data/fixtures/cardiology_counts.csv",
        "docs/architecture.md",
        "docs/adr/001-local-first-vertical-slice.md",
        "docs/agent-system.md",
        "docs/datasets.md",
        "docs/mcp-tools.md",
        "docs/provenance.md",
        "docs/roadmap.md",
        "docs/scaffold-verification.md",
        "examples/cardiologist_search.md",
        "examples/dataset_discovery.md",
        "scripts/show_tree.py",
    ]
    required += [f".cursor/agents/{name}.md" for name in AGENTS]
    required += [f".cursor/commands/{name}.md" for name in COMMANDS]
    required += [f"skills/{name}/SKILL.md" for name in SKILLS]
    required += [f".cursor/skills/{name}/SKILL.md" for name in (*SKILLS, *COMMANDS)]
    for relative in required:
        check((ROOT / relative).is_file(), f"Missing file: {relative}")
    if errors:
        return errors

    check(ROOT.name == "cms-data-mcp", "Project root must be named cms-data-mcp")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    check(project["project"]["name"] == "cms-data-mcp", "Distribution name mismatch")
    check(
        project["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == ["src/cms_mcp"],
        "Wheel must include the cms_mcp package",
    )

    files = [
        path
        for path in ROOT.rglob("*")
        if path.is_file() and not (set(path.relative_to(ROOT).parts) & GENERATED)
    ]
    for path in files:
        relative = str(path.relative_to(ROOT))
        if path.suffix == ".py":
            ast.parse(path.read_text(), filename=str(relative))
        if path.suffix != ".md":
            continue
        for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", path.read_text()):
            parsed = urlsplit(target)
            if parsed.scheme or not parsed.path:
                continue
            destination = (path.parent / unquote(parsed.path)).resolve()
            check(destination.is_relative_to(ROOT), f"Link escapes project: {relative}: {target}")
            check(destination.exists(), f"Broken link: {relative}: {target}")

    metadata = json.loads((ROOT / "tests/fixtures/catalog_entry.json").read_text())
    with (ROOT / "data/fixtures/cardiology_counts.csv").open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames
    check(metadata["synthetic"] is True, "Fixture must be labeled synthetic")
    check(metadata["contains_real_records"] is False, "Fixture cannot contain real records")
    check(
        urlsplit(metadata["source_url"]).hostname == "fixtures.invalid",
        "Fixture URL is not synthetic",
    )
    check(fields == [field["name"] for field in metadata["fields"]], "Fixture schema mismatch")
    check(len(rows) == metadata["row_count"], "Fixture row count mismatch")
    selected = [
        row
        for row in rows
        if row["state"] == "CA" and row["specialty"] == "CARDIOVASCULAR DISEASE (CARDIOLOGY)"
    ]
    cases = json.loads((ROOT / "tests/evals/scenarios.json").read_text())
    check(
        cases["status"] in {"specification_only", "supervised_run_recorded"}, "Unknown eval status"
    )
    identifiers = [case["id"] for case in cases["cases"]]
    check(len(set(identifiers)) == len(identifiers), "Duplicate eval case IDs")
    expected = next(
        case["expected"] for case in cases["cases"] if case["id"] == "california_cardiology"
    )
    check(expected["rows"] == 1, "The current aggregate has exactly one normalized row")
    check(
        sum(int(row["record_count"]) for row in selected) == expected["record_count_sum"],
        "Eval expected sum differs from fixture",
    )
    return errors


if __name__ == "__main__":
    try:
        failures = verify()
    except (KeyError, ValueError, OSError, SyntaxError, StopIteration) as exc:
        failures = [f"Invalid scaffold content: {exc}"]
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        raise SystemExit(1)
    print("PASS: scaffold files, metadata, Python syntax, links, and synthetic eval expectations")
    print("Scope: setup consistency only; run pytest separately for product behavior.")
