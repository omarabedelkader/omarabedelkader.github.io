from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path
from urllib.parse import urlencode, urljoin
import json
import os
import re
import shutil
import unicodedata

import pypandoc
import yaml

from last_updated import last_updated_label
from publications import inject_publications


# ======================================================
# Paths
# ======================================================

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent

DOCS = ROOT / "docs"
RESOURCES = ROOT / "resources"
SOURCES = ROOT / "sources"
TEMPLATES = ROOT / "templates"

SITE_URL = "https://omarabedelkader.github.io/"
ISSUES_NEW_URL = "https://github.com/omarabedelkader/omarabedelkader.github.io/issues/new"

SITE_SOURCES = [
    {
        "md": SOURCES / "site.md",
        "html": DOCS / "index.html",
        "lang": "en",
        "pagetitle": "Omar AbedelKader",
        "description": "Official website of Omar AbedelKader, AI engineer and researcher. Projects, publications, CV, and contact details.",
    },
    {
        "md": SOURCES / "site-fr.md",
        "html": DOCS / "fr" / "index.html",
        "lang": "fr",
        "pagetitle": "Omar AbedelKader — Version française",
        "description": "Site officiel d'Omar AbedelKader, ingénieur et chercheur en IA. Projets, publications, CV et coordonnées.",
    },
]

CSS_SRC = TEMPLATES / "style.css"
JS_SRC = TEMPLATES / "main.js"
ASSETS_SRC = TEMPLATES / "assets"

CSS_DST = DOCS / "style.css"
JS_DST = DOCS / "main.js"
ASSETS_DST = DOCS / "assets"

FAVICON_SRC = TEMPLATES / "favicon.ico"
FAVICON_DST = DOCS / "favicon.ico"
HEADER_INCLUDE = RESOURCES / "seo_head.html"

BLOG_SRC_DIR = SOURCES / "blog"
BLOG_FR_SRC_DIR = SOURCES / "blog-fr"
BLOG_FEED_LIMIT = 20

VIEWPORT_META = '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />'
VIEWPORT_RE = re.compile(r'<meta name="viewport" content="[^"]*" />')
FRONTMATTER_RE = re.compile(r"^---\s*\n(?P<yaml>.*?)\n---\s*\n?", re.DOTALL)
H1_RE = re.compile(r"^\s*#\s+([^\n]+?)\s*#*\s*$", re.MULTILINE)
LEADING_H1_RE = re.compile(r"^\s*#\s+([^\n]+?)\s*#*\s*\n+")
NEWS_TOKEN = "{{NEWS_FROM_SOURCES}}"
BLOG_TOKEN = "{{BLOG_FROM_SOURCES}}"

DOCS.mkdir(exist_ok=True)


# ======================================================
# Copy static assets
# ======================================================

shutil.copyfile(CSS_SRC, CSS_DST)
shutil.copyfile(JS_SRC, JS_DST)
if ASSETS_SRC.exists():
    shutil.copytree(ASSETS_SRC, ASSETS_DST, dirs_exist_ok=True)

shutil.copyfile(FAVICON_SRC, FAVICON_DST)

CV_SRC_DIR = ROOT / "cv"
CV_DST_DIR = DOCS / "cv"
CV_DST_DIR.mkdir(parents=True, exist_ok=True)

for cv_pdf in CV_SRC_DIR.glob("*.pdf"):
    shutil.copyfile(cv_pdf, CV_DST_DIR / cv_pdf.name)


# ======================================================
# Shared helpers
# ======================================================

H2_RE = re.compile(r"^##\s+(.+?)\s*$")
CURRENT_ITEM_BULLET_RE = re.compile(r"^(\s*[-+]\s+)\*(?![\s*])(.+)$")
CURRENT_MARKED_SECTIONS = {
    "services",
    "students",
    "etudiants",
    "public-talks",
    "presentations-publiques",
}

EN_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
FR_MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)


@dataclass(frozen=True)
class BlogPost:
    slug: str
    lang: str
    source_path: Path
    title: str
    description: str
    published: date
    updated: date | None
    tags: tuple[str, ...]
    body: str
    draft: bool


def section_slug(title: str) -> str:
    normalized = unicodedata.normalize("NFD", title.lower())
    ascii_title = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")


def normalize_mobile_viewport(html: str) -> str:
    return VIEWPORT_RE.sub(VIEWPORT_META, html, count=1)


def html_attr(value: str) -> str:
    return escape(str(value), quote=True)


def json_for_script(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def split_frontmatter(markdown: str, source_path: Path | None = None) -> tuple[dict, str]:
    if markdown.lstrip().startswith("---") and not markdown.startswith("---"):
        prefix = f"{source_path}: " if source_path else ""
        raise ValueError(f"{prefix}blog front matter must start at the first column of the file")

    match = FRONTMATTER_RE.match(markdown)
    if not match:
        return {}, markdown

    metadata = yaml.safe_load(match.group("yaml")) or {}
    if not isinstance(metadata, dict):
        raise ValueError("front matter must be a YAML mapping")
    return metadata, markdown[match.end() :]


def boolish(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def coerce_date(value, source_path: Path, field: str) -> date:
    if value is None or value == "":
        return datetime.fromtimestamp(source_path.stat().st_mtime).date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise ValueError(f"{source_path}: invalid blog `{field}` date {value!r}; use YYYY-MM-DD") from exc


def first_h1(markdown: str) -> str | None:
    match = H1_RE.search(markdown)
    return match.group(1).strip() if match else None


def remove_leading_duplicate_h1(markdown: str, title: str) -> str:
    match = LEADING_H1_RE.match(markdown)
    if not match:
        return markdown
    if section_slug(match.group(1)) == section_slug(title):
        return markdown[match.end() :]
    return markdown


def markdown_excerpt(markdown: str, limit: int = 180) -> str:
    text = re.sub(r"(```[\s\S]*?```|~~~[\s\S]*?~~~)", " ", markdown)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^[ \t#>*+-]+", " ", text, flags=re.MULTILINE)
    text = re.sub(r"[*_`~]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def normalize_tags(value) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        parts = re.split(r"\s*,\s*", value)
    elif isinstance(value, list):
        parts = [str(item).strip() for item in value]
    else:
        parts = [str(value).strip()]
    return tuple(part for part in parts if part)


def format_date_for_lang(value: date, lang: str) -> str:
    if lang == "fr":
        return f"{value.day} {FR_MONTHS[value.month - 1]} {value.year}"
    return f"{EN_MONTHS[value.month - 1]} {value.day}, {value.year}"


def rss_date(value: date) -> str:
    dt = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return format_datetime(dt, usegmt=True)


def html_url_path(html_path: Path) -> str:
    rel = html_path.relative_to(DOCS).as_posix()
    if rel == "index.html":
        return ""
    if rel.endswith("/index.html"):
        return rel[:-10]
    return rel


def absolute_url_for_html(html_path: Path) -> str:
    return urljoin(SITE_URL, html_url_path(html_path))


def relative_url(from_html: Path, to_html: Path) -> str:
    rel = os.path.relpath(to_html, from_html.parent).replace(os.sep, "/")
    if rel == "index.html":
        return "./"
    if rel.endswith("/index.html"):
        return rel[:-10] or "./"
    return rel


def footer_html(lang: str, source_path: Path) -> str:
    footer_label = "Dernière mise à jour" if lang == "fr" else "Last updated"
    copyright_text = "Copyright © 2024 Omar AbedelKader"
    return (
        f"<footer class='site-footer'>{footer_label}: {last_updated_label(source_path)}"
        f"<br>{copyright_text}</footer>"
    )


# ======================================================
# Blog source model
# ======================================================

def read_blog_post(path: Path, lang: str, slug_override: str | None = None) -> BlogPost:
    metadata, body = split_frontmatter(path.read_text(encoding="utf-8"), path)
    if not metadata:
        raise ValueError(f"{path}: blog posts must start with YAML front matter containing at least `title` and `date`")
    for required in ("title", "date"):
        if required not in metadata:
            raise ValueError(f"{path}: blog front matter is missing required `{required}`")

    slug = section_slug(str(slug_override or metadata.get("slug") or path.stem))
    if not slug:
        raise ValueError(f"{path}: blog slug cannot be empty")

    title = str(metadata.get("title") or first_h1(body) or path.stem.replace("-", " ").title()).strip()
    if not title:
        raise ValueError(f"{path}: blog title cannot be empty")

    body = remove_leading_duplicate_h1(body, title).strip()
    description = str(metadata.get("description") or metadata.get("summary") or markdown_excerpt(body)).strip()
    published = coerce_date(metadata.get("date"), path, "date")
    updated = coerce_date(metadata.get("updated"), path, "updated") if metadata.get("updated") else None

    return BlogPost(
        slug=slug,
        lang=lang,
        source_path=path,
        title=title,
        description=description,
        published=published,
        updated=updated,
        tags=normalize_tags(metadata.get("tags")),
        body=body,
        draft=boolish(metadata.get("draft")),
    )


def ensure_unique_slugs(posts: list[BlogPost], lang: str) -> None:
    seen: dict[str, Path] = {}
    for post in posts:
        if post.slug in seen:
            raise ValueError(f"Duplicate {lang} blog slug `{post.slug}` in {seen[post.slug]} and {post.source_path}")
        seen[post.slug] = post.source_path


def collect_blog_posts() -> dict[str, list[BlogPost]]:
    if not BLOG_SRC_DIR.exists():
        return {"en": [], "fr": []}

    en_posts: list[BlogPost] = []
    fr_posts: list[BlogPost] = []
    missing_fr: list[Path] = []

    for path in sorted(BLOG_SRC_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue

        en_post = read_blog_post(path, "en")
        if en_post.draft:
            continue

        en_posts.append(en_post)
        fr_path = BLOG_FR_SRC_DIR / path.name
        if not fr_path.exists():
            missing_fr.append(path)
            continue

        fr_post = read_blog_post(fr_path, "fr", slug_override=en_post.slug)
        if not fr_post.draft:
            fr_posts.append(fr_post)

    if missing_fr:
        missing = "\n".join(f"- {path.relative_to(ROOT)}" for path in missing_fr)
        raise SystemExit(
            "Missing generated French blog translations. Run `./run.sh` so the blog "
            f"translation step can create them first.\n{missing}"
        )

    ensure_unique_slugs(en_posts, "English")
    ensure_unique_slugs(fr_posts, "French")

    key = lambda post: (post.published, post.title.lower())
    return {
        "en": sorted(en_posts, key=key, reverse=True),
        "fr": sorted(fr_posts, key=key, reverse=True),
    }


def blog_post_html_path(post: BlogPost) -> Path:
    if post.lang == "fr":
        return DOCS / "fr" / "blog" / post.slug / "index.html"
    return DOCS / "blog" / post.slug / "index.html"


def blog_index_html_path(lang: str) -> Path:
    return DOCS / "fr" / "blog" / "index.html" if lang == "fr" else DOCS / "blog" / "index.html"


def blog_feed_path(lang: str) -> Path:
    return DOCS / "fr" / "blog" / "feed.xml" if lang == "fr" else DOCS / "blog" / "feed.xml"


def latest_blog_source(posts: list[BlogPost]) -> Path:
    if not posts:
        return SOURCES / "site.md"
    return max(posts, key=lambda post: post.source_path.stat().st_mtime).source_path


# ======================================================
# Markdown preprocessing
# ======================================================

def mark_current_items(markdown: str) -> str:
    lines = markdown.splitlines(keepends=True)
    in_marked_section = False
    processed = []

    for line in lines:
        newline = "\n" if line.endswith("\n") else ""
        content = line[:-1] if newline else line

        heading = H2_RE.match(content)
        if heading:
            in_marked_section = section_slug(heading.group(1)) in CURRENT_MARKED_SECTIONS

        if in_marked_section:
            current = CURRENT_ITEM_BULLET_RE.match(content)
            if current:
                prefix, body = current.groups()
                content = f'{prefix}<span class="current-item-marker" data-current-item="true"></span>{body}'

        processed.append(content + newline)

    return "".join(processed)


def inject_news(markdown: str, language: str) -> str:
    if NEWS_TOKEN not in markdown:
        return markdown

    news_file = SOURCES / ("news-fr.md" if language == "fr" else "news.md")
    fallback = "- Aucune actualité." if language == "fr" else "- No news."
    news = news_file.read_text(encoding="utf-8").strip() if news_file.exists() else fallback
    return markdown.replace(NEWS_TOKEN, news)


def inject_blog_summary(markdown: str, language: str, posts_by_lang: dict[str, list[BlogPost]]) -> str:
    if BLOG_TOKEN not in markdown:
        return markdown

    posts = posts_by_lang[language]
    if not posts:
        fallback = "- Aucun billet publié pour le moment." if language == "fr" else "- No blog posts published yet."
        return markdown.replace(BLOG_TOKEN, fallback)

    lines: list[str] = []
    for post in posts[:5]:
        date_text = format_date_for_lang(post.published, language)
        title = post.title.replace("\n", " ")
        description = post.description.replace("\n", " ")
        lines.append(f"- [{title}](blog/{post.slug}/) — {date_text}. {description}")

    all_link = "[Voir tous les billets](blog/)" if language == "fr" else "[View all posts](blog/)"
    lines.append("")
    lines.append(all_link)
    return markdown.replace(BLOG_TOKEN, "\n".join(lines))


# ======================================================
# Pandoc conversion
# ======================================================

def build_page(config: dict, posts_by_lang: dict[str, list[BlogPost]]) -> None:
    config["html"].parent.mkdir(parents=True, exist_ok=True)

    extra_args = [
        "--standalone",
        f"--metadata=lang={config['lang']}",
        "--citeproc",
        f"--resource-path={RESOURCES}",
        "--bibliography=publications.bib",
        "--csl=apa.csl",
        "--metadata=link-citations:true",
        "--css=../style.css" if config["lang"] == "fr" else "--css=style.css",
        f"--metadata=pagetitle={config['pagetitle']}",
        "--metadata=title=Omar AbedelKader",
        f"--metadata=description={config['description']}",
        "--metadata=keywords=Omar AbedelKader,Omar Abdelkader,Omar Abedelkader,AI engineer,machine learning,publications,CV,blog",
        f"--include-in-header={HEADER_INCLUDE}",
    ]

    rendered_md = inject_publications(
        config["md"].read_text(encoding="utf-8"),
        RESOURCES / "publications.bib",
        config["lang"],
        include_selected=True,
    )
    rendered_md = inject_news(rendered_md, config["lang"])
    rendered_md = inject_blog_summary(rendered_md, config["lang"], posts_by_lang)
    rendered_md = mark_current_items(rendered_md)

    html = pypandoc.convert_text(
        rendered_md,
        to="html5",
        format="md",
        extra_args=extra_args,
    )

    html = normalize_mobile_viewport(html)

    script_path = "../main.js" if config["lang"] == "fr" else "main.js"
    html = html.replace(
        "<body>",
        "<body><main class='cv' id='cv'>",
        1,
    ).replace(
        "</body>",
        "</main>"
        f"{footer_html(config['lang'], config['md'])}"
        f"<script src='{script_path}' defer></script>"
        "</body>",
        1,
    )

    config["html"].write_text(html, encoding="utf-8")


def blog_head_common(
    html_path: Path,
    lang: str,
    title: str,
    description: str,
    og_type: str,
    alternate_html_path: Path | None,
    feed_xml_path: Path | None,
    post: BlogPost | None = None,
) -> str:
    canonical = absolute_url_for_html(html_path)
    lines = [
        f'<link rel="canonical" href="{html_attr(canonical)}" />',
        f'<link rel="icon" href="{html_attr(relative_url(html_path, FAVICON_DST))}" />',
    ]

    if alternate_html_path is not None:
        en_path = html_path if lang == "en" else alternate_html_path
        fr_path = alternate_html_path if lang == "en" else html_path
        lines.extend(
            [
                f'<link rel="alternate" hreflang="en" href="{html_attr(absolute_url_for_html(en_path))}" />',
                f'<link rel="alternate" hreflang="fr" href="{html_attr(absolute_url_for_html(fr_path))}" />',
                f'<link rel="alternate" hreflang="x-default" href="{html_attr(absolute_url_for_html(en_path))}" />',
            ]
        )

    if feed_xml_path is not None:
        feed_title = "Omar AbedelKader — Blog"
        lines.append(
            f'<link rel="alternate" type="application/rss+xml" title="{html_attr(feed_title)}" '
            f'href="{html_attr(urljoin(SITE_URL, feed_xml_path.relative_to(DOCS).as_posix()))}" />'
        )

    lines.extend(
        [
            f'<meta property="og:type" content="{html_attr(og_type)}" />',
            f'<meta property="og:title" content="{html_attr(title)}" />',
            f'<meta property="og:description" content="{html_attr(description)}" />',
            f'<meta property="og:url" content="{html_attr(canonical)}" />',
            '<meta name="twitter:card" content="summary" />',
            f'<meta name="twitter:title" content="{html_attr(title)}" />',
            f'<meta name="twitter:description" content="{html_attr(description)}" />',
        ]
    )

    if post is not None:
        lines.append(f'<meta property="article:published_time" content="{post.published.isoformat()}" />')
        if post.updated:
            lines.append(f'<meta property="article:modified_time" content="{post.updated.isoformat()}" />')
        for tag in post.tags:
            lines.append(f'<meta property="article:tag" content="{html_attr(tag)}" />')
        data = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": post.title,
            "description": post.description,
            "datePublished": post.published.isoformat(),
            "dateModified": (post.updated or post.published).isoformat(),
            "author": {
                "@type": "Person",
                "name": "Omar AbedelKader",
                "url": SITE_URL,
            },
            "mainEntityOfPage": canonical,
            "inLanguage": lang,
            "keywords": list(post.tags),
        }
        lines.append(f'<script type="application/ld+json">{json_for_script(data)}</script>')

    return "\n  ".join(lines)


def convert_blog_markdown(
    markdown: str,
    html_path: Path,
    lang: str,
    title: str,
    pagetitle: str,
    description: str,
    head_html: str,
    main_class: str,
    main_id: str,
    before_content: str,
    after_title: str,
    after_content: str,
    footer_source: Path,
) -> None:
    html_path.parent.mkdir(parents=True, exist_ok=True)
    extra_args = [
        "--standalone",
        f"--metadata=lang={lang}",
        "--citeproc",
        f"--resource-path={RESOURCES}",
        "--bibliography=publications.bib",
        "--csl=apa.csl",
        "--metadata=link-citations:true",
        f"--css={relative_url(html_path, CSS_DST)}",
        f"--metadata=pagetitle={pagetitle}",
        f"--metadata=title={title}",
        f"--metadata=description={description}",
        "--metadata=keywords=Omar AbedelKader,Omar Abdelkader,Omar Abedelkader,AI engineer,machine learning,software engineering,Pharo,blog",
    ]

    html = pypandoc.convert_text(markdown, to="html5", format="md", extra_args=extra_args)
    html = normalize_mobile_viewport(html)
    html = html.replace("</head>", f"  {head_html}\n</head>", 1)
    if after_title:
        html = html.replace("</header>", f"</header>\n{after_title}", 1)
    html = html.replace(
        "<body>",
        f"<body><main class='cv {main_class}' id='{main_id}'>\n{before_content}",
        1,
    ).replace(
        "</body>",
        f"{after_content}\n</main>{footer_html(lang, footer_source)}</body>",
        1,
    )
    html_path.write_text(html, encoding="utf-8")


def blog_tag_html(tags: tuple[str, ...]) -> str:
    if not tags:
        return ""
    tag_items = "".join(f'<span class="blog-tag">{escape(tag)}</span>' for tag in tags)
    return f'<span class="blog-tags">{tag_items}</span>'


def blog_post_count(count: int, lang: str) -> str:
    if lang == "fr":
        return f"{count} billet{'s' if count != 1 else ''}"
    return f"{count} post{'s' if count != 1 else ''}"


def tag_slug(tag: str) -> str:
    return section_slug(tag) or "tag"


def build_blog_card(post: BlogPost, index_path: Path, lang: str) -> str:
    post_href = relative_url(index_path, blog_post_html_path(post))
    date_text = format_date_for_lang(post.published, lang)
    tags = blog_tag_html(post.tags)
    tags_value = " ".join(tag_slug(tag) for tag in post.tags)
    search_value = " ".join([post.title, post.description, " ".join(post.tags)]).lower()
    return (
        '<article class="blog-card" role="listitem" data-blog-card '
        f'data-year="{post.published.year}" data-tags="{html_attr(tags_value)}" '
        f'data-search="{html_attr(search_value)}">'
        f'<h3><a href="{html_attr(post_href)}">{escape(post.title)}</a></h3>'
        f'<p class="blog-card-meta"><time datetime="{post.published.isoformat()}">{date_text}</time>{tags}</p>'
        f'<p>{escape(post.description)}</p>'
        "</article>"
    )


def blog_archive_script() -> str:
    return """<script>
(() => {
  const archive = document.querySelector("[data-blog-archive]");
  if (!archive) return;

  const yearButtons = Array.from(archive.querySelectorAll("[data-blog-year]"));
  const tagButtons = Array.from(archive.querySelectorAll("[data-blog-tag]"));
  const viewButtons = Array.from(archive.querySelectorAll("[data-blog-view]"));
  const search = archive.querySelector("[data-blog-search]");
  const sections = Array.from(archive.querySelectorAll("[data-blog-year-section]"));
  const cards = Array.from(archive.querySelectorAll("[data-blog-card]"));
  const count = archive.querySelector("[data-blog-count]");
  const empty = archive.querySelector("[data-blog-empty]");
  const singular = archive.dataset.singular || "post";
  const plural = archive.dataset.plural || "posts";
  const resultLabel = archive.dataset.resultLabel || "Showing";
  const yearLabel = archive.dataset.yearLabel || "Year";
  const tagLabel = archive.dataset.tagLabel || "Topic";
  const noMatches = archive.dataset.noMatches || "No matching posts.";

  const state = {
    year: "all",
    tag: "all",
    query: "",
    view: "grid"
  };

  const countLabel = (value) => `${value} ${value === 1 ? singular : plural}`;
  const setPressed = (buttons, key, value) => {
    buttons.forEach((button) => {
      const active = button.dataset[key] === value;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
  };

  const apply = () => {
    let visibleCount = 0;
    const query = state.query.trim().toLowerCase();

    cards.forEach((card) => {
      const yearMatches = state.year === "all" || card.dataset.year === state.year;
      const tagMatches = state.tag === "all" || (card.dataset.tags || "").split(" ").includes(state.tag);
      const queryMatches = !query || (card.dataset.search || "").includes(query);
      const visible = yearMatches && tagMatches && queryMatches;
      card.hidden = !visible;
      if (visible) visibleCount += 1;
    });

    sections.forEach((section) => {
      section.hidden = !section.querySelector("[data-blog-card]:not([hidden])");
    });

    setPressed(yearButtons, "blogYear", state.year);
    setPressed(tagButtons, "blogTag", state.tag);
    setPressed(viewButtons, "blogView", state.view);
    archive.classList.toggle("is-list", state.view === "list");
    archive.classList.toggle("is-grid", state.view !== "list");

    if (count) {
      const filters = [];
      if (state.year !== "all") filters.push(`${yearLabel} ${state.year}`);
      if (state.tag !== "all") {
        const tagButton = tagButtons.find((button) => button.dataset.blogTag === state.tag);
        filters.push(`${tagLabel} ${(tagButton && tagButton.dataset.label) || state.tag}`);
      }
      count.textContent = filters.length
        ? `${resultLabel} ${countLabel(visibleCount)} · ${filters.join(" · ")}`
        : `${resultLabel} ${countLabel(visibleCount)}`;
    }

    if (empty) {
      empty.hidden = visibleCount !== 0;
      empty.textContent = noMatches;
    }
  };

  yearButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.year = button.dataset.blogYear || "all";
      apply();
    });
  });

  tagButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.tag = button.dataset.blogTag || "all";
      apply();
    });
  });

  viewButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.view = button.dataset.blogView || "grid";
      apply();
    });
  });

  if (search) {
    search.addEventListener("input", () => {
      state.query = search.value || "";
      apply();
    });
  }

  apply();
})();
</script>"""


def build_blog_index(posts: list[BlogPost], lang: str) -> None:
    html_path = blog_index_html_path(lang)
    alternate_path = blog_index_html_path("en" if lang == "fr" else "fr")
    title = "Blog"
    description = (
        "Billets d'Omar AbedelKader sur l'IA, le génie logiciel, Pharo et la pratique de la recherche."
        if lang == "fr"
        else "Posts by Omar AbedelKader on AI, software engineering, Pharo, and research practice."
    )

    if posts:
        posts_by_year: dict[int, list[BlogPost]] = {}
        for post in posts:
            posts_by_year.setdefault(post.published.year, []).append(post)

        years = sorted(posts_by_year, reverse=True)
        all_years_label = "Toutes les années" if lang == "fr" else "All years"
        all_tags_label = "Tous les sujets" if lang == "fr" else "All topics"
        year_label = "Année" if lang == "fr" else "Year"
        tag_label = "Sujet" if lang == "fr" else "Topic"
        result_label = "Affichage de" if lang == "fr" else "Showing"
        no_matches = "Aucun billet ne correspond à ces filtres." if lang == "fr" else "No posts match these filters."
        singular = "billet" if lang == "fr" else "post"
        plural = "billets" if lang == "fr" else "posts"
        search_label = "Rechercher" if lang == "fr" else "Search"
        search_placeholder = "Rechercher dans les billets" if lang == "fr" else "Search posts"
        view_label = "Affichage" if lang == "fr" else "View"
        grid_label = "Grille" if lang == "fr" else "Grid"
        list_label = "Liste" if lang == "fr" else "List"
        years_label = "Filtrer par année" if lang == "fr" else "Filter by year"
        tags_label = "Filtrer par sujet" if lang == "fr" else "Filter by topic"
        all_button = "Tous" if lang == "fr" else "All"

        tags = sorted({tag for post in posts for tag in post.tags}, key=str.casefold)

        controls = [
            '<div class="blog-toolbar">',
            '<label class="blog-search-label">',
            f'<span>{escape(search_label)}</span>',
            f'<input type="search" data-blog-search placeholder="{html_attr(search_placeholder)}" autocomplete="off" spellcheck="false" />',
            "</label>",
            f'<div class="blog-view-toggle" role="toolbar" aria-label="{html_attr(view_label)}">',
            (
                '<button type="button" class="blog-view-button is-active" data-blog-view="grid" aria-pressed="true">'
                f"{escape(grid_label)}</button>"
            ),
            (
                '<button type="button" class="blog-view-button" data-blog-view="list" aria-pressed="false">'
                f"{escape(list_label)}</button>"
            ),
            "</div>",
            "</div>",
            f'<div class="blog-filter-group" aria-label="{html_attr(years_label)}">',
            f'<div class="blog-filter-label">{escape(years_label)}</div>',
            '<div class="blog-chip-row" role="toolbar">',
            (
                '<button type="button" class="blog-filter-chip is-active" data-blog-year="all" aria-pressed="true">'
                f'<span>{escape(all_button)}</span><strong>{len(posts)}</strong></button>'
            ),
        ]
        for year in years:
            controls.append(
                '<button type="button" class="blog-filter-chip" '
                f'data-blog-year="{year}" aria-pressed="false">'
                f'<span>{year}</span><strong>{len(posts_by_year[year])}</strong></button>'
            )
        controls.extend(["</div>", "</div>"])

        if tags:
            controls.extend(
                [
                    f'<div class="blog-filter-group" aria-label="{html_attr(tags_label)}">',
                    f'<div class="blog-filter-label">{escape(tags_label)}</div>',
                    '<div class="blog-chip-row" role="toolbar">',
                    (
                        '<button type="button" class="blog-filter-chip is-active" data-blog-tag="all" '
                        f'aria-pressed="true" data-label="{html_attr(all_tags_label)}">'
                        f'<span>{escape(all_tags_label)}</span><strong>{len(posts)}</strong></button>'
                    ),
                ]
            )
            for tag in tags:
                tag_count = sum(1 for post in posts if tag in post.tags)
                controls.append(
                    '<button type="button" class="blog-filter-chip" '
                    f'data-blog-tag="{html_attr(tag_slug(tag))}" data-label="{html_attr(tag)}" aria-pressed="false">'
                    f'<span>{escape(tag)}</span><strong>{tag_count}</strong></button>'
                )
            controls.extend(["</div>", "</div>"])

        sections = []
        for year in years:
            cards = "\n".join(build_blog_card(post, html_path, lang) for post in posts_by_year[year])
            sections.append(
                f'<section class="blog-year-section" data-blog-year-section data-blog-year="{year}" '
                f'data-count="{len(posts_by_year[year])}">'
                f"<h2>{year}</h2>"
                '<div class="blog-index-list" role="list">'
                f"{cards}"
                "</div>"
                "</section>"
            )

        body = (
            '<div class="blog-archive" data-blog-archive '
            f'data-total="{len(posts)}" '
            f'data-year-label="{html_attr(year_label)}" '
            f'data-tag-label="{html_attr(tag_label)}" '
            f'data-result-label="{html_attr(result_label)}" '
            f'data-no-matches="{html_attr(no_matches)}" '
            f'data-singular="{html_attr(singular)}" '
            f'data-plural="{html_attr(plural)}">'
            + "\n".join(controls)
            + f'<p class="blog-archive-count" data-blog-count>{escape(result_label)} {blog_post_count(len(posts), lang)}</p>'
            + '<div class="blog-archive-years">'
            + "\n".join(sections)
            + "</div>"
            + '<p class="blog-empty" data-blog-empty hidden></p>'
            + blog_archive_script()
            + "</div>"
        )
    else:
        empty = "Aucun billet publié pour le moment." if lang == "fr" else "No blog posts published yet."
        body = f'<p class="blog-empty">{empty}</p>'

    head = blog_head_common(
        html_path=html_path,
        lang=lang,
        title=title,
        description=description,
        og_type="website",
        alternate_html_path=alternate_path,
        feed_xml_path=blog_feed_path(lang),
    )
    convert_blog_markdown(
        markdown=body,
        html_path=html_path,
        lang=lang,
        title=title,
        pagetitle="Blog | Omar AbedelKader",
        description=description,
        head_html=head,
        main_class="blog-index",
        main_id="blog-index",
        before_content="",
        after_title="",
        after_content="",
        footer_source=latest_blog_source(posts),
    )


def issue_note_html(post: BlogPost) -> str:
    page_url = absolute_url_for_html(blog_post_html_path(post))
    if post.lang == "fr":
        title = f"Problème avec le billet : {post.title}"
        body = f"J'ai trouvé un problème sur ce billet :\n\n{page_url}\n\nProblème :\n"
        text = "Si vous pensez qu'il y a un problème avec ce billet, veuillez "
        link_text = "ouvrir une issue"
        suffix = "."
    else:
        title = f"Problem with blog post: {post.title}"
        body = f"I found a problem on this blog post:\n\n{page_url}\n\nProblem:\n"
        text = "If you think there is a problem with this post, please "
        link_text = "create an issue"
        suffix = "."

    issue_href = f"{ISSUES_NEW_URL}?{urlencode({'title': title, 'body': body})}"
    return (
        '<aside class="blog-issue-note">'
        f'<p>{text}<a href="{html_attr(issue_href)}">{link_text}</a>{suffix}</p>'
        "</aside>"
    )


def build_blog_post(post: BlogPost, alternate_post: BlogPost) -> None:
    html_path = blog_post_html_path(post)
    alternate_path = blog_post_html_path(alternate_post)
    date_text = format_date_for_lang(post.published, post.lang)
    updated_text = ""
    if post.updated:
        label = "Mis à jour" if post.lang == "fr" else "Updated"
        updated_text = f'<span>{label}: {format_date_for_lang(post.updated, post.lang)}</span>'

    post_meta = (
        '<div class="blog-post-meta">'
        f'<time datetime="{post.published.isoformat()}">{date_text}</time>'
        f"{updated_text}"
        f"{blog_tag_html(post.tags)}"
        "</div>"
    )
    head = blog_head_common(
        html_path=html_path,
        lang=post.lang,
        title=post.title,
        description=post.description,
        og_type="article",
        alternate_html_path=alternate_path,
        feed_xml_path=blog_feed_path(post.lang),
        post=post,
    )
    convert_blog_markdown(
        markdown=post.body,
        html_path=html_path,
        lang=post.lang,
        title=post.title,
        pagetitle=f"{post.title} | Omar AbedelKader",
        description=post.description,
        head_html=head,
        main_class="blog-page",
        main_id="blog-post",
        before_content="",
        after_title=post_meta,
        after_content=issue_note_html(post),
        footer_source=post.source_path,
    )


def clean_blog_output() -> None:
    for path in (DOCS / "blog", DOCS / "fr" / "blog"):
        if path.exists():
            shutil.rmtree(path)


def write_blog_feed(posts: list[BlogPost], lang: str) -> None:
    feed_path = blog_feed_path(lang)
    feed_path.parent.mkdir(parents=True, exist_ok=True)

    channel_title = "Omar AbedelKader — Blog"
    channel_description = (
        "Billets sur l'IA, le génie logiciel, Pharo et la pratique de la recherche."
        if lang == "fr"
        else "Posts on AI, software engineering, Pharo, and research practice."
    )
    channel_link = urljoin(SITE_URL, "fr/blog/" if lang == "fr" else "blog/")
    latest_date = posts[0].published if posts else datetime.fromtimestamp((SOURCES / "site.md").stat().st_mtime).date()

    items = []
    for post in posts[:BLOG_FEED_LIMIT]:
        post_link = absolute_url_for_html(blog_post_html_path(post))
        items.append(
            "  <item>\n"
            f"    <title>{escape(post.title)}</title>\n"
            f"    <link>{escape(post_link)}</link>\n"
            f"    <guid isPermaLink=\"true\">{escape(post_link)}</guid>\n"
            f"    <pubDate>{rss_date(post.published)}</pubDate>\n"
            f"    <description>{escape(post.description)}</description>\n"
            "  </item>"
        )

    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "<channel>\n"
        f"  <title>{escape(channel_title)}</title>\n"
        f"  <link>{escape(channel_link)}</link>\n"
        f"  <description>{escape(channel_description)}</description>\n"
        f"  <language>{'fr' if lang == 'fr' else 'en'}</language>\n"
        f"  <lastBuildDate>{rss_date(latest_date)}</lastBuildDate>\n"
        f"{chr(10).join(items)}\n"
        "</channel>\n"
        "</rss>\n"
    )
    feed_path.write_text(rss, encoding="utf-8")


def build_blog(posts_by_lang: dict[str, list[BlogPost]]) -> None:
    clean_blog_output()
    build_blog_index(posts_by_lang["en"], "en")
    build_blog_index(posts_by_lang["fr"], "fr")

    fr_by_slug = {post.slug: post for post in posts_by_lang["fr"]}
    en_by_slug = {post.slug: post for post in posts_by_lang["en"]}
    for en_post in posts_by_lang["en"]:
        build_blog_post(en_post, fr_by_slug[en_post.slug])
    for fr_post in posts_by_lang["fr"]:
        build_blog_post(fr_post, en_by_slug[fr_post.slug])

    write_blog_feed(posts_by_lang["en"], "en")
    write_blog_feed(posts_by_lang["fr"], "fr")


# ======================================================
# SEO
# ======================================================

def sitemap_entry(loc: str, lastmod: str, changefreq: str, priority: str) -> str:
    return (
        "  <url>\n"
        f"    <loc>{escape(loc)}</loc>\n"
        f"    <lastmod>{lastmod}</lastmod>\n"
        f"    <changefreq>{changefreq}</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        "  </url>"
    )


def write_seo_files(posts_by_lang: dict[str, list[BlogPost]]) -> None:
    robots_txt = f"""User-agent: *
Allow: /

Sitemap: {urljoin(SITE_URL, "sitemap.xml")}
"""
    (DOCS / "robots.txt").write_text(robots_txt, encoding="utf-8")

    home_lastmod = datetime.fromtimestamp((DOCS / "index.html").stat().st_mtime).strftime("%Y-%m-%d")
    entries = [
        sitemap_entry(urljoin(SITE_URL, ""), home_lastmod, "monthly", "1.0"),
        sitemap_entry(urljoin(SITE_URL, "fr/"), home_lastmod, "monthly", "0.9"),
        sitemap_entry(urljoin(SITE_URL, "blog/"), home_lastmod, "weekly", "0.8"),
        sitemap_entry(urljoin(SITE_URL, "fr/blog/"), home_lastmod, "weekly", "0.8"),
    ]

    for post in posts_by_lang["en"] + posts_by_lang["fr"]:
        post_lastmod = (post.updated or post.published).isoformat()
        entries.append(sitemap_entry(absolute_url_for_html(blog_post_html_path(post)), post_lastmod, "monthly", "0.7"))

    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )
    (DOCS / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8")


def main() -> int:
    posts_by_lang = collect_blog_posts()
    for page in SITE_SOURCES:
        build_page(page, posts_by_lang)
    build_blog(posts_by_lang)
    write_seo_files(posts_by_lang)
    print("Site and blog built successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
