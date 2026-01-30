from pathlib import Path
import pypandoc

# Directory where this script lives: /build
SCRIPT_DIR = Path(__file__).resolve().parent

# Project root
ROOT = SCRIPT_DIR.parent

# Teaching directory
TEACHING_DIR = ROOT / "teaching"

# Input Markdown file
input_md = TEACHING_DIR / "teaching.md"

# Output PDF in the SAME directory
output_pdf = input_md.with_suffix(".pdf")

# Resources directory
resources = ROOT / "resources"

pypandoc.convert_file(
    str(input_md),
    "pdf",
    outputfile=str(output_pdf),
    extra_args=[
        "--pdf-engine=xelatex",
        "--citeproc",
        f"--bibliography={resources / 'publications.bib'}",
        f"--csl={resources / 'apa.csl'}",
        "-H", str(resources / "header.tex"),
        "-V", "geometry=margin=0.5in",
        "-V", "mainfont=Times New Roman",
    ]
)

print("Teaching PDF generated successfully:", output_pdf)
