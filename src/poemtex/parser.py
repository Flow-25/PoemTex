from __future__ import annotations

from difflib import get_close_matches
from pathlib import Path
import re

from .errors import PoemError, SourceLocation, WarningMessage
from .model import Collection, Poem, Section, StanzaBreak, TextLine


COLLECTION_DIRECTIVES = {
    "collection", "title", "subtitle", "author", "language", "theme", "theme-file",
    "paper", "dedication", "epigraph", "epigraph-author", "contents", "page-numbers",
    "smart-quotes", "poem-pages", "include", "section",
}
POEM_HEADER_DIRECTIVES = {
    "title", "subtitle", "author", "dedication", "epigraph", "epigraph-author",
}
BODY_DIRECTIVES = {"align", "end", "space"}


def _value(text: str) -> str:
    value = text.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _directive(line: str) -> tuple[str, str] | None:
    match = re.match(r"^@([a-z][a-z-]*)(?:\s+(.*))?$", line.strip(), re.IGNORECASE)
    if not match:
        return None
    return match.group(1).lower(), _value(match.group(2) or "")


def _bool(value: str, location: SourceLocation) -> bool:
    normalized = value.lower()
    if normalized in {"yes", "true", "on"}:
        return True
    if normalized in {"no", "false", "off"}:
        return False
    raise PoemError(f"expected yes or no, got {value!r}", location)


def _unknown(name: str, allowed: set[str], location: SourceLocation) -> PoemError:
    matches = get_close_matches(name, allowed, n=1, cutoff=0.55)
    hint = f"Did you mean @{matches[0]}?" if matches else f"Known directives: {', '.join('@' + x for x in sorted(allowed))}"
    return PoemError(f"unknown directive @{name}", location, hint)


def parse_poem(path: Path) -> tuple[Poem, list[WarningMessage]]:
    path = path.resolve()
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise PoemError(f"poem file does not exist: {path}") from exc
    except UnicodeDecodeError as exc:
        raise PoemError(f"{path} is not valid UTF-8", hint="Save .poem files using UTF-8 encoding.") from exc

    metadata: dict[str, str] = {}
    metadata_lines: dict[str, int] = {}
    body: list[TextLine | StanzaBreak] = []
    warnings: list[WarningMessage] = []
    in_header = True
    alignment = "default"
    align_started: SourceLocation | None = None
    pending_blank = False

    for number, original in enumerate(raw.splitlines(), 1):
        location = SourceLocation(path, number)
        line = original.rstrip()
        if line.startswith("\t") or "\t" in line:
            line = line.expandtabs(4)
            warnings.append(WarningMessage("tab expanded to 4 spaces; spaces are more predictable in poems", location))

        directive = _directive(line) if line.lstrip().startswith("@") else None
        if in_header:
            if not line.strip() or line.lstrip().startswith(";;"):
                continue
            if directive:
                name, value = directive
                if name == "collection":
                    raise PoemError("a collection cannot be included as a poem", location, "Use `poem build` on the collection root instead.")
                if name not in POEM_HEADER_DIRECTIVES:
                    if name in BODY_DIRECTIVES:
                        in_header = False
                    else:
                        raise _unknown(name, POEM_HEADER_DIRECTIVES | BODY_DIRECTIVES, location)
                else:
                    if not value:
                        raise PoemError(f"@{name} needs a value", location)
                    if name in metadata:
                        raise PoemError(f"@{name} is specified more than once", location,
                                        f"The first value is on line {metadata_lines[name]}.")
                    metadata[name] = value
                    metadata_lines[name] = number
                    continue
            else:
                in_header = False

        if not line.strip():
            pending_blank = bool(body)
            continue
        if line.lstrip().startswith(";;"):
            continue
        if directive:
            name, value = directive
            if name == "align":
                if align_started:
                    raise PoemError("alignment blocks cannot be nested", location, f"The current block started at {align_started}.")
                if value not in {"left", "center", "right"}:
                    raise PoemError("@align must be followed by left, center, or right", location)
                alignment = value
                align_started = location
                continue
            if name == "end":
                if value:
                    raise PoemError("@end does not take a value", location)
                if not align_started:
                    raise PoemError("@end has no matching @align", location)
                alignment = "default"
                align_started = None
                continue
            if name == "space":
                try:
                    amount = int(value)
                except ValueError as exc:
                    raise PoemError("@space must be followed by a whole number from 1 to 5", location) from exc
                if not 1 <= amount <= 5:
                    raise PoemError("@space must be between 1 and 5", location)
                if body and not isinstance(body[-1], StanzaBreak):
                    body.append(StanzaBreak(amount))
                elif body:
                    body[-1] = StanzaBreak(amount)
                pending_blank = False
                continue
            raise _unknown(name, BODY_DIRECTIVES, location)
        if pending_blank:
            body.append(StanzaBreak())
            pending_blank = False
        body.append(TextLine(line, number, alignment))
        unbreakable = max((len(token) for token in line.split()), default=0)
        if unbreakable > 55:
            warnings.append(WarningMessage(
                f"very long unbroken text ({unbreakable} characters) may cross the page margin",
                location,
            ))

    if align_started:
        raise PoemError("unclosed @align block", align_started, "Add @end after the aligned lines.")
    title = metadata.get("title")
    if not title:
        raise PoemError("poem has no title", SourceLocation(path), "Add @title \"Your title\" at the top.")
    if not any(isinstance(item, TextLine) for item in body):
        warnings.append(WarningMessage("poem has no body", SourceLocation(path)))
    if metadata.get("epigraph-author") and not metadata.get("epigraph"):
        warnings.append(WarningMessage("@epigraph-author has no @epigraph to attribute", SourceLocation(path, metadata_lines["epigraph-author"])))
    poem = Poem(
        source=path, title=title, body=body, subtitle=metadata.get("subtitle", ""),
        author=metadata.get("author", ""), dedication=metadata.get("dedication", ""),
        epigraph=metadata.get("epigraph", ""), epigraph_author=metadata.get("epigraph-author", ""),
    )
    return poem, warnings


def parse_collection(path: Path) -> Collection:
    path = path.resolve()
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise PoemError(f"collection file does not exist: {path}") from exc
    except UnicodeDecodeError as exc:
        raise PoemError(f"{path} is not valid UTF-8", hint="Save .poem files using UTF-8 encoding.") from exc

    lines = raw.splitlines()
    first = next(((i, line) for i, line in enumerate(lines, 1) if line.strip() and not line.lstrip().startswith(";;")), None)
    if not first or _directive(first[1]) != ("collection", ""):
        raise PoemError("this is a poem fragment, not a collection", SourceLocation(path, first[0] if first else 1),
                        "A buildable root starts with @collection. Use `poem preview` to preview a fragment.")

    metadata: dict[str, str] = {}
    metadata_lines: dict[str, int] = {}
    item_specs: list[tuple[str, str, int]] = []
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(";;"):
            continue
        directive = _directive(line)
        if not directive:
            raise PoemError("collections may contain directives only", SourceLocation(path, number),
                            "Put poem text in a separate file and add it with @include.")
        name, value = directive
        if name not in COLLECTION_DIRECTIVES:
            raise _unknown(name, COLLECTION_DIRECTIVES, SourceLocation(path, number))
        if name == "collection":
            if number != first[0] or value:
                raise PoemError("@collection must appear once, without a value, at the start", SourceLocation(path, number))
            continue
        if not value:
            raise PoemError(f"@{name} needs a value", SourceLocation(path, number))
        if name in {"include", "section"}:
            item_specs.append((name, value, number))
        else:
            if name in metadata:
                raise PoemError(f"@{name} is specified more than once", SourceLocation(path, number),
                                f"The first value is on line {metadata_lines[name]}.")
            metadata[name] = value
            metadata_lines[name] = number

    if "title" not in metadata:
        raise PoemError("collection has no title", SourceLocation(path), "Add @title \"Collection title\".")
    if "author" not in metadata:
        raise PoemError("collection has no author", SourceLocation(path), "Add @author \"Author name\".")

    paper = metadata.get("paper", "a5").lower()
    if paper not in {"a5", "a4", "letter"}:
        raise PoemError(f"unsupported paper size {paper!r}", hint="Choose a5, a4, or letter.")
    poem_pages = metadata.get("poem-pages", "new").lower()
    if poem_pages not in {"new", "flow"}:
        raise PoemError("@poem-pages must be new or flow")
    language = metadata.get("language", "pl").lower()
    if language not in {"pl", "polish", "en", "english"}:
        raise PoemError(f"unsupported language {language!r}", hint="Version 0.1 supports pl and en.")

    root = path.parent.resolve()
    items: list[Poem | Section] = []
    dependencies = {path}
    warnings: list[WarningMessage] = []
    included: set[Path] = set()
    for kind, value, number in item_specs:
        if kind == "section":
            items.append(Section(value, number))
            continue
        include = (root / value).resolve()
        try:
            include.relative_to(root)
        except ValueError as exc:
            raise PoemError("included files must stay inside the project directory", SourceLocation(path, number)) from exc
        if include.suffix != ".poem":
            raise PoemError("included files must use the .poem extension", SourceLocation(path, number))
        if include in included:
            raise PoemError(f"poem included more than once: {value}", SourceLocation(path, number))
        included.add(include)
        poem, poem_warnings = parse_poem(include)
        items.append(poem)
        dependencies.add(include)
        warnings.extend(poem_warnings)

    if not any(isinstance(item, Poem) for item in items):
        warnings.append(WarningMessage("collection contains no poems", SourceLocation(path)))
    for current, following in zip(items, items[1:]):
        if isinstance(current, Section) and isinstance(following, Section):
            warnings.append(WarningMessage(
                f"section {current.title!r} has no poem beneath it",
                SourceLocation(path, current.line_number),
            ))
    if items and isinstance(items[-1], Section):
        warnings.append(WarningMessage("the final @section has no poem beneath it", SourceLocation(path, items[-1].line_number)))
    if metadata.get("epigraph-author") and not metadata.get("epigraph"):
        warnings.append(WarningMessage("@epigraph-author has no @epigraph to attribute", SourceLocation(path, metadata_lines["epigraph-author"])))

    theme_file = None
    if "theme-file" in metadata:
        theme_file = (root / metadata["theme-file"]).resolve()
        try:
            theme_file.relative_to(root)
        except ValueError as exc:
            raise PoemError("theme file must stay inside the project directory") from exc
        dependencies.add(theme_file)

    return Collection(
        source=path, title=metadata["title"], author=metadata["author"], items=items,
        subtitle=metadata.get("subtitle", ""), language=language,
        theme=metadata.get("theme", "literary-classic"), paper=paper,
        dedication=metadata.get("dedication", ""), epigraph=metadata.get("epigraph", ""),
        epigraph_author=metadata.get("epigraph-author", ""),
        contents=_bool(metadata.get("contents", "yes"), SourceLocation(path, metadata_lines.get("contents", 1))),
        page_numbers=_bool(metadata.get("page-numbers", "yes"), SourceLocation(path, metadata_lines.get("page-numbers", 1))),
        smart_quotes=_bool(metadata.get("smart-quotes", "yes"), SourceLocation(path, metadata_lines.get("smart-quotes", 1))),
        poem_pages=poem_pages, theme_file=theme_file, warnings=warnings,
        dependencies=dependencies,
    )


def is_collection(path: Path) -> bool:
    try:
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip() and not line.lstrip().startswith(";;"):
                return _directive(line) == ("collection", "")
    except OSError:
        return False
    return False
