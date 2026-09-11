from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SourceLocation:
    path: Path
    line: int = 1
    column: int = 1

    def __str__(self) -> str:
        return f"{self.path}:{self.line}:{self.column}"


class PoemError(Exception):
    """An error suitable for showing directly to a writer."""

    def __init__(self, message: str, location: SourceLocation | None = None, hint: str | None = None):
        super().__init__(message)
        self.message = message
        self.location = location
        self.hint = hint

    def pretty(self) -> str:
        where = f"{self.location}: " if self.location else ""
        result = f"error: {where}{self.message}"
        if self.hint:
            result += f"\n  hint: {self.hint}"
        return result


@dataclass(slots=True)
class WarningMessage:
    message: str
    location: SourceLocation | None = None

    def pretty(self) -> str:
        where = f"{self.location}: " if self.location else ""
        return f"warning: {where}{self.message}"

