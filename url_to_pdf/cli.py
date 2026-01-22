import click

from .extractor import extract_article
from .image_handler import cleanup_images, download_images, download_top_image
from .pdf_generator import (
    find_available_fonts,
    generate_pdf,
    get_default_font,
    get_font_families,
)
from .progress import ProgressReporter
from .state_machine import JobState


def _handle_list_fonts() -> None:
    """Handle --list-fonts flag: display available fonts and exit."""
    available = find_available_fonts()
    all_families = get_font_families()

    if not available:
        click.echo("No fonts are available in the system.")
        click.echo("\nPlease install one of the following:")
        for name, family in all_families.items():
            click.echo(f"  - {family.display_name}")
        raise click.ClickException("No fonts available")

    try:
        default = get_default_font()
    except RuntimeError:
        default = None

    click.echo("Available fonts:")
    for name in available:
        family = all_families[name]
        default_mark = " (default)" if name == default else ""
        click.echo(f"  * {name} ({family.display_name}){default_mark}")


def _validate_required_args(url: str | None, output: str | None) -> None:
    """Validate that required arguments are provided.

    Args:
        url: The URL to extract content from
        output: The output file path

    Raises:
        click.ClickException: If required arguments are missing
    """
    if not url:
        raise click.ClickException("URL is required (unless using --list-fonts)")
    if not output:
        raise click.ClickException("Output file path is required (-o/--output)")


def _show_font_info(font: str | None, verbose: bool) -> None:
    """Display information about the selected font.

    Args:
        font: Font family name or None for default
        verbose: Whether to show output
    """
    if not verbose:
        return

    if font:
        click.echo(f"Using font: {font}")
    else:
        try:
            default_font = get_default_font()
            click.echo(f"Using default font: {default_font}")
        except RuntimeError:
            pass


def _show_article_info(article, url: str, verbose: bool) -> None:
    """Display extracted article information.

    Args:
        article: Extracted article object
        url: Source URL
        verbose: Whether to show output
    """
    if not verbose:
        return

    click.echo(f"Extracting article from: {url}")
    click.echo(f"Title: {article.title}")
    click.echo(f"Text length: {len(article.text)} chars")
    click.echo(f"Top image: {article.top_image or 'None'}")
    click.echo(f"Found {len(article.images)} images")


def _download_article_images(article, no_images: bool, max_images: int, verbose: bool):
    """Download article images if needed.

    Args:
        article: Extracted article object
        no_images: Whether to skip image download
        max_images: Maximum number of images to download
        verbose: Whether to show detailed output (disables progress bars)

    Returns:
        Tuple of (top_image, images_list)
    """
    top_image = None
    images = []

    if no_images:
        return top_image, images

    show_progress = not verbose  # only without verbose mode

    if article.top_image:
        top_image = download_top_image(
            article.top_image, verbose=verbose, show_progress=show_progress
        )

    if article.images:
        skip_urls = {article.top_image} if article.top_image else set()
        images = download_images(
            article.images,
            max_images=max_images,
            verbose=verbose,
            skip_urls=skip_urls,
            show_progress=show_progress,
        )

    # Итоговое сообщение
    if not verbose:
        total = len(images) + (1 if top_image else 0)
        click.echo(f"Downloaded {total} image(s)")
    elif verbose:
        click.echo(
            f"Downloaded {len(images)} images" + (" + top image" if top_image else "")
        )

    return top_image, images


def _download_article_images_with_progress(
    article, no_images: bool, max_images: int, progress_reporter: ProgressReporter
):
    """Download article images with progress updates.

    Args:
        article: Extracted article object
        no_images: Whether to skip image download
        max_images: Maximum number of images to download
        progress_reporter: Progress reporter instance

    Returns:
        Tuple of (top_image, images_list)
    """
    top_image = None
    images = []

    if no_images:
        return top_image, images

    # Calculate total images for progress
    total_images = 0
    if article.top_image:
        total_images += 1
    if article.images:
        total_images += min(len(article.images), max_images)

    # Callback for image download progress
    def on_image_downloaded(downloaded: int, total: int):
        progress_reporter.update_images_progress(downloaded, total)

    # Download top image
    if article.top_image:
        top_image = download_top_image(article.top_image, verbose=False, show_progress=False)
        if top_image:
            on_image_downloaded(1, total_images)

    # Download other images
    if article.images:
        skip_urls = {article.top_image} if article.top_image else set()
        images = download_images(
            article.images,
            max_images=max_images,
            verbose=False,
            skip_urls=skip_urls,
            show_progress=False,
            progress_callback=on_image_downloaded,
        )

    return top_image, images


@click.command()
@click.argument("url", required=False)
@click.option(
    "-o",
    "--output",
    help="Output PDF file path",
)
@click.option(
    "--title",
    default=None,
    help="Custom title for the PDF (overrides extracted title)",
)
@click.option(
    "--no-images",
    is_flag=True,
    default=False,
    help="Skip downloading and including images",
)
@click.option(
    "--max-images",
    default=10,
    type=int,
    help="Maximum number of images to include (default: 10)",
)
@click.option(
    "--font",
    default=None,
    help="Font family to use (e.g., noto-sans, noto-serif, liberation-sans)",
)
@click.option(
    "--list-fonts",
    is_flag=True,
    default=False,
    help="List available fonts and exit",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose output",
)
def main(
    url: str | None,
    output: str | None,
    title: str | None,
    no_images: bool,
    max_images: int,
    font: str | None,
    list_fonts: bool,
    verbose: bool,
) -> None:
    """Extract article from URL and save as PDF.

    URL is the web page URL to extract content from.
    """
    # Handle --list-fonts
    if list_fonts:
        _handle_list_fonts()
        return

    # Validate required arguments
    _validate_required_args(url, output)
    assert url is not None  # Type narrowing for type checker
    assert output is not None  # Type narrowing for type checker

    # Show font information
    _show_font_info(font, verbose)

    all_images = []

    try:
        # Use progress reporter for non-verbose mode
        if not verbose:
            with ProgressReporter(url) as progress_reporter:
                # Stage 1: Extract article
                progress_reporter.update_state(JobState.EXTRACTING)
                article = extract_article(url)

                # Stage 2: Download images
                progress_reporter.update_state(JobState.DOWNLOADING_IMAGES)
                top_image, images = _download_article_images_with_progress(
                    article, no_images, max_images, progress_reporter
                )
                all_images = ([top_image] if top_image else []) + images

                # Stage 3: Generate PDF
                progress_reporter.update_state(JobState.GENERATING_PDF)
                generate_pdf(
                    article, all_images, output, custom_title=title, font_family=font
                )

                # Stage 4: Completed
                progress_reporter.update_state(JobState.COMPLETED)

            click.echo(f"✓ Saved: {output}")
        else:
            # Verbose mode: use old behavior
            article = extract_article(url)
            _show_article_info(article, url, verbose)

            # Download images
            top_image, images = _download_article_images(
                article, no_images, max_images, verbose
            )
            all_images = ([top_image] if top_image else []) + images

            # Generate PDF
            click.echo(f"Generating PDF: {output}")
            generate_pdf(article, all_images, output, custom_title=title, font_family=font)
            click.echo(f"✓ Saved: {output}")

    except Exception as e:
        raise click.ClickException(f"Failed: {e}")
    finally:
        if all_images:
            cleanup_images(all_images)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
