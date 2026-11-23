from pathlib import Path
import re
import unicodedata

import pypandoc
from last_updated import last_updated_label
from publications import inject_publications
from short_cv import shorten
from teaching import inject_teaching

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent  # ← project root

resources = ROOT / "resources"

output_dir = ROOT / "cv-full"
output_dir.mkdir(exist_ok=True)

short_cv_dir = ROOT / "cv-short"
short_cv_dir.mkdir(exist_ok=True)

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


def style_resume_entries(markdown: str) -> str:
    """Use the same institution-first layout for experience and education."""
    section_re = re.compile(
        r"(^## (?:Professional Experience|Expériences professionnelles|Education|Éducation))[ \t]*\n"
        r"(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    entry_re = re.compile(
        r"^- \*\*(?P<role>.+?)\*\*(?: · \*(?P<dates>.+?)\*)?[ \t]*\n"
        r"[ \t]+(?P<organization>[^\n]+)"
        # Optional description bullets, indented under the entry.
        r"(?P<details>(?:\n[ \t]+[-+][ \t]+[^\n]+)*)",
        re.MULTILINE,
    )
    detail_re = re.compile(r"^[ \t]+[-+][ \t]+(.+)$", re.MULTILINE)

    def replace_entry(match: re.Match[str]) -> str:
        organization, _, location = match["organization"].partition(" · ")
        fields = [organization, match["dates"] or "", match["role"], location]
        command = r"\cvexperience" + "".join(
            "{" + latex_escape(field.strip()) + "}" for field in fields
        )
        items = detail_re.findall(match["details"])
        if items:
            # Keep the entry and its bullets on one page (about 110 characters per line).
            lines_needed = 2 + sum(1 + len(item) // 110 for item in items)
            command = rf"\needspace{{{lines_needed}\baselineskip}}" + "\n" + command
            command += "\n\\begin{cvdetails}\n" + "\n".join(
                "\\item " + latex_escape(item.strip()) for item in items
            ) + "\n\\end{cvdetails}"
        return "\n```{=latex}\n" + command + "\n```\n"

    def replace_section(match: re.Match[str]) -> str:
        return match[1] + "\n" + entry_re.sub(replace_entry, match[2])

    return section_re.sub(replace_section, markdown)


SITE_URL = "https://www.omarabedelkader.com"


def other_language_note(output_pdf: Path, language: str) -> str:
    """A small closing line, written in the other language, linking to that version of the CV."""
    if language == "en":
        other_name, text = output_pdf.name.replace("-en.", "-fr."), "Ce CV est également disponible en français :"
    else:
        other_name, text = output_pdf.name.replace("-fr.", "-en."), "This CV is also available in English:"
    url = f"{SITE_URL}/{output_pdf.parent.name}/{other_name}"
    return "\n\n```{=latex}\n\\cvotherlanguage{" + latex_escape(text) + "}{" + url + "}\n```\n"


def prepare_markdown(markdown: str, output_pdf: Path, language: str) -> str:
    """The Markdown that Pandoc turns into the CV's LaTeX."""
    rendered_md = inject_publications(
        markdown,
        resources / "publications.bib",
        language,
        grouping="rank",
    )
    rendered_md = style_interests_heading(rendered_md)
    rendered_md = style_doi_links(rendered_md)
    rendered_md = inject_teaching(rendered_md, language, output="latex")
    rendered_md = style_resume_entries(rendered_md)
    # A separator after the last section has nothing to separate (and can push the
    # closing line onto a page of its own).
    rendered_md = re.sub(r"(?:\n\s*-{3,}\s*)+\s*\Z", "", rendered_md.rstrip())
    return rendered_md + other_language_note(output_pdf, language)


def render_pdf(markdown: str, output_pdf: Path, language: str) -> None:
    rendered_md = prepare_markdown(markdown, output_pdf, language)

    pypandoc.convert_text(
        rendered_md,
        "pdf",
        format="md",
        outputfile=str(output_pdf),
        extra_args=[
            "--pdf-engine=xelatex",
            "--citeproc",
            f"--lua-filter={resources / 'cv-indent.lua'}",
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


for input_md, output_pdf, language in cv_builds:
    markdown = input_md.read_text(encoding="utf-8")
    render_pdf(markdown, output_pdf, language)
    # Readable copy next to the PDF, with the publication list filled in. Edit sources/, not this file.
    output_pdf.with_suffix(".md").write_text(
        inject_teaching(
            inject_publications(markdown, resources / "publications.bib", language, grouping="rank"),
            language, output="markdown",
        ),
        encoding="utf-8",
    )

print("CV generated successfully:", output_pdf)

# Short CV: derived from the same sources, so it is refreshed on every build.
english_cv = cv_builds[0][0].read_text(encoding="utf-8")
for input_md, _output_pdf, language in cv_builds:
    short_md = shorten(
        input_md.read_text(encoding="utf-8"),
        reference=None if language == "en" else english_cv,
        language=language,
    )
    short_source = short_cv_dir / f"short-cv-{language}.md"
    short_source.write_text(short_md, encoding="utf-8")
    render_pdf(short_md, short_cv_dir / f"short-cv-{language}.pdf", language)

print("Short CV generated successfully:", short_cv_dir)
