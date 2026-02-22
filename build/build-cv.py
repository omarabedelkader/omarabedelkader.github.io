from pathlib import Path
import pypandoc
from last_updated import last_updated_label
from publications import inject_publications

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent  # ← project root

resources = ROOT / "resources"

output_dir = ROOT / "cv"
output_dir.mkdir(exist_ok=True)

cv_builds = [
    (ROOT / "sources" / "cv.md", output_dir / "cv-en.pdf"),
    (ROOT / "sources" / "cv-fr.md", output_dir / "cv-fr.pdf"),
]

for input_md, output_pdf in cv_builds:
    rendered_md = inject_publications(
        input_md.read_text(encoding="utf-8"),
        resources / "publications.bib",
    )

pypandoc.convert_text(
    rendered_md,
    "pdf",
    format="md",
    outputfile=str(output_pdf),
    extra_args=[
        "--pdf-engine=xelatex",
        "--citeproc",
        f"--bibliography={resources / 'publications.bib'}",
        f"--csl={resources / 'apa.csl'}",
        "-H", str(resources / "header.tex"),
        "-V", "geometry=margin=0.5in",
    ]
)

print("CV generated successfully:", output_pdf)
