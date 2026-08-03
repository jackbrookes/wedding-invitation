"""Create the A5 wedding menu in the established Jack & Tlhompho style."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib.colors import white
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output" / "pdf" / "wedding-menu-a5.pdf"
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


@lru_cache(maxsize=8)
def monochrome_asset(path: str) -> Image.Image:
    """Turn the suite's ivory line art into crisp white art with transparency."""
    source = Image.open(path).convert("RGBA")
    alpha = source.getchannel("A")
    solid = Image.new("RGBA", source.size, (255, 255, 255, 255))
    solid.putalpha(alpha)
    return solid


@lru_cache(maxsize=8)
def rendered_script(text: str, size_pt: float) -> Image.Image:
    dpi = 600
    font = ImageFont.truetype(str(SCRIPT_FONT), round(size_pt * dpi / 72))
    bbox = font.getbbox(text)
    pad = 28
    image = Image.new("RGBA", (bbox[2] - bbox[0] + pad * 2, bbox[3] - bbox[1] + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(image).text((pad - bbox[0], pad - bbox[1]), text, font=font, fill=(255, 255, 255, 255))
    return image


def draw_script_centred(c: Canvas, text: str, y: float, size_pt: float, max_width: float) -> None:
    image = rendered_script(text, size_pt)
    width = image.width * 72 / 600
    height = image.height * 72 / 600
    if width > max_width:
        scale = max_width / width
        width *= scale
        height *= scale
    c.drawImage(ImageReader(image), (PAGE_W - width) / 2, y, width=width, height=height, mask="auto")


def draw_arch_frame(c: Canvas, inset: float, line_width: float) -> None:
    x0 = inset
    x1 = PAGE_W - inset
    y0 = inset
    shoulder = 144 * mm
    apex = PAGE_H - inset
    mid = PAGE_W / 2

    p = c.beginPath()
    p.moveTo(x0, y0)
    p.lineTo(x0, shoulder)
    p.curveTo(x0, 178 * mm, 28 * mm, apex, mid, apex)
    p.curveTo(PAGE_W - 28 * mm, apex, x1, 178 * mm, x1, shoulder)
    p.lineTo(x1, y0)
    p.close()
    c.setLineWidth(line_width)
    c.drawPath(p, stroke=1, fill=0)


def draw_flourish(c: Canvas) -> None:
    top = monochrome_asset(str(TOP_FLORAL))
    top_w = 35 * mm
    top_h = top_w * top.height / top.width
    c.drawImage(ImageReader(top), (PAGE_W - top_w) / 2, 181.8 * mm, width=top_w, height=top_h, mask="auto")

    corner = monochrome_asset(str(CORNER_FLORAL))
    corner_h = 43 * mm
    corner_w = corner_h * corner.width / corner.height
    c.saveState()
    c.setFillAlpha(0.82)
    c.drawImage(ImageReader(corner), PAGE_W - 11 * mm - corner_w, 9.5 * mm, width=corner_w, height=corner_h, mask="auto")
    c.restoreState()


def draw_section(c: Canvas, heading: str, items: list[str | tuple[str, str]], heading_y: float) -> float:
    draw_spaced_centred(c, heading.upper(), heading_y, 9.2, 2.05)
    y = heading_y - 8.1 * mm
    c.setFont("Oranienbaum", 12.2)
    for item in items:
        if isinstance(item, tuple):
            title, descriptor = item
            c.setFont("Oranienbaum", 12.2)
            c.drawCentredString(PAGE_W / 2, y, title)
            y -= 4.5 * mm
            c.setFont("Oranienbaum", 9.4)
            c.drawCentredString(PAGE_W / 2, y, descriptor)
            y -= 5.6 * mm
        else:
            c.setFont("Oranienbaum", 12.2)
            c.drawCentredString(PAGE_W / 2, y, item)
            y -= 6.3 * mm
    return y


def build_pdf() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    register_fonts()

    c = Canvas(str(OUTPUT), pagesize=A5, pageCompression=1)
    c.setTitle("Wedding Menu - Jack and Tlhompho")
    c.setAuthor("Jack and Tlhompho")
    c.setSubject("A5 wedding menu")

    background = Image.open(BACKGROUND_TEXTURE).convert("RGB")
    c.drawImage(ImageReader(background), 0, 0, width=PAGE_W, height=PAGE_H, mask="auto")
    c.setStrokeColor(white)
    c.setFillColor(white)

    draw_arch_frame(c, 7.5 * mm, 0.7)
    draw_arch_frame(c, 9.8 * mm, 0.3)
    draw_flourish(c)

    draw_script_centred(c, "Menu", 151.5 * mm, 47, 72 * mm)
    c.setLineWidth(0.45)
    c.line(PAGE_W / 2 - 14 * mm, 148.8 * mm, PAGE_W / 2 + 14 * mm, 148.8 * mm)

    y = draw_section(c, "Mains", ["White Rice", "Fried Rice", "Creamy Samp", "Bogobe jwa Lerotse"], 137.3 * mm)
    y = draw_section(c, "Meats", ["Fried Chicken", "Beef Stew", "Seswaa"], y - 3.1 * mm)
    y = draw_section(c, "Salads", ["Beetroot", "Chakalaka", "Coleslaw", "Butternut"], y - 3.1 * mm)
    c.setFont("Oranienbaum", 12.2)
    c.drawCentredString(PAGE_W / 2, y - 3.1 * mm, "Soup")

    draw_spaced_centred(c, "J & T", 15.5 * mm, 7.6, 1.5)
    c.showPage()
    c.save()


if __name__ == "__main__":
    build_pdf()
    print(f"Created {OUTPUT}")
