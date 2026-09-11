from __future__ import annotations

import argparse
from dataclasses import fields
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from . import __version__
from .compiler import compile_generated, compile_pdf, generate, load_document, slugify
from .errors import PoemError
from .gallery import build_gallery
from .model import Poem
from .parser import is_collection, parse_collection
from .render import render_collection
from .themes import BUILTIN_THEMES, REQUIRED_FONT_FILES, Theme, load_theme


def _path(value: str) -> Path:
    path = Path(value)
    if path.suffix != ".poem":
        raise argparse.ArgumentTypeError("source files must use the .poem extension")
    return path


def _default_source() -> Path:
    preferred = Path("book.poem")
    if preferred.exists():
        return preferred
    roots = [path for path in Path.cwd().glob("*.poem") if is_collection(path)]
    if len(roots) == 1:
        return roots[0]
    if not roots:
        raise PoemError("no collection found", hint="Run `poem init NAME`, or pass a .poem file.")
    raise PoemError("more than one collection found", hint="Choose one explicitly: poem build path/to/book.poem")


def _source(value: Path | None) -> Path:
    return (value or _default_source()).resolve()


def _show_result(result, action: str = "built") -> None:
    for warning in result.warnings:
        print(warning.pretty(), file=sys.stderr)
    print(f"✓ {action} {result.pdf}")


def command_build(args: argparse.Namespace) -> int:
    result = compile_pdf(_source(args.source), args.output, theme_override=args.theme)
    _show_result(result)
    return 0


def command_check(args: argparse.Namespace) -> int:
    source = _source(args.source)
    collection, warnings = load_document(source, preview_fragment=True)
    load_theme(collection.theme, collection.theme_file)
    for warning in warnings:
        print(warning.pretty(), file=sys.stderr)
    count = sum(isinstance(item, Poem) for item in collection.items)
    kind = "collection" if is_collection(source) else "poem"
    print(f"✓ {source}: valid {kind} ({count} poem{'s' if count != 1 else ''})")
    return 0


def _snapshot(paths: set[Path]) -> dict[Path, int | None]:
    result = {}
    for path in paths:
        try:
            result[path] = path.stat().st_mtime_ns
        except OSError:
            result[path] = None
    return result


def _find_collection_for(fragment: Path):
    fragment = fragment.resolve()
    for directory in [fragment.parent, *fragment.parents]:
        matches = []
        for candidate in sorted(directory.glob("*.poem")):
            if not is_collection(candidate):
                continue
            try:
                collection = parse_collection(candidate)
            except PoemError:
                continue
            if fragment in collection.dependencies:
                matches.append(collection)
        if len(matches) > 1:
            names = ", ".join(item.source.name for item in matches)
            raise PoemError(
                f"poem belongs to more than one collection: {names}",
                hint="Preview a collection explicitly, or move each collection into its own directory.",
            )
        if matches:
            return matches[0]
        if directory == Path.cwd().anchor:
            break
    return None


def command_preview(args: argparse.Namespace) -> int:
    source = _source(args.source)
    fragment = not is_collection(source)
    inherited_state = [_find_collection_for(source) if fragment else None]

    def build_once():
        inherited = _find_collection_for(source) if fragment else None
        inherited_state[0] = inherited
        if inherited:
            # A fragment preview remains focused, but inherits its collection's safe theme.
            inherited_output = args.output or inherited.source.parent / "build"
            result = generate(source, inherited_output, preview_fragment=True, theme_override=args.theme)
            result.collection.theme = args.theme or inherited.theme
            result.collection.theme_file = None if args.theme else inherited.theme_file
            result.collection.language = inherited.language
            result.collection.paper = inherited.paper
            result.collection.smart_quotes = inherited.smart_quotes
            result.collection.author = inherited.author
            # Regenerate now that preview metadata has inherited the project design.
            theme = load_theme(inherited.theme, inherited.theme_file)
            result.tex.write_text(render_collection(result.collection, theme), encoding="utf-8")
            return compile_generated(result)
        return compile_pdf(source, args.output, preview_fragment=fragment, theme_override=args.theme)

    try:
        result = build_once()
        _show_result(result, "previewed")
    except PoemError:
        raise
    if not args.no_open:
        opener = shutil.which("xdg-open")
        if opener:
            subprocess.Popen([opener, str(result.pdf)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            print("warning: xdg-open is unavailable; open the PDF path shown above", file=sys.stderr)
    if args.once:
        return 0

    print("Watching for changes. Press Ctrl+C to stop.")
    watched = set(result.collection.dependencies)
    inherited = inherited_state[0]
    if inherited:
        watched |= inherited.dependencies
    state = _snapshot(watched)
    try:
        while True:
            time.sleep(args.interval)
            current = _snapshot(watched)
            if current == state:
                continue
            state = current
            time.sleep(0.12)  # absorb an editor's atomic-save burst
            try:
                result = build_once()
                inherited = inherited_state[0]
                watched = set(result.collection.dependencies) | (inherited.dependencies if inherited else set())
                state = _snapshot(watched)
                _show_result(result, "updated")
            except PoemError as exc:
                print(exc.pretty(), file=sys.stderr)
                print("Keeping the last successful PDF; still watching.", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nPreview stopped.")
    return 0


def command_themes(args: argparse.Namespace) -> int:
    if args.example:
        theme = BUILTIN_THEMES[args.example]
        print(f'# Complete safe metatemplate based on {theme.name}.')
        print(f'extends = {json.dumps(theme.name)}')
        for field in fields(Theme):
            if field.name in {"name", "description"}:
                continue
            value = getattr(theme, field.name)
            encoded = json.dumps(value, ensure_ascii=False) if isinstance(value, str) else str(value).lower()
            print(f"{field.name} = {encoded}")
        return 0
    for name, theme in BUILTIN_THEMES.items():
        marker = " (default)" if name == "literary-classic" else ""
        print(f"{name}{marker}\n  {theme.description}")
        if args.details:
            print(f"  body_font = {theme.body_font!r}\n  title_font = {theme.title_font!r}")
            print(f"  body_size = {theme.body_size}\n  line_height = {theme.line_height}")
            print(f"  margins = {theme.margin_inner_mm}/{theme.margin_outer_mm}/{theme.margin_top_mm}/{theme.margin_bottom_mm} mm")
            print(f"  colors = #{theme.text_color} on #{theme.background_color}, accent #{theme.accent_color}")
            print(f"  title_case = {theme.collection_title_case}/{theme.poem_title_case}, tracking = {theme.title_letter_spacing}")
            print(f"  section = {theme.section_align}/{theme.section_case}, {theme.section_title_size} pt")
    if args.details:
        print("\nCustom themes may override: body_font, title_font, body_size, line_height,")
        print("poem_title_size, collection_title_size, all margin_*_mm values, stanza_gap_em,")
        print("poem_title_gap_em, continuation_indent_em, title_align, poem_align,")
        print("page_number_position, ornament, text_color, accent_color, background_color,")
        print("title_letter_spacing, collection_title_case, and poem_title_case.")
        print("title_page_top_fraction, section_title_size, section_letter_spacing,")
        print("section_case, section_align, and section_gap_em.")
    return 0


def command_doctor(args: argparse.Namespace) -> int:
    """Explain whether this machine can build and preview PoemTeX projects."""
    required_commands = [("python3", "Python 3.11+"), ("lualatex", "LuaLaTeX PDF engine")]
    optional_commands = [("latexmk", "automatic TeX reruns"), ("xdg-open", "opening preview PDFs")]
    missing = False
    print("PoemTeX environment")
    for command, purpose in required_commands:
        found = shutil.which(command)
        print(f"  {'✓' if found else '✗'} {purpose}: {found or 'missing'}")
        missing |= found is None
    for command, purpose in optional_commands:
        found = shutil.which(command)
        print(f"  {'✓' if found else '·'} {purpose}: {found or 'optional; not found'}")

    kpsewhich = shutil.which("kpsewhich")
    packages = ["babel.sty", "fontspec.sty", "geometry.sty", "microtype.sty", "needspace.sty", "fancyhdr.sty", "hyperref.sty", "xcolor.sty"]
    if kpsewhich:
        absent = []
        for package in packages:
            check = subprocess.run([kpsewhich, package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if check.returncode:
                absent.append(package)
        if absent:
            missing = True
            print(f"  ✗ TeX packages: missing {', '.join(absent)}")
        else:
            print(f"  ✓ TeX packages: {len(packages)} required packages found")
        absent_fonts = []
        for font_file in sorted(REQUIRED_FONT_FILES):
            check = subprocess.run([kpsewhich, font_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if check.returncode:
                absent_fonts.append(font_file)
        if absent_fonts:
            missing = True
            print(f"  ✗ Theme fonts: missing {', '.join(absent_fonts)}")
        else:
            print(f"  ✓ Theme fonts: {len(REQUIRED_FONT_FILES)} font families/files found")
    elif shutil.which("lualatex"):
        print("  · TeX package inspection: kpsewhich unavailable")
    if missing:
        print("\nInstall a reasonably complete TeX Live distribution with LuaLaTeX.")
        return 1
    print("\n✓ Ready to build poems.")
    return 0


def command_gallery(args: argparse.Namespace) -> int:
    source = _source(args.source)
    if not is_collection(source):
        raise PoemError("a theme gallery needs a collection", hint="Pass its @collection root, not one poem fragment.")
    output = (args.output or source.parent / "build" / "theme-gallery").resolve()
    index, combined, contact = build_gallery(source, output)
    print(f"✓ gallery: {index}")
    if combined:
        print(f"✓ combined PDF: {combined}")
    if contact:
        print(f"✓ contact sheet: {contact}")
    if args.open:
        opener = shutil.which("xdg-open")
        if opener:
            subprocess.Popen([opener, str(index)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            print("warning: xdg-open is unavailable; open index.html manually", file=sys.stderr)
    return 0


def command_init(args: argparse.Namespace) -> int:
    target = Path(args.name).resolve()
    if target.exists() and any(target.iterdir()):
        raise PoemError(f"directory is not empty: {target}", hint="Choose a new project name.")
    target.mkdir(parents=True, exist_ok=True)
    (target / "poems").mkdir(exist_ok=True)
    (target / "theme").mkdir(exist_ok=True)
    (target / "book.poem").write_text(
        '@collection\n@title "Mój tomik"\n@author "Twoje imię"\n@language pl\n'
        '@theme literary-classic\n@theme-file theme/theme.toml\n@paper a5\n'
        '@contents yes\n@page-numbers yes\n\n@include poems/pierwszy.poem\n', encoding="utf-8")
    (target / "poems" / "pierwszy.poem").write_text(
        '@title "Pierwszy wiersz"\n\nPierwsza linia,\n    linia z wcięciem.\n\nDruga strofa\npozostaje sobą.\n', encoding="utf-8")
    (target / "theme" / "theme.toml").write_text(
        '# Bezpieczne ustawienia wyglądu — to nie jest kod TeX.\nextends = "literary-classic"\n'
        '# stanza_gap_em = 1.0\n# ornament = "•"\n', encoding="utf-8")
    print(f"✓ created {target}")
    print(f"  cd {target} && poem preview")
    return 0


def command_new(args: argparse.Namespace) -> int:
    title = args.title.strip()
    if not title or "\n" in title or "\r" in title:
        raise PoemError("poem title must be one non-empty line")
    collection_path = _source(args.collection)
    collection = parse_collection(collection_path)
    project_root = collection_path.parent.resolve()
    poems_dir = (project_root / args.directory).resolve()
    try:
        poems_dir.relative_to(project_root)
    except ValueError as exc:
        raise PoemError("poem directory must stay inside the collection project") from exc
    poems_dir.mkdir(parents=True, exist_ok=True)
    filename = args.filename or f"{slugify(title)}.poem"
    if Path(filename).name != filename or not filename.endswith(".poem"):
        raise PoemError("--filename must be a simple name ending in .poem")
    poem_path = poems_dir / filename
    if poem_path.exists():
        raise PoemError(f"poem already exists: {poem_path}", hint="Choose a different title or --filename.")
    poem_path.write_text(f"@title {title}\n\nPierwsza linia.\n", encoding="utf-8")
    if not args.no_include:
        relative = poem_path.relative_to(project_root).as_posix()
        existing = collection_path.read_text(encoding="utf-8")
        collection_path.write_text(existing.rstrip() + f"\n\n@include {relative}\n", encoding="utf-8")
    print(f"✓ created {poem_path}")
    if not args.no_include:
        print(f"✓ included in {collection_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="poem", description="Write poems, not TeX.")
    parser.add_argument("--version", action="version", version=f"PoemTeX {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="compile a collection to PDF")
    build.add_argument("source", nargs="?", type=_path)
    build.add_argument("-o", "--output", type=Path, help="output directory (default: build)")
    build.add_argument("--theme", choices=BUILTIN_THEMES, help="temporarily use a built-in theme")
    build.set_defaults(func=command_build)
    check = sub.add_parser("check", help="validate without running TeX")
    check.add_argument("source", nargs="?", type=_path)
    check.add_argument("-o", "--output", type=Path, help=argparse.SUPPRESS)
    check.set_defaults(func=command_check)
    preview = sub.add_parser("preview", help="build, open, and watch for changes")
    preview.add_argument("source", nargs="?", type=_path)
    preview.add_argument("-o", "--output", type=Path)
    preview.add_argument("--theme", choices=BUILTIN_THEMES, help="temporarily preview a built-in theme")
    preview.add_argument("--no-open", action="store_true", help="do not open a PDF viewer")
    preview.add_argument("--once", action="store_true", help="build once instead of watching")
    preview.add_argument("--interval", type=float, default=0.5, help=argparse.SUPPRESS)
    preview.set_defaults(func=command_preview)
    themes = sub.add_parser("themes", help="list the built-in visual themes")
    themes.add_argument("--details", action="store_true")
    themes.add_argument("--example", choices=BUILTIN_THEMES, help="print a complete TOML metatemplate")
    themes.set_defaults(func=command_themes)
    doctor = sub.add_parser("doctor", help="check Python, TeX, and preview dependencies")
    doctor.set_defaults(func=command_doctor)
    gallery = sub.add_parser("gallery", help="build comparable previews of every theme")
    gallery.add_argument("source", nargs="?", type=_path)
    gallery.add_argument("-o", "--output", type=Path, help="gallery directory")
    gallery.add_argument("--open", action="store_true", help="open the HTML gallery when finished")
    gallery.set_defaults(func=command_gallery)
    init = sub.add_parser("init", help="create a poetry collection project")
    init.add_argument("name", help="new project directory")
    init.set_defaults(func=command_init)
    new = sub.add_parser("new", help="create and include a new poem")
    new.add_argument("title", help="poem title")
    new.add_argument("--collection", type=_path, help="collection root (default: book.poem)")
    new.add_argument("--directory", default="poems", help="poem directory relative to the collection")
    new.add_argument("--filename", help="override the generated .poem filename")
    new.add_argument("--no-include", action="store_true", help="create the fragment without editing the collection")
    new.set_defaults(func=command_new)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return args.func(args)
    except PoemError as exc:
        print(exc.pretty(), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
