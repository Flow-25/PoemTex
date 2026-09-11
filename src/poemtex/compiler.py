from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile

from .errors import PoemError, WarningMessage
from .model import Collection
from .parser import is_collection, parse_collection, parse_poem
from .render import fragment_collection, render_collection
from .themes import load_theme


@dataclass(slots=True)
class BuildResult:
    pdf: Path
    tex: Path
    collection: Collection
    warnings: list[WarningMessage]
    cache_dir: Path | None = None


def slugify(text: str) -> str:
    polish = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.translate(polish)).strip("-").lower()
    return slug or "collection"


def load_document(path: Path, preview_fragment: bool = False) -> tuple[Collection, list[WarningMessage]]:
    path = path.resolve()
    if is_collection(path):
        collection = parse_collection(path)
        return collection, collection.warnings
    if not preview_fragment:
        parse_collection(path)  # raises the specific fragment error
    poem, warnings = parse_poem(path)
    collection = fragment_collection(poem)
    collection.warnings = warnings
    return collection, warnings


def generate(
    path: Path,
    output_dir: Path | None = None,
    preview_fragment: bool = False,
    theme_override: str | None = None,
    cache_dir: Path | None = None,
) -> BuildResult:
    collection, warnings = load_document(path, preview_fragment)
    if theme_override:
        collection.theme = theme_override
        collection.theme_file = None
    theme = load_theme(collection.theme, collection.theme_file)
    tex_source = render_collection(collection, theme)
    output_dir = (output_dir or path.resolve().parent / "build").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(collection.title)
    tex_path = output_dir / f"{slug}.tex"
    tex_path.write_text(tex_source, encoding="utf-8")
    return BuildResult(output_dir / f"{slug}.pdf", tex_path, collection, warnings, cache_dir)


def _latex_command() -> tuple[list[str], str]:
    if shutil.which("latexmk"):
        return ["latexmk", "-lualatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error"], "latexmk"
    if shutil.which("lualatex"):
        return ["lualatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error"], "lualatex"
    raise PoemError(
        "LuaLaTeX was not found",
        hint="Install TeX Live (including lualatex, fontspec, babel, geometry, microtype, fancyhdr, and hyperref).",
    )


def _useful_latex_error(output: str) -> str:
    patterns = [
        r"^[^\n]*\.tex:\d+: (?!.*Fatal error)(.+)$",
        r"^! (?!.*Fatal error)(.+)$",
        r"^Latexmk: (.+)$",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, output, flags=re.MULTILINE)
        if matches:
            useful = [match.strip() for match in matches if "return code" not in match]
            if useful:
                return useful[-1]
    return "the PDF engine reported an error"


def _collect_latex_warnings(output: str) -> list[WarningMessage]:
    warnings = []
    seen = set()
    for line in output.splitlines():
        if line.startswith("Missing character:"):
            message = "PDF font warning: " + line.removeprefix("Missing character:").strip()
            if message not in seen:
                warnings.append(WarningMessage(message))
                seen.add(message)
    return warnings


def compile_generated(generated: BuildResult) -> BuildResult:
    command, engine = _latex_command()
    build_root = generated.tex.parent
    with tempfile.TemporaryDirectory(prefix="poemtex-", dir=build_root) as temp_name:
        temp = Path(temp_name)
        temp_tex = temp / generated.tex.name
        temp_tex.write_text(generated.tex.read_text(encoding="utf-8"), encoding="utf-8")
        env = os.environ.copy()
        # A project-local cache works in sandboxes, containers, and read-only homes.
        # It is also reused between builds, so the first font scan is paid only once.
        tex_cache = generated.cache_dir or build_root / ".tex-cache"
        tex_cache.mkdir(exist_ok=True)
        env["TEXMFVAR"] = str(tex_cache)
        env["TEXMFCACHE"] = str(tex_cache)
        passes = 1 if engine == "latexmk" else 2
        output = ""
        for _ in range(passes):
            process = subprocess.run(
                [*command, temp_tex.name], cwd=temp, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace",
            )
            output += process.stdout
            if process.returncode != 0:
                log = build_root / f"{generated.tex.stem}.log"
                log.write_text(output, encoding="utf-8")
                raise PoemError(_useful_latex_error(output), hint=f"Full engine output: {log}")
        temp_pdf = temp / generated.pdf.name
        if not temp_pdf.exists():
            raise PoemError("PDF engine finished without creating a PDF")
        staging = generated.pdf.with_suffix(".pdf.new")
        shutil.copy2(temp_pdf, staging)
        staging.replace(generated.pdf)
        old_error_log = build_root / f"{generated.tex.stem}.log"
        if old_error_log.exists():
            old_error_log.unlink()
        generated.warnings.extend(_collect_latex_warnings(output))
    return generated


def compile_pdf(
    path: Path,
    output_dir: Path | None = None,
    preview_fragment: bool = False,
    theme_override: str | None = None,
    cache_dir: Path | None = None,
) -> BuildResult:
    return compile_generated(generate(path, output_dir, preview_fragment, theme_override, cache_dir))
