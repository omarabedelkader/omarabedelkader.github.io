from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import re
import sys

from publications import _parse_bib_entries, _publication_group
from sync_state import load_state, save_state


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
    # Identity of the item in resources/sync-state.json; survives rewording.
    key: str = ""


H2_RE = re.compile(r"^##\s+(.+?)\s*$")
H3_RE = re.compile(r"^###\s+(.+?)\s*$")
BULLET_RE = re.compile(r"^\s*[-+]\s+(.+?)\s*$")
YEAR_RE = re.compile(r"\b(20\d{2})\b")
EMPTY_LINK_RE = re.compile(r"\s*\[[^\]]+\]\(\s*\)")
LINK_RE = re.compile(r"\[[^\]]*\]\([^)]*\)")
LINK_TARGET_RE = re.compile(r"\]\((https?://[^)\s]+)\)")


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
    if len(LINK_RE.sub("", text)) <= limit:
        return text

    # Too long: keep whole links and cut only in plain text, so the Markdown stays valid.
    kept: list[str] = []
    visible = 0
    position = 0
    for link in [*LINK_RE.finditer(text), None]:
        plain = text[position : link.start() if link else len(text)]
        if visible + len(plain) > limit:
            kept.append(plain[: max(0, limit - visible - 1)].rstrip() + "…")
            break
        kept.append(plain)
        visible += len(plain)
        if link:
            kept.append(link.group(0))
            position = link.end()
    return "".join(kept)


def clean_generated_line(text: str) -> str:
    text = EMPTY_LINK_RE.sub("", text)
    text = text.replace("Réviseur fantôme chez", "Réviseur fantôme à")
    return re.sub(r"\s+", " ", text).strip()


def first_year(text: str) -> int | None:
    match = YEAR_RE.search(text)
    return int(match.group(1)) if match else None


def publication_link(entry: dict[str, str]) -> str:
    doi = entry.get("doi", "")
    if doi:
        url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
        return f" [DOI]({url})"
    # When the only link is the page the entry came from, the source link already covers it.
    if entry.get("url") and entry["url"] != entry.get("source"):
        return f" [Link]({entry['url']})"
    return ""


SOURCE_NAMES = {
    "scholar.google.": "Google Scholar",
    "conf.researchr.org": "conf.researchr.org",
}


def source_link(entry: dict[str, str], language: str) -> str:
    """Link to the page the publication was found on, when the entry records one."""
    source = entry.get("source", "")
    if not source:
        return ""
    name = next((label for domain, label in SOURCE_NAMES.items() if domain in source), "")
    separator = " : " if language == "fr" else ": "
    label = f"Source{separator}{name}" if name else "Source"
    return f" [{label}]({source})"


def bullet_key(section: str, year: int, body: str) -> str:
    link = LINK_TARGET_RE.search(body)
    identity = link.group(1) if link else re.sub(r"\W+", "", body.lower())
    return f"{section}:{year}:{identity}"


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
        link = publication_link(entry)
        source_en = source_link(entry, "en")
        source_fr = source_link(entry, "fr")

        if group == "journal":
            en = f"**{year}** — Journal article: *{title}* published in *{venue}*.{link}{source_en}"
            fr = f"**{year}** — Article de revue : *{title}* publié dans *{venue}*.{link}{source_fr}"
            priority = 100
        elif group == "conference":
            en = f"**{year}** — Conference paper: *{title}* accepted at *{venue}*.{link}{source_en}"
            fr = f"**{year}** — Article de conférence : *{title}* accepté à *{venue}*.{link}{source_fr}"
            priority = 90
        else:
            en = f"**{year}** — Publication: *{title}*.{link}{source_en}"
            fr = f"**{year}** — Publication : *{title}*.{link}{source_fr}"
            priority = 80

        items.append(NewsItem(year, priority, order, en, fr, key=f"publication:{entry.get('key') or title}"))

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
                key=bullet_key(en_prefix, year, en_body),
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
                key=bullet_key("Recognition", year, en_body),
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


def collect_news(max_year: int | None = None) -> list[NewsItem]:
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
    return items


def news_line(item: NewsItem, language: str) -> str:
    return f"- {clean_generated_line(item.en if language == 'en' else item.fr)}"


def prepend_news(path: Path, items: list[NewsItem], language: str) -> None:
    """Put new lines on top and leave every existing line exactly as it is."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    placeholders = {"- No news.", "- Aucune actualité."}
    kept = [line for line in existing.splitlines() if line.strip() and line.strip() not in placeholders]
    lines = [news_line(item, language) for item in items] + kept
    if not lines:
        lines = ["- No news." if language == "en" else "- Aucune actualité."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Add website news lines for items that appeared in the sources since the last run. "
            "Existing lines of the news files are never rewritten."
        )
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=DEFAULT_MAX_ITEMS,
        help="Number of lines written when a news file is created from scratch.",
    )
    parser.add_argument("--max-year", type=int, default=None)
    parser.add_argument("--en-output", type=Path, default=SOURCES / "news.md")
    parser.add_argument("--fr-output", type=Path, default=SOURCES / "news-fr.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    items = collect_news(max_year=args.max_year)
    state = load_state()
    announced = state.get("news")

    if announced is None or not args.en_output.exists():
        # First run: everything currently in the sources counts as already announced.
        new_items = [] if args.en_output.exists() else items[: max(1, args.max_items)]
        announced = []
    else:
        new_items = [item for item in items if item.key not in set(announced)]

    if new_items or not args.fr_output.exists():
        prepend_news(args.en_output, new_items, "en")
        prepend_news(args.fr_output, new_items, "fr")

    state["news"] = sorted(set(announced) | {item.key for item in items})
    save_state(state)

    if new_items:
        print(f"News: {len(new_items)} new item{'s' if len(new_items) != 1 else ''}")
        for item in new_items:
            print(f"  + {clean_generated_line(item.en)}")
    else:
        print("Nothing to change: no new item to announce in the news.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
