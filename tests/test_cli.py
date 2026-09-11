from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import tomllib

from poemtex.cli import main
from poemtex.themes import BUILTIN_THEMES


class CliTests(unittest.TestCase):
    def run_cli(self, argv):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_init_creates_a_valid_project(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "nowy"
            code, output, error = self.run_cli(["init", str(target)])
            self.assertEqual(code, 0, error)
            self.assertTrue((target / "book.poem").exists())
            code, output, error = self.run_cli(["check", str(target / "book.poem")])
            self.assertEqual(code, 0, error)
            self.assertIn("valid collection", output)

    def test_new_creates_and_includes_poem(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "book"
            code, _, error = self.run_cli(["init", str(target)])
            self.assertEqual(code, 0, error)
            code, output, error = self.run_cli(["new", "Nocne światło", "--collection", str(target / "book.poem")])
            self.assertEqual(code, 0, error)
            self.assertTrue((target / "poems" / "nocne-swiatlo.poem").exists())
            self.assertIn("@include poems/nocne-swiatlo.poem", (target / "book.poem").read_text(encoding="utf-8"))
            self.assertIn("included", output)
            code, _, error = self.run_cli([
                "new", "Escape", "--collection", str(target / "book.poem"), "--directory", "../outside",
            ])
            self.assertEqual(code, 2)
            self.assertIn("inside", error)

    def test_build_rejects_fragment_with_hint(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "p.poem"
            path.write_text("@title P\n\nx\n", encoding="utf-8")
            code, _, error = self.run_cli(["build", str(path)])
            self.assertEqual(code, 2)
            self.assertIn("preview", error)

    def test_themes_lists_all_choices(self):
        code, output, error = self.run_cli(["themes"])
        self.assertEqual(code, 0, error)
        for theme_name in BUILTIN_THEMES:
            self.assertIn(theme_name, output)

    def test_themes_can_emit_valid_metatemplate(self):
        code, output, error = self.run_cli(["themes", "--example", "midnight-ink"])
        self.assertEqual(code, 0, error)
        self.assertIn('extends = "midnight-ink"', output)
        self.assertIn('background_color = "161B26"', output)
        self.assertEqual(tomllib.loads(output)["poem_align"], "left")

    def test_build_and_preview_accept_theme_override(self):
        parser = __import__("poemtex.cli", fromlist=["build_parser"]).build_parser()
        self.assertEqual(parser.parse_args(["build", "--theme", "modern-minimal"]).theme, "modern-minimal")
        self.assertEqual(parser.parse_args(["preview", "--theme", "quiet-manuscript"]).theme, "quiet-manuscript")

    def test_doctor_reports_environment(self):
        code, output, error = self.run_cli(["doctor"])
        self.assertIn(code, {0, 1})
        self.assertIn("PoemTeX environment", output)
        self.assertEqual(error, "")

    def test_gallery_command_is_available(self):
        parser = __import__("poemtex.cli", fromlist=["build_parser"]).build_parser()
        args = parser.parse_args(["gallery", "book.poem", "--output", "previews", "--open"])
        self.assertEqual(args.source, Path("book.poem"))
        self.assertEqual(args.output, Path("previews"))
        self.assertTrue(args.open)

if __name__ == "__main__":
    unittest.main()
