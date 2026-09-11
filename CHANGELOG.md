# Changelog

## 0.2.0 — 2026-09-11

### Themes and previews

- Added Romantic Garden, Midnight Ink, Editorial Serif, Spare Haiku, and Bold
  Broadsheet alongside the three original themes.
- Added safe tokens for page background, title tracking and case, title-page
  position, and section typography.
- Added `poem gallery`, producing individual PDFs, representative title/poem
  images, labeled comparisons, a contact sheet, an HTML gallery, and a combined
  PDF.
- Gallery builds share one font cache and compile concurrently after warm-up.
- Added temporary `--theme` overrides to `build` and `preview`.
- Added `poem themes --example THEME` to emit a complete valid TOML template.

### Writing workflow

- Added `poem new TITLE` to create and include a safely named poem fragment.
- Added `poem doctor`, including checks for all required packages and theme
  fonts.
- Fragment previews inherit collection paper, language, author, quote rules,
  and theme while remaining focused one-page proofs.

### Typography and correctness

- Added nested Polish quote conversion (`„outer «inner» outer”`).
- Stanzas now strongly prefer to remain intact across page boundaries.
- Added missing-glyph warnings, long-token warnings, duplicate-metadata errors,
  ambiguous collection detection, and validation for theme contrast and line
  spacing.
- Fixed alignment-dependent title-page composition and made `poem_align`
  effective while retaining explicit per-block overrides.
- Centered-title themes now center the visual measure of left-aligned verse,
  keeping poem headings and bodies compositionally connected.
- PDF creation dates now reflect the build time unless the caller explicitly
  supplies `SOURCE_DATE_EPOCH` for a reproducible build.

## 0.1.0 — 2026-09-11

- Initial `.poem` parser, collection includes, three themes, LuaLaTeX compiler,
  live preview, Polish typography, safe styling, project initialization, format
  specification, example collection, and test suite.
