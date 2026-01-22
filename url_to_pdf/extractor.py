import re
from dataclasses import dataclass
from typing import Literal, Optional
from urllib.parse import urljoin

from lxml import html
from newspaper import Article, Config

ALLOWED_TAGS = {"b", "strong", "i", "em", "u"}


@dataclass
class ContentBlock:
    type: Literal["heading", "paragraph"]
    text: str
    html: str = ""
    level: int = 0  # For headings: 1-6


def _clean_html(element: html.HtmlElement, base_url: str = "") -> str:
    """Extract HTML keeping only allowed formatting tags and links."""
    result = []

    def process_node(node):
        if isinstance(node, str):
            result.append(node)
            return

        tag = node.tag if hasattr(node, "tag") else None

        if tag in ALLOWED_TAGS:
            normalized_tag = "b" if tag == "strong" else "i" if tag == "em" else tag
            result.append(f"<{normalized_tag}>")
        elif tag == "a":
            href = node.get("href", "")
            if href and not href.startswith("#"):
                if base_url and not href.startswith(("http://", "https://")):
                    href = urljoin(base_url, href)
                result.append(f'<a href="{href}">')

        if node.text:
            result.append(node.text)

        for child in node:
            process_node(child)
            if child.tail:
                result.append(child.tail)

        if tag in ALLOWED_TAGS:
            normalized_tag = "b" if tag == "strong" else "i" if tag == "em" else tag
            result.append(f"</{normalized_tag}>")
        elif tag == "a":
            href = node.get("href", "")
            if href and not href.startswith("#"):
                result.append("</a>")

    if element.text:
        result.append(element.text)

    for child in element:
        process_node(child)
        if child.tail:
            result.append(child.tail)

    text = "".join(result)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@dataclass
class ExtractedArticle:
    title: str
    content: list[ContentBlock]
    text: str  # Plain text fallback
    authors: list[str]
    images: list[str]
    top_image: Optional[str]
    source_url: str


def _extract_content_blocks(
    doc: html.HtmlElement, base_url: str = ""
) -> list[ContentBlock]:
    """Extract structured content with headings from article HTML."""
    blocks: list[ContentBlock] = []

    content_selectors = [
        "//article",
        '//div[contains(@class, "entry-content")]',
        '//div[contains(@class, "post-content")]',
        '//div[contains(@class, "article-content")]',
        '//div[contains(@class, "content")]',
        "//main",
    ]

    content_root = None
    for selector in content_selectors:
        results = doc.xpath(selector)
        if results:
            content_root = results[0]
            break

    if content_root is None:
        content_root = doc.xpath("//body")[0] if doc.xpath("//body") else doc

    for element in content_root.iter():
        if element.tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            text = element.text_content().strip()
            if text:
                level = int(element.tag[1])
                blocks.append(
                    ContentBlock(
                        type="heading",
                        text=text,
                        html=_clean_html(element, base_url),
                        level=level,
                    )
                )
        elif element.tag == "p":
            text = element.text_content().strip()
            if text and len(text) > 20:
                blocks.append(
                    ContentBlock(
                        type="paragraph",
                        text=text,
                        html=_clean_html(element, base_url),
                    )
                )

    return blocks


def _find_top_image(doc: html.HtmlElement, base_url: str) -> Optional[str]:
    """Find the main article image using multiple strategies."""
    selectors = [
        '//meta[@property="og:image"]/@content',
        '//meta[@name="twitter:image"]/@content',
        '//meta[@name="twitter:image:src"]/@content',
        '//img[contains(@class, "post-thumbnail")]/@src',
        '//img[contains(@class, "wp-post-image")]/@src',
        '//img[contains(@class, "featured")]/@src',
        "//article//img/@src",
        '//div[contains(@class, "entry")]//img/@src',
        '//div[contains(@class, "content")]//img/@src',
    ]

    for selector in selectors:
        results = doc.xpath(selector)
        for result in results:
            if result and not result.startswith("data:"):
                img_url = urljoin(base_url, result)
                if "32x32" not in img_url and "favicon" not in img_url.lower():
                    return img_url
    return None


def extract_article(url: str, timeout: int = 30) -> ExtractedArticle:
    """Extract article content from URL using newspaper4k."""
    config = Config()
    config.request_timeout = timeout
    config.browser_user_agent = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    article = Article(url, config=config)
    article.download()
    article.parse()

    top_image = article.top_image
    content: list[ContentBlock] = []

    try:
        doc = html.fromstring(article.html)
        if not top_image or "32x32" in top_image or "favicon" in top_image.lower():
            top_image = _find_top_image(doc, url) or article.top_image
        content = _extract_content_blocks(doc, url)
    except Exception:
        pass

    if not content and article.text:
        for para in article.text.split("\n\n"):
            para = para.strip()
            if para:
                content.append(ContentBlock(type="paragraph", text=para))

    images = list(article.images) if article.images else []
    if top_image and top_image not in images:
        images.insert(0, top_image)

    return ExtractedArticle(
        title=article.title or "Untitled",
        content=content,
        text=article.text or "",
        authors=list(article.authors) if article.authors else [],
        images=images,
        top_image=top_image,
        source_url=url,
    )
