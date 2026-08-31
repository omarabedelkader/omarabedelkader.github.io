from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from html import unescape
from pathlib import Path

try:
    import requests
    from deep_translator import GoogleTranslator
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency: deep-translator or requests. "
        "Install dependencies with `pip install -r requirements.txt`."
    ) from exc


FENCE_RE = re.compile(r"(```[^\n]*\n[\s\S]*?\n```|~~~[^\n]*\n[\s\S]*?\n~~~)")
HR_RE = re.compile(r"\s{0,3}([-*_])(?:\s*\1){2,}\s*$")
GOOGLE_TRANSLATE_JSON_URL = "https://translate.googleapis.com/translate_a/single"
MYMEMORY_TRANSLATE_URL = "https://api.mymemory.translated.net/get"
TRANSLATION_CACHE_FILE = Path(
    os.environ.get(
        "TRANSLATION_CACHE_FILE",
        str(Path(__file__).resolve().parents[1] / ".translation-cache.json"),
    )
)
MARKDOWN_PREFIX_RE = re.compile(
    r"^(\s{0,3}(?:#{1,6}\s+|[-*+]\s+(?:\[[ xX]\]\s+)?|>\s+|\d+\.\s+))(.*)$"
)
MARKDOWN_LINK_RE = re.compile(r"(!?)\[([^\]\n]*)\]\(([^)\n]*)\)")
MARKDOWN_EMPHASIS_RE = re.compile(
    r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1"
    r"|(?<!\*)\*(?![\s*])(.+?)(?<!\s)\*(?!\*)"
    r"|(?<![A-Za-z0-9_])_(?![\s_])(.+?)(?<!\s)_(?![A-Za-z0-9_])"
)
EMPHASIZED_NOT_RE = re.compile(r"(\*\*|__|\*|_)not\1", re.IGNORECASE)
TOKEN_RE = re.compile(r"XQMDTOKEN\d+QX")
PROTECTED_TERMS = (
    "AbedelKader",
    "AI4SE",
    "BENEVOL",
    "BiLSTM",
    "Café IA",
    "ChatPharo",
    "Complishon",
    "DeGatto",
    "EESMACF",
    "ESUG",
    "EVREF",
    "FrameNet",
    "GDR-SciLog",
    "GitHub",
    "Google Summer of Code",
    "Hugging Face",
    "ICSE",
    "ICSME",
    "IDMC",
    "INERIS",
    "Inria",
    "IWST",
    "LaBRI",
    "LatexDo",
    "LinearSVC",
    "MiniLM",
    "Model Context Protocol",
    "ORCID",
    "Pharo",
    "Pharo-AI",
    "Pharo-Copilot",
    "Pharo-HuggingFace",
    "Pharo-Infer",
    "Pharo-LLM",
    "Pharo-MCP",
    "PharoLLM",
    "Progress",
    "Qwen",
    "RAG",
    "RCLN",
    "SBERT",
    "SE4AI",
    "Synapse-NeuroTech-Lille",
    "ChatGPT",
    "Claude",
    "DeepSeek",
    "HuggingFace",
    "LM Studio",
    "Ollama",
    "Tonel",
    "vLLM",
    "feenk",
)


class Protector:
    def __init__(self) -> None:
        self.values: list[str] = []

    def add(self, value: str) -> str:
        token = f"XQMDTOKEN{len(self.values)}QX"
        self.values.append(value)
        return token

    def protect_re(self, text: str, pattern: str, flags: int = 0) -> str:
        return re.sub(pattern, lambda match: self.add(match.group(0)), text, flags=flags)

    def restore(self, text: str) -> str:
        for index, value in enumerate(self.values):
            text = text.replace(f"XQMDTOKEN{index}QX", value)
        return text


class MarkdownTranslator:
    def __init__(self, source: str, target: str) -> None:
        self.target = target
        self.translator = GoogleTranslator(source=source, target=target)
        self.translation_cache = self._load_translation_cache()

    def translate_markdown(self, markdown: str) -> str:
        frontmatter, body = self._split_frontmatter(markdown)
        translated_parts: list[str] = []

        for part in FENCE_RE.split(body):
            if not part:
                continue
            if part.startswith(("```", "~~~")):
                translated_parts.append(self._translate_fence(part))
            else:
                translated_parts.append(self._translate_markdown_lines(part))

        return frontmatter + "".join(translated_parts)

    def _split_frontmatter(self, markdown: str) -> tuple[str, str]:
        if not markdown.startswith("---\n"):
            return "", markdown

        end_match = re.search(r"\n---\s*\n", markdown[4:])
        if not end_match:
            return "", markdown

        end = 4 + end_match.end()
        return markdown[:end], markdown[end:]

    def _translate_fence(self, fence: str) -> str:
        lines = fence.splitlines(keepends=True)
        if not lines:
            return fence

        info = lines[0].strip()
        if "{=latex}" not in info:
            return fence

        body = "".join(lines[1:-1])
        if "\\cvheader" not in body:
            return fence

        return lines[0] + self._translate_cvheader(body) + lines[-1]

    def _translate_cvheader(self, latex: str) -> str:
        parsed = self._parse_command_groups(latex, "\\cvheader", 3)
        if parsed is None:
            return latex

        prefix, groups, suffix = parsed
        name, left, right = groups
        translated_left = self._translate_latex_group(left)
        translated_right = self._translate_latex_group(right)
        return f"{prefix}\\cvheader{{{name}}}{{{translated_left}}}{{{translated_right}}}{suffix}"

    def _parse_command_groups(
        self,
        text: str,
        command: str,
        count: int,
    ) -> tuple[str, list[str], str] | None:
        start = text.find(command)
        if start == -1:
            return None

        pos = start + len(command)
        groups: list[str] = []

        for _ in range(count):
            while pos < len(text) and text[pos].isspace():
                pos += 1
            if pos >= len(text) or text[pos] != "{":
                return None

            end = self._find_balanced_brace(text, pos)
            if end is None:
                return None

            groups.append(text[pos + 1 : end])
            pos = end + 1

        return text[:start], groups, text[pos:]

    def _find_balanced_brace(self, text: str, start: int) -> int | None:
        depth = 0
        escaped = False

        for pos in range(start, len(text)):
            char = text[pos]
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return pos

        return None

    def _translate_latex_group(self, text: str) -> str:
        parts = re.split(r"(\\\\)", text)
        translated: list[str] = []

        for part in parts:
            if part == "\\\\":
                translated.append(part)
            else:
                translated.append(self._translate_with_outer_space(part))

        return "".join(translated)

    def _translate_markdown_lines(self, text: str) -> str:
        translated: list[str] = []

        for line in text.splitlines(keepends=True):
            newline = "\n" if line.endswith("\n") else ""
            content = line[:-1] if newline else line
            translated.append(self._translate_markdown_line(content) + newline)

        return "".join(translated)

    def _translate_markdown_line(self, line: str) -> str:
        if not line.strip() or HR_RE.fullmatch(line):
            return line

        trailing_spaces = len(line) - len(line.rstrip(" "))
        trailing = " " * trailing_spaces
        core_line = line[:-trailing_spaces] if trailing_spaces else line

        match = MARKDOWN_PREFIX_RE.match(core_line)
        if match:
            prefix, content = match.groups()
            marker = ""
            if prefix.lstrip().startswith(("-", "*", "+")) and content.startswith("*") and not content.startswith(("**", "* ")):
                marker = "*"
                content = content[1:]
            return prefix + marker + self._translate_with_outer_space(content) + trailing

        return self._translate_with_outer_space(core_line) + trailing

    def _translate_with_outer_space(self, text: str) -> str:
        leading = text[: len(text) - len(text.lstrip())]
        trailing = text[len(text.rstrip()) :]
        core = text.strip()
        if not core:
            return text
        return leading + self._translate_text(core) + trailing

    def _translate_text(self, text: str) -> str:
        emphasized_not = self._translate_emphasized_not(text)
        if emphasized_not is not None:
            return emphasized_not

        emphasized = self._translate_markdown_emphasis(text)
        if emphasized is not None:
            return emphasized

        return self._translate_plain_text(text)

    def _translate_emphasized_not(self, text: str) -> str | None:
        match = EMPHASIZED_NOT_RE.search(text)
        if not match:
            return None

        delimiter = match.group(1)
        plain_text = f"{text[:match.start()]}not{text[match.end():]}"
        translated = self._translate_plain_text(plain_text)

        if self.target == "fr":
            return re.sub(r"\bpas\b", f"{delimiter}pas{delimiter}", translated, count=1)
        return translated

    def _translate_markdown_emphasis(self, text: str) -> str | None:
        translated: list[str] = []
        position = 0
        found = False

        for match in MARKDOWN_EMPHASIS_RE.finditer(text):
            found = True
            translated.append(self._translate_with_outer_space(text[position : match.start()]))

            delimiter = match.group(1)
            inner = match.group(2)
            if delimiter is None:
                delimiter = "*" if match.group(3) is not None else "_"
                inner = match.group(3) if match.group(3) is not None else match.group(4)

            translated.append(f"{delimiter}{self._translate_with_outer_space(inner or '')}{delimiter}")
            position = match.end()

        if not found:
            return None

        translated.append(self._translate_with_outer_space(text[position:]))
        return "".join(translated)

    def _translate_plain_text(self, text: str) -> str:
        if not re.search(r"[A-Za-z]", text):
            return text

        protector = Protector()
        protected = text
        protected = protector.protect_re(protected, r"\{\{[^{}]+\}\}")
        protected = protector.protect_re(protected, r"\\cite\{[^{}]+\}")
        protected = self._protect_markdown_links(protected, protector)
        protected = protector.protect_re(protected, r"`[^`\n]+`")
        protected = protector.protect_re(protected, r"\\href\{[^{}]*\}\{[^{}]*\}")
        protected = protector.protect_re(protected, r"\\icon\{[^{}]*\}")
        protected = protector.protect_re(protected, r"\\fa[A-Za-z]+")
        protected = protector.protect_re(protected, r"\\today")
        protected = protector.protect_re(protected, r"https?://[^\s<>)\]]+")
        protected = protector.protect_re(protected, r"mailto:[^\s<>)\]]+")
        protected = protector.protect_re(
            protected,
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        )
        protected = self._protect_terms(protected, protector)

        if not self._has_translatable_text(protected):
            return protector.restore(protected)

        translated = self._translate_protected_text(protected)
        return self._postprocess_translation(protector.restore(translated))

    def _has_translatable_text(self, text: str) -> bool:
        return bool(re.search(r"[A-Za-zÀ-ÿ]", TOKEN_RE.sub("", text)))

    def _translate_protected_text(self, text: str) -> str:
        if not TOKEN_RE.search(text):
            return self._translate_chunk(text)

        try:
            return self._translate_chunk(text, attempts=1)
        except RuntimeError:
            translated = self._translate_around_tokens(text)
            self._remember_translation(text, translated)
            return translated

    def _translate_around_tokens(self, text: str) -> str:
        translated: list[str] = []
        position = 0

        for match in TOKEN_RE.finditer(text):
            translated.append(self._translate_fragment(text[position : match.start()]))
            translated.append(match.group(0))
            position = match.end()

        translated.append(self._translate_fragment(text[position:]))
        return "".join(translated)

    def _translate_fragment(self, text: str) -> str:
        if not self._has_translatable_text(text):
            return text
        return self._translate_chunk(text)

    def _protect_markdown_links(self, text: str, protector: Protector) -> str:
        def replace(match: re.Match[str]) -> str:
            bang, label, target = match.groups()
            if bang or self._preserve_link_label(label):
                translated_label = label
            else:
                translated_label = self._translate_text(label)
            translated_target = "#actuel" if self.target == "fr" and target == "#current" else target
            return protector.add(f"{bang}[{translated_label}]({translated_target})")

        return MARKDOWN_LINK_RE.sub(replace, text)

    def _preserve_link_label(self, label: str) -> bool:
        stripped = re.sub(r"[*_`]", "", label).strip()
        if not stripped or "\\icon" in stripped:
            return True
        if not re.search(r"[A-Za-zÀ-ÿ]", stripped):
            return True

        words = stripped.split()
        properish = all(
            re.fullmatch(r"[A-ZÀ-Ý0-9][A-Za-zÀ-ÿ0-9'._:/+-]*", word)
            for word in words
        )
        return properish

    def _protect_terms(self, text: str, protector: Protector) -> str:
        protected = text
        for term in sorted(PROTECTED_TERMS, key=len, reverse=True):
            pattern = rf"(?<![A-Za-z0-9_-]){re.escape(term)}(?![A-Za-z0-9_-])"
            protected = re.sub(pattern, lambda match: protector.add(match.group(0)), protected)
        return protected

    def _postprocess_translation(self, text: str) -> str:
        if self.target != "fr":
            return text

        exact_replacements = {
            "Sur moi": "À propos de moi",
            "Blogue": "Blog",
            "Logiciel": "Logiciels",
            "News": "Actualités",
            "Discussions publiques": "Présentations publiques",
            "Stage Bachelor": "Stage de licence",
        }
        if text in exact_replacements:
            return exact_replacements[text]

        replacements = {
            "doctorat. en Informatique": "doctorat en informatique",
            "doctorat. en informatique": "doctorat en informatique",
            "Grands modèles linguistiques": "Grands modèles de langage",
            "Intelligence de code": "Intelligence du code",
            "Maintenance Logiciel": "Maintenance logicielle",
            "Mise à jour\xa0:": "Dernière mise à jour :",
            "Mise à jour :": "Dernière mise à jour :",
            "Shadow Reviewer chez": "Réviseur fantôme à",
            "Réviseur fantôme chez": "Réviseur fantôme à",
        }
        for source, target in replacements.items():
            text = text.replace(source, target)
        return text

    def _translate_chunk(self, text: str, attempts: int = 3) -> str:
        cached = self._cached_translation(text)
        if cached is not None:
            return cached

        last_error: Exception | None = None
        for attempt in range(attempts):
            for translate in (
                self._translate_with_deep_translator,
                self._translate_with_google_json,
                self._translate_with_mymemory,
            ):
                try:
                    translated = translate(text)
                    self._remember_translation(text, translated)
                    return translated
                except Exception as exc:
                    last_error = exc

            if attempt < attempts - 1:
                time.sleep(1 + attempt)

        raise RuntimeError(f"Translation failed for: {text[:120]!r}") from last_error

    def _translate_with_deep_translator(self, text: str) -> str:
        translated = self.translator.translate(text)
        if translated is None:
            raise RuntimeError("translator returned no text")
        return translated

    def _translate_with_google_json(self, text: str) -> str:
        response = requests.get(
            GOOGLE_TRANSLATE_JSON_URL,
            params={
                "client": "gtx",
                "sl": self.translator.source,
                "tl": self.translator.target,
                "dt": "t",
                "q": text,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()

        try:
            translated = "".join(part[0] for part in payload[0] if part and part[0])
        except (IndexError, TypeError) as exc:
            raise RuntimeError("Google JSON translator returned an unexpected response") from exc

        if not translated:
            raise RuntimeError("Google JSON translator returned no text")
        return translated

    def _translate_with_mymemory(self, text: str) -> str:
        response = requests.get(
            MYMEMORY_TRANSLATE_URL,
            params={
                "q": text,
                "langpair": f"{self.translator.source}|{self.translator.target}",
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()

        try:
            translated = payload["responseData"]["translatedText"]
        except (KeyError, TypeError) as exc:
            raise RuntimeError("MyMemory translator returned an unexpected response") from exc

        if not translated:
            raise RuntimeError("MyMemory translator returned no text")
        return unescape(str(translated))

    def _cache_key(self, text: str) -> str:
        key = "\0".join((self.translator.source, self.translator.target, text))
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _cached_translation(self, text: str) -> str | None:
        return self.translation_cache.get(self._cache_key(text))

    def _remember_translation(self, text: str, translated: str) -> None:
        self.translation_cache[self._cache_key(text)] = translated
        self._save_translation_cache()

    def _load_translation_cache(self) -> dict[str, str]:
        if not TRANSLATION_CACHE_FILE.exists():
            return {}

        try:
            data = json.loads(TRANSLATION_CACHE_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

        if not isinstance(data, dict):
            return {}
        return {str(key): str(value) for key, value in data.items()}

    def _save_translation_cache(self) -> None:
        try:
            TRANSLATION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            temp_path = TRANSLATION_CACHE_FILE.with_name(f"{TRANSLATION_CACHE_FILE.name}.tmp")
            temp_path.write_text(
                json.dumps(self.translation_cache, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            temp_path.replace(TRANSLATION_CACHE_FILE)
        except OSError:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Translate Markdown while preserving build syntax.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source", default="en")
    parser.add_argument("--target", default="fr")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    markdown = args.input.read_text(encoding="utf-8")
    translator = MarkdownTranslator(source=args.source, target=args.target)
    translated = translator.translate_markdown(markdown)
    args.output.write_text(translated, encoding="utf-8")
    if not args.quiet:
        print(f"Translated {args.input} -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
