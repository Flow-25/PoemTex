from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import unittest

from poemtex.gallery import _html, optional_artifact, representative_poem
from poemtex.model import Collection, Poem, TextLine
from poemtex.themes import BUILTIN_THEMES


class GalleryTests(unittest.TestCase):
    def test_prefers_typographically_rich_poem(self):
        plain = Poem(Path("plain.poem"), "Plain", [TextLine("line", 1)])
        rich = Poem(Path("rich.poem"), "Rich", [TextLine("*styled*", 1, "right")], epigraph="Motto")
        collection = Collection(Path("book.poem"), "Book", "Author", [plain, rich])
        self.assertIs(representative_poem(collection), rich)

    def test_optional_tool_failure_is_not_fatal(self):
        with redirect_stderr(StringIO()) as error:
            succeeded = optional_artifact(["/definitely/missing/poemtex-tool"], "thumbnail")
        self.assertFalse(succeeded)
        self.assertIn("warning", error.getvalue())

    def test_html_explains_design_and_escapes_values(self):
        theme = BUILTIN_THEMES["midnight-ink"]
        markup = _html([("midnight-ink", theme, Path("book.pdf"), Path("title.png"), Path("section.png"), Path("poem.png"))])
        self.assertIn("TeX Gyre Schola", markup)
        self.assertIn("#161B26", markup)
        self.assertIn('href="midnight-ink/book.pdf"', markup)
        self.assertIn("section.png", markup)


if __name__ == "__main__":
    unittest.main()
