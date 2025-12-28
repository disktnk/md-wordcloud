# md-wordcloud

A multilingual word cloud generator for markdown files that supports both English and Japanese text.

## Overview

This script scans markdown files in a specified directory, extracts meaningful tokens from both English and Japanese content, and generates a word cloud visualization. It handles the complexities of multilingual text processing:

- **Japanese tokenization**: Uses MeCab for morphological analysis, extracting nouns, adjectives, and verbs while filtering out particles and common stopwords
- **English tokenization**: Pattern-based extraction with case normalization and stopword filtering
- **Markdown processing**: Intelligently strips code blocks, URLs, HTML tags, links, footnotes, and other markdown syntax to focus on actual content
- **Frontmatter support**: Includes post titles from YAML frontmatter in the analysis
- **Frequency-based visualization**: Generates word clouds using the most common tokens, with customizable colors, sizes, and fonts
- **Configurable filtering**: Stopwords and case normalization rules are loaded from external files for easy customization
- **Output**: Generates both a PNG image of the word cloud and a log file containing token frequencies

## Configuration Files

The script uses external configuration files for flexibility:

- **`stopwords_en.txt`**: English stopwords (one word per line)
- **`stopwords_ja.txt`**: Japanese stopwords (one word per line)
- **`normalize.json`**: Case normalization rules in JSON format with `"en"` and `"ja"` keys

See sample files.

## Usage

```sh
$ uv sync
```

Prepare setting files, following commands use sample files:

```sh
$ cp stopwords_en.sample.txt stopwords_en.txt 
$ cp stopwords_ja.sample.txt stopwords_ja.txt 
$ cp normalize.sample.json normalize.json
```

If output includes Japanese, specify a font file (e.g., `/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc` on Mac):

```sh
$ uv run generate_word_cloud.py /path/to/target --font-path /path/to/font
```

## For Developers

```sh
$ uv sync --extra dev
```

```sh
$ uv run mypy .
$ uv run ruff format .
$ uv run ruff check . --fix
```

