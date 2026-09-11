# PoemTeX

**Write poems, not TeX.** PoemTeX is a small, safe language for writing poems in
`.poem` files and turning them into carefully typeset PDFs. It is designed first
for Polish-language poetry, complete collections, and writers who should never
need to see a LaTeX command.

This is an evolving Linux prototype. The file format is deliberately narrow: it
values readable sources, predictable typography, and friendly errors over a vast
set of features.

The complete user manual is available as LaTeX source in
[`docs/poemtex-user-guide.tex`](docs/poemtex-user-guide.tex). A locally compiled,
nine-page PDF is written to `docs/build/poemtex-user-guide.pdf`.

## A first collection

The root file explicitly declares itself as a collection:

```poem
@collection
@title "Światło i cisza"
@author "Anna Kowalska"
@language pl
@theme literary-classic
@paper a5

@section "Światło"
@include poems/poranek.poem
@include poems/okno.poem
```

Each included file contains one poem:

```poem
@title "Poranek"

Pierwsza linia,
    linia z wcięciem.

Druga strofa ma *cichy akcent*
i **mocniejsze słowo**.
```

Then:

```sh
poem check
poem build
poem preview
```

`preview` opens the PDF and watches every included poem and theme file. If an
edit contains an error, it explains the problem and keeps the last good PDF.
Use `poem preview poems/poranek.poem` to focus on one included poem while keeping
the collection's visual theme.

Compare a different design without editing the collection:

```sh
poem preview --theme modern-minimal
poem build --theme quiet-manuscript --output build/manuscript
```

Build browsable previews of every installed theme from identical content:

```sh
poem gallery --open
```

This creates individual PDFs, cover/section/poem thumbnails, a browsable
`index.html`, a contact sheet when ImageMagick is available, and a combined PDF
when Poppler's `pdfunite` is available.

## Install for development

Requirements are intentionally ordinary:

- Linux and Python 3.11 or newer;
- TeX Live with LuaLaTeX and common packages (`babel`, `fontspec`, `geometry`,
  `microtype`, `needspace`, `fancyhdr`, `hyperref`, and `xcolor`);
- `latexmk` is recommended, but PoemTeX falls back to running `lualatex` twice.

From this repository:

```sh
./poem --help
```

The local launcher has no Python installation step. To install the `poem`
command into a virtual environment instead:

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/poem --help
```

Or try it without installation:

```sh
PYTHONPATH=src python3 -m poemtex.cli build examples/swiatlo-i-cisza/book.poem
```

Start a separate collection with `poem init my-book`.
If compilation is unavailable on another Linux machine, `poem doctor` reports
the exact missing engine or TeX packages without exposing a TeX stack trace.

Inside a collection, create and include another poem without editing two files:

```sh
poem new "Nocne światło"
```

## The whitespace contract

Whitespace matters in poetry, so PoemTeX follows explicit rules:

1. Every nonblank source line is one poetic line. It is never joined to the next.
2. Leading spaces and repeated spaces inside a line are visually preserved.
3. Tabs become four spaces and produce a warning. Spaces are recommended.
4. Trailing spaces are ignored.
5. One or more blank lines produce one stanza gap. This prevents accidental
   editor whitespace from changing pagination.
6. For an intentionally larger gap, write `@space 2` through `@space 5`.
7. Long lines wrap at words with a hanging indent. They are never silently
   shrunk, and automatic hyphenation is disabled.

These rules are part of the format, not implementation accidents.

## Language reference

### Collection directives

`@collection` must be the first meaningful line. A collection then accepts:

| Directive | Meaning | Default |
|---|---|---|
| `@title TEXT` | Collection title | required |
| `@author TEXT` | Author | required |
| `@subtitle TEXT` | Optional subtitle | empty |
| `@language pl` | Polish or English typography | `pl` |
| `@theme NAME` | A built-in base theme | `literary-classic` |
| `@theme-file PATH` | Safe TOML theme overrides | none |
| `@paper a5` | `a5`, `a4`, or `letter` | `a5` |
| `@dedication TEXT` | Front-matter dedication | empty |
| `@epigraph TEXT` | Front-matter epigraph | empty |
| `@epigraph-author TEXT` | Epigraph attribution | empty |
| `@contents yes` | Show the contents page | `yes` |
| `@page-numbers yes` | Show page numbers | `yes` |
| `@smart-quotes yes` | Convert paired `"..."` to Polish quotes | `yes` |
| `@poem-pages new` | `new` page per poem, or `flow` | `new` |
| `@section TEXT` | Add a collection division | — |
| `@include PATH` | Insert a poem at this position | — |

Quoted and unquoted values both work. Paths are relative to the collection and
cannot escape its directory. Includes are explicit—there are no surprising
wildcards—and duplicate includes are diagnosed.

### Poem directives and styling

A poem header supports `@title`, `@subtitle`, `@author`, `@dedication`,
`@epigraph`, and `@epigraph-author`. After the body begins, only these structural
directives have special meaning:

```poem
@align right
tekst po prawej
jeszcze jedna linia
@end

@space 2
```

Inline styling is deliberately small:

- `*kursywa*`
- `**pogrubienie**`
- `{smallcaps: Kapitaliki}`
- `\*` for a literal asterisk

A line beginning with `;;` is a private comment. All TeX-special characters are
ordinary text. Raw TeX is not supported: this keeps documents safe, portable,
and independent from the PDF engine.

## Themes: templates for templates

PoemTeX includes eight starting points:

- `literary-classic` (default): warm TeX Gyre Pagella, balanced book proportions;
- `modern-minimal`: airy sans-serif editorial design;
- `quiet-manuscript`: intimate monospaced body with a restrained serif title;
- `romantic-garden`: warm ivory paper, rose details, and rounded Bonum type;
- `midnight-ink`: a dark navy screen edition with cool blue details;
- `editorial-serif`: journal-like serif text with crisp uppercase sans titles;
- `spare-haiku`: centered headings, left-set poems, and radical whitespace;
- `bold-broadsheet`: large display titles with compact Termes body text.

### Choosing a starting theme

| Theme | Best starting point for | Medium |
|---|---|---|
| Literary Classic | General poetry books and mixed-length collections | Print/PDF |
| Modern Minimal | Contemporary free verse and clean portfolios | Print/PDF |
| Quiet Manuscript | Intimate, diaristic, or archival-feeling work | Print/PDF |
| Romantic Garden | Lyrical, personal, and nature-centered collections | Print/PDF |
| Midnight Ink | Nocturnal work and atmospheric digital editions | Screen |
| Editorial Serif | Journal submissions and confident literary editions | Print/PDF |
| Spare Haiku | Haiku, fragments, and very short meditative poems | Print/PDF |
| Bold Broadsheet | Performance poetry and poster-like statements | Print/PDF |

Run `poem themes --details` to inspect them. A project may customize design
tokens in `theme/theme.toml` without writing TeX:

```sh
poem themes --example romantic-garden
```

The command prints a complete valid metatemplate. A smaller file may override
only the tokens it needs:

```toml
extends = "literary-classic"
body_size = 11.2
line_height = 16.0
stanza_gap_em = 1.15
ornament = "•"
accent_color = "6F5944"
background_color = "FFFCF8"
title_letter_spacing = 1.5
collection_title_case = "as-written"
poem_title_case = "as-written"
title_page_top_fraction = 0.20
section_align = "left"
section_case = "uppercase"
```

Unknown properties and unreasonable numeric values are errors. This token file
is the “metatemplate”: themes describe design decisions, while PoemTeX owns and
can improve the underlying typesetting machinery.

## Design boundaries for version 0.1

- Included poem files are fragments. `poem build fragment.poem` refuses to call
  one a finished book; `poem preview fragment.poem` intentionally wraps it.
- Images, arbitrary TeX, nested collections, EPUB, and side-by-side translation
  are not yet part of the language.
- Smart quote conversion changes only balanced straight double quotes. It does
  not guess at apostrophes or rewrite unmatched quotes.
- Generated `.tex` files in `build/` are useful for diagnosis but are not public
  source files and should not be edited.

See [FORMAT.md](FORMAT.md) for the compact normative format specification and
[CONTRIBUTING.md](CONTRIBUTING.md) for development notes. User-visible changes
are recorded in [CHANGELOG.md](CHANGELOG.md).

## License

MIT.
