"""Generate six foldable wedding place cards per A4 sheet.

Edit name-cards.txt (one name per line), then run:
    python generate_name_cards.py

The PDF includes the named cards followed by three full sheets of Reserved cards.
"""

from __future__ import annotations

import argparse
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader


ROOT = Path(__file__).resolve().parent
DEFAULT_NAMES = ROOT / "name-cards.txt"
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "wedding-name-cards-a4-sirivennela.pdf"
NAME_FONT = ROOT / "assets" / "Sirivennela-Regular.ttf"
ORANIENBAUM_FONT = ROOT / "assets" / "Oranienbaum-Regular.ttf"
FLORAL_ASSET = ROOT / "assets" / "name-card-floral-monotone.png"

DEEP_BROWN = HexColor("#5c4a3a")
DUSTY_ROSE = HexColor("#c9a77d")
CUT_GREY = HexColor("#9b948d")
FOLD_GREY = HexColor("#b9b1aa")
FOLD_MARK = HexColor("#b28a58")

PAGE_W, PAGE_H = A4
PAGE_MARGIN = 8 * mm
COL_GAP = 4 * mm
ROW_GAP = 4 * mm
CARD_W = (PAGE_W - 2 * PAGE_MARGIN - COL_GAP) / 2
CARD_H = (PAGE_H - 2 * PAGE_MARGIN - 2 * ROW_GAP) / 3
FACE_H = CARD_H / 2


def register_fonts() -> str:
    """Register the requested Oranienbaum monogram font."""
    if ORANIENBAUM_FONT.exists():
        pdfmetrics.registerFont(TTFont("Oranienbaum", str(ORANIENBAUM_FONT)))
        return "Oranienbaum"
    return "Times-Roman"


def read_names(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Names file not found: {path}")
    return [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


@lru_cache(maxsize=64)
def rendered_name(text: str, size_pt: float) -> Image.Image:
    """Render the Sirivennela name font as a high-resolution transparent image."""
    if not NAME_FONT.exists():
        raise FileNotFoundError(f"Required font not found: {NAME_FONT}")
    dpi = 600
    font = ImageFont.truetype(str(NAME_FONT), round(size_pt * dpi / 72))
    bbox = font.getbbox(text)
    pad = 18
    image = Image.new("RGBA", (bbox[2] - bbox[0] + 2 * pad, bbox[3] - bbox[1] + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(image).text((pad - bbox[0], pad - bbox[1]), text, font=font, fill=(42, 32, 25, 255))
    return image


def draw_name(c: Canvas, w: float, h: float, name: str) -> None:
    """Place Sirivennela text at the true vertical centre of each card face."""
    size_pt = 25.0
    max_width = w - 15 * mm
    while size_pt > 9:
        image = rendered_name(name, size_pt)
        width_pt = image.width * 72 / 600
        if width_pt <= max_width:
            break
        size_pt -= 0.5

    image = rendered_name(name, size_pt)
    width_pt = image.width * 72 / 600
    height_pt = image.height * 72 / 600
    c.drawImage(ImageReader(image), (w - width_pt) / 2, (h - height_pt) / 2 + 2.2 * mm, width=width_pt, height=height_pt, mask="auto")


@lru_cache(maxsize=1)
def floral_image() -> tuple[ImageReader, int, int]:
    if not FLORAL_ASSET.exists():
        raise FileNotFoundError(f"Floral asset not found: {FLORAL_ASSET}")
    image = Image.open(FLORAL_ASSET).convert("RGBA")
    return ImageReader(image), image.width, image.height


def draw_face(c: Canvas, w: float, h: float, name: str | None, monogram_font: str) -> None:
    c.setFillColor(DUSTY_ROSE)
    c.setFont(monogram_font, 10.5)
    c.drawCentredString(w / 2, h - 6.2 * mm, "J & T")

    if name:
        draw_name(c, w, h, name)

    floral, image_w, image_h = floral_image()
    floral_w = 34 * mm
    floral_h = floral_w * image_h / image_w
    c.saveState()
    c.setBlendMode("Multiply")
    c.drawImage(floral, (w - floral_w) / 2, 2.2 * mm, width=floral_w, height=floral_h)
    c.restoreState()


def draw_card(c: Canvas, x: float, y: float, name: str | None, monogram_font: str) -> None:
    # Card perimeter: short dash pattern behaves like a dotted cutting guide.
    c.saveState()
    c.setStrokeColor(CUT_GREY)
    c.setLineWidth(0.45)
    c.setDash(0.7, 1.65)
    c.rect(x, y, CARD_W, CARD_H, stroke=1, fill=0)
    c.restoreState()

    # Tiny centre fold registration mark, kept subtle for printing.
    c.saveState()
    c.setStrokeColor(FOLD_MARK)
    c.setLineWidth(0.8)
    mark_half = 1.6 * mm
    c.line(x + CARD_W / 2 - mark_half, y + FACE_H, x + CARD_W / 2 + mark_half, y + FACE_H)
    c.restoreState()

    # Lower face reads normally.
    c.saveState()
    c.translate(x, y)
    draw_face(c, CARD_W, FACE_H, name, monogram_font)
    c.restoreState()

    # Upper face is rotated so it reads correctly from the other side after folding.
    c.saveState()
    c.translate(x + CARD_W, y + CARD_H)
    c.rotate(180)
    draw_face(c, CARD_W, FACE_H, name, monogram_font)
    c.restoreState()


def draw_sheet(c: Canvas, names: list[str | None], monogram_font: str) -> None:
    c.setFillColor(HexColor("#ffffff"))
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)

    for index in range(6):
        row = index // 2
        col = index % 2
        x = PAGE_MARGIN + col * (CARD_W + COL_GAP)
        y = PAGE_H - PAGE_MARGIN - CARD_H - row * (CARD_H + ROW_GAP)
        name = names[index] if index < len(names) else None
        draw_card(c, x, y, name, monogram_font)

    c.showPage()


def build_pdf(names: list[str], output: Path, blank_pages: int) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    monogram_font = register_fonts()
    c = Canvas(str(output), pagesize=A4, pageCompression=1)
    c.setTitle("Wedding Name Cards - Jack and Tlhompho")
    c.setAuthor("Jack and Tlhompho")
    c.setSubject("Six foldable place cards per A4 sheet")

    named_pages = max(1, math.ceil(len(names) / 6))
    for page_number in range(named_pages):
        start = page_number * 6
        draw_sheet(c, names[start : start + 6], monogram_font)

    for _ in range(blank_pages):
        draw_sheet(c, ["Reserved"] * 6, monogram_font)

    c.save()
    return named_pages + blank_pages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--names", type=Path, default=DEFAULT_NAMES, help="UTF-8 text file, one name per line")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output PDF path")
    parser.add_argument("--blank-pages", type=int, default=3, help="Number of blank card sheets to append")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.blank_pages < 0:
        raise ValueError("--blank-pages must be zero or greater")
    names = read_names(args.names)
    pages = build_pdf(names, args.output, args.blank_pages)
    print(f"Created {args.output} with {len(names)} names across {pages} A4 pages.")


if __name__ == "__main__":
    main()
