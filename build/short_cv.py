"""Derive the short CV from the full CV Markdown.

The short CV is never edited by hand: it is rebuilt from `sources/cv.md` (and
its French translation) on every run, so it always follows the full CV. What
is kept from each section is decided by `RULES` below.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

H2_RE = re.compile(r"^##\s+(.+?)\s*$")
H3_RE = re.compile(r"^###\s+")
BULLET_RE = re.compile(r"^\s*[-+]\s+")
HR_RE = re.compile(r"^\s*-{3,}\s*$")

PUBLICATIONS_URL = "https://www.omarabedelkader.com/publications.html"


@dataclass(frozen=True)
class Rule:
    """How much of a section goes into the short CV (None means no limit)."""

    groups: int | None = None  # `###` groups kept, counted from the top
    bullets: int | None = None  # bullets kept in each group
    first_line_only: bool = False  # drop the description lines under a bullet


# Keyed by the slug of the English `##` heading. Sections not listed are left out.
# The limits are tuned so that the short CV fits on one page.
RULES: dict[str, Rule] = {
    "interests": Rule(),
    "about-me": Rule(groups=2, bullets=2),
    "publications": Rule(),
    "services": Rule(groups=1, bullets=3),
    "teaching": Rule(groups=1, bullets=2),
    "software": Rule(bullets=1),
    "public-talks": Rule(groups=1, bullets=2),
    "professional-experience": Rule(),
    "education": Rule(),
    "languages": Rule(),
}


def section_slug(title: str) -> str:
    normalized = unicodedata.normalize("NFD", title.lower())
    ascii_title = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")


def rule_for(heading: str) -> Rule | None:
    # "Interests: A · B · C" is a heading that carries its own content.
    slug = section_slug(heading.split(":", 1)[0])
    return RULES.get(slug)


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


def limit_bullets(lines: list[str], rule: Rule) -> list[str]:
    kept: list[str] = []
    count = 0
    keeping = True
    for line in lines:
        if BULLET_RE.match(line):
            count += 1
            keeping = rule.bullets is None or count <= rule.bullets
            if keeping:
                kept.append(line.rstrip() if rule.first_line_only else line)
        elif not line.strip():
            if kept and kept[-1].strip():
                kept.append("")
        elif keeping and not (rule.first_line_only and count):
            kept.append(line)

    # A trailing hard line break ("  ") with nothing after it would open a gap in the list.
    for index, line in enumerate(kept):
        following = kept[index + 1] if index + 1 < len(kept) else ""
        if not following.strip() or BULLET_RE.match(following):
            kept[index] = line.rstrip()
    return kept


def shorten_section(body: list[str], rule: Rule) -> list[str]:
    body = [line for line in body if not HR_RE.match(line)]
    intro: list[str] = []
    groups: list[list[str]] = []
    for line in body:
        if H3_RE.match(line):
            groups.append([line])
        elif groups:
            groups[-1].append(line)
        else:
            intro.append(line)

    result = limit_bullets(intro, rule)
    for group in groups[: rule.groups]:
        if result and result[-1].strip():
            result.append("")
        result.append(group[0])
        result.extend(limit_bullets(group[1:], rule))
    while result and not result[-1].strip():
        result.pop()
    return result


def shorten(markdown: str, reference: str | None = None, *, language: str = "en") -> str:
    """Build the short CV.

    `reference` is the English CV when `markdown` is a translation: the sections
    are in the same order in both files, so the English headings pick the rules.
    """
    preamble, sections = split_sections(markdown)
    headings = [heading for heading, _ in sections]
    if reference is not None:
        reference_headings = [heading for heading, _ in split_sections(reference)[1]]
        if len(reference_headings) != len(headings):
            raise ValueError("The translated CV does not have the same sections as the English CV")
        headings = reference_headings

    parts = ["\n".join(preamble).rstrip()]
    for (heading, body), rule_heading in zip(sections, headings):
        rule = rule_for(rule_heading)
        if rule is None:
            continue
        if section_slug(rule_heading) == "publications":
            text = (
                f"La liste de mes publications est disponible [ici]({PUBLICATIONS_URL})."
                if language == "fr"
                else f"The list of my publications can be seen [here]({PUBLICATIONS_URL})."
            )
        else:
            text = "\n".join(shorten_section(body, rule))
        parts.append(f"## {heading}\n\n{text}".rstrip())
    return "\n\n".join(part for part in parts if part) + "\n"
