#!/usr/bin/env python3

"""Generate a simple multilingual word cloud from markdown posts."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

import frontmatter  # type: ignore
import MeCab  # type: ignore
from PIL import Image
from wordcloud import WordCloud  # type: ignore


JA_ALLOWED_POS = {"名詞", "形容詞", "動詞"}

EN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9']+")
JA_PATTERN = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]+")
URL_PATTERN = re.compile(r"(https?://|www\.)\S+")
CODE_BLOCK_PATTERN = re.compile(r"```.*?```", flags=re.DOTALL)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
MARKDOWN_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\([^)]+\)")
FOOTNOTE_REF_PATTERN = re.compile(r"\[\^[^\]]*\]")
FOOTNOTE_DEF_PATTERN = re.compile(r"\[\^[^\]]+\]:.*$", flags=re.MULTILINE)
SHORTCODE_PATTERN = re.compile(r"\{\{.*?\}\}", flags=re.DOTALL)
SYMBOL_PATTERN = re.compile(r"[*_`>#~\-]+")
BRACKETS_PATTERN = re.compile(r"[\\\[\]\(\){}<>]")


def _load_stopwords(path: Path) -> set[str]:
    """Load stopwords from a file, one word per line."""
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8") as fh:
        return {line.strip() for line in fh if line.strip()}


def _load_normalize_config(path: Path) -> dict[str, dict[str, str]]:
    """Load case normalization rules from a JSON file."""
    if not path.exists():
        return {"ja": {}, "en": {}}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _strip_markdown(text: str) -> str:
    text = CODE_BLOCK_PATTERN.sub(" ", text)
    text = URL_PATTERN.sub(" ", text)
    text = HTML_TAG_PATTERN.sub(" ", text)
    text = MARKDOWN_LINK_PATTERN.sub(" ", text)
    text = FOOTNOTE_DEF_PATTERN.sub(" ", text)
    text = FOOTNOTE_REF_PATTERN.sub(" ", text)
    text = SHORTCODE_PATTERN.sub(" ", text)
    text = SYMBOL_PATTERN.sub(" ", text)
    text = BRACKETS_PATTERN.sub(" ", text)
    text = re.sub(r"!\s+", " ", text)
    text = re.sub(r"\(\s*\)", " ", text)
    text = re.sub(r"\{\s*\}", " ", text)
    text = re.sub(r"(?<![A-Za-z])\d+(?![A-Za-z])", " ", text)
    text = re.sub(r"\\+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _load_markdown_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as fh:
        post = frontmatter.load(fh)
    content = post.content
    if post.get("title"):
        content = f"{post['title']}\n{content}"
    content = _strip_markdown(content)
    return content


def _normalize_case(text: str, replacements: dict[str, str]) -> str:
    return replacements.get(text, text)


def _tokenize_japanese(
    text: str, stopwords_ja: set[str], normalize_ja: dict[str, str]
) -> Iterable[str]:
    tagger = MeCab.Tagger("")
    tagger.parse("")  # required workaround for some MeCab builds
    node = tagger.parseToNode(text)
    while node:
        surface = node.surface
        if surface:
            features = node.feature.split(",")
            pos = features[0] if features else ""
            lemma = features[6] if len(features) > 6 else ""
            base = lemma if lemma not in ("*", "") else surface
            if re.fullmatch(r"[ァ-ヴー]+", base) and re.search(r"[一-龯]", surface):
                base = surface
            base = _normalize_case(base, normalize_ja)
            if pos in JA_ALLOWED_POS and base not in stopwords_ja and len(base) > 1:
                yield base
        node = node.next
    return


def _normalize_en_case(token: str, overrides: dict[str, str]) -> str:
    lowered = token.lower()
    if lowered in overrides:
        return overrides[lowered]
    if token.isupper():
        return token
    return lowered


def _tokenize_english(
    text: str, stopwords_en: set[str], normalize_en: dict[str, str]
) -> Iterable[str]:
    for match in EN_PATTERN.findall(text):
        token = _normalize_en_case(match, normalize_en)
        # Check stopwords with case-insensitive comparison
        if token.lower() in stopwords_en:
            continue
        if len(token) <= 2 and not any(char.isdigit() for char in token):
            continue
        yield token


def tokenize(
    text: str,
    stopwords_ja: set[str],
    stopwords_en: set[str],
    normalize_ja: dict[str, str],
    normalize_en: dict[str, str],
) -> list[str]:
    tokens: list[str] = []
    tokens.extend(_tokenize_japanese(text, stopwords_ja, normalize_ja))
    tokens.extend(_tokenize_english(text, stopwords_en, normalize_en))
    return tokens


def collect_tokens(
    target: Path,
    stopwords_ja: set[str],
    stopwords_en: set[str],
    normalize_ja: dict[str, str],
    normalize_en: dict[str, str],
) -> Counter[str]:
    counter: Counter[str] = Counter()
    paths = sorted(p for p in target.rglob("*.md") if p.is_file())
    for path in paths:
        text = _load_markdown_text(path)
        for token in tokenize(
            text, stopwords_ja, stopwords_en, normalize_ja, normalize_en
        ):
            counter[token] += 1
    return counter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a multilingual word cloud from markdown posts."
    )
    parser.add_argument(
        "target",
        type=Path,
        help="Directory that contains markdown files (e.g. content/posts/2025).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=80,
        help="Number of tokens to include in the word cloud.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=900,
        help="Width of the generated image.",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=600,
        help="Height of the generated image.",
    )
    parser.add_argument(
        "--bg-color",
        type=str,
        default="white",
        help="Background color for the word cloud image.",
    )
    parser.add_argument(
        "--font-path",
        type=Path,
        help="Path to a font file that supports Japanese (recommended).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("word_cloud.png"),
        help="Image file to write (PNG).",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=Path("word_cloud.log"),
        help="Optional path to write the token frequency list.",
    )
    parser.add_argument(
        "--stopwords-en",
        type=Path,
        default=Path("stopwords_en.txt"),
        help="Path to English stopwords file (one word per line).",
    )
    parser.add_argument(
        "--stopwords-ja",
        type=Path,
        default=Path("stopwords_ja.txt"),
        help="Path to Japanese stopwords file (one word per line).",
    )
    parser.add_argument(
        "--normalize-case",
        type=Path,
        default=Path("normalize.json"),
        help="Path to case normalization config file (JSON with 'en' and 'ja' keys).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target_dir = args.target
    if not target_dir.is_dir():
        raise SystemExit(f"Target directory not found: {target_dir}")

    stopwords_en = _load_stopwords(args.stopwords_en)
    stopwords_ja = _load_stopwords(args.stopwords_ja)
    normalize_config = _load_normalize_config(args.normalize_case)
    normalize_en = normalize_config.get("en", {})
    normalize_ja = normalize_config.get("ja", {})

    print(f"Scanning markdown files under {target_dir} ...")
    counter = collect_tokens(
        target_dir, stopwords_ja, stopwords_en, normalize_ja, normalize_en
    )
    if not counter:
        raise SystemExit("No tokens were extracted from the provided directory.")

    normalized_counter: Counter[str] = Counter()
    for token, freq in counter.items():
        if re.search(r"[A-Za-z]", token):
            norm = _normalize_en_case(token, normalize_en)
        else:
            norm = token
        normalized_counter[norm] += freq

    top_list = normalized_counter.most_common(args.top)
    log_lines = [f"{token}\t{freq}" for token, freq in top_list]
    args.log.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"Top tokens written to {args.log}")

    top_tokens = dict(top_list)
    font_path_str = str(args.font_path) if args.font_path else None
    wc_light = WordCloud(
        width=args.width,
        height=args.height,
        background_color=None,
        mode="RGBA",
        font_path=font_path_str,
        collocations=False,
        stopwords=stopwords_en,
        prefer_horizontal=1.0,
    ).generate_from_frequencies(top_tokens)
    light_array = wc_light.to_array()
    Image.fromarray(light_array).save(str(args.output))
    print(f"Word cloud image saved to {args.output}")


if __name__ == "__main__":
    main()
