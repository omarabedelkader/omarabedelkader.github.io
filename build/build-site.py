from pathlib import Path
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

DOCS.mkdir(exist_ok=True)

# ======================================================
# Copy static assets
# ======================================================

shutil.copyfile(CSS_SRC, CSS_DST)
shutil.copyfile(JS_SRC, JS_DST)

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
    "<footer class='site-footer'>Last updated: January 2026</footer>"
    "<script src='main.js' defer></script>"
    "</body>"
)

HTML_FILE.write_text(html, encoding="utf-8")
print("Site built successfully.")
