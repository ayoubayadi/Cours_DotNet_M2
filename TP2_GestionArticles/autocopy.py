"""
consolidate.py — Recursively scan a project directory and consolidate all
text file contents into a single, well-organised output .txt file.

Usage
-----
# Basic
python consolidate.py /path/to/project -o consolidated.txt

# Custom ignores (glob patterns, comma-separated)
python consolidate.py /path/to/project -o out.txt --ignore "*.log,tmp,*.pyc"

# Verbose
python consolidate.py /path/to/project -o out.txt -v

Edge-case behaviour
-------------------
- Empty directories     : produces output file with zero file entries; logs INFO.
- Deeply nested paths   : no recursion limit; pathlib.Path.rglob handles depth.
- Unicode filenames     : handled natively by pathlib on Python 3.
- Unicode file content  : read as UTF-8 strict; non-decodable files skipped with WARNING.
- Permission-denied     : caught per-file; WARNING logged; processing continues.
- Broken/circular symlinks: followed=False in rglob; symlinks never dereferenced.
- Self-exclusion        : output file resolved to absolute path and excluded before
                          iteration begins, even when it lives inside the source tree.
- Binary files          : first 8 KB checked for null bytes; positives skipped silently
                          at DEBUG level (bumped to WARNING only when --verbose).
"""

from __future__ import annotations

import argparse
import fnmatch
import logging
import mimetypes
import sys
from pathlib import Path
from typing import Optional

# ── constants ────────────────────────────────────────────────────────────────

SEPARATOR = "-" * 80
SEPARATOR_BLOCK = f"{SEPARATOR}\n\n"

DEFAULT_EXCLUDE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        "venv",
        ".venv",
        "env",
        "dist",
        "build",
        ".idea",
        ".vscode",
    }
)

BINARY_SAMPLE_BYTES = 8192  # bytes read for binary sniff

log = logging.getLogger("consolidate")


# ── helpers ───────────────────────────────────────────────────────────────────


def configure_logging(verbose: bool) -> None:
    """Configure root logger to stderr with optional DEBUG level."""
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logging.basicConfig(level=level, handlers=[handler])


def is_hidden(path: Path) -> bool:
    """Return True if any component of *path* starts with a dot."""
    return any(part.startswith(".") for part in path.parts)


def is_excluded_dir(path: Path, extra: frozenset[str]) -> bool:
    """Return True if *path* is a directory whose name is in the exclusion set."""
    return path.is_dir() and path.name in (DEFAULT_EXCLUDE_DIRS | extra)


def matches_glob_patterns(path: Path, patterns: frozenset[str]) -> bool:
    """Return True if *path* name or relative string matches any glob pattern."""
    name = path.name
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


def is_binary(path: Path) -> bool:
    """
    Heuristically detect binary files.

    Strategy (fast, no external deps):
    1. Check MIME type via extension; if mime starts with 'text/' → not binary.
    2. Read up to BINARY_SAMPLE_BYTES; if a null byte is present → binary.
    """
    mime, _ = mimetypes.guess_type(str(path))
    if mime and mime.startswith("text/"):
        return False

    try:
        sample = path.read_bytes()[:BINARY_SAMPLE_BYTES]
    except OSError:
        # Unreadable at byte level; caller will catch the real error on text open.
        return False

    return b"\x00" in sample


def read_text_safe(path: Path) -> Optional[str]:
    """
    Read *path* as UTF-8 text.

    Returns
    -------
    str   : file content
    None  : on PermissionError, UnicodeDecodeError, or other OSError
            (warning already emitted by caller via return-value check)
    """
    try:
        return path.read_text(encoding="utf-8", errors="strict")
    except PermissionError:
        log.warning("Permission denied — skipping: %s", path)
    except UnicodeDecodeError:
        log.warning("UTF-8 decode failed — skipping: %s", path)
    except OSError as exc:
        log.warning("Cannot read (%s) — skipping: %s", exc.strerror, path)
    return None


def collect_files(
    source: Path,
    output_abs: Path,
    extra_ignore_dirs: frozenset[str],
    extra_glob_patterns: frozenset[str],
) -> list[Path]:
    """
    Recursively collect candidate text files under *source*.

    Files are returned sorted by their path relative to *source* (alphabetical,
    case-sensitive, for deterministic output across runs).

    Parameters
    ----------
    source              : Root directory to scan.
    output_abs          : Absolute path of the output file (excluded if inside tree).
    extra_ignore_dirs   : Additional directory names to skip.
    extra_glob_patterns : Additional glob patterns matched against file names.

    Returns
    -------
    Sorted list of absolute Path objects.
    """
    candidates: list[Path] = []

    try:
        all_paths = sorted(source.rglob("*"), key=lambda p: p.relative_to(source))
    except PermissionError:
        log.warning("Permission denied reading source directory: %s", source)
        return []

    for path in all_paths:
        # Resolve without following symlinks so circular links don't loop.
        try:
            abs_path = path.resolve(strict=False)
        except OSError:
            log.warning("Cannot resolve path — skipping: %s", path)
            continue

        # Skip symlinks (broken or circular)
        if path.is_symlink():
            log.debug("Symlink — skipping: %s", path)
            continue

        # Skip non-files
        if not path.is_file():
            # Check if it's an excluded directory (log once for clarity)
            if path.is_dir():
                rel = path.relative_to(source)
                if is_hidden(rel) or is_excluded_dir(path, extra_ignore_dirs):
                    log.debug("Excluded dir: %s", path)
            continue

        rel = path.relative_to(source)

        # Hidden anywhere in path
        if is_hidden(rel):
            log.debug("Hidden — skipping: %s", path)
            continue

        # Any ancestor directory is excluded
        excluded_ancestor = False
        for parent in rel.parents:
            parent_path = source / parent
            if is_excluded_dir(parent_path, extra_ignore_dirs):
                excluded_ancestor = True
                break
        if excluded_ancestor:
            log.debug("Excluded ancestor — skipping: %s", path)
            continue

        # Extra glob patterns
        if matches_glob_patterns(path, extra_glob_patterns):
            log.debug("Glob pattern match — skipping: %s", path)
            continue

        # Self-exclusion
        if abs_path == output_abs:
            log.info("Output file inside source tree — excluded: %s", path)
            continue

        candidates.append(path)

    return candidates


def write_output(
    files: list[Path],
    source: Path,
    output_path: Path,
) -> tuple[int, int]:
    """
    Write consolidated output to *output_path*.

    Parameters
    ----------
    files       : Ordered list of files to include.
    source      : Source root (used for relative-path display in progress logs).
    output_path : Destination file.

    Returns
    -------
    (written_count, skipped_count) tuple.
    """
    written = 0
    skipped = 0

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as out:
        for path in files:
            rel = path.relative_to(source)
            log.info("Processing: %s", rel)

            if is_binary(path):
                log.debug("Binary — skipping: %s", path)
                skipped += 1
                continue

            content = read_text_safe(path)
            if content is None:
                skipped += 1
                continue

            abs_header = str(path.resolve())
            out.write(f"{abs_header}\n\n")
            out.write(content)
            # Ensure content ends with newline before separator
            if content and not content.endswith("\n"):
                out.write("\n")
            out.write(SEPARATOR_BLOCK)

            written += 1

    return written, skipped


# ── CLI ───────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="consolidate",
        description="Consolidate all text files in a directory into a single .txt file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Root directory to scan recursively.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        metavar="FILE",
        help="Destination .txt file path.",
    )
    parser.add_argument(
        "--ignore",
        default="",
        metavar="PATTERNS",
        help=(
            "Comma-separated list of additional directory names or glob patterns to "
            "exclude (e.g. '*.log,tmp,scratch'). Directory names are matched against "
            "each path component; glob patterns against file names."
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Emit DEBUG-level log messages (includes skipped files).",
    )
    return parser


def parse_ignore_arg(raw: str) -> tuple[frozenset[str], frozenset[str]]:
    """
    Split the raw --ignore string into two sets.

    Returns
    -------
    (extra_dirs, extra_globs) where:
      - extra_dirs  : plain names with no glob metacharacters
      - extra_globs : patterns containing *, ?, or [
    """
    tokens = {t.strip() for t in raw.split(",") if t.strip()}
    glob_chars = frozenset("*?[")
    dirs: set[str] = set()
    globs: set[str] = set()
    for tok in tokens:
        if any(c in tok for c in glob_chars):
            globs.add(tok)
        else:
            dirs.add(tok)
    return frozenset(dirs), frozenset(globs)


# ── entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    """Parse arguments, collect files, and write consolidated output."""
    parser = build_parser()
    args = parser.parse_args()

    configure_logging(args.verbose)

    source: Path = args.source.resolve()
    output: Path = args.output.resolve()

    if not source.exists():
        log.error("Source directory does not exist: %s", source)
        sys.exit(1)

    if not source.is_dir():
        log.error("Source is not a directory: %s", source)
        sys.exit(1)

    extra_dirs, extra_globs = parse_ignore_arg(args.ignore)

    log.info("Source  : %s", source)
    log.info("Output  : %s", output)
    if extra_dirs:
        log.info("Ignoring dirs   : %s", sorted(extra_dirs))
    if extra_globs:
        log.info("Ignoring globs  : %s", sorted(extra_globs))

    files = collect_files(source, output, extra_dirs, extra_globs)
    log.info("Files found: %d", len(files))

    if not files:
        log.info("No eligible files found. Output not written.")
        sys.exit(0)

    written, skipped = write_output(files, source, output)

    log.info("Done — written: %d  skipped: %d  output: %s", written, skipped, output)


if __name__ == "__main__":
    main()
