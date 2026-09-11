from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from poemtex.errors import PoemError
from poemtex.model import Poem, Section, StanzaBreak, TextLine
from poemtex.parser import parse_collection, parse_poem


class ParserTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_poem_preserves_lines_and_normalizes_blank_runs(self):
        with TemporaryDirectory() as directory:
            path = self.write(Path(directory), "p.poem", '@title "Tytuł"\n\n  raz  dwa\n\n\ntrzy   \n')
            poem, warnings = parse_poem(path)
            self.assertEqual(poem.title, "Tytuł")
            self.assertEqual(poem.body, [TextLine("  raz  dwa", 3), StanzaBreak(), TextLine("trzy", 6)])
            self.assertEqual(warnings, [])

    def test_tabs_warn_and_expand(self):
        with TemporaryDirectory() as directory:
            path = self.write(Path(directory), "p.poem", "@title T\n\n\ta\tb\n")
            poem, warnings = parse_poem(path)
            self.assertEqual(poem.body[0].text, "    a   b")
            self.assertEqual(len(warnings), 1)

    def test_alignment_and_space(self):
        with TemporaryDirectory() as directory:
            path = self.write(Path(directory), "p.poem", "@title T\n\n@align right\na\n@end\n@space 3\nb\n")
            poem, _ = parse_poem(path)
            self.assertEqual(poem.body[0].alignment, "right")
            self.assertEqual(poem.body[1], StanzaBreak(3))
            self.assertEqual(poem.body[2].alignment, "default")

    def test_unclosed_alignment_is_friendly_error(self):
        with TemporaryDirectory() as directory:
            path = self.write(Path(directory), "p.poem", "@title T\n@align center\na\n")
            with self.assertRaisesRegex(PoemError, "unclosed @align"):
                parse_poem(path)

    def test_typo_suggests_directive(self):
        with TemporaryDirectory() as directory:
            path = self.write(Path(directory), "p.poem", "@titlle T\na\n")
            with self.assertRaises(PoemError) as caught:
                parse_poem(path)
            self.assertIn("@title", caught.exception.hint)

    def test_duplicate_metadata_is_rejected(self):
        with TemporaryDirectory() as directory:
            path = self.write(Path(directory), "p.poem", "@title One\n@title Two\n\nx\n")
            with self.assertRaisesRegex(PoemError, "more than once"):
                parse_poem(path)

    def test_long_unbroken_text_warns(self):
        with TemporaryDirectory() as directory:
            path = self.write(Path(directory), "p.poem", "@title T\n\n" + "x" * 60 + "\n")
            _, warnings = parse_poem(path)
            self.assertIn("page margin", warnings[0].message)

    def test_collection_preserves_include_and_section_order(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "poems/a.poem", "@title A\n\na\n")
            book = self.write(root, "book.poem", "@collection\n@title B\n@author A\n@section One\n@include poems/a.poem\n")
            parsed = parse_collection(book)
            self.assertIsInstance(parsed.items[0], Section)
            self.assertIsInstance(parsed.items[1], Poem)

    def test_empty_sections_warn_at_exact_lines(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "p.poem", "@title P\n\np\n")
            book = self.write(
                root, "book.poem",
                "@collection\n@title B\n@author A\n@section Empty\n@section Used\n@include p.poem\n@section Final\n",
            )
            parsed = parse_collection(book)
            section_warnings = [warning for warning in parsed.warnings if "section" in warning.message]
            self.assertEqual([warning.location.line for warning in section_warnings], [4, 7])

    def test_duplicate_include_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "p.poem", "@title P\n\nx\n")
            book = self.write(root, "book.poem", "@collection\n@title B\n@author A\n@include p.poem\n@include p.poem\n")
            with self.assertRaisesRegex(PoemError, "more than once"):
                parse_collection(book)

    def test_include_cannot_escape_project(self):
        with TemporaryDirectory() as parent:
            root = Path(parent) / "book"
            root.mkdir()
            self.write(Path(parent), "outside.poem", "@title X\n\nx\n")
            book = self.write(root, "book.poem", "@collection\n@title B\n@author A\n@include ../outside.poem\n")
            with self.assertRaisesRegex(PoemError, "inside the project"):
                parse_collection(book)

    def test_fragment_is_not_collection(self):
        with TemporaryDirectory() as directory:
            path = self.write(Path(directory), "p.poem", "@title P\n\nx\n")
            with self.assertRaisesRegex(PoemError, "fragment"):
                parse_collection(path)


if __name__ == "__main__":
    unittest.main()
