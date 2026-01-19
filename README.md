# url-to-pdf

CLI tool to extract article content from a web page and save it as PDF.

## Features

- Extracts article text, title, and images
- Preserves text formatting (bold, italic, links)
- Filters out ads and tracking images
- Supports Cyrillic text
- Multiple font choices with Unicode/Cyrillic support (Noto Sans, Liberation, DejaVu, Free fonts)
- Automatic font detection and fallback

## Installation

Install as package

```bash
pip Install -e .

```

## Usage

```bash
# Basic usage (uses default font)
url-to-pdf https://example.com/article -o article.pdf

# With custom title
url-to-pdf https://example.com/article -o article.pdf --title "My Title"

# Without images
url-to-pdf https://example.com/article -o article.pdf --no-images

# Verbose output
url-to-pdf https://example.com/article -o article.pdf -v

# List available fonts
url-to-pdf --list-fonts

# Use specific font (sans-serif)
url-to-pdf https://example.com/article -o article.pdf --font noto-sans

# Use serif font
url-to-pdf https://example.com/article -o article.pdf --font noto-serif

# Use Liberation Sans (metrics-compatible with Arial)
url-to-pdf https://example.com/article -o article.pdf --font liberation-sans

# With verbose output showing which font is used
url-to-pdf https://example.com/article -o article.pdf -v --font noto-serif
```

### Available Fonts

The tool supports the following font families with Unicode/Cyrillic support:

- **noto-sans** (Noto Sans) - Google's comprehensive sans-serif font
- **noto-serif** (Noto Serif) - Google's comprehensive serif font
- **liberation-sans** (Liberation Sans) - Metrics-compatible with Arial
- **liberation-serif** (Liberation Serif) - Metrics-compatible with Times New Roman
- **free-sans** (Free Sans) - GNU FreeFont sans-serif
- **free-serif** (Free Serif) - GNU FreeFont serif
- **dejavu-sans** (DejaVu Sans) - Popular Linux sans-serif font
- **dejavu-serif** (DejaVu Serif) - Popular Linux serif font

The tool will automatically detect which fonts are installed in your system and use the first available one as default. Use `--list-fonts` to see which fonts are available on your system.

## Development

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Run linter
uv run pylint url_to_pdf
```

## License

MIT
