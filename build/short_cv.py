"""Derive the one-page CV from the full CV.

The short CV is never edited by hand: it is rebuilt from `sources/cv.md` (and
its French translation), `resources/publications.bib` and
`resources/teaching.json` on every run, so it always follows the full CV.

It is a summary rather than a cut-down copy: a line of key figures, then each
section as dated rows (a narrow date column and one line of text per row),
in the spirit of a classic academic CV.
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal
from pathlib import Path
import re
import unicodedata

from publications import _format_publication, _parse_bib_entries, _publication_rank
from teaching import teaching_rows

ROOT = Path(__file__).resolve().parents[1]
BIB = ROOT / "resources" / "publications.bib"

H2_RE = re.compile(r"^##\s+(.+?)\s*$")
H3_RE = re.compile(r"^###\s+(.+?)\s*$")
BULLET_RE = re.compile(r"^[-+]\s+(.*\S)\s*$")
EMPTY_LINK_RE = re.compile(r"\s*\[[^\]]*\]\(\s*\)")
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
ENTRY_RE = re.compile(
    r"^- \*\*(?P<role>.+?)\*\*(?: · \*(?P<dates>.+?)\*)?[ \t]*\n"
    r"[ \t]+(?P<organization>[^\n]+)"
    r"(?P<details>(?:\n[ \t]+[-+][ \t]+[^\n]+)*)",
    re.MULTILINE,
)
DETAIL_RE = re.compile(r"^[ \t]+[-+][ \t]+(.+)$", re.MULTILINE)
# "…, April 2026 - July 2026" at the end of a student line: the year column already says it.
TRAILING_DATES_RE = re.compile(r",\s*[^,]*\d{4}\s*-\s*[^,]*\d{4}\s*$")

LABELS = {
    "en": {
        "key-figures": "Key figures",
        "education": "Education",
        "experience": "Professional Experience",
        "awards": "Awards",
        "publications": "Publications",
        "services": "Professional Activities",
        "teaching": "Teaching",
        "students": "Supervision",
        "talks": "Talks",
        "volunteering": "Volunteering",
        "languages": "Languages",
    },
    "fr": {
        "key-figures": "Chiffres clés",
        "education": "Formation",
        "experience": "Expériences professionnelles",
        "awards": "Distinctions",
        "publications": "Publications",
        "services": "Activités professionnelles",
        "teaching": "Enseignement",
        "students": "Encadrement",
        "talks": "Présentations",
        "volunteering": "Bénévolat",
        "languages": "Langues",
    },
}

RANK_LABELS = {
    "en": {"a": "CORE A", "b": "CORE B", "c": "CORE C", "q1": "Q1 journal", "q2": "Q2 journal",
           "q3": "Q3 journal", "q4": "Q4 journal", "unranked": "Other"},
    "fr": {"a": "CORE A", "b": "CORE B", "c": "CORE C", "q1": "Revue Q1", "q2": "Revue Q2",
           "q3": "Revue Q3", "q4": "Revue Q4", "unranked": "Autre"},
}
RANK_ORDER = ("a", "b", "c", "q1", "q2", "q3", "q4", "unranked")
OWN_NAME = "AbedelKader, O."


def section_slug(title: str) -> str:
    normalized = unicodedata.normalize("NFD", title.lower())
    ascii_title = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")


def split_sections(markdown: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Return the lines before the first `##` and the (heading, body lines) sections."""
    preamble: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    in_fence = False
    for line in markdown.split("\n"):
        if line.startswith("```"):
            in_fence = not in_fence
        heading = None if in_fence else H2_RE.match(line)
        if heading:
            sections.append((heading.group(1), []))
        elif sections:
            sections[-1][1].append(line)
        else:
            preamble.append(line)
    return preamble, sections


def clean(text: str) -> str:
    # Icon links without a target (slides or video not published yet) would be dead links.
    return EMPTY_LINK_RE.sub("", text).strip()


def groups(body: list[str]) -> list[tuple[str, list[str]]]:
    """`###` groups of a section, each with the first line of its bullets."""
    result: list[tuple[str, list[str]]] = []
    for line in body:
        heading = H3_RE.match(line)
        if heading:
            result.append((heading.group(1).rstrip(":").strip(), []))
            continue
        bullet = BULLET_RE.match(line)
        if bullet and result:
            result[-1][1].append(clean(bullet.group(1)))
    return [(title, items) for title, items in result if items]


def bullets(body: list[str]) -> list[str]:
    return [clean(match.group(1)) for line in body if (match := BULLET_RE.match(line))]


def year_span(text: str) -> str:
    years = YEAR_RE.findall(text)
    if not years:
        return ""
    first, last = years[0], years[-1]
    return first if first == last else f"{first}–{last}"


def row(date: str, text: str) -> str:
    """One dated row; the PDF filter lays these lists out as a two-column block."""
    return f"- [{date}]{{.cvdate}} {text}"


def joined(items: list[str]) -> str:
    return "; ".join(item.rstrip(".") for item in items) + "."


# "Role: what was done that year" -> "Role" (the URL's "https://" is not a separator).
ROLE_SEPARATOR_RE = re.compile(r"[\s\u00a0\u202f]*:[\s\u00a0\u202f]+(?!//)")
TALKS_PER_YEAR = 2


def merged_roles(year_groups: list[tuple[str, list[str]]]) -> list[str]:
    """One row per role with the span of years it was held (details stay in the full CV)."""
    years: dict[str, list[int]] = {}
    for title, items in year_groups:
        for year in (int(value) for value in YEAR_RE.findall(title)):
            for item in items:
                role = ROLE_SEPARATOR_RE.split(item, maxsplit=1)[0].rstrip(".").strip()
                years.setdefault(role, []).append(year)
    ordered = sorted(years.items(), key=lambda pair: (-max(pair[1]), -min(pair[1])))
    return [row(str(min(span)) if min(span) == max(span) else f"{min(span)}–{max(span)}", f"{role}.")
            for role, span in ordered]


def plural(count: int, singular: str, plural_form: str) -> str:
    return f"{count} {singular if count == 1 else plural_form}"


def total_hours() -> Decimal:
    return sum((Decimal(item["hours"]) for item in teaching_rows()), Decimal(0))


def hours_text(value: Decimal, language: str) -> str:
    if value == value.to_integral():
        return str(int(value))
    return str(value).replace(".", ",") if language == "fr" else str(value)


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def entry_rows(body: list[str], with_detail: bool) -> list[str]:
    rows = []
    for match in ENTRY_RE.finditer("\n".join(body)):
        organization = match["organization"].split(" · ")[0].strip()
        text = f"**{match['role'].strip()}**, {organization}"
        details = DETAIL_RE.findall(match["details"])
        if with_detail and details:
            text += f" — {details[0].strip()}"
        rows.append(row(year_span(match["dates"] or ""), text))
    return rows


def award_rows(body: list[str], english_body: list[str]) -> list[str]:
    """Awards are the "About Me" group whose English title is "Awards"."""
    for (english_title, _), (_, items) in zip(groups(english_body), groups(body)):
        if section_slug(english_title) == "awards":
            return [row(year_span(item), item) for item in items]
    return []


def publication_rows(language: str) -> list[str]:
    entries = _parse_bib_entries(BIB.read_text(encoding="utf-8"))
    entries.sort(key=lambda entry: (RANK_ORDER.index(_publication_rank(entry)), -int(entry.get("year") or 0)))
    rows = []
    for entry in entries:
        citation = _format_publication(entry, language, extras=False).removeprefix("- ")
        citation = re.sub(re.escape(OWN_NAME), lambda match: f"**{match.group(0)}**", citation, flags=re.I)
        rows.append(row(RANK_LABELS[language][_publication_rank(entry)], citation))
    return rows


def teaching_row(language: str) -> list[str]:
    rows = teaching_rows()
    if not rows:
        return []
    courses: dict[str, list[str]] = {}
    for item in rows:
        titles = courses.setdefault(item["institution"], [])
        if item["title"][language] not in titles:
            titles.append(item["title"][language])
    years = sorted(int(item["year"]) for item in rows)
    span = str(years[0]) if years[0] == years[-1] else f"{years[0]}–{years[-1]}"
    places = "; ".join(f"{place}: {', '.join(titles)}" for place, titles in courses.items())
    return [row(span, f"**{hours_text(total_hours(), language)} h EQTD** — {places}.")]


def key_figures(english: dict[str, list[str]], language: str) -> str:
    """One line of counts, like the "Indexes" line of a senior academic CV."""
    fr = language == "fr"
    entries = _parse_bib_entries(BIB.read_text(encoding="utf-8"))
    ranks = Counter(_publication_rank(entry) for entry in entries)
    rank_parts = []
    for rank in RANK_ORDER:
        count = ranks[rank]
        if not count or rank == "unranked":
            continue
        if rank.startswith("q"):
            label = (f"revue{'s' if count > 1 else ''} {rank.upper()}" if fr
                     else f"{rank.upper()} journal{'s' if count > 1 else ''}")
        else:
            label = RANK_LABELS[language][rank]
        rank_parts.append(f"{count} {label}")
    parts = [f"{len(entries)} publications" + (f" ({', '.join(rank_parts)})" if rank_parts else "")]

    awards = award_rows(english.get("about-me", []), english.get("about-me", []))
    best_papers = sum(1 for item in awards if "best paper" in item.lower())
    if best_papers:
        parts.append(plural(best_papers, "prix du meilleur article", "prix du meilleur article") if fr
                     else plural(best_papers, "best paper award", "best paper awards"))

    if teaching_rows():
        hours = hours_text(total_hours(), language)
        parts.append(f"{hours} h d’enseignement" if fr else f"{hours} h of teaching")

    students = len(bullets(english.get("students", [])))
    if students:
        parts.append(plural(students, "étudiant encadré", "étudiants encadrés") if fr
                     else plural(students, "student supervised", "students supervised"))

    dated_services = [item for title, items in groups(english.get("services", []))
                      if YEAR_RE.search(title) for item in items]
    committees = sum(1 for item in dated_services if re.search(r"\bPC\b|Program Committee|Artifact|Shadow", item))
    organizing = sum(1 for item in dated_services if re.search(r"organi[sz]ing committee", item, re.I))
    if committees:
        parts.append(plural(committees, "comité de programme", "comités de programme") if fr
                     else plural(committees, "program committee", "program committees"))
    if organizing:
        parts.append(plural(organizing, "comité d’organisation", "comités d’organisation") if fr
                     else plural(organizing, "organizing committee", "organizing committees"))
    return " · ".join(parts) + "."


def shorten(markdown: str, reference: str | None = None, *, language: str = "en") -> str:
    """Build the one-page CV.

    `reference` is the English CV when `markdown` is a translation: the sections
    are in the same order in both files, so the English headings identify them.
    """
    preamble, sections = split_sections(markdown)
    english_sections = split_sections(reference)[1] if reference is not None else sections
    if len(english_sections) != len(sections):
        raise ValueError("The translated CV does not have the same sections as the English CV")
    local: dict[str, list[str]] = {}
    english: dict[str, list[str]] = {}
    interests = None
    for (heading, body), (english_heading, english_body) in zip(sections, english_sections):
        slug = section_slug(english_heading.split(":", 1)[0])
        if slug == "interests":
            interests = heading
        local[slug] = body
        english[slug] = english_body

    def dated_groups(slug: str, transform=lambda item: item) -> list[str]:
        return [row(title, joined([transform(item) for item in items])) for title, items in groups(local.get(slug, []))]

    blocks = [
        ("education", entry_rows(local.get("education", []), with_detail=False)),
        ("experience", entry_rows(local.get("professional-experience", []), with_detail=True)),
        ("awards", award_rows(local.get("about-me", []), english.get("about-me", []))),
        ("publications", publication_rows(language)),
        ("services", dated_groups("services")),
        # No Teaching section here: the hours are in the key figures and the courses
        # under the lecturer positions of the experience section.
        ("students", dated_groups("students", lambda item: TRAILING_DATES_RE.sub("", item))),
        ("talks", [row(title, joined(items[:TALKS_PER_YEAR])) for title, items in groups(local.get("public-talks", []))]),
        ("volunteering", merged_roles(groups(local.get("volunteering", [])))),
    ]

    labels = LABELS[language]
    parts = ["\n".join(preamble).rstrip()]
    # Compact headings with a full-width rule, for this page only.
    parts.append("```{=latex}\n\\cvcompactlayout\n```")
    if interests:
        parts.append(f"## {interests}")
    # Languages close the key figures block: one line instead of a whole section.
    languages = bullets(local.get("languages", []))
    figures = key_figures(english, language)
    if languages:
        colon = "\u00a0:" if language == "fr" else ":"
        figures += f"  \n**{labels['languages']}{colon}** " + " · ".join(language_item.replace("**", "") for language_item in languages)
    parts.append(f"## {labels['key-figures']}\n\n```{{=latex}}\n\\small\\raggedright\n```\n\n{figures}")
    for slug, rows in blocks:
        if rows:
            parts.append(f"## {labels[slug]}\n\n" + "\n".join(rows))
    return "\n\n".join(part for part in parts if part) + "\n"
