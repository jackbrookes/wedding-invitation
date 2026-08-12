"""Create the A5 wedding menu in the established Jack & Tlhompho style."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib.colors import black, white
from reportlab.lib.pagesizes import A4, A5, A6
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output" / "pdf" / "wedding-menu-a5.pdf"
OUTPUT_BW = ROOT / "output" / "pdf" / "wedding-menu-a5-black-white.pdf"
OUTPUT_A6 = ROOT / "output" / "pdf" / "wedding-menu-a6.pdf"
OUTPUT_A6_BW = ROOT / "output" / "pdf" / "wedding-menu-a6-black-white.pdf"
OUTPUT_A6_4UP = ROOT / "output" / "pdf" / "wedding-menu-a6-4up-a4.pdf"
OUTPUT_A6_4UP_BW = ROOT / "output" / "pdf" / "wedding-menu-a6-4up-a4-black-white.pdf"
ORANIENBAUM = ROOT / "assets" / "Oranienbaum-Regular.ttf"
SCRIPT_FONT = ROOT / "MsClaudy-Regular.otf"
TOP_FLORAL = ROOT / "assets" / "floral-frame-top-ivory.png"
CORNER_FLORAL = ROOT / "assets" / "floral-corner-ivory.png"
BACKGROUND_TEXTURE = ROOT / "texture-21.png"

PAGE_W, PAGE_H = A5


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("Oranienbaum", str(ORANIENBAUM)))


def spaced_width(text: str, font: str, size: float, tracking: float) -> float:
    return sum(pdfmetrics.stringWidth(ch, font, size) for ch in text) + tracking * max(0, len(text) - 1)


def draw_spaced_centred(c: Canvas, text: str, y: float, size: float, tracking: float) -> None:
    c.setFont("Oranienbaum", size)
    width = spaced_width(text, "Oranienbaum", size, tracking)
    x = (PAGE_W - width) / 2
    for ch in text:
        c.drawString(x, y, ch)
        x += pdfmetrics.stringWidth(ch, "Oranienbaum", size) + tracking


@lru_cache(maxsize=16)
def monochrome_asset(path: str, colour: tuple[int, int, int]) -> Image.Image:
    """Recolour line art while preserving its transparency."""
    source = Image.open(path).convert("RGBA")
    alpha = source.getchannel("A")
    solid = Image.new("RGBA", source.size, (*colour, 255))
    solid.putalpha(alpha)
    return solid


@lru_cache(maxsize=16)
def rendered_script(text: str, size_pt: float, colour: tuple[int, int, int]) -> Image.Image:
    dpi = 600
    font = ImageFont.truetype(str(SCRIPT_FONT), round(size_pt * dpi / 72))
    bbox = font.getbbox(text)
    pad = 28
    image = Image.new("RGBA", (bbox[2] - bbox[0] + pad * 2, bbox[3] - bbox[1] + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(image).text((pad - bbox[0], pad - bbox[1]), text, font=font, fill=(*colour, 255))
    return image


def draw_script_centred(c: Canvas, text: str, y: float, size_pt: float, max_width: float, colour: tuple[int, int, int]) -> None:
    image = rendered_script(text, size_pt, colour)
    width = image.width * 72 / 600
    height = image.height * 72 / 600
    if width > max_width:
        scale = max_width / width
        width *= scale
        height *= scale
    c.drawImage(ImageReader(image), (PAGE_W - width) / 2, y, width=width, height=height, mask="auto")


def draw_arch_frame(c: Canvas, inset: float, line_width: float, compact: bool = False) -> None:
    x0 = inset
    x1 = PAGE_W - inset
    y0 = inset
    shoulder = (101 * mm if compact else 144 * mm)
    apex = PAGE_H - inset
    mid = PAGE_W / 2

    p = c.beginPath()
    p.moveTo(x0, y0)
    p.lineTo(x0, shoulder)
    control_y = 121 * mm if compact else 178 * mm
    control_x = 16 * mm if compact else 28 * mm
    p.curveTo(x0, control_y, control_x, apex, mid, apex)
    p.curveTo(PAGE_W - control_x, apex, x1, control_y, x1, shoulder)
    p.lineTo(x1, y0)
    p.close()
    c.setLineWidth(line_width)
    c.drawPath(p, stroke=1, fill=0)


def draw_cut_guides(c: Canvas, page_width: float, page_height: float, black_and_white: bool) -> None:
    """Draw short, subtle L-shaped guides at each trim corner."""
    guide_length = 2.2 * mm
    c.saveState()
    c.setStrokeColor(black if black_and_white else white)
    c.setLineWidth(0.3)
    c.setStrokeAlpha(0.62)
    for x, x_direction in ((0, 1), (page_width, -1)):
        for y, y_direction in ((0, 1), (page_height, -1)):
            c.line(x, y, x + x_direction * guide_length, y)
            c.line(x, y, x, y + y_direction * guide_length)
    c.restoreState()


def draw_flourish(c: Canvas, colour: tuple[int, int, int], compact: bool = False) -> None:
    top = monochrome_asset(str(TOP_FLORAL), colour)
    top_w = (28 * mm if compact else 35 * mm)
    top_h = top_w * top.height / top.width
    top_y = 130.5 * mm if compact else 181.8 * mm
    c.drawImage(ImageReader(top), (PAGE_W - top_w) / 2, top_y, width=top_w, height=top_h, mask="auto")

    corner = monochrome_asset(str(CORNER_FLORAL), colour)
    corner_h = (30 * mm if compact else 43 * mm)
    corner_w = corner_h * corner.width / corner.height
    c.saveState()
    c.setFillAlpha(0.82)
    corner_right = 6 * mm if compact else 11 * mm
    corner_y = 6 * mm if compact else 9.5 * mm
    c.drawImage(ImageReader(corner), PAGE_W - corner_right - corner_w, corner_y, width=corner_w, height=corner_h, mask="auto")
    c.restoreState()


def draw_section(
    c: Canvas,
    heading: str,
    items: list[str | tuple[str, str]],
    heading_y: float,
    item_size: float = 12.2,
    item_gap: float = 6.3,
    heading_size: float = 9.2,
    heading_gap: float = 8.1,
) -> float:
    draw_spaced_centred(c, heading.upper(), heading_y, heading_size, 2.05)
    y = heading_y - heading_gap * mm
    c.setFont("Oranienbaum", item_size)
    for item in items:
        if isinstance(item, tuple):
            title, descriptor = item
            c.setFont("Oranienbaum", item_size)
            c.drawCentredString(PAGE_W / 2, y, title)
            y -= 4.5 * mm
            c.setFont("Oranienbaum", 9.4)
            c.drawCentredString(PAGE_W / 2, y, descriptor)
            y -= 5.6 * mm
        else:
            c.setFont("Oranienbaum", item_size)
            c.drawCentredString(PAGE_W / 2, y, item)
            y -= item_gap * mm
    return y


def draw_menu_page(c: Canvas, black_and_white: bool, page_size, compact: bool) -> None:
    """Draw one menu page at the current canvas origin."""
    global PAGE_W, PAGE_H
    PAGE_W, PAGE_H = page_size

    colour = (0, 0, 0) if black_and_white else (255, 255, 255)
    if black_and_white:
        c.setFillColor(white)
        c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    else:
        background = Image.open(BACKGROUND_TEXTURE).convert("RGB")
        c.drawImage(ImageReader(background), 0, 0, width=PAGE_W, height=PAGE_H, mask="auto")
    c.setStrokeColor(black if black_and_white else white)
    c.setFillColor(black if black_and_white else white)

    outer_inset = 2.5 * mm if compact else 7.5 * mm
    inner_inset = 4.0 * mm if compact else 9.8 * mm
    draw_arch_frame(c, outer_inset, 0.7, compact)
    draw_arch_frame(c, inner_inset, 0.3, compact)
    draw_flourish(c, colour, compact)

    title_y = 111.5 * mm if compact else 151.5 * mm
    rule_y = 109.5 * mm if compact else 148.8 * mm
    draw_script_centred(c, "Menu", title_y, 38 if compact else 47, 62 * mm if compact else 72 * mm, colour)
    c.setLineWidth(0.45)
    c.line(PAGE_W / 2 - 12 * mm, rule_y, PAGE_W / 2 + 12 * mm, rule_y)

    if compact:
        item_size, item_gap, heading_size, heading_gap, section_gap = 12.2, 5.5, 10.0, 6.6, 1.6
        y = draw_section(c, "Mains", ["White Rice", "Fried Rice", "Creamy Samp", "Bogobe jwa Lerotse"], 100.5 * mm, item_size, item_gap, heading_size, heading_gap)
        y = draw_section(c, "Meats", ["Fried Chicken", "Beef Stew", "Seswaa"], y - section_gap * mm, item_size, item_gap, heading_size, heading_gap)
        y = draw_section(c, "Salads", ["Beetroot", "Chakalaka", "Coleslaw", "Butternut"], y - section_gap * mm, item_size, item_gap, heading_size, heading_gap)
        c.setFont("Oranienbaum", item_size)
        c.drawCentredString(PAGE_W / 2, y - 4.0 * mm, "Soup")
    else:
        y = draw_section(c, "Mains", ["White Rice", "Fried Rice", "Creamy Samp", "Bogobe jwa Lerotse"], 137.3 * mm)
        y = draw_section(c, "Meats", ["Fried Chicken", "Beef Stew", "Seswaa"], y - 3.1 * mm)
        y = draw_section(c, "Salads", ["Beetroot", "Chakalaka", "Coleslaw", "Butternut"], y - 3.1 * mm)
        c.setFont("Oranienbaum", 12.2)
        c.drawCentredString(PAGE_W / 2, y - 3.1 * mm, "Soup")

    draw_spaced_centred(c, "J & T", 6.2 * mm if compact else 15.5 * mm, 7.4 if compact else 7.6, 1.5)


def build_pdf(
    output: Path = OUTPUT,
    black_and_white: bool = False,
    page_size=A5,
    compact: bool = False,
) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    register_fonts()

    c = Canvas(str(output), pagesize=page_size, pageCompression=1)
    c.setTitle("Wedding Menu - Jack and Tlhompho")
    c.setAuthor("Jack and Tlhompho")
    c.setSubject("A5 wedding menu")
    draw_menu_page(c, black_and_white, page_size, compact)
    c.showPage()
    c.save()


def build_4up_pdf(output: Path, black_and_white: bool = False) -> None:
    """Create a single A4 sheet containing four correctly sized A6 menus."""
    global PAGE_W, PAGE_H
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    register_fonts()

    tile_w, tile_h = A6
    sheet_w, sheet_h = A4
    x_margin = (sheet_w - 2 * tile_w) / 2
    y_margin = (sheet_h - 2 * tile_h) / 2

    c = Canvas(str(output), pagesize=A4, pageCompression=1)
    c.setTitle("Wedding Menu - A6 4-up on A4")
    c.setAuthor("Jack and Tlhompho")
    c.setSubject("Four A6 wedding menus on one A4 sheet")
    c.setFillColor(white)
    c.rect(0, 0, sheet_w, sheet_h, stroke=0, fill=1)

    for x in (x_margin, x_margin + tile_w):
        for y in (y_margin, y_margin + tile_h):
            c.saveState()
            c.translate(x, y)
            draw_menu_page(c, black_and_white, A6, compact=True)
            draw_cut_guides(c, tile_w, tile_h, black_and_white)
            c.restoreState()

    PAGE_W, PAGE_H = A6
    c.showPage()
    c.save()


if __name__ == "__main__":
    build_pdf()
    build_pdf(OUTPUT_BW, black_and_white=True)
    build_pdf(OUTPUT_A6, page_size=A6, compact=True)
    build_pdf(OUTPUT_A6_BW, black_and_white=True, page_size=A6, compact=True)
    build_4up_pdf(OUTPUT_A6_4UP)
    build_4up_pdf(OUTPUT_A6_4UP_BW, black_and_white=True)
    print(f"Created {OUTPUT}")
    print(f"Created {OUTPUT_BW}")
    print(f"Created {OUTPUT_A6}")
    print(f"Created {OUTPUT_A6_BW}")
    print(f"Created {OUTPUT_A6_4UP}")
    print(f"Created {OUTPUT_A6_4UP_BW}")
