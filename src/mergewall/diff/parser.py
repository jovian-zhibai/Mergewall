"""Unified diff parser.

Converts raw unified diff text (from GitHub API) into a StructuredDiff
with per-file, per-hunk, per-line data.
"""

from __future__ import annotations

import os
import re

from mergewall.diff.models import ChangeType, DiffLine, FileDiff, Hunk, StructuredDiff

_HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)")
_FILE_HEADER_RE = re.compile(r"^diff --git a/(.+) b/(.+)")


def parse_diff(raw_diff: str) -> StructuredDiff:
    """Parse a unified diff string into a StructuredDiff.

    Handles: binary files, renames, new/deleted files, empty hunks.
    """
    files: list[FileDiff] = []
    current_file: FileDiff | None = None
    current_hunk: Hunk | None = None
    new_line_counter: int = 0
    old_line_counter: int = 0

    for line in raw_diff.splitlines():
        # File header: "diff --git a/path b/path"
        file_match = _FILE_HEADER_RE.match(line)
        if file_match:
            if current_file:
                files.append(current_file)
            current_file = FileDiff(
                old_path=file_match.group(1),
                new_path=file_match.group(2),
                change_type=ChangeType.MODIFIED,
            )
            current_hunk = None
            new_line_counter = 0
            old_line_counter = 0
            continue

        if current_file is None:
            continue

        # Detect file metadata
        if line.startswith("rename from "):
            current_file.change_type = ChangeType.RENAMED
            continue
        if line.startswith("new file"):
            current_file.change_type = ChangeType.ADDED
            continue
        if line.startswith("deleted file"):
            current_file.change_type = ChangeType.DELETED
            continue
        if line.startswith("Binary files"):
            current_file.is_binary = True
            continue
        # Skip index lines, --- / +++ headers
        if line.startswith("index ") or line.startswith("--- ") or line.startswith("+++ "):
            continue

        # Hunk header
        hunk_match = _HUNK_HEADER_RE.match(line)
        if hunk_match:
            old_start = int(hunk_match.group(1))
            old_count = int(hunk_match.group(2) or "1")
            new_start = int(hunk_match.group(3))
            new_count = int(hunk_match.group(4) or "1")
            current_hunk = Hunk(
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                context_header=hunk_match.group(5).strip(),
            )
            current_file.hunks.append(current_hunk)
            new_line_counter = new_start
            old_line_counter = old_start
            continue

        # Diff content lines
        if current_hunk is not None and line:
            prefix = line[0]
            content = line[1:] if len(line) > 1 else ""

            if prefix == "+":
                current_hunk.lines.append(DiffLine(
                    old_line=None,
                    new_line=new_line_counter,
                    content=content,
                    change_type="+",
                ))
                new_line_counter += 1
            elif prefix == "-":
                current_hunk.lines.append(DiffLine(
                    old_line=old_line_counter,
                    new_line=None,
                    content=content,
                    change_type="-",
                ))
                old_line_counter += 1
            elif prefix == " ":
                current_hunk.lines.append(DiffLine(
                    old_line=old_line_counter,
                    new_line=new_line_counter,
                    content=content,
                    change_type=" ",
                ))
                new_line_counter += 1
                old_line_counter += 1

    if current_file:
        files.append(current_file)

    # Detect languages from file extensions
    from mergewall.utils.parser import EXT_LANG
    for f in files:
        ext = os.path.splitext(f.new_path)[1].lower()
        f.language = EXT_LANG.get(ext, "unknown")

    return StructuredDiff(files=files)
