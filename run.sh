#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="python3"
REQUIREMENTS_FILE="$ROOT_DIR/requirements.txt"
TOTAL_TASKS=6
VERBOSE="${VERBOSE:-0}"

run_command() {
  if [ "$VERBOSE" = "1" ]; then
    "$@"
    return
  fi

  local log_file
  log_file="$(mktemp "${TMPDIR:-/tmp}/site-build.XXXXXX")"

  if "$@" >"$log_file" 2>&1; then
    rm -f "$log_file"
    return 0
  fi

  local status=$?
  echo "Command failed: $*" >&2
  sed -n '1,200p' "$log_file" >&2
  rm -f "$log_file"
  return "$status"
}

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment..."
  run_command "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

. "$VENV_DIR/bin/activate"

echo "Preparing Python dependencies..."
run_command python -m pip --disable-pip-version-check install -q --upgrade pip
run_command python -m pip --disable-pip-version-check install -q -r "$REQUIREMENTS_FILE"

run_task() {
  local number="$1"
  local title="$2"
  shift 2

  echo "==> Task ${number}/${TOTAL_TASKS}: ${title}"
  (cd "$ROOT_DIR" && run_command "$@")
}

run_task 1 "Translate CV: sources/cv.md -> sources/cv-fr.md" \
  python build/translate-markdown.py \
    --input sources/cv.md \
    --output sources/cv-fr.md \
    --source en \
    --target fr \
    --quiet

run_task 2 "Build CV PDFs: cv/cv-en.pdf and cv/cv-fr.pdf" \
  python build/build-cv.py

run_task 3 "Translate site: sources/site.md -> sources/site-fr.md" \
  python build/translate-markdown.py \
    --input sources/site.md \
    --output sources/site-fr.md \
    --source en \
    --target fr \
    --quiet

run_task 4 "Translate blog posts: sources/blog/*.md -> sources/blog-fr/*.md" \
  python build/translate-blog.py \
    --quiet

run_task 5 "Generate website news: sources/news.md and sources/news-fr.md" \
  python build/generate-news.py

run_task 6 "Build website HTML and blog pages under docs/" \
  python build/build-site.py

echo "Pipeline completed successfully."
