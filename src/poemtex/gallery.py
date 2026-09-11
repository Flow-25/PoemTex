from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import html
from pathlib import Path
import shutil
import subprocess
import sys

from .compiler import compile_pdf
from .model import Collection, Poem, TextLine
from .themes import BUILTIN_THEMES


def representative_poem(collection: Collection) -> Poem | None:
    poems = [item for item in collection.items if isinstance(item, Poem)]
    if not poems:
        return None

    def richness(poem: Poem) -> tuple[int, int]:
        lines = [item for item in poem.body if isinstance(item, TextLine)]
        score = 5 * bool(poem.epigraph or poem.dedication)
        score += 3 * any(line.alignment != "default" for line in lines)
        score += sum(1 for line in lines if "*" in line.text or "{smallcaps:" in line.text)
        return score, len(lines)

    return max(poems, key=richness)


def optional_artifact(command: list[str], label: str) -> bool:
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        return True
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.strip().splitlines()[-1] if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        print(f"warning: could not create {label}: {detail}", file=sys.stderr)
        return False


def _pdf_page_count(pdf: Path) -> int:
    pdfinfo = shutil.which("pdfinfo")
    if not pdfinfo:
        return 1
    result = subprocess.run([pdfinfo, str(pdf)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    return 1


def _find_poem_page(pdf: Path, poem: Poem | None) -> int:
    pages = _pdf_page_count(pdf)
    extractor = shutil.which("pdftotext")
    if not extractor or poem is None:
        return pages
    for page in range(pages, 1, -1):
        result = subprocess.run(
            [extractor, "-f", str(page), "-l", str(page), str(pdf), "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        if poem.title.casefold() in result.stdout.casefold():
            return page
    return pages


def _html(cards) -> str:
    rendered = []
    for name, theme, pdf, title_image, section_image, poem_image in cards:
        images = ""
        if title_image and section_image and poem_image:
            images = (
                f'<a class="pages" href="{name}/{html.escape(pdf.name)}">'
                f'<img src="{name}/title.png" alt="{name} title page">'
                f'<img src="{name}/section.png" alt="{name} section opening">'
                f'<img src="{name}/poem.png" alt="{name} poem page"></a>'
            )
        rendered.append(
            f'<article><h2>{html.escape(name)}</h2><p>{html.escape(theme.description)}</p>'
            f'<dl><div><dt>Body</dt><dd>{html.escape(theme.body_font)}</dd></div>'
            f'<div><dt>Titles</dt><dd>{html.escape(theme.title_font)}</dd></div>'
            f'<div><dt>Layout</dt><dd>{theme.title_align} titles · {theme.poem_align} poems</dd></div>'
            f'<div><dt>Palette</dt><dd><i style="--c:#{theme.background_color}"></i>'
            f'<i style="--c:#{theme.text_color}"></i><i style="--c:#{theme.accent_color}"></i></dd></div></dl>{images}'
            f'<a href="{name}/{html.escape(pdf.name)}">Open full PDF</a></article>'
        )
    return """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width"><title>PoemTeX theme gallery</title>
<style>body{margin:0;background:#e8e6e2;color:#222;font:16px system-ui,sans-serif}header{padding:3rem max(4vw,1rem) 2rem}h1{margin:0 0 .5rem;font-size:clamp(2rem,5vw,4rem)}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(390px,1fr));gap:2rem;padding:0 max(4vw,1rem) 4rem}article{background:#fff;padding:1.2rem;border-radius:8px;box-shadow:0 5px 24px #0002}h2{margin:.1rem 0}dl{font-size:.82rem;color:#555}dl div{display:flex;gap:.6rem}dt{font-weight:700;min-width:3.5rem}dd{margin:0}.pages{display:grid;grid-template-columns:repeat(3,1fr);gap:.7rem;margin:1rem 0}.pages img{display:block;width:100%;box-shadow:0 2px 10px #0003}i{display:inline-block;width:1.1rem;height:1.1rem;margin-right:.25rem;border:1px solid #aaa;border-radius:50%;background:var(--c);vertical-align:middle}a{color:#7a3428;font-weight:650;text-decoration-thickness:.08em}</style>
<header><h1>PoemTeX themes</h1><p>The same collection rendered in every built-in design.</p>
<p><a href="contact-sheet.png">Contact sheet</a> · <a href="all-themes.pdf">Combined PDF</a></p></header><main>""" + "".join(rendered) + "</main></html>\n"


def build_gallery(source: Path, output: Path) -> tuple[Path, Path | None, Path | None]:
    output.mkdir(parents=True, exist_ok=True)
    pdftoppm, pdfunite, montage = (shutil.which(name) for name in ("pdftoppm", "pdfunite", "montage"))
    cards, pdfs, comparisons = [], [], []
    shared_cache = output / ".tex-cache"
    theme_items = list(BUILTIN_THEMES.items())
    print(f"Building {len(theme_items)} theme previews…")

    def build_theme(name: str):
        return compile_pdf(source, output / name, theme_override=name, cache_dir=shared_cache)

    first_name, _ = theme_items[0]
    compiled = {first_name: build_theme(first_name)}
    print(f"  ✓ {first_name}")
    workers = max(1, min(4, len(theme_items) - 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(build_theme, name): name for name, _ in theme_items[1:]}
        for future in as_completed(futures):
            name = futures[future]
            compiled[name] = future.result()
            print(f"  ✓ {name}")

    for name, theme in theme_items:
        theme_dir, result = output / name, compiled[name]
        for warning in result.warnings:
            print(f"    {warning.pretty()}", file=sys.stderr)
        pdfs.append(result.pdf)
        title_image = section_image = poem_image = None
        if pdftoppm:
            title_prefix, section_prefix, poem_prefix = theme_dir / "title", theme_dir / "section", theme_dir / "poem"
            title_ok = optional_artifact([pdftoppm, "-f", "1", "-singlefile", "-png", "-r", "90", str(result.pdf), str(title_prefix)], f"{name} title thumbnail")
            first_poem = next((item for item in result.collection.items if isinstance(item, Poem)), None)
            section_page = _find_poem_page(result.pdf, first_poem)
            section_ok = optional_artifact([pdftoppm, "-f", str(section_page), "-singlefile", "-png", "-r", "90", str(result.pdf), str(section_prefix)], f"{name} section thumbnail")
            page = _find_poem_page(result.pdf, representative_poem(result.collection))
            poem_ok = optional_artifact([pdftoppm, "-f", str(page), "-singlefile", "-png", "-r", "90", str(result.pdf), str(poem_prefix)], f"{name} poem thumbnail")
            if title_ok and section_ok and poem_ok:
                title_image = title_prefix.with_suffix(".png")
                section_image = section_prefix.with_suffix(".png")
                poem_image = poem_prefix.with_suffix(".png")
            if montage and title_image and section_image and poem_image:
                comparison, staging = theme_dir / "comparison.png", theme_dir / "comparison.new.png"
                if optional_artifact([montage, str(title_image), str(section_image), str(poem_image), "-thumbnail", "280x", "-tile", "3x1", "-geometry", "+16+16", "-title", name, str(staging)], f"{name} comparison image"):
                    staging.replace(comparison)
                    comparisons.append(comparison)
        cards.append((name, theme, result.pdf, title_image, section_image, poem_image))

    combined = output / "all-themes.pdf"
    if pdfunite:
        staging = output / "all-themes.new.pdf"
        if optional_artifact([pdfunite, *map(str, pdfs), str(staging)], "combined PDF"):
            staging.replace(combined)
    contact = output / "contact-sheet.png"
    if montage and comparisons:
        staging = output / "contact-sheet.new.png"
        if optional_artifact([montage, *map(str, comparisons), "-tile", "2x", "-geometry", "+20+20", str(staging)], "contact sheet"):
            staging.replace(contact)
    index = output / "index.html"
    index.write_text(_html(cards), encoding="utf-8")
    return index, combined if combined.exists() else None, contact if contact.exists() else None
