#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="python3"
REQUIREMENTS_FILE="$ROOT_DIR/requirements.txt"
TOTAL_TASKS=7
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
  else
    local status=$?
    echo "Command failed: $*" >&2
    sed -n '1,200p' "$log_file" >&2
    rm -f "$log_file"
    return "$status"
  fi
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

# Task 1 prints its report (what was added, what needs attention), so it is not silenced.
# SKIP_SYNC=1 skips it: the CI workflow runs the same check itself before calling this script.
if [ "${SKIP_SYNC:-0}" = "1" ]; then
  echo "==> Task 1/${TOTAL_TASKS}: Check Google Scholar and conf.researchr.org (skipped)"
else
  echo "==> Task 1/${TOTAL_TASKS}: Check Google Scholar and conf.researchr.org for new items"
  (cd "$ROOT_DIR" && python build/sync-updates.py)
fi

run_task 2 "Translate CV: sources/cv.md -> sources/cv-fr.md" \
  python build/translate-markdown.py \
    --input sources/cv.md \
    --output sources/cv-fr.md \
    --source en \
    --target fr \
    --quiet

run_task 3 "Build CV PDFs: cv/ (full) and short-cv/ (short), English and French" \
  python build/build-cv.py

run_task 4 "Translate site: sources/site.md -> sources/site-fr.md" \
  python build/translate-markdown.py \
    --input sources/site.md \
    --output sources/site-fr.md \
    --source en \
    --target fr \
    --quiet

run_task 5 "Translate blog posts: sources/blog/*.md -> sources/blog-fr/*.md" \
  python build/translate-blog.py \
    --quiet

# Like task 1, this one reports what it added (or that there was nothing to add).
echo "==> Task 6/${TOTAL_TASKS}: Add new items to website news: sources/news.md and sources/news-fr.md"
(cd "$ROOT_DIR" && python build/generate-news.py)

run_task 7 "Build website HTML, section pages, short CV and blog pages under docs/" \
  python build/build-site.py

echo "Pipeline completed successfully."

# Content files only: the PDFs and HTML are rewritten on every run even when nothing changed.
changed="$(cd "$ROOT_DIR" && git status --short -- sources resources 2>/dev/null || true)"
if [ -z "$changed" ]; then
  echo "Nothing to change: the content is identical to the last commit."
else
  echo "Content changed since the last commit (review, then commit and push):"
  echo "$changed"
fi
