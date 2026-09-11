from pathlib import Path
from dataclasses import replace
from tempfile import TemporaryDirectory
import unittest

from poemtex.compiler import _collect_latex_warnings, generate, slugify
from poemtex.errors import PoemError
from poemtex.model import Collection, Poem, TextLine
from poemtex.render import inline_tex, render_collection, smart_quotes, tex_escape
from poemtex.themes import BUILTIN_THEMES, load_theme


class RenderTests(unittest.TestCase):
    def test_all_tex_metacharacters_are_escaped(self):
        source = r"% # & _ { } $ ^ ~ \\input{secret}"
        rendered = tex_escape(source)
        self.assertNotIn(r"\input{secret}", rendered)
        for expected in (r"\%", r"\#", r"\&", r"\_", r"\$", r"\textbackslash{}"):
            self.assertIn(expected, rendered)

    def test_inline_styles_and_literal_asterisk(self):
        rendered = inline_tex(r"*cicho* **głośno** \*gwiazda", False)
        self.assertEqual(rendered, r"\emph{cicho} \textbf{głośno} *gwiazda")

    def test_unmatched_style_is_literal(self):
        self.assertEqual(inline_tex("*otwarte", False), "*otwarte")

    def test_missing_pdf_glyph_becomes_warning(self):
        warnings = _collect_latex_warnings("Missing character: There is no ❦ in font Example!\n")
        self.assertEqual(len(warnings), 1)
        self.assertIn("❦", warnings[0].message)

    def test_spaces_are_explicit(self):
        rendered = inline_tex("    a   b", False)
        self.assertTrue(rendered.startswith(r"\hspace*{2em}"))
        self.assertIn(r"\hspace*{1em}", rendered)

    def test_polish_smart_quotes(self):
        self.assertEqual(smart_quotes('Powiedział "cisza".'), "Powiedział „cisza”.")
        self.assertEqual(smart_quotes('"Powiedział "tak"."'), "„Powiedział «tak».”")
        self.assertEqual(smart_quotes('"raz" i "dwa"'), "„raz” i „dwa”")
        self.assertEqual(smart_quotes('Niedomknięty "tekst'), 'Niedomknięty "tekst')

    def test_slug_handles_polish(self):
        self.assertEqual(slugify("Światło i cisza"), "swiatlo-i-cisza")

    def test_generation_is_safe_and_contains_unicode(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "p.poem").write_text("@title P\n\nżąć % \\input{x}\n", encoding="utf-8")
            (root / "book.poem").write_text("@collection\n@title B\n@author A\n@include p.poem\n", encoding="utf-8")
            result = generate(root / "book.poem")
            tex = result.tex.read_text(encoding="utf-8")
            self.assertIn("żąć", tex)
            self.assertIn(r"\%", tex)
            self.assertNotIn(r"\input{x}", tex)

    def test_custom_theme_validates_keys_and_ranges(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bad.toml"
            path.write_text('extends="literary-classic"\nbody_size=100\n', encoding="utf-8")
            with self.assertRaisesRegex(PoemError, "between"):
                load_theme("literary-classic", path)
            path.write_text('extends="literary-classic"\nmagic=1\n', encoding="utf-8")
            with self.assertRaisesRegex(PoemError, "unknown theme setting"):
                load_theme("literary-classic", path)
            path.write_text('extends="literary-classic"\nbody_size=true\n', encoding="utf-8")
            with self.assertRaisesRegex(PoemError, "between"):
                load_theme("literary-classic", path)
            path.write_text('extends=["literary-classic"]\n', encoding="utf-8")
            with self.assertRaisesRegex(PoemError, "unknown built-in"):
                load_theme("literary-classic", path)
            path.write_text('extends="literary-classic"\nbody_size=14\nline_height=14\n', encoding="utf-8")
            with self.assertRaisesRegex(PoemError, "too tight"):
                load_theme("literary-classic", path)
            path.write_text('extends="literary-classic"\ntext_color="777777"\nbackground_color="888888"\n', encoding="utf-8")
            with self.assertRaisesRegex(PoemError, "contrast"):
                load_theme("literary-classic", path)
            path.write_text('extends="literary-classic"\nsection_align="diagonal"\n', encoding="utf-8")
            with self.assertRaisesRegex(PoemError, "left, center, or right"):
                load_theme("literary-classic", path)

    def test_theme_default_alignment_is_used_but_explicit_alignment_wins(self):
        poem = Poem(Path("p.poem"), "P", [TextLine("default", 1), TextLine("forced", 2, "left")])
        collection = Collection(Path("book.poem"), "B", "A", [poem], contents=False)
        theme = replace(load_theme("literary-classic"), poem_align="center")
        tex = render_collection(collection, theme)
        self.assertIn(r"\PoemLineCenter{default}", tex)
        self.assertIn(r"\PoemLine{forced}", tex)
        self.assertNotIn("addcontentsline", tex)

    def test_spare_haiku_body_starts_left_aligned(self):
        self.assertEqual(BUILTIN_THEMES["spare-haiku"].poem_align, "left")

    def test_centered_title_centers_the_left_aligned_poem_measure(self):
        poem = Poem(Path("p.poem"), "P", [TextLine("short line", 1)])
        collection = Collection(Path("book.poem"), "B", "A", [poem], contents=False)
        tex = render_collection(collection, load_theme("literary-classic"))
        self.assertIn(r"\begin{PoemBody}{28.00}", tex)
        self.assertIn(r"\leftskip=\PoemBodyInset\rightskip=\PoemBodyInset", tex)

    def test_left_title_keeps_the_full_poem_measure(self):
        poem = Poem(Path("p.poem"), "P", [TextLine("short line", 1)])
        collection = Collection(Path("book.poem"), "B", "A", [poem], contents=False)
        tex = render_collection(collection, load_theme("modern-minimal"))
        self.assertIn(r"\begin{PoemBody}{0.00}", tex)

    def test_lines_stay_with_their_stanza_when_possible(self):
        from poemtex.model import StanzaBreak
        poem = Poem(Path("p.poem"), "P", [TextLine("one", 1), TextLine("two", 2), StanzaBreak(), TextLine("three", 4)])
        collection = Collection(Path("book.poem"), "B", "A", [poem], contents=False)
        tex = render_collection(collection, load_theme("literary-classic"))
        self.assertIn(r"\PoemLine{one}\nopagebreak[3]", tex)
        self.assertNotIn(r"\PoemLine{two}\nopagebreak", tex)


if __name__ == "__main__":
    unittest.main()
