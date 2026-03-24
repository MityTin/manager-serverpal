"""
Project cleanup utility for Manager ServerPal.

Usage:
  python cleanup_project.py --dry-run
  python cleanup_project.py --apply
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _iter_paths() -> list[Path]:
    paths: list[Path] = []

    # Python caches
    paths.extend(ROOT.rglob("__pycache__"))
    paths.extend(ROOT.rglob("*.pyc"))
    paths.extend(ROOT.rglob("*.pyo"))

    # Build leftovers
    for rel in ("build", "dist"):
        p = ROOT / rel
        if p.exists():
            paths.append(p)

    paths.extend(ROOT.glob("*.spec"))

    # Temporary logs/artifacts
    paths.extend(ROOT.glob("*.log"))
    paths.extend(ROOT.glob("*.tmp"))

    # Ignore venv internals from cleanup by default to avoid accidental breakage.
    filtered: list[Path] = []
    for p in paths:
        try:
            p.relative_to(ROOT / ".venv")
            continue
        except ValueError:
            pass
        filtered.append(p)
    return filtered


def _delete_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean cache/build temp files.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete files (without this, script is dry-run).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print cleanup targets only.",
    )
    args = parser.parse_args()

    dry_run = (not args.apply) or args.dry_run
    targets = sorted(set(_iter_paths()))

    if not targets:
        print("Nothing to clean.")
        return 0

    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"[{mode}] Found {len(targets)} cleanup target(s):")
    for t in targets:
        rel = t.relative_to(ROOT)
        print(f" - {rel}")

    if dry_run:
        print("\nNo files were deleted. Re-run with --apply to remove them.")
        return 0

    for t in targets:
        _delete_path(t)

    print("\nCleanup completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

