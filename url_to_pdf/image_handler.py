import re
import tempfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional, Callable

import click
import requests
from PIL import Image

AD_PATTERNS = [
    r"(?<![a-z])ad[sx]?[_\-./]",
    r"(?<![a-z])banner",
    r"tracker",
    r"pixel",
    r"(?<![a-z])logo",
    r"(?<![a-z])icon",
    r"avatar",
    r"button",
    r"sprite",
    r"social",
    r"share",
    r"widget",
    r"badge",
    r"promo",
    r"sponsor",
    r"doubleclick",
    r"googlesyndication",
    r"googleadservices",
    r"facebook\.com/tr",
    r"analytics",
    r"(?<![a-z])stat[_\-./]",
    r"counter",
    r"beacon",
    r"sber",
    r"yoomoney",
    r"yoo[-_]",
    r"boosty",
    r"patreon",
    r"paypal",
    r"donate",
    r"payment",
    r"pay[-_.]",
]

AD_PATTERN_RE = re.compile("|".join(AD_PATTERNS), re.IGNORECASE)

MIN_WIDTH = 100
MIN_HEIGHT = 100
MIN_ASPECT_RATIO = 0.2
MAX_ASPECT_RATIO = 5.0


@dataclass
class DownloadedImage:
    path: Path
    width: int
    height: int
    original_url: str


def is_ad_url(url: str) -> bool:
    """Check if URL matches advertising/tracking patterns."""
    return bool(AD_PATTERN_RE.search(url))


def download_image(url: str, timeout: int = 10) -> Optional[DownloadedImage]:
    """Download single image and return its info."""
    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            return None

        image_data = BytesIO(response.content)
        img = Image.open(image_data)
        width, height = img.size

        suffix = Path(url.split("?")[0]).suffix or ".jpg"
        if suffix.lower() not in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
            suffix = ".jpg"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(tmp.name, quality=85)
            return DownloadedImage(
                path=Path(tmp.name),
                width=width,
                height=height,
                original_url=url,
            )
    except Exception:
        return None


def filter_image(img: DownloadedImage) -> bool:
    """Check if image passes quality filters."""
    if img.width < MIN_WIDTH or img.height < MIN_HEIGHT:
        return False

    aspect_ratio = img.width / img.height
    if aspect_ratio < MIN_ASPECT_RATIO or aspect_ratio > MAX_ASPECT_RATIO:
        return False

    if is_ad_url(img.original_url):
        return False

    return True


def download_top_image(
    url: str,
    verbose: bool = False,
    show_progress: bool = True,
) -> Optional[DownloadedImage]:
    """Download top image without URL pattern filtering."""
    if not url:
        return None

    # show only without verbose and show_progress mode
    if show_progress and not verbose:
        click.echo("Downloading top image...")
    elif verbose:
        print(f"  Downloading top image: {url[:60]}...")

    img = download_image(url)
    if img is None:
        if verbose:
            print("    Failed to download")
        return None

    if img.width < MIN_WIDTH or img.height < MIN_HEIGHT:
        if verbose:
            print(f"    Too small ({img.width}x{img.height})")
        img.path.unlink(missing_ok=True)
        return None

    if verbose:
        print(f"    OK ({img.width}x{img.height})")
    return img


def download_images(
    image_urls: list[str],
    max_images: int = 10,
    verbose: bool = False,
    skip_urls: Optional[set[str]] = None,
    show_progress: bool = True,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> list[DownloadedImage]:
    """Download and filter images from URLs.

    Args:
        image_urls: List of image URLs to download
        max_images: Maximum number of images to download
        verbose: Enable verbose output
        skip_urls: Set of URLs to skip
        show_progress: Show progress bar (click.progressbar)
        progress_callback: Callback function for progress updates (downloaded, total)

    Returns:
        List of successfully downloaded images
    """
    downloaded: list[DownloadedImage] = []
    skip_urls = skip_urls or set()

    # Фильтруем URL заранее (удаляем ads и skip_urls)
    urls_to_process = [
        url for url in image_urls if url not in skip_urls and not is_ad_url(url)
    ][: max_images * 2]  # Берем с запасом, т.к. некоторые могут не загрузиться

    total_to_process = min(len(urls_to_process), max_images)

    # Режим с progress_callback (для rich)
    if progress_callback:
        for url in urls_to_process:
            if len(downloaded) >= max_images:
                break

            img = download_image(url)
            if img and filter_image(img):
                downloaded.append(img)
                progress_callback(len(downloaded), total_to_process)
            elif img:
                img.path.unlink(missing_ok=True)

    # Режим прогресс-бара (существующий код)
    elif show_progress and not verbose:
        with click.progressbar(
            urls_to_process,
            label="Downloading images",
            show_pos=True,
            item_show_func=lambda url: f"{url[:40]}..." if url else "",
        ) as progress_bar:
            for url in progress_bar:
                if len(downloaded) >= max_images:
                    break

                img = download_image(url)
                if img and filter_image(img):
                    downloaded.append(img)
                elif img:
                    img.path.unlink(missing_ok=True)

    # Режим verbose (существующий код)
    else:
        for url in urls_to_process:
            if len(downloaded) >= max_images:
                break

            if verbose:
                print(f"  Downloading: {url[:60]}...")

            img = download_image(url)
            if img is None:
                if verbose:
                    print("    Failed to download")
                continue

            if not filter_image(img):
                if verbose:
                    print(f"    Filtered out ({img.width}x{img.height})")
                img.path.unlink(missing_ok=True)
                continue

            if verbose:
                print(f"    OK ({img.width}x{img.height})")
            downloaded.append(img)

    return downloaded


def cleanup_images(images: list[DownloadedImage]) -> None:
    """Remove temporary image files."""
    for img in images:
        img.path.unlink(missing_ok=True)
