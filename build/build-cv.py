from pathlib import Path
import pypandoc

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent  # ← project root

input_md = ROOT / "index.md"
resources = ROOT / "resources"

output_dir = ROOT / "cv"
output_dir.mkdir(exist_ok=True)

output_pdf = output_dir / "cv-en.pdf"

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

print("CV generated successfully:", output_pdf)
