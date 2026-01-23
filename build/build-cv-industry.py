# build-cv-industry.py
from pathlib import Path
import re
import textwrap
import tempfile
import pypandoc

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent  # project root

INPUT_MD = ROOT / "index.md"
RESOURCES = ROOT / "resources"

OUTPUT_DIR = ROOT / "cv"
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_PDF = OUTPUT_DIR / "cv-industry.pdf"
GENERATED_MD = OUTPUT_DIR / "_cv-industry.generated.md"


# ----------------------------
# Markdown extraction helpers
# ----------------------------
def _strip_yaml_front_matter(md: str) -> str:
    # Remove a leading YAML front matter block if present
    if md.lstrip().startswith("---"):
        parts = md.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip("\n")
    return md


def _extract_contact_block(md: str) -> str:
    """
    Your file has a contact block right after YAML, delimited by horizontal rules (---).
    We grab the first such block that contains Email/Website/GitHub etc.
    """
    md_no_yaml = _strip_yaml_front_matter(md)
    blocks = re.split(r"\n---\n", md_no_yaml)
    # After YAML, content often looks like: (empty), contact, rest...
    # We'll pick the first block that looks like contact info.
    for b in blocks:
        if any(k in b for k in ["Email:", "Website:", "GitHub:", "LinkedIn:", "Hugging Face:"]):
            return b.strip()
    return ""


def _split_sections_by_h2(md: str) -> dict:
    """
    Splits on '## ' headings and returns {heading: content}.
    Keeps content until next '## '.
    """
    md_no_yaml = _strip_yaml_front_matter(md)
    # Keep the contact block out of section parsing; it's handled separately.
    # But leaving it in doesn't hurt; we still key off ## headings.
    pattern = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(md_no_yaml))
    sections = {}
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_no_yaml)
        content = md_no_yaml[start:end].strip()
        sections[title] = content
    return sections


def _take_bullets(text: str, max_items: int) -> str:
    """
    Keep up to max_items markdown list items (lines starting with '-' or '*').
    """
    lines = [ln.rstrip() for ln in text.splitlines()]
    bullets = [ln for ln in lines if re.match(r"^\s*[-*]\s+", ln)]
    return "\n".join(bullets[:max_items]).strip()


def _shorten_paragraph(text: str, max_chars: int = 280) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _extract_experience_entries(exp_md: str, max_roles: int = 2) -> str:
    """
    Experience section uses patterns like:
    **Role** — Company (Location)
    *Dates*
    - bullets...

    We'll take the first max_roles roles and keep up to ~3 bullets per role.
    """
    # Split roles on blank line followed by '**'
    chunks = re.split(r"\n\s*\n(?=\*\*)", exp_md.strip())
    roles_out = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk.startswith("**"):
            continue
        lines = chunk.splitlines()
        header = lines[0].strip()
        dates = ""
        rest = "\n".join(lines[1:]).strip()
        # find italic date line if present
        m = re.search(r"^\*(.+?)\*\s*$", rest, flags=re.MULTILINE)
        if m:
            dates = f"*{m.group(1).strip()}*"
        bullets = _take_bullets(chunk, 3)
        role_block = "\n".join([x for x in [header, dates, bullets] if x]).strip()
        roles_out.append(role_block)
        if len(roles_out) >= max_roles:
            break
    return "\n\n".join(roles_out).strip()


def _extract_software_top(soft_md: str, keep_projects=None, max_bullets_per_project: int = 3) -> str:
    """
    Software section uses '### ProjectName' subheadings.
    We'll keep a curated set (default: your most industry-relevant) and
    keep a few bullets + the GitHub line if present.
    """
    if keep_projects is None:
        keep_projects = ["PharoGPT", "Pharo-Copilot", "ChatPharo", "INERIS-IA"]

    # Split on ### headings
    parts = re.split(r"^###\s+", soft_md, flags=re.MULTILINE)
    # parts[0] is intro (usually empty). Each subsequent starts with "Name\n..."
    projects = {}
    for p in parts[1:]:
        name = p.splitlines()[0].strip()
        body = "\n".join(p.splitlines()[1:]).strip()
        projects[name] = body

    out = []
    for name in keep_projects:
        body = projects.get(name)
        if not body:
            continue
        bullets = _take_bullets(body, max_bullets_per_project)
        # Keep repo line(s) if exist
        repo_lines = []
        for ln in body.splitlines():
            if "GitHub Repository" in ln or ln.strip().startswith("**GitHub Repository:**"):
                repo_lines.append(ln.strip())
        block = f"### {name}\n"
        if bullets:
            block += bullets + "\n"
        if repo_lines:
            block += "\n".join(repo_lines) + "\n"
        out.append(block.strip())
    return "\n\n".join(out).strip()


def _extract_education_lean(edu_md: str) -> str:
    """
    Keep the Education section but make sure it’s not too long.
    Typically already compact; we keep as-is.
    """
    return edu_md.strip()


def _extract_skills_lean(skills_md: str) -> str:
    """
    Convert the "Technologies & Skills" multi-line bold categories into a compact bullet list.
    """
    lines = [ln.strip() for ln in skills_md.splitlines() if ln.strip()]
    # Keep first ~6 lines (usually the bold categories)
    keep = []
    for ln in lines:
        if ln.startswith("**") and ":" in ln:
            keep.append(ln)
    if not keep:
        keep = lines
    keep = keep[:6]
    return "\n".join([f"- {re.sub(r'^-\\s*', '', k)}" for k in keep]).strip()


def _extract_languages(lng_md: str) -> str:
    bullets = _take_bullets(lng_md, 3)
    return bullets.strip()


# ----------------------------
# Build the one-page industry CV markdown
# ----------------------------
def build_industry_md(full_md: str) -> str:
    contact = _extract_contact_block(full_md)
    sections = _split_sections_by_h2(full_md)

    about = sections.get("About Me", "").strip()
    about_line = _shorten_paragraph(about, max_chars=260)

    expertise = sections.get("Core Expertise", "")
    expertise_bullets = _take_bullets(expertise, 6)

    responsibilities = sections.get("Responsibilities", "")
    responsibilities_bullets = _take_bullets(responsibilities, 4)

    education = _extract_education_lean(sections.get("Education", ""))

    experience = _extract_experience_entries(sections.get("Experience", ""), max_roles=2)

    software = _extract_software_top(sections.get("Software", ""))

    awards = sections.get("Awards and Honors", "")
    awards_keep = awards.strip()
    # keep it short: take first bold line + next line if present
    if awards_keep:
        a_lines = [ln for ln in awards_keep.splitlines() if ln.strip()]
        awards_keep = "\n".join(a_lines[:3]).strip()

    skills = _extract_skills_lean(sections.get("Technologies & Skills", ""))

    languages = _extract_languages(sections.get("Languages", ""))

    # Create a clean YAML for industry version (no bibliography/csl to keep it compact)
    yaml = textwrap.dedent(
        """\
        ---
        title: "Omar AbedelKader"
        date: "Last updated: January 2026"
        ---
        """
    ).strip()

    md = []
    md.append(yaml)
    md.append("")  # spacer

    if contact:
        md.append(contact)
        md.append("\n---\n")

    # Two-column content should be concise and scannable
    md.append("## Summary")
    md.append(about_line)

    if expertise_bullets:
        md.append("\n## Core Strengths")
        md.append(expertise_bullets)

    if experience:
        md.append("\n## Experience")
        md.append(experience)

    if software:
        md.append("\n## Projects")
        md.append(software)

    if responsibilities_bullets:
        md.append("\n## Leadership & Community")
        md.append(responsibilities_bullets)

    if awards_keep:
        md.append("\n## Awards")
        md.append(awards_keep)

    if education:
        md.append("\n## Education")
        md.append(education)

    if skills:
        md.append("\n## Skills")
        md.append(skills)

    if languages:
        md.append("\n## Languages")
        md.append(languages)

    # Small footer line (kept short)
    md.append("\n---\n")
    return "\n\n".join(md).strip() + "\n"


# ----------------------------
# Pandoc -> PDF (two columns, one page style)
# ----------------------------
def main() -> None:
    if not INPUT_MD.exists():
        raise FileNotFoundError(f"Missing {INPUT_MD}")

    full_md = INPUT_MD.read_text(encoding="utf-8")
    industry_md = build_industry_md(full_md)
    GENERATED_MD.write_text(industry_md, encoding="utf-8")

    header_tex = RESOURCES / "header.tex"

    # Create small LaTeX includes on the fly so you don't have to add files to your repo
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        industry_header = td / "industry-header.tex"
        industry_before = td / "industry-before.tex"
        industry_after = td / "industry-after.tex"

        industry_header.write_text(
            textwrap.dedent(
                r"""
                % --- Industry CV tight layout + two columns ---
                \usepackage{multicol}
                \setlength{\columnsep}{0.25in}
                \setlength{\parindent}{0pt}

                % Tighten section spacing a bit
                \usepackage{titlesec}
                \titlespacing*{\section}{0pt}{0.6em}{0.35em}
                \titlespacing*{\subsection}{0pt}{0.5em}{0.25em}
                \titlespacing*{\subsubsection}{0pt}{0.4em}{0.2em}

                % Tighten lists
                \usepackage{enumitem}
                \setlist[itemize]{noitemsep, topsep=0.2em, leftmargin=*}
                \setlist[enumerate]{noitemsep, topsep=0.2em, leftmargin=*}

                % Avoid page numbers (industry one-pager)
                \pagestyle{empty}
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        industry_before.write_text(
            textwrap.dedent(
                r"""
                \begin{multicols}{2}
                \small
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        industry_after.write_text(
            textwrap.dedent(
                r"""
                \end{multicols}
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        extra_args = [
            "--pdf-engine=xelatex",
            # Use multiple header includes: your existing header + industry tweaks
            "-H",
            str(header_tex) if header_tex.exists() else str(industry_header),
            "-H",
            str(industry_header),
            "--include-before-body",
            str(industry_before),
            "--include-after-body",
            str(industry_after),
            # Tight margins to fit one page better
            "-V",
            "geometry=margin=0.7in",
            "-V",
            "fontsize=10pt",
            "-V",
            "mainfont=Times New Roman",
        ]

        # Convert from the generated industry markdown
        pypandoc.convert_file(
            str(GENERATED_MD),
            "pdf",
            outputfile=str(OUTPUT_PDF),
            extra_args=extra_args,
        )

    print("Industry CV generated successfully:", OUTPUT_PDF)


if __name__ == "__main__":
    main()
