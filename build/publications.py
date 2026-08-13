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
        entry_type_match = re.match(r"@([^{\s]+)", part)
        fields = {
            "entry_type": entry_type_match.group(1).lower() if entry_type_match else "",
            "author": _extract_field(part, "author"),
            "title": _extract_field(part, "title"),
            "booktitle": _extract_field(part, "booktitle"),
            "journal": _extract_field(part, "journal"),
            "year": _extract_field(part, "year"),
            "doi": _extract_field(part, "doi"),
            "keywords": _extract_field(part, "keywords"),
            "rank": _extract_field(part, "rank"),
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
    def to_apa_name(name: str) -> str:
        name = name.strip()
        if not name:
            return ""

        if "," in name:
            last, given = [part.strip() for part in name.split(",", 1)]
        else:
            parts = name.split()
            if len(parts) == 1:
                return parts[0]
            last, given = parts[-1], " ".join(parts[:-1])

        initials = " ".join(
            f"{part[0]}."
            for part in re.split(r"[-\s]+", given)
            if part and part[0].isalpha()
        )
        return f"{last}, {initials}".strip()

    names = [to_apa_name(a) for a in re.split(r"\s+and\s+", authors) if a.strip()]
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]}, & {names[1]}"
    return f"{', '.join(names[:-1])}, & {names[-1]}"


def _publication_group(entry: dict[str, str]) -> str:
    entry_type = entry.get("entry_type", "")
    if entry.get("journal") or entry_type == "article":
        return "journal"
    if entry.get("booktitle") or entry_type in {"inproceedings", "conference"}:
        return "conference"
    return "other"


def _format_publication(entry: dict[str, str]) -> str:
    authors = _format_authors(entry.get("author", ""))
    year = entry.get("year", "")
    title = entry.get("title", "")
    venue = entry.get("journal") or entry.get("booktitle")
    doi = entry.get("doi", "")

    segments = []
    if authors:
        segments.append(authors)
    if year:
        segments.append(f"({year}).")
    if title:
        segments.append(f"{title}.")
    if venue:
        segments.append(f"*{venue}*.")
    if doi:
        doi_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
        segments.append(f"[DOI]({doi_url}).")
    return f"- {' '.join(segments).strip()}"


def _publication_headings(language: str) -> dict[str, str]:
    if language == "fr":
        return {
            "journal": "Articles de revue",
            "conference": "Articles de conférence",
            "other": "Autres publications",
        }
    return {
        "journal": "Journals",
        "conference": "Conferences",
        "other": "Other publications",
    }


def _publication_rank(entry: dict[str, str]) -> str:
    rank = entry.get("rank", "").strip().lower()
    keywords = [
        keyword.strip().lower()
        for keyword in re.split(r"[,;]\s*|\s+", entry.get("keywords", ""))
        if keyword.strip()
    ]

    candidates = [rank, *keywords]
    for candidate in candidates:
        normalized = candidate.removeprefix("rank-").removeprefix("rank")
        if normalized in {"a", "b", "c"}:
            return normalized
        if normalized in {"q1", "q2", "q3", "q4"}:
            return normalized
    return "unranked"


def _rank_headings(language: str) -> dict[str, str]:
    if language == "fr":
        return {
            "a": "Rang A",
            "b": "Rang B",
            "c": "Rang C",
            "q1": "Revues Q1",
            "q2": "Revues Q2",
            "q3": "Revues Q3",
            "q4": "Revues Q4",
            "unranked": "Publications non classées",
        }
    return {
        "a": "Rank A",
        "b": "Rank B",
        "c": "Rank C",
        "q1": "Q1 Journals",
        "q2": "Q2 Journals",
        "q3": "Q3 Journals",
        "q4": "Q4 Journals",
        "unranked": "Unranked Publications",
    }


def _group_entries_by_venue(entries: list[dict[str, str]]) -> dict[str, list[str]]:
    grouped_entries = {
        "journal": [],
        "conference": [],
        "other": [],
    }
    for entry in entries:
        grouped_entries[_publication_group(entry)].append(_format_publication(entry))
    return grouped_entries


def _group_entries_by_rank(entries: list[dict[str, str]]) -> dict[str, list[str]]:
    grouped_entries = {
        "a": [],
        "b": [],
        "c": [],
        "q1": [],
        "q2": [],
        "q3": [],
        "q4": [],
        "unranked": [],
    }
    for entry in entries:
        grouped_entries[_publication_rank(entry)].append(_format_publication(entry))
    return grouped_entries


def generate_publications_markdown(
    bib_path: Path,
    language: str = "en",
    grouping: str = "venue",
) -> str:
    entries = _parse_bib_entries(bib_path.read_text(encoding="utf-8"))
    if not entries:
        return "- No publications available."

    if grouping == "rank":
        grouped_entries = _group_entries_by_rank(entries)
        headings = _rank_headings(language)
        group_order = ("a", "b", "c", "q1", "q2", "q3", "q4", "unranked")
    elif grouping == "venue":
        grouped_entries = _group_entries_by_venue(entries)
        headings = _publication_headings(language)
        group_order = ("journal", "conference", "other")
    else:
        raise ValueError(f"Unknown publication grouping: {grouping}")

    sections = []
    for group_name in group_order:
        lines = grouped_entries[group_name]
        if lines:
            sections.append(f"### {headings[group_name]}\n\n" + "\n".join(lines))
    return "\n\n".join(sections)


def inject_publications(
    markdown_text: str,
    bib_path: Path,
    language: str = "en",
    grouping: str = "venue",
) -> str:
    publication_lines = generate_publications_markdown(bib_path, language, grouping)
    return markdown_text.replace(PUBLICATIONS_TOKEN, publication_lines)
