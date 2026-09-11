import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from poemtex.compiler import compile_pdf
from poemtex.themes import BUILTIN_THEMES


@unittest.skipUnless(os.environ.get("POEMTEX_PDF_TESTS") == "1", "set POEMTEX_PDF_TESTS=1 for real LuaLaTeX tests")
class PdfIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("lualatex"), "LuaLaTeX is not installed")
    def test_all_builtin_themes_compile_polish(self):
        with TemporaryDirectory() as directory:
            shared_cache = Path(directory) / ".tex-cache"
            for theme in BUILTIN_THEMES:
                with self.subTest(theme=theme):
                    root = Path(directory) / theme
                    root.mkdir()
                    (root / "wiersz.poem").write_text(
                        '@title "Źródło"\n\n    Żółć, gęślą jaźń — *cicho*.\n', encoding="utf-8")
                    (root / "book.poem").write_text(
                        f'@collection\n@title "Próba"\n@author "Łucja"\n@theme {theme}\n@include wiersz.poem\n',
                        encoding="utf-8")
                    result = compile_pdf(root / "book.poem", cache_dir=shared_cache)
                    self.assertTrue(result.pdf.exists())
                    self.assertGreater(result.pdf.stat().st_size, 5_000)
                    self.assertFalse(
                        any("font warning" in warning.message for warning in result.warnings),
                        [warning.message for warning in result.warnings],
                    )


if __name__ == "__main__":
    unittest.main()
