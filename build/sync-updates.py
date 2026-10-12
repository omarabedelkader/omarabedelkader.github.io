"""Pull new items from Google Scholar and conf.researchr.org into the sources.

Run by the monthly CI workflow (`.github/workflows/monthly-update.yml`); it is
deliberately not part of `run.sh`.

What it does:
- conf.researchr.org profile: a new committee role becomes a bullet in the
  Services section of `sources/site.md` and `sources/cv.md`; a new accepted
  paper becomes an entry in `resources/publications.bib` (authors and track
  are read from the paper's details page).
- Google Scholar profile: a new paper becomes an entry in
  `resources/publications.bib`.

The news lines and the French files are not written here: `run.sh` derives
them from the sources afterwards.

Every remote item is recorded in `resources/sync-state.json` the first time it
is handled and is never touched again (see `sync_state.py`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher
from html import unescape
from pathlib import Path
import argparse
import os
import re
import sys
import time
import unicodedata

import requests

from publications import _parse_bib_entries
from sync_state import load_state, save_state

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent
BIB_FILE = ROOT / "resources" / "publications.bib"
SITE_MD = ROOT / "sources" / "site.md"
CV_MD = ROOT / "sources" / "cv.md"

SCHOLAR_USER = "Wl01zhQAAAAJ"
SCHOLAR_LIST_URL = (
    "https://scholar.google.com/citations"
    f"?user={SCHOLAR_USER}&hl=en&cstart=0&pagesize=100&sortby=pubdate"
)
SCHOLAR_DETAIL_URL = (
    "https://scholar.google.com/citations"
    f"?view_op=view_citation&hl=en&user={SCHOLAR_USER}&citation_for_view={SCHOLAR_USER}:{{id}}"
)
RESEARCHR_PROFILE_URL = "https://conf.researchr.org/profile/omarabedelkader"

# How the site owner is written in the .bib file, whatever the remote spelling.
OWNER_ASCII_NAME = "omar abedelkader"
OWNER_BIB_NAME = "AbedelKader, Omar"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)
REQUEST_PAUSE_SECONDS = 3
TITLE_MATCH_RATIO = 0.92
SERVICE_SECTION_SLUGS = {"services"}
# Rows of a researchr details page worth keeping in the ledger next to the author list.
DETAIL_FIELDS = {"Track", "When", "Where", "Session"}

H2_RE = re.compile(r"^##\s+(.+?)\s*$")
H3_RE = re.compile(r"^###\s+(.+?)\s*$")
TAG_RE = re.compile(r"<[^>]+>")


class SourceUnavailable(Exception):
    """A remote source could not be read; the other source is still processed."""


@dataclass
class Report:
    added: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recorded: int = 0

    def markdown(self) -> str:
        lines: list[str] = []
        if self.added:
            lines.append("Added:")
            lines.extend(f"- {item}" for item in self.added)
        else:
            lines.append("Nothing to change: no new paper or role on Google Scholar or conf.researchr.org.")
        if self.pending:
            lines.append("")
            lines.append("Needs a manual entry (not enough data to import):")
            lines.extend(f"- {item}" for item in self.pending)
        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            lines.extend(f"- {item}" for item in self.warnings)
        return "\n".join(lines) + "\n"


# ======================================================
# Small text helpers
# ======================================================

def ascii_fold(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def section_slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", ascii_fold(title.lower())).strip("-")


def text_of(html: str) -> str:
    return re.sub(r"\s+", " ", unescape(TAG_RE.sub("", html))).strip()


def title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", ascii_fold(title.lower()))


def same_title(left: str, right: str) -> bool:
    a, b = title_key(left), title_key(right)
    if not a or not b:
        return False
    return a == b or SequenceMatcher(None, a, b).ratio() >= TITLE_MATCH_RATIO


def fetch(url: str) -> str:
    last_error: Exception | None = None
    for attempt in range(3):
        if attempt:
            time.sleep(REQUEST_PAUSE_SECONDS * (attempt + 1))
        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
                timeout=30,
            )
        except requests.RequestException as exc:
            last_error = exc
            continue
        if response.status_code == 200:
            return response.text
        last_error = RuntimeError(f"HTTP {response.status_code}")
    raise SourceUnavailable(f"{url}: {last_error}")


# ======================================================
# Bibliography
# ======================================================

def bib_author(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    if ascii_fold(name).lower() == OWNER_ASCII_NAME:
        return OWNER_BIB_NAME
    parts = name.split(" ")
    if len(parts) == 1:
        return parts[0]
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


def bib_value(text: str) -> str:
    # The site's .bib reader only understands one level of braces.
    return re.sub(r"\s+", " ", text.replace("{", "").replace("}", "")).strip()


def new_bib_key(authors: list[str], year: str, title: str, existing: set[str]) -> str:
    surname = bib_author(authors[0]).split(",")[0] if authors else "paper"
    stop_words = {"a", "an", "the", "on", "of", "for", "in", "to", "and", "towards"}
    words = [word for word in re.findall(r"[a-z0-9]+", ascii_fold(title.lower())) if word not in stop_words]
    base = re.sub(r"[^a-z0-9]", "", ascii_fold(surname.lower())) + year + (words[0] if words else "")
    key, suffix = base, 2
    while key in existing:
        key = f"{base}{suffix}"
        suffix += 1
    return key


def render_bib_entry(entry_type: str, key: str, fields: dict[str, str], origin: str) -> str:
    lines = [f"% Imported from {origin} on {date.today().isoformat()}. Review and edit freely: it will not be re-imported."]
    lines.append(f"@{entry_type}{{{key},")
    body = [f"  {name} = {{{bib_value(value)}}}" for name, value in fields.items() if value]
    lines.append(",\n".join(body))
    lines.append("}")
    return "\n".join(lines)


def append_bib_entry(bib_text: str, entry: str) -> str:
    return bib_text.rstrip("\n") + "\n\n" + entry + "\n"


def doi_from_link(link: str) -> str:
    arxiv = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", link)
    if arxiv:
        return f"10.48550/arXiv.{arxiv.group(1)}"
    doi = re.search(r"doi\.org/(10\.\d{4,9}/[^\s?#]+)", link)
    return doi.group(1) if doi else ""


# ======================================================
# Markdown: add a bullet under `### <year>` of a section
# ======================================================

def insert_year_bullet(markdown: str, section_slugs: set[str], year: int, bullet: str) -> str:
    lines = markdown.split("\n")
    start = end = None
    for index, line in enumerate(lines):
        heading = H2_RE.match(line)
        if not heading:
            continue
        if start is None and section_slug(heading.group(1)) in section_slugs:
            start = index
        elif start is not None:
            end = index
            break
    if start is None:
        raise ValueError(f"No section named {sorted(section_slugs)} found")
    end = len(lines) if end is None else end

    older_heading = None
    for index in range(start + 1, end):
        heading = H3_RE.match(lines[index])
        if not heading:
            continue
        heading_year = re.search(r"\b(20\d{2})\b", heading.group(1))
        if not heading_year:
            continue
        if int(heading_year.group(1)) == year:
            lines.insert(index + 1, bullet)
            return "\n".join(lines)
        if int(heading_year.group(1)) < year and older_heading is None:
            older_heading = index

    # No heading for that year yet: years are listed newest first.
    block = [f"### {year}", bullet, ""]
    if older_heading is not None:
        position = older_heading
    else:
        position = end
        while position > start + 1 and (not lines[position - 1].strip() or lines[position - 1].strip() == "---"):
            position -= 1
        block = ["", *block[:-1]]
    lines[position:position] = block
    return "\n".join(lines)


# ======================================================
# conf.researchr.org
# ======================================================

@dataclass(frozen=True)
class ResearchrItem:
    year: int
    conference: str
    kind: str
    href: str
    text: str

    @property
    def state_id(self) -> str:
        return f"{self.kind}|{self.href or self.text}"

    @property
    def edition(self) -> str:
        return f"{self.conference}'{self.year % 100:02d}"


def parse_researchr_profile(html: str) -> list[ResearchrItem]:
    marker = html.find('id="contributions-timeline"')
    if marker == -1:
        raise SourceUnavailable("conf.researchr.org: profile page has no contributions timeline")
    timeline = html[marker:]
    stop = timeline.find('id="embedWidget"')
    if stop != -1:
        timeline = timeline[:stop]

    items: list[ResearchrItem] = []
    for year_block in timeline.split('<div class="contribution-year">')[1:]:
        year_match = re.match(r"\s*<h3>(\d{4})</h3>", year_block)
        if not year_match:
            continue
        for conference_block in year_block.split("<h4>")[1:]:
            name_html, _, rest = conference_block.partition("</h4>")
            conference = re.sub(r"\s*-\s*External$", "", text_of(name_html))
            for kind, href, label in re.findall(
                r'<li><small title="([^"]*)".*?<a href="([^"]*)"[^>]*>(.*?)</a>', rest, flags=re.DOTALL
            ):
                items.append(
                    ResearchrItem(
                        year=int(year_match.group(1)),
                        conference=conference,
                        kind=unescape(kind),
                        href=unescape(href),
                        text=text_of(label),
                    )
                )
    return items


def split_track(text: str) -> tuple[str, str]:
    match = re.match(r"^(.*?) within the (.+?)-track$", text)
    return (match.group(1), match.group(2)) if match else (text, "")


def parse_researchr_details(html: str) -> dict[str, str]:
    rows = re.findall(
        r'<label class="col-sm-2 control-label"[^>]*>(.*?)</label><div class="col-sm-10">(.*?)</div></div>',
        html,
        flags=re.DOTALL,
    )
    details: dict[str, str] = {}
    for label, value in rows:
        name = text_of(label)
        if name == "Who":
            people = [text_of(person) for person in re.findall(r"<a [^>]*>(.*?)</a>", value, flags=re.DOTALL)]
            details[name] = "; ".join(people) if people else text_of(value).replace(", ", "; ")
        elif name in DETAIL_FIELDS and name not in details:
            details[name] = text_of(value)
    return details


def service_bullets(item: ResearchrItem) -> tuple[str, str]:
    """Bullet for site.md (inline links) and for cv.md (icon links)."""
    role, track = split_track(item.text)
    description = f"{role}, {track}" if track and track.lower() not in role.lower() else role
    site = f"- {description} at [{item.edition}]({item.href})" if item.href else f"- {description} at {item.edition}"
    cv = (
        f"- {description} at {item.edition} [\\icon{{\\faLink}}]({item.href})"
        if item.href
        else f"- {description} at {item.edition}"
    )
    return site, cv


def sync_researchr(state: dict, texts: dict[Path, str], report: Report) -> None:
    seen: dict = state.setdefault("researchr", {})
    items = parse_researchr_profile(fetch(RESEARCHR_PROFILE_URL))
    today = date.today().isoformat()

    for item in items:
        if item.state_id in seen:
            continue

        record = {"first_seen": today, "text": item.text, "conference": item.conference, "year": item.year}
        authored = re.match(r"^Author of (.+)$", split_track(item.text)[0])

        if not authored:
            if item.href and any(item.href in text for text in (texts[SITE_MD], texts[CV_MD])):
                seen[item.state_id] = {**record, "status": "already-listed"}
                report.recorded += 1
                continue
            site_bullet, cv_bullet = service_bullets(item)
            texts[SITE_MD] = insert_year_bullet(texts[SITE_MD], SERVICE_SECTION_SLUGS, item.year, site_bullet)
            texts[CV_MD] = insert_year_bullet(texts[CV_MD], SERVICE_SECTION_SLUGS, item.year, cv_bullet)
            seen[item.state_id] = {**record, "status": "added-to-services"}
            report.added.append(f"Service ({item.year}): {site_bullet[2:]}")
            continue

        title = authored.group(1)
        entries = _parse_bib_entries(texts[BIB_FILE])
        match = next((entry for entry in entries if same_title(entry["title"], title)), None)
        if match:
            seen[item.state_id] = {**record, "status": "already-in-bib", "bibkey": match["key"]}
            report.recorded += 1
            continue

        if "conf.researchr.org/details/" not in item.href:
            # Without a details page there is no author list; leave it for Scholar or a manual entry.
            report.pending.append(f"{item.edition}: {title} ({item.href or 'no link'})")
            continue

        time.sleep(REQUEST_PAUSE_SECONDS)
        try:
            details = parse_researchr_details(fetch(item.href))
        except SourceUnavailable:
            details = {}
        authors = [name for name in details.get("Who", "").split("; ") if name]
        if not authors:
            report.pending.append(f"{item.edition}: {title} (no author list on {item.href})")
            continue

        track = details.get("Track") or split_track(item.text)[1]
        venue = f"{item.conference} {item.year}"
        booktitle = track if track.lower().startswith(venue.lower()) else f"{venue} {track}".strip()
        key = new_bib_key(authors, str(item.year), title, {entry["key"] for entry in entries})
        entry = render_bib_entry(
            "inproceedings",
            key,
            {
                "author": " and ".join(bib_author(name) for name in authors),
                "title": title,
                "booktitle": booktitle,
                "year": str(item.year),
                "url": item.href,
            },
            origin="conf.researchr.org",
        )
        texts[BIB_FILE] = append_bib_entry(texts[BIB_FILE], entry)
        seen[item.state_id] = {**record, "status": "added-to-bib", "bibkey": key, "details": details}
        report.added.append(f"Publication `{key}` from conf.researchr.org: {title} ({booktitle})")


# ======================================================
# Google Scholar
# ======================================================

@dataclass(frozen=True)
class ScholarRow:
    citation_id: str
    title: str
    authors: str
    venue: str
    year: str


def parse_scholar_list(html: str) -> list[ScholarRow]:
    rows: list[ScholarRow] = []
    for row in re.findall(r'<tr class="gsc_a_tr">(.*?)</tr>', html, flags=re.DOTALL):
        citation = re.search(r"citation_for_view=[^:\"&]+:([^\"&]+)", row)
        title = re.search(r'class="gsc_a_at">(.*?)</a>', row, flags=re.DOTALL)
        if not citation or not title:
            continue
        gray = re.findall(r'<div class="gs_gray">(.*?)</div>', row, flags=re.DOTALL)
        year = re.search(r'class="gsc_a_h[^"]*">(\d{4})<', row)
        venue = re.sub(r'<span class="gs_oph">.*?</span>', "", gray[1], flags=re.DOTALL) if len(gray) > 1 else ""
        rows.append(
            ScholarRow(
                citation_id=unescape(citation.group(1)),
                title=text_of(title.group(1)),
                authors=text_of(gray[0]) if gray else "",
                venue=text_of(venue),
                year=year.group(1) if year else "",
            )
        )
    return rows


def parse_scholar_detail(html: str) -> dict[str, str]:
    details = {
        text_of(name): text_of(value)
        for name, value in re.findall(
            r'<div class="gsc_oci_field">(.*?)</div><div class="gsc_oci_value"[^>]*>(.*?)</div>',
            html,
            flags=re.DOTALL,
        )
    }
    link = re.search(r'class="gsc_oci_title_link" href="([^"]+)"', html)
    if link:
        details["link"] = unescape(link.group(1))
    return details


def scholar_bib_entry(row: ScholarRow, details: dict[str, str], existing_keys: set[str]) -> tuple[str, str]:
    authors = [name.strip() for name in details.get("Authors", "").split(",") if name.strip()]
    year = (details.get("Publication date", "")[:4] or row.year).strip()
    link = details.get("link", "")
    doi = doi_from_link(link)
    journal = details.get("Journal", "")
    conference = details.get("Conference", "") or details.get("Book", "")
    key = new_bib_key(authors, year, row.title, existing_keys)

    fields = {"author": " and ".join(bib_author(name) for name in authors), "title": row.title}
    if conference:
        entry_type = "inproceedings"
        fields["booktitle"] = conference
    elif journal and "arxiv" not in journal.lower():
        entry_type = "article"
        fields["journal"] = journal
        fields["volume"] = details.get("Volume", "")
        fields["pages"] = details.get("Pages", "")
    else:
        # Preprints and anything Scholar cannot classify land under "Other publications".
        entry_type = "misc"
        fields["howpublished"] = journal or details.get("Source", "") or details.get("Publisher", "") or row.venue
    fields["year"] = year
    fields["doi"] = doi
    if not doi:
        fields["url"] = link

    return key, render_bib_entry(entry_type, key, fields, origin=f"Google Scholar ({row.citation_id})")


def sync_scholar(state: dict, texts: dict[Path, str], report: Report) -> None:
    seen: dict = state.setdefault("scholar", {})
    html = fetch(SCHOLAR_LIST_URL)
    rows = parse_scholar_list(html)
    if not rows:
        # A profile with papers never renders an empty table; this is a block page or a layout change.
        raise SourceUnavailable("Google Scholar: no publication rows found (blocked request or changed page layout)")
    today = date.today().isoformat()

    for row in rows:
        if row.citation_id in seen:
            continue

        entries = _parse_bib_entries(texts[BIB_FILE])
        match = next((entry for entry in entries if same_title(entry["title"], row.title)), None)
        if match:
            seen[row.citation_id] = {"first_seen": today, "title": row.title, "status": "already-in-bib", "bibkey": match["key"]}
            report.recorded += 1
            continue

        time.sleep(REQUEST_PAUSE_SECONDS)
        try:
            details = parse_scholar_detail(fetch(SCHOLAR_DETAIL_URL.format(id=row.citation_id)))
        except SourceUnavailable:
            details = {}
        if not details.get("Authors"):
            report.pending.append(f"Google Scholar: {row.title} (details page could not be read)")
            continue

        key, entry = scholar_bib_entry(row, details, {item["key"] for item in entries})
        texts[BIB_FILE] = append_bib_entry(texts[BIB_FILE], entry)
        seen[row.citation_id] = {"first_seen": today, "title": row.title, "status": "added-to-bib", "bibkey": key}
        report.added.append(f"Publication `{key}` from Google Scholar: {row.title} ({row.venue or 'no venue'})")


# ======================================================
# Entry point
# ======================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import new items from Google Scholar and conf.researchr.org.")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing anything.")
    parser.add_argument("--report", type=Path, default=None, help="Also write the Markdown report to this file.")
    parser.add_argument("--skip-scholar", action="store_true")
    parser.add_argument("--skip-researchr", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state = load_state()
    texts = {path: path.read_text(encoding="utf-8") for path in (BIB_FILE, SITE_MD, CV_MD)}
    original = dict(texts)
    report = Report()

    # researchr first: it knows the conference and track, so its entries are the better ones.
    sources = []
    if not args.skip_researchr:
        sources.append(("conf.researchr.org", sync_researchr))
    if not args.skip_scholar:
        sources.append(("Google Scholar", sync_scholar))

    for name, sync in sources:
        try:
            sync(state, texts, report)
        except SourceUnavailable as exc:
            report.warnings.append(f"{name} was not checked this time: {exc}")

    summary = report.markdown()
    print(summary, end="")
    for warning in report.warnings:
        print(f"::warning::{warning}")

    if args.report:
        args.report.write_text(summary, encoding="utf-8")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as handle:
            handle.write("## Monthly sync\n\n" + summary)

    if args.dry_run:
        print("Dry run: nothing was written.")
        return 0

    for path, text in texts.items():
        if text != original[path]:
            path.write_text(text, encoding="utf-8")
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
