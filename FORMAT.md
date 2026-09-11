# Poem format 0.1

This document defines the portable behavior of `.poem` files. “Must” denotes a
format requirement; visual measurements belong to the selected theme.

## Encoding and files

- Files must be UTF-8; a UTF-8 byte-order mark is accepted.
- A collection root must begin with `@collection` as its first nonblank,
  non-comment line. A file without it is a poem fragment.
- A collection root consists only of directives. A fragment has an initial
  metadata header followed by its body.
- A full-line comment starts with `;;` after optional indentation.
- Directive names are ASCII, lowercase by convention, and case-insensitive.

## Lines and spaces

- Each nonblank body line creates a poetic line in order.
- Leading and repeated interior ASCII spaces must be represented visually.
- Trailing whitespace has no effect.
- A tab is normalized to the next four-space tab stop and emits a warning.
- Any nonzero run of blank body lines becomes one stanza break.
- `@space N`, where `N` is 1–5, creates or replaces the preceding stanza break.
- Lines may wrap at word boundaries. Continuations use the theme's hanging
  indent. Automatic word hyphenation is disabled. A token longer than 55
  characters emits a warning because it may cross the page margin.
- A page break is strongly discouraged between two lines of the same stanza.
  Stanza boundaries are preferred break points; exceptionally long stanzas may
  still flow to the next page rather than overflowing it.

## Inline text

- `*text*` is emphasis, normally italic.
- `**text**` is strong emphasis, normally bold.
- `{smallcaps: text}` is small capitals.
- A backslash escapes `*`, `\`, or `"` in source text.
- Unpaired styling markers are rendered literally.
- Every TeX-special character is escaped by the compiler. No source construct
  injects raw TeX.

## Inclusion

- `@include` paths are relative to the collection root's directory.
- They must have a `.poem` suffix and remain within that directory after path
  resolution.
- Each target must be a fragment and may occur at most once in a collection.
- Items appear in directive order; `@section` participates in that order.

## Diagnostics

Malformed UTF-8, invalid or unknown directives, missing required metadata,
invalid values, missing includes, duplicate includes, root escapes, nested
alignment blocks, and unmatched `@align`/`@end` are errors. Diagnostics identify
the source path and line whenever possible. Tabs and empty poems are warnings.
