from __future__ import annotations

from dataclasses import dataclass, fields, replace
from pathlib import Path
import re
import tomllib

from .errors import PoemError


@dataclass(frozen=True, slots=True)
class Theme:
    name: str
    description: str
    body_font: str
    title_font: str
    body_size: float
    line_height: float
    poem_title_size: float
    collection_title_size: float
    margin_inner_mm: float
    margin_outer_mm: float
    margin_top_mm: float
    margin_bottom_mm: float
    stanza_gap_em: float
    poem_title_gap_em: float
    continuation_indent_em: float
    title_align: str
    poem_align: str
    page_number_position: str
    ornament: str
    text_color: str = "191919"
    accent_color: str = "555555"
    background_color: str = "FFFFFF"
    title_letter_spacing: float = 0.0
    collection_title_case: str = "as-written"
    poem_title_case: str = "as-written"
    title_page_top_fraction: float = 0.20
    section_title_size: float = 9.0
    section_letter_spacing: float = 7.0
    section_case: str = "uppercase"
    section_align: str = "left"
    section_gap_em: float = 2.2


BUILTIN_THEMES: dict[str, Theme] = {
    "literary-classic": Theme(
        name="literary-classic", description="Warm, restrained literary book",
        body_font="TeX Gyre Pagella", title_font="TeX Gyre Pagella",
        body_size=11.0, line_height=15.5, poem_title_size=17.0,
        collection_title_size=30.0, margin_inner_mm=22, margin_outer_mm=19,
        margin_top_mm=24, margin_bottom_mm=25, stanza_gap_em=1.0,
        poem_title_gap_em=1.8, continuation_indent_em=1.5,
        title_align="center", poem_align="left", page_number_position="outer",
        ornament="•", text_color="211E1A", accent_color="756653",
    ),
    "modern-minimal": Theme(
        name="modern-minimal", description="Airy contemporary editorial design",
        body_font="TeX Gyre Heros", title_font="TeX Gyre Heros",
        body_size=10.5, line_height=15.0, poem_title_size=16.0,
        collection_title_size=32.0, margin_inner_mm=21, margin_outer_mm=23,
        margin_top_mm=27, margin_bottom_mm=24, stanza_gap_em=1.15,
        poem_title_gap_em=2.2, continuation_indent_em=1.5,
        title_align="left", poem_align="left", page_number_position="center",
        ornament="—", text_color="151515", accent_color="6B6B6B",
        title_page_top_fraction=0.14, section_title_size=8.5,
    ),
    "quiet-manuscript": Theme(
        name="quiet-manuscript", description="Intimate, tactile manuscript character",
        body_font="Latin Modern Mono", title_font="Latin Modern Roman",
        body_size=10.2, line_height=15.2, poem_title_size=16.0,
        collection_title_size=28.0, margin_inner_mm=20, margin_outer_mm=18,
        margin_top_mm=23, margin_bottom_mm=25, stanza_gap_em=1.05,
        poem_title_gap_em=1.7, continuation_indent_em=2.0,
        title_align="center", poem_align="left", page_number_position="center",
        ornament="· · ·", text_color="24211E", accent_color="766F68",
        title_page_top_fraction=0.22, section_case="as-written", section_align="center",
    ),
    "romantic-garden": Theme(
        name="romantic-garden", description="Soft, lyrical pages with a botanical warmth",
        body_font="TeX Gyre Bonum", title_font="TeX Gyre Bonum",
        body_size=11.0, line_height=16.2, poem_title_size=18.0,
        collection_title_size=31.0, margin_inner_mm=23, margin_outer_mm=21,
        margin_top_mm=28, margin_bottom_mm=26, stanza_gap_em=1.2,
        poem_title_gap_em=2.1, continuation_indent_em=1.4,
        title_align="center", poem_align="left", page_number_position="center",
        ornament="• • •", text_color="302421", accent_color="986F72",
        background_color="FFFCF8", title_letter_spacing=1.5,
        title_page_top_fraction=0.24, section_align="center", section_gap_em=2.6,
    ),
    "midnight-ink": Theme(
        name="midnight-ink", description="A dark, atmospheric screen-reading edition",
        body_font="TeX Gyre Schola", title_font="TeX Gyre Schola",
        body_size=11.0, line_height=16.0, poem_title_size=18.0,
        collection_title_size=30.0, margin_inner_mm=22, margin_outer_mm=20,
        margin_top_mm=25, margin_bottom_mm=25, stanza_gap_em=1.1,
        poem_title_gap_em=2.0, continuation_indent_em=1.5,
        title_align="center", poem_align="left", page_number_position="outer",
        ornament="•", text_color="E7E8EE", accent_color="93A7CC",
        background_color="161B26", title_letter_spacing=2.0,
        title_page_top_fraction=0.24, section_align="center", section_letter_spacing=9,
    ),
    "editorial-serif": Theme(
        name="editorial-serif", description="Confident journal typography with crisp sans titles",
        body_font="TeX Gyre Schola", title_font="TeX Gyre Adventor",
        body_size=10.5, line_height=15.0, poem_title_size=16.0,
        collection_title_size=34.0, margin_inner_mm=20, margin_outer_mm=24,
        margin_top_mm=24, margin_bottom_mm=23, stanza_gap_em=0.9,
        poem_title_gap_em=1.6, continuation_indent_em=1.4,
        title_align="left", poem_align="left", page_number_position="outer",
        ornament="—", text_color="161616", accent_color="A44332",
        title_letter_spacing=1.0, collection_title_case="uppercase",
        title_page_top_fraction=0.16, section_title_size=8.5, section_letter_spacing=4,
    ),
    "spare-haiku": Theme(
        name="spare-haiku", description="Meditative composition with radical whitespace",
        body_font="Libertinus Serif", title_font="Libertinus Serif",
        body_size=11.0, line_height=17.0, poem_title_size=14.0,
        collection_title_size=25.0, margin_inner_mm=30, margin_outer_mm=30,
        margin_top_mm=34, margin_bottom_mm=30, stanza_gap_em=1.5,
        poem_title_gap_em=2.8, continuation_indent_em=1.0,
        title_align="center", poem_align="left", page_number_position="center",
        ornament="○", text_color="292929", accent_color="868686",
        title_letter_spacing=3.0, title_page_top_fraction=0.27,
        section_title_size=8.0, section_case="lowercase", section_align="center", section_gap_em=3.0,
    ),
    "bold-broadsheet": Theme(
        name="bold-broadsheet", description="Large, assertive display type inspired by poetry posters",
        body_font="TeX Gyre Termes", title_font="TeX Gyre Heros",
        body_size=11.5, line_height=15.5, poem_title_size=22.0,
        collection_title_size=38.0, margin_inner_mm=18, margin_outer_mm=18,
        margin_top_mm=21, margin_bottom_mm=22, stanza_gap_em=1.0,
        poem_title_gap_em=1.4, continuation_indent_em=1.2,
        title_align="left", poem_align="left", page_number_position="outer",
        ornament="—", text_color="111111", accent_color="111111",
        title_letter_spacing=0.5, poem_title_case="uppercase",
        title_page_top_fraction=0.12, section_title_size=10.0, section_letter_spacing=2,
    ),
}

# TeX Live filenames used by `poem doctor`; themes themselves refer to family
# names so LuaLaTeX can choose bold and italic faces automatically.
REQUIRED_FONT_FILES = {
    "texgyrepagella-regular.otf", "texgyreheros-regular.otf",
    "lmmono10-regular.otf", "lmroman10-regular.otf",
    "texgyrebonum-regular.otf", "texgyreschola-regular.otf",
    "texgyreadventor-regular.otf", "LibertinusSerif-Regular.otf",
    "texgyretermes-regular.otf",
}

_NUMERIC_RANGES = {
    "body_size": (7, 24), "line_height": (8, 36), "poem_title_size": (9, 48),
    "collection_title_size": (12, 72), "margin_inner_mm": (5, 60),
    "margin_outer_mm": (5, 60), "margin_top_mm": (5, 70),
    "margin_bottom_mm": (5, 70), "stanza_gap_em": (0.2, 5),
    "poem_title_gap_em": (0, 8), "continuation_indent_em": (0, 8),
    "title_letter_spacing": (0, 20),
    "title_page_top_fraction": (0.05, 0.4), "section_title_size": (6, 24),
    "section_letter_spacing": (0, 20), "section_gap_em": (0, 8),
}
_SAFE_KEYS = {f.name for f in fields(Theme)} - {"name", "description"}


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    light, dark = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def _validate_coherence(theme: Theme) -> None:
    if theme.line_height < theme.body_size * 1.1:
        raise PoemError(
            "theme line_height is too tight for body_size",
            hint=f"Use line_height of at least {theme.body_size * 1.1:.1f} for body_size {theme.body_size:.1f}.",
        )
    ratio = _contrast(theme.text_color, theme.background_color)
    if ratio < 3.0:
        raise PoemError(
            f"theme text has insufficient contrast ({ratio:.2f}:1)",
            hint="Choose more distinct text_color and background_color values (at least 3:1).",
        )


def load_theme(name: str, custom_file: Path | None = None) -> Theme:
    if name not in BUILTIN_THEMES:
        choices = ", ".join(BUILTIN_THEMES)
        raise PoemError(f"unknown theme {name!r}", hint=f"Available themes: {choices}")
    theme = BUILTIN_THEMES[name]
    if custom_file is None:
        return theme
    try:
        data = tomllib.loads(custom_file.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise PoemError(f"could not read theme file {custom_file}: {exc}") from exc
    base = data.pop("extends", name)
    if not isinstance(base, str) or base not in BUILTIN_THEMES:
        raise PoemError(f"theme extends unknown built-in theme {base!r}")
    theme = BUILTIN_THEMES[base]
    unknown = set(data) - _SAFE_KEYS
    if unknown:
        raise PoemError(f"unknown theme setting {sorted(unknown)[0]!r}", hint="Run `poem themes --details` to see supported settings.")
    for key, value in data.items():
        if key in _NUMERIC_RANGES:
            low, high = _NUMERIC_RANGES[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
                raise PoemError(f"theme setting {key!r} must be between {low} and {high}")
        elif key in {"title_align", "poem_align", "section_align"} and value not in {"left", "center", "right"}:
            raise PoemError(f"theme setting {key!r} must be left, center, or right")
        elif key == "page_number_position" and value not in {"outer", "center", "hidden"}:
            raise PoemError("page_number_position must be outer, center, or hidden")
        elif key in {"collection_title_case", "poem_title_case", "section_case"} and value not in {"as-written", "uppercase", "lowercase"}:
            raise PoemError(f"theme setting {key!r} must be as-written, uppercase, or lowercase")
        elif not isinstance(value, str):
            raise PoemError(f"theme setting {key!r} must be text")
        elif key in {"body_font", "title_font"} and not re.fullmatch(r"[\w .-]{1,80}", value):
            raise PoemError(f"theme setting {key!r} contains unsupported characters")
        elif key in {"text_color", "accent_color", "background_color"} and not re.fullmatch(r"[0-9A-Fa-f]{6}", value):
            raise PoemError(f"theme setting {key!r} must be a six-digit hexadecimal color")
        elif key == "ornament" and (len(value) > 12 or any(char in value for char in "\\{}")):
            raise PoemError("theme ornament must be at most 12 plain characters")
    customized = replace(theme, name=custom_file.stem, description=f"Custom theme based on {base}", **data)
    _validate_coherence(customized)
    return customized
