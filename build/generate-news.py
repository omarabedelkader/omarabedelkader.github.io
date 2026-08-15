from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import re
import sys

from publications import _parse_bib_entries, _publication_group


BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent
SOURCES = ROOT / "sources"
RESOURCES = ROOT / "resources"

DEFAULT_MAX_ITEMS = 6


@dataclass(frozen=True)
class NewsItem:
    year: int
    priority: int
    source_order: int
    en: str
    fr: str


H2_RE = re.compile(r"^##\s+(.+?)\s*$")
H3_RE = re.compile(r"^###\s+(.+?)\s*$")
BULLET_RE = re.compile(r"^\s*[-+]\s+(.+?)\s*$")
YEAR_RE = re.compile(r"\b(20\d{2})\b")
EMPTY_LINK_RE = re.compile(r"\s*\[[^\]]+\]\(\s*\)")


def section_slug(title: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFD", title.lower())
    ascii_title = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")


def extract_h2(markdown: str, accepted_slugs: set[str]) -> str:
    lines = markdown.splitlines()
    capture = False
    collected: list[str] = []

    for line in lines:
        heading = H2_RE.match(line)
        if heading:
            if capture:
                break
            capture = section_slug(heading.group(1)) in accepted_slugs
            continue
        if capture:
            collected.append(line)

    return "\n".join(collected).strip()


def compact(text: str, limit: int = 230) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = text.removeprefix("*").strip()
    if len(text) <= limit:
        return text
    sentence = re.split(r"(?<=[.!?])\s+", text[:limit], maxsplit=1)[0].strip()
    if sentence and len(sentence) >= 80:
        return sentence
    return text[: limit - 1].rstrip() + "…"


def clean_generated_line(text: str) -> str:
    text = EMPTY_LINK_RE.sub("", text)
    text = text.replace("Réviseur fantôme chez", "Réviseur fantôme à")
    return re.sub(r"\s+", " ", text).strip()


def first_year(text: str) -> int | None:
    match = YEAR_RE.search(text)
    return int(match.group(1)) if match else None


def doi_link(doi: str) -> str:
    if not doi:
        return ""
    url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
    return f" [DOI]({url})"


def publication_items(max_year: int | None = None) -> list[NewsItem]:
    entries = _parse_bib_entries((RESOURCES / "publications.bib").read_text(encoding="utf-8"))
    items: list[NewsItem] = []

    for order, entry in enumerate(entries):
        year_text = entry.get("year", "")
        if not year_text.isdigit():
            continue
        year = int(year_text)
        if max_year is not None and year > max_year:
            continue

        title = entry.get("title", "")
        venue = entry.get("journal") or entry.get("booktitle") or "publication venue"
        group = _publication_group(entry)
        link = doi_link(entry.get("doi", ""))

        if group == "journal":
            en = f"**{year}** — Journal article: *{title}* published in *{venue}*.{link}"
            fr = f"**{year}** — Article de revue : *{title}* publié dans *{venue}*.{link}"
            priority = 100
        elif group == "conference":
            en = f"**{year}** — Conference paper: *{title}* accepted at *{venue}*.{link}"
            fr = f"**{year}** — Article de conférence : *{title}* accepté à *{venue}*.{link}"
            priority = 90
        else:
            en = f"**{year}** — Publication: *{title}*."
            fr = f"**{year}** — Publication : *{title}*."
            priority = 80

        items.append(NewsItem(year, priority, order, en, fr))

    return items


def section_year_bullets(section: str) -> list[tuple[int, str]]:
    current_year: int | None = None
    bullets: list[tuple[int, str]] = []

    for line in section.splitlines():
        heading = H3_RE.match(line)
        if heading:
            current_year = first_year(heading.group(1))
            continue

        bullet = BULLET_RE.match(line)
        if not bullet:
            continue

        body = clean_generated_line(compact(bullet.group(1)))
        year = first_year(body) or current_year
        if year is not None:
            bullets.append((year, body))

    return bullets


def paired_section_items(
    en_markdown: str,
    fr_markdown: str,
    slugs: set[str],
    en_prefix: str,
    fr_prefix: str,
    priority: int,
    source_offset: int,
) -> list[NewsItem]:
    en_bullets = section_year_bullets(extract_h2(en_markdown, slugs))
    fr_bullets = section_year_bullets(extract_h2(fr_markdown, slugs))
    items: list[NewsItem] = []

    for index, (year, en_body) in enumerate(en_bullets):
        fr_body = fr_bullets[index][1] if index < len(fr_bullets) else en_body
        items.append(
            NewsItem(
                year=year,
                priority=priority,
                source_order=source_offset + index,
                en=f"**{year}** — {en_prefix}: {en_body}",
                fr=f"**{year}** — {fr_prefix} : {fr_body}",
            )
        )

    return items


def about_items(en_markdown: str, fr_markdown: str) -> list[NewsItem]:
    def about_bullets(markdown: str) -> list[str]:
        section = extract_h2(markdown, {"about-me", "a-propos-de-moi"})
        lines: list[str] = []
        capture = False
        for line in section.splitlines():
            heading = H3_RE.match(line)
            if heading:
                capture = section_slug(heading.group(1)) in {"awards", "recompenses", "honors", "honneurs"}
                continue
            bullet = BULLET_RE.match(line)
            if capture and bullet:
                lines.append(compact(bullet.group(1)))
        return lines

    en_lines = about_bullets(en_markdown)
    fr_lines = about_bullets(fr_markdown)
    items: list[NewsItem] = []

    for index, en_body in enumerate(en_lines):
        year = first_year(en_body)
        if year is None:
            continue
        fr_body = fr_lines[index] if index < len(fr_lines) else en_body
        items.append(
            NewsItem(
                year=year,
                priority=70,
                source_order=300 + index,
                en=f"**{year}** — Recognition: {en_body}",
                fr=f"**{year}** — Distinction : {fr_body}",
            )
        )

    return items


def dedupe(items: list[NewsItem]) -> list[NewsItem]:
    seen: set[str] = set()
    unique: list[NewsItem] = []

    for item in items:
        key = re.sub(r"\W+", "", item.en.lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    return unique


def collect_news(max_items: int, max_year: int | None = None) -> list[NewsItem]:
    en_markdown = (SOURCES / "site.md").read_text(encoding="utf-8")
    fr_path = SOURCES / "site-fr.md"
    fr_markdown = fr_path.read_text(encoding="utf-8") if fr_path.exists() else en_markdown

    items = [
        *publication_items(max_year=max_year),
        *paired_section_items(
            en_markdown,
            fr_markdown,
            {"public-talks", "presentations-publiques"},
            "Public talk",
            "Présentation publique",
            60,
            400,
        ),
        *paired_section_items(
            en_markdown,
            fr_markdown,
            {"students", "etudiants"},
            "Student supervision",
            "Encadrement",
            55,
            500,
        ),
        *paired_section_items(
            en_markdown,
            fr_markdown,
            {"services"},
            "Service",
            "Service",
            50,
            600,
        ),
        *about_items(en_markdown, fr_markdown),
    ]

    if max_year is not None:
        items = [item for item in items if item.year <= max_year]

    items = dedupe(items)
    items.sort(key=lambda item: (item.year, item.priority, -item.source_order), reverse=True)
    return items[:max_items]


def write_news_file(path: Path, items: list[NewsItem], language: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not items:
        fallback = "- No news." if language == "en" else "- Aucune actualité."
        path.write_text(f"{fallback}\n", encoding="utf-8")
        return

    lines = [f"- {clean_generated_line(item.en if language == 'en' else item.fr)}" for item in items]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate small website news snippets from repository sources.")
    parser.add_argument("--max-items", type=int, default=DEFAULT_MAX_ITEMS)
    parser.add_argument("--max-year", type=int, default=None)
    parser.add_argument("--en-output", type=Path, default=SOURCES / "news.md")
    parser.add_argument("--fr-output", type=Path, default=SOURCES / "news-fr.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    items = collect_news(max_items=max(1, args.max_items), max_year=args.max_year)
    write_news_file(args.en_output, items, "en")
    write_news_file(args.fr_output, items, "fr")

    if items:
        print(f"News: yes ({len(items)} item{'s' if len(items) != 1 else ''})")
        print(f"Wrote {args.en_output}")
        print(f"Wrote {args.fr_output}")
    else:
        print("News: no news")
        print(f"Wrote {args.en_output}")
        print(f"Wrote {args.fr_output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
