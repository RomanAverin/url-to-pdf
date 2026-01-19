import click

from .extractor import extract_article
from .image_handler import cleanup_images, download_images, download_top_image
from .pdf_generator import generate_pdf


@click.command()
@click.argument("url")
@click.option(
    "-o",
    "--output",
    required=True,
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
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose output",
)
def main(
    url: str,
    output: str,
    title: str | None,
    no_images: bool,
    max_images: int,
    verbose: bool,
) -> None:
    """Extract article from URL and save as PDF.

    URL is the web page URL to extract content from.
    """
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
        generate_pdf(article, all_images, output, custom_title=title)
        click.echo(f"Saved: {output}")
    finally:
        cleanup_images(all_images)


if __name__ == "__main__":
    main()
