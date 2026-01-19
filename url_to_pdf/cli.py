import click

from .extractor import extract_article
from .image_handler import cleanup_images, download_images, download_top_image
from .pdf_generator import (
    find_available_fonts,
    generate_pdf,
    get_default_font,
    get_font_families,
)


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

        return

    # Check required arguments
    if not url:
        raise click.ClickException("URL is required (unless using --list-fonts)")
    if not output:
        raise click.ClickException("Output file path is required (-o/--output)")

    # Determine which font to use
    font_to_use = font
    if verbose:
        if font_to_use:
            click.echo(f"Using font: {font_to_use}")
        else:
            try:
                default_font = get_default_font()
                click.echo(f"Using default font: {default_font}")
            except RuntimeError:
                pass

    if verbose:
        click.echo(f"Extracting article from: {url}")

    try:
        article = extract_article(url)
    except Exception as e:
        raise click.ClickException(f"Failed to extract article: {e}")

    if verbose:
        click.echo(f"Title: {article.title}")
        click.echo(f"Text length: {len(article.text)} chars")
        click.echo(f"Top image: {article.top_image or 'None'}")
        click.echo(f"Found {len(article.images)} images")

    top_image = None
    images = []

    if not no_images:
        if article.top_image:
            if verbose:
                click.echo("Downloading top image...")
            top_image = download_top_image(article.top_image, verbose=verbose)

        if article.images:
            if verbose:
                click.echo("Downloading article images...")
            skip_urls = {article.top_image} if article.top_image else set()
            images = download_images(
                article.images,
                max_images=max_images,
                verbose=verbose,
                skip_urls=skip_urls,
            )
        if verbose:
            click.echo(f"Downloaded {len(images)} images" + (" + top image" if top_image else ""))

    all_images = ([top_image] if top_image else []) + images

    try:
        if verbose:
            click.echo(f"Generating PDF: {output}")
        generate_pdf(
            article, all_images, output, custom_title=title, font_family=font_to_use
        )
        click.echo(f"Saved: {output}")
    finally:
        cleanup_images(all_images)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
