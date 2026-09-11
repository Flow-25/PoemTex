from __future__ import annotations

from pathlib import Path
import re

from .model import Collection, Poem, Section, StanzaBreak, TextLine
from .themes import Theme


TEX_ESCAPES = {
    "\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$",
    "&": r"\&", "#": r"\#", "%": r"\%", "_": r"\_",
    "^": r"\textasciicircum{}", "~": r"\textasciitilde{}",
}


def tex_escape(text: str) -> str:
    return "".join(TEX_ESCAPES.get(char, char) for char in text)


def smart_quotes(text: str) -> str:
    """Turn paired straight quotes into Polish outer/nested quotation marks."""
    output: list[str] = []
    depth = 0
    escaped = False
    for index, char in enumerate(text):
        if escaped:
            output.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
            output.append(char)
        elif char == '"':
            previous = text[index - 1] if index else ""
            following = text[index + 1] if index + 1 < len(text) else ""
            opening = depth == 0 or (
                bool(following) and not following.isspace()
                and (previous.isspace() or previous in "([{—–-")
            )
            output.append("„" if opening and depth == 0 else "«" if opening else "»" if depth > 1 else "”")
            depth += 1 if opening else -1
        else:
            output.append(char)
    return "".join(output) if depth == 0 else text


def _plain_with_spaces(text: str) -> str:
    escaped = tex_escape(text)
    escaped = re.sub(r" {2,}", lambda m: " " + rf"\hspace*{{{(len(m.group(0)) - 1) * 0.5:g}em}}", escaped)
    return escaped


def inline_tex(text: str, use_smart_quotes: bool = True) -> str:
    if use_smart_quotes:
        text = smart_quotes(text)
    leading = len(text) - len(text.lstrip(" "))
    text = text[leading:]
    out: list[str] = [rf"\hspace*{{{leading * 0.5:g}em}}"] if leading else []
    plain: list[str] = []
    i = 0

    def flush() -> None:
        if plain:
            out.append(_plain_with_spaces("".join(plain)))
            plain.clear()

    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text) and text[i + 1] in {"*", "\\", '"'}:
            plain.append(text[i + 1])
            i += 2
            continue
        if text.startswith("**", i):
            end = text.find("**", i + 2)
            if end >= 0:
                flush()
                out.append(r"\textbf{" + _plain_with_spaces(text[i + 2:end]) + "}")
                i = end + 2
                continue
        if text[i] == "*":
            end = text.find("*", i + 1)
            if end >= 0:
                flush()
                out.append(r"\emph{" + _plain_with_spaces(text[i + 1:end]) + "}")
                i = end + 1
                continue
        if text.startswith("{smallcaps:", i):
            end = text.find("}", i + 11)
            if end >= 0:
                flush()
                out.append(r"\textsc{" + _plain_with_spaces(text[i + 11:end].strip()) + "}")
                i = end + 1
                continue
        plain.append(text[i])
        i += 1
    flush()
    return "".join(out)


def _align_command(alignment: str, theme_default: str) -> str:
    if alignment == "default":
        alignment = theme_default
    return {"left": "PoemLine", "center": "PoemLineCenter", "right": "PoemLineRight"}[alignment]


def _poem_measure_em(poem: Poem, theme: Theme) -> float:
    """Estimate a comfortable verse measure for centered-title/left-body layouts."""
    if theme.title_align != "center" or theme.poem_align != "left":
        return 0.0
    longest = max(
        (len(item.text.expandtabs(4)) for item in poem.body if isinstance(item, TextLine)),
        default=0,
    )
    # The TeX side caps this at the available width. The floor keeps short poems
    # from collapsing into a narrow column while still centering their text block.
    return max(28.0, longest * 0.55)


def _render_poem(poem: Poem, theme: Theme, smart: bool, add_to_contents: bool = True) -> str:
    title = _title_case(inline_tex(poem.title, smart), theme.poem_title_case)
    subtitle = inline_tex(poem.subtitle, smart) if poem.subtitle else ""
    parts = [r"\PoemStart{" + title + "}{" + subtitle + "}"]
    if add_to_contents:
        parts.append(r"\phantomsection\addcontentsline{toc}{subsection}{" + inline_tex(poem.title, smart) + "}")
    if poem.dedication:
        parts.append(r"\PoemDedication{" + inline_tex(poem.dedication, smart) + "}")
    if poem.epigraph:
        parts.append(r"\PoemEpigraph{" + inline_tex(poem.epigraph, smart) + "}{" + inline_tex(poem.epigraph_author, smart) + "}")
    parts.append(rf"\begin{{PoemBody}}{{{_poem_measure_em(poem, theme):.2f}}}")
    for index, item in enumerate(poem.body):
        if isinstance(item, StanzaBreak):
            parts.append(rf"\StanzaBreak{{{item.lines}}}")
        else:
            command = _align_command(item.alignment, theme.poem_align)
            rendered = rf"\{command}{{{inline_tex(item.text, smart)}}}"
            if index + 1 < len(poem.body) and isinstance(poem.body[index + 1], TextLine):
                rendered += r"\nopagebreak[3]"
            parts.append(rendered)
    parts.extend([r"\end{PoemBody}", r"\PoemEnd"])
    return "\n".join(parts)


def _paper_option(paper: str) -> str:
    return {"a5": "a5paper", "a4": "a4paper", "letter": "letterpaper"}[paper]


def _title_case(text: str, setting: str) -> str:
    if setting == "uppercase":
        return r"\MakeUppercase{" + text + "}"
    if setting == "lowercase":
        return r"\MakeLowercase{" + text + "}"
    return text


def render_collection(collection: Collection, theme: Theme) -> str:
    lang = "polish" if collection.language.lower() in {"pl", "polish"} else "english"
    page_number = "" if not collection.page_numbers or theme.page_number_position == "hidden" else (
        r"\fancyfoot[LE,RO]{\small\thepage}" if theme.page_number_position == "outer" else r"\fancyfoot[C]{\small\thepage}"
    )
    title_declaration = {"left": r"\raggedright", "center": r"\centering", "right": r"\raggedleft"}[theme.title_align]
    section_declaration = {"left": r"\raggedright", "center": r"\centering", "right": r"\raggedleft"}[theme.section_align]
    display_collection_title = _title_case(inline_tex(collection.title, collection.smart_quotes), theme.collection_title_case)
    poem_break = r"\clearpage" if collection.poem_pages == "new" else r"\par\vspace{3\baselineskip}"
    preamble = rf"""% Generated by PoemTeX. Edit the .poem sources, not this file.
\documentclass[10pt,twoside,openany,{_paper_option(collection.paper)}]{{book}}
\usepackage[{lang}]{{babel}}
\usepackage{{fontspec}}
\usepackage{{geometry}}
\usepackage{{microtype}}
\usepackage{{needspace}}
\usepackage{{fancyhdr}}
\usepackage{{hyperref}}
\usepackage{{xcolor}}
\geometry{{inner={theme.margin_inner_mm}mm,outer={theme.margin_outer_mm}mm,top={theme.margin_top_mm}mm,bottom={theme.margin_bottom_mm}mm}}
\setmainfont{{{theme.body_font}}}
\newfontfamily\TitleFont{{{theme.title_font}}}
\definecolor{{PoemText}}{{HTML}}{{{theme.text_color}}}
\definecolor{{PoemAccent}}{{HTML}}{{{theme.accent_color}}}
\definecolor{{PoemBackground}}{{HTML}}{{{theme.background_color}}}
\pagecolor{{PoemBackground}}
\color{{PoemText}}
\hypersetup{{hidelinks,pdftitle={{{tex_escape(collection.title)}}},pdfauthor={{{tex_escape(collection.author)}}}}}
\setlength{{\parindent}}{{0pt}}
\frenchspacing
\hyphenpenalty=10000
\exhyphenpenalty=10000
\emergencystretch=1.5em
\pagestyle{{fancy}}
\fancyhf{{}}
{page_number}
\renewcommand{{\headrulewidth}}{{0pt}}
\newcommand{{\PoemStart}}[2]{{%
  \needspace{{7\baselineskip}}%
  {{{title_declaration}\TitleFont\addfontfeatures{{LetterSpace={theme.title_letter_spacing}}}\fontsize{{{theme.poem_title_size}}}{{{theme.poem_title_size * 1.2:.2f}}}\selectfont #1%
  \if\relax\detokenize{{#2}}\relax\else\\[.35em]\fontsize{{{theme.body_size}}}{{{theme.line_height}}}\selectfont\color{{PoemAccent}}#2\fi
  \par}}\vspace{{{theme.poem_title_gap_em}em}}%
}}%
\newdimen\PoemBodyWidth
\newdimen\PoemBodyInset
\newenvironment{{PoemBody}}[1]{{%
  \fontsize{{{theme.body_size}}}{{{theme.line_height}}}\selectfont
  \PoemBodyInset=0pt
  \PoemBodyWidth=#1em
  \ifdim\PoemBodyWidth>0pt
    \ifdim\PoemBodyWidth>.94\linewidth\PoemBodyWidth=.94\linewidth\fi
    \PoemBodyInset=\linewidth
    \advance\PoemBodyInset by -\PoemBodyWidth
    \divide\PoemBodyInset by 2
  \fi
  \leftskip=\PoemBodyInset\rightskip=\PoemBodyInset
}}{{\par}}
\newcommand{{\PoemLine}}[1]{{\par\noindent\hangindent={theme.continuation_indent_em}em\hangafter=1 #1\par}}
\newcommand{{\PoemLineCenter}}[1]{{\par{{\leftskip=\PoemBodyInset plus 1fil\rightskip=\PoemBodyInset plus 1fil\parfillskip=0pt #1\par}}}}
\newcommand{{\PoemLineRight}}[1]{{\par{{\leftskip=\PoemBodyInset plus 1fil\rightskip=\PoemBodyInset\parfillskip=0pt #1\par}}}}
\newcommand{{\StanzaBreak}}[1]{{\par\vspace{{#1\dimexpr {theme.stanza_gap_em}em\relax}}}}
\newcommand{{\PoemDedication}}[1]{{\begin{{flushright}}\itshape\color{{PoemAccent}}#1\end{{flushright}}\vspace{{1em}}}}
\newcommand{{\PoemEpigraph}}[2]{{\begin{{flushright}}\begin{{minipage}}{{.68\textwidth}}\itshape #1\if\relax\detokenize{{#2}}\relax\else\\[.35em]\upshape\small— #2\fi\end{{minipage}}\end{{flushright}}\vspace{{1.2em}}}}
\newcommand{{\PoemEnd}}{{\par}}
\newcommand{{\PoemBreak}}{{{poem_break}}}
\newcommand{{\SectionStart}}[1]{{%
  \needspace{{10\baselineskip}}%
  {{{section_declaration}\TitleFont\fontsize{{{theme.section_title_size}}}{{{theme.section_title_size * 1.25:.2f}}}\selectfont\addfontfeatures{{LetterSpace={theme.section_letter_spacing}}}\color{{PoemAccent}}#1\par}}%
  \vspace{{{theme.section_gap_em}em}}%
}}
\newcommand{{\CollectionOrnament}}{{\textcolor{{PoemAccent}}{{{tex_escape(theme.ornament)}}}}}
\begin{{document}}
"""
    if collection.show_title_page:
        preamble += rf"""\pagenumbering{{roman}}
\thispagestyle{{empty}}
\vspace*{{{theme.title_page_top_fraction}\textheight}}
{{{title_declaration}
{{\TitleFont\addfontfeatures{{LetterSpace={theme.title_letter_spacing}}}\fontsize{{{theme.collection_title_size}}}{{{theme.collection_title_size * 1.15:.2f}}}\selectfont {display_collection_title}\par}}
"""
        if collection.subtitle:
            preamble += rf"\vspace{{1em}}{{\TitleFont\large\color{{PoemAccent}} {inline_tex(collection.subtitle, collection.smart_quotes)}\par}}" + "\n"
        preamble += rf"""\vspace{{2.2em}}\CollectionOrnament\par}}
\vfill
{{{title_declaration}\TitleFont\large {inline_tex(collection.author, collection.smart_quotes)}\par}}
\clearpage
"""
    if collection.show_title_page and (collection.dedication or collection.epigraph):
        preamble += r"\thispagestyle{empty}\vspace*{.25\textheight}" + "\n"
        if collection.dedication:
            preamble += r"\begin{center}\itshape " + inline_tex(collection.dedication, collection.smart_quotes) + r"\end{center}" + "\n"
        if collection.epigraph:
            preamble += r"\PoemEpigraph{" + inline_tex(collection.epigraph, collection.smart_quotes) + "}{" + inline_tex(collection.epigraph_author, collection.smart_quotes) + "}\n"
        preamble += r"\clearpage" + "\n"
    if collection.show_title_page and collection.contents:
        preamble += r"\tableofcontents\clearpage" + "\n"
    preamble += (r"\clearpage\pagenumbering{arabic}" if collection.show_title_page else r"\pagenumbering{gobble}") + "\n"

    body: list[str] = []
    first_poem = True
    section_waiting = False
    for item in collection.items:
        if isinstance(item, Section):
            if not first_poem:
                body.append(r"\clearpage")
            section_title = _title_case(inline_tex(item.title, collection.smart_quotes), theme.section_case)
            body.append(r"\SectionStart{" + section_title + "}")
            if collection.contents:
                body.append(r"\addcontentsline{toc}{section}{" + inline_tex(item.title, collection.smart_quotes) + "}")
            section_waiting = True
        else:
            if not first_poem and not section_waiting:
                body.append(r"\PoemBreak")
            body.append(_render_poem(item, theme, collection.smart_quotes, add_to_contents=collection.contents))
            first_poem = False
            section_waiting = False
    return preamble + "\n".join(body) + "\n\\end{document}\n"


def fragment_collection(poem: Poem, theme_name: str = "literary-classic") -> Collection:
    return Collection(
        source=poem.source, title=poem.title, subtitle=poem.subtitle,
        author=poem.author or "Podgląd utworu", items=[poem], theme=theme_name,
        contents=False, page_numbers=False, poem_pages="flow", show_title_page=False,
        dependencies={poem.source},
    )
