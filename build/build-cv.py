from pathlib import Path
import pypandoc
from last_updated import last_updated_label
from publications import render_grouped_publications_markdown

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent  # ← project root

input_md = ROOT / "sources" / "cv.md"
resources = ROOT / "resources"

output_dir = ROOT / "cv"
output_dir.mkdir(exist_ok=True)

output_pdf = output_dir / "cv-en.pdf"

source_md = input_md.read_text(encoding="utf-8")
publications_md = render_grouped_publications_markdown(resources / "publications.bib")
processed_md = source_md.replace("{{PUBLICATIONS_GROUPED}}", publications_md)
temp_input_md = output_dir / ".cv-rendered.md"
temp_input_md.write_text(processed_md, encoding="utf-8")

pypandoc.convert_file(
    str(temp_input_md),
    "pdf",
    outputfile=str(output_pdf),
    extra_args=[
        "--pdf-engine=xelatex",
        "--citeproc",
        "-M", f"date=Last updated: {last_updated_label(input_md)}",
        f"--bibliography={resources / 'publications.bib'}",
        f"--csl={resources / 'apa.csl'}",
        "-H", str(resources / "header.tex"),
        "-V", "geometry=margin=0.5in",
    ]
)

temp_input_md.unlink(missing_ok=True)
print("CV generated successfully:", output_pdf)
