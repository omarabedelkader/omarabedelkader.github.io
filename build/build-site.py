from pathlib import Path
from datetime import datetime
from last_updated import last_updated_label
import shutil
import pypandoc
from publications import render_grouped_publications_markdown

# ======================================================
# Paths
# ======================================================

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent  # project root

DOCS = ROOT / "docs"
RESOURCES = ROOT / "resources"
TEMPLATES = ROOT / "templates"

MD_FILE = ROOT / "sources" / "site.md"
HTML_FILE = DOCS / "index.html"

CSS_SRC = TEMPLATES / "style.css"
JS_SRC = TEMPLATES / "main.js"

CSS_DST = DOCS / "style.css"
JS_DST = DOCS / "main.js"

# NEW: favicon + header include snippet
FAVICON_SRC = TEMPLATES / "favicon.ico"
FAVICON_DST = DOCS / "favicon.ico"
HEADER_INCLUDE = TEMPLATES / "header.html"

DOCS.mkdir(exist_ok=True)

# ======================================================
# Copy static assets
# ======================================================

shutil.copyfile(CSS_SRC, CSS_DST)
shutil.copyfile(JS_SRC, JS_DST)

# NEW: copy favicon into docs/
shutil.copyfile(FAVICON_SRC, FAVICON_DST)

# ======================================================
# Pandoc conversion
# ======================================================

PUBLICATIONS_MD = render_grouped_publications_markdown(RESOURCES / "publications.bib")
source_markdown = MD_FILE.read_text(encoding="utf-8").replace("{{PUBLICATIONS_GROUPED}}", PUBLICATIONS_MD)

extra_args = [
    "--standalone",
    "--citeproc",
    f"--resource-path={RESOURCES}",
    "--bibliography=publications.bib",
    "--csl=apa.csl",
    "--metadata=link-citations:true",
    "--css=style.css",
    "--metadata=pagetitle=Omar AbedelKader",
    "--metadata=title=Omar AbedelKader",
    "--metadata=author=Omar AbedelKader",
    "--metadata=description=Official website of Omar AbedelKader, AI engineer and researcher. Projects, publications, CV, and contact details.",
    "--metadata=keywords=Omar AbedelKader,Omar Abdelkader,Omar Abedelkader,AI engineer,machine learning,publications,CV",

    # NEW: inject <link rel="icon" ...> into <head>
    f"--include-in-header={HEADER_INCLUDE}",
]

html = pypandoc.convert_text(
    source_markdown,
    to="html5",
    format="md",
    extra_args=extra_args,
)

# Keep quick-link emojis in a professional position near the page title.
# main.js builds the emoji bar dynamically inside the sticky area, so we
# relocate it after that render pass to align with the H1 header.
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

# ======================================================
# Inject layout
# ======================================================

html = html.replace(
    "<body>",
    "<body><main class='cv' id='cv'>"
).replace(
    "</body>",
    "</main>"
     f"<footer class='site-footer'>Last updated: {last_updated_label(MD_FILE)}</footer>"
    "<script src='main.js' defer></script>"
    f"{EMOJI_REPOSITION_SCRIPT}"
    "</body>"
)

HTML_FILE.write_text(html, encoding="utf-8")
print("Site built successfully.")
