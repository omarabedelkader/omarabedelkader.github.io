"""One teaching dataset for both CV PDFs and the bilingual website."""
from decimal import Decimal
from html import escape
import json
from pathlib import Path
from urllib.parse import urlsplit

TOKEN = "{{TEACHING_FROM_DATA}}"
SHORT_TOKEN = "{{TEACHING_SHORT_FROM_DATA}}"
DATA = Path(__file__).resolve().parents[1] / "resources" / "teaching.json"


def teaching_rows(short: bool = False) -> list[dict]:
    rows = json.loads(DATA.read_text(encoding="utf-8"))
    # Retain the established short-CV selection: two entries from the latest year.
    return rows[:2] if short else rows


def labels(language: str) -> list[str]:
    return (
        ["Intitulé", "Année", "Établissement", "Volume horaire (EQTD)", "Niveau", "Eff.", "Lang."]
        if language == "fr" else
        ["Course", "Year", "Institution", "Hours (EQTD)", "Level", "Students", "Lang."]
    )


def hours(value: str | Decimal, language: str) -> str:
    value = str(value)
    return value.replace(".", ",") if language == "fr" else value


def values(row: dict, language: str) -> list[str]:
    kind = row["format"]
    if language == "en":
        kind = {"TP": "Lab", "TD": "Tutorial", "CM": "Lecture", "Projet": "Project"}[kind]
    return [
        f"{row['code']} {row['title'][language]}", str(row["year"]), row["institution"],
        f"{kind} ({hours(row['hours'], language)})", row["level"],
        str(row["students"]), row["language"],
    ]


def total_label(language: str) -> str:
    return "Volume horaire total" if language == "fr" else "Total teaching hours"


def latex(text: str) -> str:
    mapping = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
               "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(mapping.get(char, char) for char in text)


def render_latex(rows: list[dict], language: str, short: bool) -> str:
    headings = labels(language)
    headings[3] = "Heures" if language == "fr" else "Hours"
    cells = [rf"\textbf{{{latex(label)}}}" for label in headings]
    cells[3] = rf"\shortstack[l]{{\textbf{{{headings[3]}}}\\\textbf{{(EQTD)}}}}"
    if short:
        cells[3] = rf"\textbf{{{headings[3]} (EQTD)}}"
    lines = [
        "```{=latex}", r"\begingroup" + (r"\footnotesize" if short else r"\small"),
        r"\setlength{\tabcolsep}{3pt}", r"\setlength{\aboverulesep}{1pt}",
        r"\setlength{\belowrulesep}{1pt}", r"\renewcommand{\arraystretch}{1}",
        r"\noindent\begin{tabularx}{\linewidth}{@{}>{\raggedright\arraybackslash}Xlllcrc@{}}",
        "" if short else r"\toprule", " & ".join(cells) + r" \\", r"\midrule",
    ]
    previous_year = None
    for row in rows:
        if previous_year is not None and previous_year != row["year"]:
            lines.append(r"\midrule")
        cells = [latex(value) for value in values(row, language)]
        if row["url"]:
            icon = r"\faGraduationCap" if urlsplit(row["url"]).hostname == "moodle.univ-lille.fr" else r"\faUniversity"
            cells[0] += rf"~\href{{{latex(row['url'])}}}{{\icon{{{icon}}}}}"
        lines.append(" & ".join(cells) + r" \\")
        previous_year = row["year"]
    if not short:
        total = sum((Decimal(row["hours"]) for row in rows), Decimal(0))
        lines.extend([
            r"\midrule",
            r"\multicolumn{3}{@{}l}{\textbf{" + total_label(language)
            + r"}} & \textbf{" + hours(total, language) + r"} & & & \\",
        ])
    lines.extend([r"\bottomrule", r"\end{tabularx}\par", r"\endgroup", "```"])
    return "\n".join(lines)


def render_html(rows: list[dict], language: str, short: bool) -> str:
    name = "Enseignements" if language == "fr" else "Teaching courses"
    lines = [
        f'<div class="teaching-table-scroll" role="region" aria-label="{name}" tabindex="0">',
        f'<table class="teaching-table"><caption class="visually-hidden">{name}</caption>',
        '<thead><tr>' + ''.join(f'<th scope="col">{escape(label)}</th>' for label in labels(language)) + '</tr></thead>',
    ]
    previous_year = None
    for row in rows:
        if previous_year != row["year"]:
            if previous_year is not None:
                lines.append('</tbody>')
            lines.append('<tbody>')
        cells = [escape(value) for value in values(row, language)]
        if row["url"]:
            moodle = urlsplit(row["url"]).hostname == "moodle.univ-lille.fr"
            icon = "🎓" if moodle else "🏛"
            link_label = escape(f"{'Moodle' if moodle else row['institution']}: {row['title'][language]}", quote=True)
            cells[0] += f' <a class="teaching-course-link" href="{escape(row["url"], quote=True)}" aria-label="{link_label}" title="{link_label}"><span aria-hidden="true">{icon}</span></a>'
        lines.append('<tr>' + ''.join(f'<td>{cell}</td>' for cell in cells) + '</tr>')
        previous_year = row["year"]
    lines.append('</tbody>')
    if not short:
        total = sum((Decimal(row["hours"]) for row in rows), Decimal(0))
        lines.append(f'<tfoot><tr><th scope="row" colspan="3">{total_label(language)}</th><td>{hours(total, language)} (EQTD)</td><td colspan="3"></td></tr></tfoot>')
    lines.extend(['</table>', '</div>'])
    return "\n".join(lines)


def render_markdown(rows: list[dict], language: str, short: bool) -> str:
    lines = ['| ' + ' | '.join(labels(language)) + ' |', '| ' + ' | '.join(['---'] * 7) + ' |']
    for row in rows:
        cells = values(row, language)
        if row["url"]:
            cells[0] = f'[{cells[0]}]({row["url"]})'
        lines.append('| ' + ' | '.join(cells) + ' |')
    if not short:
        total = sum((Decimal(row["hours"]) for row in rows), Decimal(0))
        lines.append(f'| **{total_label(language)}** | | | **{hours(total, language)} (EQTD)** | | | |')
    return '\n'.join(lines)


def inject_teaching(markdown: str, language: str, *, output: str) -> str:
    renderer = {"latex": render_latex, "html": render_html, "markdown": render_markdown}[output]
    for token, short in [(TOKEN, False), (SHORT_TOKEN, True)]:
        if token in markdown:
            markdown = markdown.replace(token, renderer(teaching_rows(short), language, short))
    return markdown
