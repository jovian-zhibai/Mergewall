"""Structured diff data models.

Represents a parsed unified diff as a hierarchy of files, hunks, and lines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ChangeType(Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass
class DiffLine:
    """A single line in a diff hunk."""
    old_line: int | None
    new_line: int | None
    content: str
    change_type: str  # "+", "-", " "


@dataclass
class Hunk:
    """A contiguous block of changes within a file."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[DiffLine] = field(default_factory=list)
    context_header: str = ""

    @property
    def added_lines(self) -> list[DiffLine]:
        return [l for l in self.lines if l.change_type == "+"]

    @property
    def removed_lines(self) -> list[DiffLine]:
        return [l for l in self.lines if l.change_type == "-"]

    @property
    def added_content(self) -> str:
        return "\n".join(l.content for l in self.added_lines)


@dataclass
class FileDiff:
    """Structured representation of a single file's diff."""
    old_path: str
    new_path: str
    change_type: ChangeType
    hunks: list[Hunk] = field(default_factory=list)
    is_binary: bool = False
    language: str = ""

    @property
    def added_lines(self) -> list[DiffLine]:
        return [line for h in self.hunks for line in h.added_lines]

    @property
    def removed_lines(self) -> list[DiffLine]:
        return [line for h in self.hunks for line in h.removed_lines]

    @property
    def added_content(self) -> str:
        return "\n".join(l.content for l in self.added_lines)

    @property
    def removed_content(self) -> str:
        return "\n".join(l.content for l in self.removed_lines)

    @property
    def net_lines_changed(self) -> int:
        return len(self.added_lines) - len(self.removed_lines)


@dataclass
class StructuredDiff:
    """The full parsed diff for a PR, broken into per-file data."""
    files: list[FileDiff] = field(default_factory=list)
    base_ref: str = ""
    head_ref: str = ""

    @property
    def total_additions(self) -> int:
        return sum(len(f.added_lines) for f in self.files)

    @property
    def total_deletions(self) -> int:
        return sum(len(f.removed_lines) for f in self.files)

    @property
    def changed_paths(self) -> list[str]:
        return [f.new_path for f in self.files]
