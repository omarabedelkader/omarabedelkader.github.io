from pathlib import Path
from datetime import datetime
from last_updated import last_updated_label
from urllib.parse import urljoin
import shutil
import pypandoc
from publications import inject_publications


# ======================================================
# Paths
# ======================================================

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent  # project root

DOCS = ROOT / "docs"
RESOURCES = ROOT / "resources"
TEMPLATES = ROOT / "templates"

SITE_SOURCES = [
    {
        "md": ROOT / "sources" / "site.md",
        "html": DOCS / "index.html",
        "lang": "en",
        "pagetitle": "Omar AbedelKader",
        "description": "Official website of Omar AbedelKader, AI engineer and researcher. Projects, publications, CV, and contact details.",
    },
    {
        "md": ROOT / "sources" / "site-fr.md",
        "html": DOCS / "fr" / "index.html",
        "lang": "fr",
        "pagetitle": "Omar AbedelKader — Version française",
        "description": "Site officiel d'Omar AbedelKader, ingénieur et chercheur en IA. Projets, publications, CV et coordonnées.",
    },
]


CSS_SRC = TEMPLATES / "style.css"
JS_SRC = TEMPLATES / "main.js"

CSS_DST = DOCS / "style.css"
JS_DST = DOCS / "main.js"

# NEW: favicon + header include snippet
FAVICON_SRC = TEMPLATES / "favicon.ico"
FAVICON_DST = DOCS / "favicon.ico"
HEADER_INCLUDE = RESOURCES / "seo_head.html"

DOCS.mkdir(exist_ok=True)

# ======================================================
# Copy static assets
# ======================================================

shutil.copyfile(CSS_SRC, CSS_DST)
shutil.copyfile(JS_SRC, JS_DST)

# NEW: copy favicon into docs/
shutil.copyfile(FAVICON_SRC, FAVICON_DST)

# Copy generated CV PDFs into docs/cv/ for GitHub Pages publishing.
CV_SRC_DIR = ROOT / "cv"
CV_DST_DIR = DOCS / "cv"
CV_DST_DIR.mkdir(parents=True, exist_ok=True)

for cv_pdf in CV_SRC_DIR.glob("*.pdf"):
    shutil.copyfile(cv_pdf, CV_DST_DIR / cv_pdf.name)


# ======================================================
# Pandoc conversion
# ======================================================

def build_page(config):
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
        "--metadata=keywords=Omar AbedelKader,Omar Abdelkader,Omar Abedelkader,AI engineer,machine learning,publications,CV",
        f"--include-in-header={HEADER_INCLUDE}",
    ]

    rendered_md = inject_publications(
        config["md"].read_text(encoding="utf-8"),
        RESOURCES / "publications.bib",
 )

    html = pypandoc.convert_text(
        rendered_md,
        to="html5",
        format="md",
        extra_args=extra_args,
    )


    script_path = "../main.js" if config["lang"] == "fr" else "main.js"
    footer_label = "Dernière mise à jour" if config["lang"] == "fr" else "Last updated"

    html = html.replace(
        "<body>",
        "<body><main class='cv' id='cv'>"
    ).replace(
        "</body>",
        "</main>"
        f"<footer class='site-footer'>{footer_label}: {last_updated_label(config['md'])}</footer>"
        f"<script src='{script_path}' defer></script>"
        f"{EMOJI_REPOSITION_SCRIPT}"
        "</body>"
    )

    config["html"].write_text(html, encoding="utf-8")

EMOJI_REPOSITION_SCRIPT = """
<script>
document.addEventListener('DOMContentLoaded', () => {
  const moveTopbarNearTitle = () => {
    const header = document.querySelector('.site-header');
    const title = header?.querySelector('h1');
    const topbar = document.querySelector('.sticky-ui .topbar');
    if (!header || !title || !topbar) {
      return false;
    }

    let row = header.querySelector('.header-row');
    if (!row) {
      row = document.createElement('div');
      row.className = 'header-row';
      header.insertBefore(row, header.firstChild);
    }

    row.append(title, topbar);
    return true;
  };

  if (moveTopbarNearTitle()) {
    return;
  }

  const observer = new MutationObserver(() => {
    if (moveTopbarNearTitle()) {
      observer.disconnect();
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });
  setTimeout(() => observer.disconnect(), 3000);
});
</script>
"""

for page in SITE_SOURCES:
    build_page(page)

print("Site built successfully.")


# ======================================================
# SEO
# ======================================================

SITE_URL = "https://omarabedelkader.github.io/"

# robots.txt
robots_txt = f"""User-agent: *
Allow: /

Sitemap: {urljoin(SITE_URL, "sitemap.xml")}
"""
(DOCS / "robots.txt").write_text(robots_txt, encoding="utf-8")

# sitemap.xml
lastmod = datetime.fromtimestamp((DOCS / "index.html").stat().st_mtime).strftime("%Y-%m-%d")
sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{SITE_URL.rstrip('/')}/</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>1.0</priority>
  </url>
    <url>
    <loc>{SITE_URL.rstrip('/')}/fr/</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>
</urlset>
"""
(DOCS / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8")