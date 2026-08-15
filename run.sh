#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="python3"
REQUIREMENTS_FILE="$ROOT_DIR/requirements.txt"
TOTAL_TASKS=5

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

echo "Activating virtual environment..."
. "$VENV_DIR/bin/activate"

echo "Installing requirements..."
python -m pip install --upgrade pip
python -m pip install -r "$REQUIREMENTS_FILE"

run_task() {
  local number="$1"
  local title="$2"
  shift 2

  echo "==> Task ${number}/${TOTAL_TASKS}: ${title}"
  (cd "$ROOT_DIR" && "$@")
}

run_task 1 "Translate CV: sources/cv.md -> sources/cv-fr.md" \
  python build/translate-markdown.py \
    --input sources/cv.md \
    --output sources/cv-fr.md \
    --source en \
    --target fr

run_task 2 "Build CV PDFs: cv/cv-en.pdf and cv/cv-fr.pdf" \
  python build/build-cv.py

run_task 3 "Translate site: sources/site.md -> sources/site-fr.md" \
  python build/translate-markdown.py \
    --input sources/site.md \
    --output sources/site-fr.md \
    --source en \
    --target fr

run_task 4 "Generate website news: sources/news.md and sources/news-fr.md" \
  python build/generate-news.py

run_task 5 "Build website HTML: docs/index.html and docs/fr/index.html" \
  python build/build-site.py

echo "Pipeline completed successfully."
