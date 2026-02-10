from pathlib import Path
from datetime import datetime
import shutil
import pypandoc

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

def get_last_updated() -> str:
    """Return the current month/year label used in the site footer."""
    return datetime.now().strftime("%B %Y")

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

extra_args = [
    "--standalone",
    "--citeproc",
    f"--resource-path={RESOURCES}",
    "--bibliography=publications.bib",
    "--csl=apa.csl",
    "--metadata=link-citations:true",
    "--css=style.css",
    "--metadata=pagetitle=Omar AbedelKader",

    # NEW: inject <link rel="icon" ...> into <head>
    f"--include-in-header={HEADER_INCLUDE}",
]

html = pypandoc.convert_text(
    MD_FILE.read_text(encoding="utf-8"),
    to="html5",
    format="md",
    extra_args=extra_args,
)

# ======================================================
# Inject layout
# ======================================================

html = html.replace(
    "<body>",
    "<body><main class='cv' id='cv'>"
).replace(
    "</body>",
    "</main>"
    f"<footer class='site-footer'>Last updated: {get_last_updated()}</footer>"
    "<script src='main.js' defer></script>"
    "</body>"
)

HTML_FILE.write_text(html, encoding="utf-8")
print("Site built successfully.")
