from __future__ import annotations

import argparse
import hashlib
import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

import yaml


BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent
DEFAULT_SOURCE_DIR = ROOT / "sources" / "blog"
DEFAULT_OUTPUT_DIR = ROOT / "sources" / "blog-fr"
GENERATED_BY = "translate-blog.py"
TRANSLATION_HASH_FIELD = "translation_source_sha256"

FRONTMATTER_RE = re.compile(r"^---\s*\n(?P<yaml>.*?)\n---\s*\n?", re.DOTALL)
TRANSLATED_FRONTMATTER_FIELDS = ("title", "description", "summary")


def load_markdown_translator():
    module_path = BUILD_DIR / "translate-markdown.py"
    spec = importlib.util.spec_from_file_location("translate_markdown", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MarkdownTranslator


def split_frontmatter(markdown: str, source_path: Path | None = None) -> tuple[dict[str, Any], str]:
    if markdown.lstrip().startswith("---") and not markdown.startswith("---"):
        prefix = f"{source_path}: " if source_path else ""
        raise ValueError(f"{prefix}blog front matter must start at the first column of the file")

    match = FRONTMATTER_RE.match(markdown)
    if not match:
        return {}, markdown

    metadata = yaml.safe_load(match.group("yaml")) or {}
    if not isinstance(metadata, dict):
        raise ValueError("front matter must be a YAML mapping")
    return metadata, markdown[match.end() :]


def remove_generated_translation(path: Path) -> None:
    if not path.exists():
        return

    try:
        metadata, _body = split_frontmatter(path.read_text(encoding="utf-8"), path)
    except Exception:
        return

    if metadata.get("generated_by") == GENERATED_BY:
        path.unlink()


def dump_markdown(metadata: dict[str, Any], body: str) -> str:
    frontmatter = yaml.safe_dump(
        metadata,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()
    return f"---\n{frontmatter}\n---\n\n{body.strip()}\n"


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def source_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def should_skip(output_path: Path, digest: str, force: bool) -> bool:
    if force or not output_path.exists():
        return False

    try:
        metadata, _body = split_frontmatter(output_path.read_text(encoding="utf-8"), output_path)
    except Exception:
        return False

    return metadata.get(TRANSLATION_HASH_FIELD) == digest


def translate_metadata(metadata: dict[str, Any], translator) -> dict[str, Any]:
    translated = dict(metadata)
    for field in TRANSLATED_FRONTMATTER_FIELDS:
        value = translated.get(field)
        if isinstance(value, str) and value.strip():
            translated[field] = translator._translate_text(value)
    return translated


def translate_post(path: Path, output_dir: Path, translator, force: bool) -> str:
    output_path = output_dir / path.name
    digest = source_hash(path)

    if should_skip(output_path, digest, force):
        return f"Blog translation unchanged: {path} -> {output_path}"

    metadata, body = split_frontmatter(path.read_text(encoding="utf-8"), path)
    if boolish(metadata.get("draft")):
        remove_generated_translation(output_path)
        return f"Blog draft skipped: {path}"

    translated_metadata = translate_metadata(metadata, translator)
    translated_metadata["language"] = "fr"
    translated_metadata["translation_source"] = path.relative_to(ROOT).as_posix()
    translated_metadata[TRANSLATION_HASH_FIELD] = digest
    translated_metadata["generated_by"] = GENERATED_BY

    translated_body = translator.translate_markdown(body)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(dump_markdown(translated_metadata, translated_body), encoding="utf-8")
    return f"Translated blog post: {path} -> {output_path}"


def iter_source_posts(source_dir: Path) -> list[Path]:
    if not source_dir.exists():
        return []
    return sorted(
        path
        for path in source_dir.glob("*.md")
        if not path.name.startswith("_")
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Translate English blog Markdown posts to French.")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--source", default="en")
    parser.add_argument("--target", default="fr")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    MarkdownTranslator = load_markdown_translator()
    translator = MarkdownTranslator(source=args.source, target=args.target)

    posts = iter_source_posts(args.source_dir)
    if not posts:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if not args.quiet:
            print(f"No blog posts to translate in {args.source_dir}")
        return 0

    for post in posts:
        message = translate_post(post, args.output_dir, translator, args.force)
        if not args.quiet:
            print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
