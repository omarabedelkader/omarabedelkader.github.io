from __future__ import annotations

from pathlib import Path
import re

PUBLICATIONS_TOKEN = "{{PUBLICATIONS_FROM_BIB}}"


def _parse_bib_entries(bib_text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    parts = re.split(r"\n(?=@)", bib_text)
    for part in parts:
        part = part.strip()
        if not part.startswith("@"):
            continue
        fields = {
            "author": _extract_field(part, "author"),
            "title": _extract_field(part, "title"),
            "booktitle": _extract_field(part, "booktitle"),
            "journal": _extract_field(part, "journal"),
            "year": _extract_field(part, "year"),
        }
        entries.append(fields)
    return entries


def _extract_field(entry_text: str, field_name: str) -> str:
    pattern = rf"{field_name}\s*=\s*(\{{(?:[^{{}}]|\{{[^{{}}]*\}})*\}}|\"[^\"]*\")"
    match = re.search(pattern, entry_text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    value = match.group(1).strip()
    if value.startswith("{") and value.endswith("}"):
        value = value[1:-1]
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return _clean_latex(value)


def _clean_latex(text: str) -> str:
    replacements = {
        r"{\\'e}": "é",
        r"{\\'E}": "É",
        "\\'e": "é",
        "\\'E": "É",
        r"\\&": "&",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = re.sub(r"[{}]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _format_authors(authors: str) -> str:
    if not authors:
        return ""
    names = [a.strip() for a in re.split(r"\s+and\s+", authors) if a.strip()]
    return ", ".join(names)


def generate_publications_markdown(bib_path: Path) -> str:
    entries = _parse_bib_entries(bib_path.read_text(encoding="utf-8"))
    if not entries:
        return "- No publications available."

    lines: list[str] = []
    for entry in entries:
        authors = _format_authors(entry.get("author", ""))
        year = entry.get("year", "")
        title = entry.get("title", "")
        venue = entry.get("journal") or entry.get("booktitle")

        segments = []
        if authors:
            segments.append(authors)
        if year:
            segments.append(f"({year}).")
        if title:
            segments.append(f"*{title}*.")
        if venue:
            segments.append(f"{venue}.")
        lines.append(f"- {' '.join(segments).strip()}")
    return "\n".join(lines)


def inject_publications(markdown_text: str, bib_path: Path) -> str:
    publication_lines = generate_publications_markdown(bib_path)
    return markdown_text.replace(PUBLICATIONS_TOKEN, publication_lines)
