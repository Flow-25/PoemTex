from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .errors import WarningMessage


Alignment = Literal["default", "left", "center", "right"]


@dataclass(slots=True)
class TextLine:
    text: str
    line_number: int
    alignment: Alignment = "default"


@dataclass(slots=True)
class StanzaBreak:
    lines: int = 1


BodyItem = TextLine | StanzaBreak


@dataclass(slots=True)
class Poem:
    source: Path
    title: str
    body: list[BodyItem]
    subtitle: str = ""
    author: str = ""
    dedication: str = ""
    epigraph: str = ""
    epigraph_author: str = ""


@dataclass(slots=True)
class Section:
    title: str
    line_number: int = 1


CollectionItem = Poem | Section


@dataclass(slots=True)
class Collection:
    source: Path
    title: str
    author: str
    items: list[CollectionItem]
    subtitle: str = ""
    language: str = "pl"
    theme: str = "literary-classic"
    paper: str = "a5"
    dedication: str = ""
    epigraph: str = ""
    epigraph_author: str = ""
    contents: bool = True
    page_numbers: bool = True
    smart_quotes: bool = True
    poem_pages: str = "new"
    show_title_page: bool = True
    theme_file: Path | None = None
    warnings: list[WarningMessage] = field(default_factory=list)
    dependencies: set[Path] = field(default_factory=set)
