from pathlib import Path
from typing import Optional

from fpdf import FPDF

from .extractor import ContentBlock, ExtractedArticle
from .image_handler import DownloadedImage

HEADING_SIZES = {
    1: 16,
    2: 14,
    3: 13,
    4: 12,
    5: 11,
    6: 11,
}

DEJAVU_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "C:/Windows/Fonts/DejaVuSans.ttf",
]

DEJAVU_BOLD_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/DejaVuSans-Bold.ttf",
]


def find_font(paths: list[str]) -> Optional[str]:
    """Find first existing font from list of paths."""
    for path in paths:
        if Path(path).exists():
            return path
    return None


class ArticlePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.font_family_name = "DejaVu"
        self._setup_fonts()

    def _setup_fonts(self):
        """Setup Unicode fonts for Cyrillic support."""
        regular_font = find_font(DEJAVU_FONT_PATHS)
        bold_font = find_font(DEJAVU_BOLD_PATHS)

        if regular_font:
            self.add_font(self.font_family_name, "", regular_font)
            if bold_font:
                self.add_font(self.font_family_name, "B", bold_font)
            self.set_font(self.font_family_name, size=12)
        else:
            self.font_family_name = "Helvetica"
            self.set_font("Helvetica", size=12)

    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_family_name, size=8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)


def generate_pdf(
    article: ExtractedArticle,
    images: list[DownloadedImage],
    output_path: str,
    custom_title: Optional[str] = None,
) -> None:
    """Generate PDF from extracted article with images."""
    pdf = ArticlePDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    effective_width = pdf.w - pdf.l_margin - pdf.r_margin

    title = custom_title or article.title
    pdf.set_font(pdf.font_family_name, "B", 18)
    pdf.multi_cell(0, 10, title)
    pdf.ln(5)

    meta_parts = []
    if article.authors:
        meta_parts.append(f"Authors: {', '.join(article.authors)}")
    if article.publish_date:
        meta_parts.append(f"Date: {article.publish_date.strftime('%Y-%m-%d')}")
    meta_parts.append(f"Source: {article.source_url}")

    if meta_parts:
        pdf.set_font(pdf.font_family_name, size=10)
        pdf.set_text_color(100, 100, 100)
        for meta in meta_parts:
            pdf.multi_cell(0, 6, meta)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(10)

    images_to_insert = list(images)

    if images_to_insert:
        top_img = images_to_insert.pop(0)
        _insert_image(pdf, top_img, effective_width)

    content_blocks = article.content if article.content else []
    paragraph_count = sum(1 for b in content_blocks if b.type == "paragraph")
    image_interval = max(1, paragraph_count // (len(images_to_insert) + 1)) if images_to_insert else 0
    paragraph_idx = 0

    for block in content_blocks:
        if block.type == "heading":
            pdf.ln(4)
            size = HEADING_SIZES.get(block.level, 12)
            pdf.set_font(pdf.font_family_name, "B", size)
            pdf.multi_cell(0, 8, block.text)
            pdf.ln(2)
            pdf.set_font(pdf.font_family_name, size=12)
        else:
            pdf.set_font(pdf.font_family_name, size=12)
            lines = block.text.split("\n")
            for line in lines:
                if line.strip():
                    pdf.multi_cell(0, 7, line.strip())
            pdf.ln(4)

            paragraph_idx += 1
            if images_to_insert and image_interval > 0 and paragraph_idx % image_interval == 0:
                img = images_to_insert.pop(0)
                _insert_image(pdf, img, effective_width)

    for img in images_to_insert:
        _insert_image(pdf, img, effective_width)

    pdf.output(output_path)


def _insert_image(pdf: ArticlePDF, img: DownloadedImage, max_width: float) -> None:
    """Insert image into PDF, scaling to fit page width."""
    try:
        img_width = min(img.width, max_width)
        scale = img_width / img.width
        img_height = img.height * scale

        if pdf.get_y() + img_height > pdf.h - pdf.b_margin:
            pdf.add_page()

        x = pdf.l_margin + (max_width - img_width) / 2
        pdf.image(str(img.path), x=x, w=img_width)
        pdf.ln(8)
    except Exception:
        pass
