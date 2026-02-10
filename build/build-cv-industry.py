from pathlib import Path
from last_updated import last_updated_label
import pypandoc

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent  # project root

input_md = ROOT / "sources" / "cv-industry.md"
resources = ROOT / "resources"

output_dir = ROOT / "cv"
output_dir.mkdir(exist_ok=True)

output_pdf = output_dir / "cv-industry.pdf"
header_tex = resources / "header.tex"

pypandoc.convert_file(
    str(input_md),
    to="pdf",
    format="markdown",
    outputfile=str(output_pdf),
    extra_args=[
        "--standalone",
        "--pdf-engine=xelatex",
        "--citeproc",
        "-M", f"date=Last updated: {last_updated_label(input_md)}",
        f"--bibliography={resources / 'publications.bib'}",
        f"--csl={resources / 'apa.csl'}",

        # Professional PDF tweaks
        "-V", "documentclass=article",
        "-V", "papersize=a4",
        "-V", "fontsize=10pt",
        "-V", "geometry=margin=0.65in",
        "-V", "mainfont=Times New Roman",
        "-V", "linestretch=1.05",

        # Two-column layout (LaTeX document class option)
        "-V", "classoption=twocolumn",

        # Your LaTeX header additions (packages, spacing, links, etc.)
        "-H", str(header_tex),
    ],
)

print("CV generated successfully:", output_pdf)
