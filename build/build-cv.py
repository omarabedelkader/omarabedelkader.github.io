from pathlib import Path
import re
import unicodedata

import pypandoc
from last_updated import last_updated_label
from publications import inject_publications

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent  # ← project root

resources = ROOT / "resources"

output_dir = ROOT / "cv"
output_dir.mkdir(exist_ok=True)

cv_builds = [
    (ROOT / "sources" / "cv.md", output_dir / "cv-en.pdf", "en"),
    (ROOT / "sources" / "cv-fr.md", output_dir / "cv-fr.pdf", "fr"),
]

INTERESTS_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
DOI_LINK_RE = re.compile(r"\[DOI\]\(([^)]+)\)")
LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def normalized_label(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = normalized.replace("’", "'").replace("‘", "'").replace("`", "'")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip().lower()


def latex_escape(text: str) -> str:
    return "".join(LATEX_ESCAPES.get(char, char) for char in text)


def style_interests_heading(markdown: str) -> str:
    def replace_heading(match: re.Match[str]) -> str:
        heading = match.group(1).strip()
        separator = heading.find(":")
        if separator == -1:
            return match.group(0)

        label = heading[:separator].strip()
        interests = re.sub(r"\s+", " ", heading[separator + 1 :].strip())
        if not re.fullmatch(r"(interests|interets|centres d['.]?interet)", normalized_label(label)):
            return match.group(0)

        return (
            "```{=latex}\n"
            f"\\cvinterests{{{latex_escape(label)}}}{{{latex_escape(interests)}}}\n"
            "```"
        )

    return INTERESTS_HEADING_RE.sub(replace_heading, markdown, count=1)


def style_doi_links(markdown: str) -> str:
    return DOI_LINK_RE.sub(r"[\\textcolor{cvblue}{DOI}](\1)", markdown)


for input_md, output_pdf, language in cv_builds:
    rendered_md = inject_publications(
        input_md.read_text(encoding="utf-8"),
        resources / "publications.bib",
        language,
        grouping="rank",
    )
    rendered_md = style_interests_heading(rendered_md)
    rendered_md = style_doi_links(rendered_md)

    pypandoc.convert_text(
        rendered_md,
        "pdf",
        format="md",
        outputfile=str(output_pdf),
        extra_args=[
            "--pdf-engine=xelatex",
            "--citeproc",
            f"--metadata=lang={'fr-FR' if language == 'fr' else 'en-US'}",
            f"--bibliography={resources / 'publications.bib'}",
            f"--csl={resources / 'apa.csl'}",
            "-H", str(resources / "header.tex"),
            "-V", "documentclass=article",
            "-V", "papersize=a4",
            "-V", "fontsize=10pt",
            "-V", "geometry=margin=0.62in",
        ]
    )

print("CV generated successfully:", output_pdf)
