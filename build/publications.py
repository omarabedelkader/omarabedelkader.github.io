from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


SECTION_TITLES = {
    "conference": "Refereed Articles in International Conferences",
    "journal": "Refereed Articles in International Journals",
    "workshop": "Refereed Articles in International Workshops",
}


@dataclass
class BibEntry:
    entry_type: str
    key: str
    fields: Dict[str, str]


@dataclass
class Publication:
    category: str
    year: int
    text: str


def _normalize_latex_text(value: str) -> str:
    replacements = {
        r"{\'e}": "é",
        r"{\'E}": "É",
        r"{\'a}": "á",
        r"{\'i}": "í",
        r"{\'o}": "ó",
        r"{\'u}": "ú",
    }
    normalized = value
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


def _strip_wrapping(value: str) -> str:
    value = value.strip().rstrip(",").strip()
    if value.startswith("{") and value.endswith("}"):
        return value[1:-1].strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1].strip()
    return value


def _split_entries(content: str) -> List[str]:
    entries: List[str] = []
    i = 0
    while i < len(content):
        if content[i] != "@":
            i += 1
            continue
        start = i
        brace_index = content.find("{", i)
        if brace_index == -1:
            break
        depth = 0
        j = brace_index
        while j < len(content):
            if content[j] == "{":
                depth += 1
            elif content[j] == "}":
                depth -= 1
                if depth == 0:
                    entries.append(content[start : j + 1])
                    i = j + 1
                    break
            j += 1
        else:
            break
    return entries


def _parse_fields(body: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    depth = 0
    token = []
    parts: List[str] = []

    for ch in body:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)

        if ch == "," and depth == 0:
            parts.append("".join(token).strip())
            token = []
        else:
            token.append(ch)

    if token:
        parts.append("".join(token).strip())

    for part in parts:
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        fields[name.strip().lower()] = _strip_wrapping(value)

    return fields


def _parse_bib(content: str) -> List[BibEntry]:
    parsed: List[BibEntry] = []
    for raw in _split_entries(content):
        kind_end = raw.find("{")
        header = raw[1:kind_end].strip().lower()
        inside = raw[kind_end + 1 : -1].strip()
        if "," not in inside:
            continue
        key, body = inside.split(",", 1)
        parsed.append(BibEntry(entry_type=header, key=key.strip(), fields=_parse_fields(body)))
    return parsed


def _guess_category(entry: BibEntry) -> str:
    explicit = entry.fields.get("pubtype", "").strip().lower()
    if explicit in SECTION_TITLES:
        return explicit

    if entry.entry_type == "article":
        return "journal"

    booktitle = entry.fields.get("booktitle", "").lower()
    if "workshop" in booktitle:
        return "workshop"

    return "conference"


def _format_publication(entry: BibEntry) -> Publication:
    authors = entry.fields.get("author", "Unknown author")
    year_str = entry.fields.get("year", "0")
    try:
        year = int(year_str)
    except ValueError:
        year = 0

    title = _normalize_latex_text(entry.fields.get("title", "Untitled").replace("{", "").replace("}", ""))
    venue = entry.fields.get("journal") or entry.fields.get("booktitle") or ""

    authors = _normalize_latex_text(authors)
    venue = _normalize_latex_text(venue)

    text = f"{authors} ({year_str}). *{title}*."
    if venue:
        text += f" {venue}."

    return Publication(category=_guess_category(entry), year=year, text=text)


def render_grouped_publications_markdown(bib_path: Path) -> str:
    entries = _parse_bib(bib_path.read_text(encoding="utf-8"))
    publications = [_format_publication(entry) for entry in entries]

    grouped: Dict[str, List[Publication]] = {key: [] for key in SECTION_TITLES}
    for publication in publications:
        grouped.setdefault(publication.category, []).append(publication)

    lines: List[str] = []
    for category, section_title in SECTION_TITLES.items():
        lines.append(f"### {section_title}")
        items = sorted(grouped.get(category, []), key=lambda pub: pub.year, reverse=True)

        if not items:
            lines.append("- _No publications yet._")
        else:
            lines.extend(f"- {item.text}" for item in items)
        lines.append("")

    return "\n".join(lines).strip() + "\n"