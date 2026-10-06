"""Print the actual project tree, excluding generated and Git internal contents."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OMIT = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
}


def print_tree(directory: Path, prefix: str = "") -> None:
    entries = sorted(
        (item for item in directory.iterdir() if item.name not in OMIT),
        key=lambda item: (not item.is_dir(), item.name),
    )
    for index, item in enumerate(entries):
        last = index == len(entries) - 1
        connector = "└── " if last else "├── "
        print(f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}")
        if item.is_dir() and not item.is_symlink():
            print_tree(item, prefix + ("    " if last else "│   "))


if __name__ == "__main__":
    print(f"{ROOT.name}/")
    print_tree(ROOT)
