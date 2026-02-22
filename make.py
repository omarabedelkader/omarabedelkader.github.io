#!/usr/bin/env python3
"""
Generate:
- a QR code (PNG)
- a simple business card (PNG + print-ready PDF)

Defaults:
- European business card size: 85 x 55 mm :contentReference[oaicite:1]{index=1}
- Creates outputs for BOTH URLs you provided.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw, ImageFont

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm


# ---------------------------
# Config
# ---------------------------

EU_CARD_W_MM = 85
EU_CARD_H_MM = 55


@dataclass(frozen=True)
class CardInfo:
    name: str
    headline: str
    organization: str
    website: str


def mm_to_px(value_mm: float, dpi: int) -> int:
    return int(round((value_mm / 25.4) * dpi))


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Try common system fonts; fall back to PIL default.
    candidates = []
    if bold:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf",
        ]
    else:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/Library/Fonts/Arial.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]

    for p in candidates:
        try:
            return ImageFont.truetype(p, size=size)
        except Exception:
            continue

    return ImageFont.load_default()


def make_qr_image(url: str, target_px: int, border: int = 4) -> Image.Image:
    """
    Create a crisp QR code near target_px without blurry scaling:
    pick a box_size that fits the QR module grid, then pad if needed.
    """
    # First pass to learn the module count (depends on content/version).
    tmp = qrcode.QRCode(error_correction=ERROR_CORRECT_H, border=border)
    tmp.add_data(url)
    tmp.make(fit=True)
    modules = tmp.modules_count
    total_modules = modules + 2 * border

    box_size = max(1, target_px // total_modules)

    qr = qrcode.QRCode(
        error_correction=ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # Pad (center) to exactly target_px if slightly smaller.
    if img.size[0] < target_px:
        padded = Image.new("RGB", (target_px, target_px), "white")
        off = (target_px - img.size[0]) // 2
        padded.paste(img, (off, off))
        img = padded
    elif img.size[0] > target_px:
        # Rare fallback: resize with nearest-neighbor.
        img = img.resize((target_px, target_px), Image.NEAREST)

    return img


def wrap_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width_px: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []

    for w in words:
        trial = (" ".join(cur + [w])).strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] <= max_width_px or not cur:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]

    if cur:
        lines.append(" ".join(cur))
    return lines


def render_business_card_png(info: CardInfo, out_png: Path, out_qr_png: Path, dpi: int, qr_mm: float) -> None:
    w_px = mm_to_px(EU_CARD_W_MM, dpi)
    h_px = mm_to_px(EU_CARD_H_MM, dpi)

    margin_px = mm_to_px(3.0, dpi)
    gap_px = mm_to_px(3.0, dpi)
    qr_px = mm_to_px(qr_mm, dpi)

    card = Image.new("RGB", (w_px, h_px), "white")
    draw = ImageDraw.Draw(card)

    # Fonts
    name_font = load_font(size=mm_to_px(4.2, dpi), bold=True)   # ~ 12–14pt at 300dpi equivalent
    main_font = load_font(size=mm_to_px(2.6, dpi), bold=False)
    small_font = load_font(size=mm_to_px(2.2, dpi), bold=False)

    # QR (right side)
    qr_img = make_qr_image(info.website, target_px=qr_px)
    out_qr_png.parent.mkdir(parents=True, exist_ok=True)
    qr_img.save(out_qr_png)

    qr_x = w_px - margin_px - qr_px
    qr_y = (h_px - qr_px) // 2
    card.paste(qr_img, (qr_x, qr_y))

    # Text area (left side)
    text_x = margin_px
    text_top = margin_px
    text_w = (qr_x - gap_px) - text_x

    # Name
    y = text_top
    draw.text((text_x, y), info.name, font=name_font, fill="black")
    y += int(name_font.size * 1.35)

    # Headline (wrap if needed)
    for line in wrap_to_width(draw, info.headline, main_font, text_w):
        draw.text((text_x, y), line, font=main_font, fill="black")
        y += int(main_font.size * 1.45)

    # Organization
    y += int(main_font.size * 0.3)
    for line in wrap_to_width(draw, info.organization, main_font, text_w):
        draw.text((text_x, y), line, font=main_font, fill="black")
        y += int(main_font.size * 1.45)

    # Website (small)
    y = h_px - margin_px - int(small_font.size * 1.2)
    website_lines = wrap_to_width(draw, info.website, small_font, text_w)
    # keep last line at bottom; draw upward if it wraps
    y = h_px - margin_px - len(website_lines) * int(small_font.size * 1.25)
    for line in website_lines:
        draw.text((text_x, y), line, font=small_font, fill="black")
        y += int(small_font.size * 1.25)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    # Embed DPI metadata for print workflows
    card.save(out_png, dpi=(dpi, dpi))


def render_business_card_pdf(info: CardInfo, out_pdf: Path, qr_img: Image.Image, qr_mm: float) -> None:
    w_pt = EU_CARD_W_MM * mm
    h_pt = EU_CARD_H_MM * mm
    margin = 3.0 * mm
    gap = 3.0 * mm

    qr_size = qr_mm * mm
    qr_x = w_pt - margin - qr_size
    qr_y = (h_pt - qr_size) / 2.0

    c = canvas.Canvas(str(out_pdf), pagesize=(w_pt, h_pt))

    # QR: ReportLab can place a PIL Image directly (drawInlineImage). :contentReference[oaicite:2]{index=2}
    c.drawInlineImage(qr_img, qr_x, qr_y, width=qr_size, height=qr_size)

    text_x = margin
    text_w = (qr_x - gap) - text_x

    # Simple text layout (no fancy wrapping in PDF; keep strings short)
    c.setFillColorRGB(0, 0, 0)

    y = h_pt - margin
    c.setFont("Helvetica-Bold", 12)
    c.drawString(text_x, y - 12, info.name)

    c.setFont("Helvetica", 9.5)
    c.drawString(text_x, y - 28, info.headline)

    c.drawString(text_x, y - 42, info.organization)

    c.setFont("Helvetica", 8.5)
    c.drawString(text_x, margin, info.website[:80])  # avoid overflow

    c.showPage()
    c.save()


def build_outputs(label: str, info: CardInfo, out_dir: Path, dpi: int, qr_mm: float) -> None:
    out_png = out_dir / f"business_card_{label}.png"
    out_pdf = out_dir / f"business_card_{label}.pdf"
    out_qr = out_dir / f"qr_{label}.png"

    render_business_card_png(info, out_png, out_qr, dpi=dpi, qr_mm=qr_mm)

    # Reuse the same QR image for the PDF
    qr_px = mm_to_px(qr_mm, dpi)
    qr_img = make_qr_image(info.website, target_px=qr_px)
    render_business_card_pdf(info, out_pdf, qr_img=qr_img, qr_mm=qr_mm)

    print(f"[OK] {label}:")
    print(f"  - {out_qr}")
    print(f"  - {out_png}")
    print(f"  - {out_pdf}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate QR code + business card (PNG + PDF).")
    parser.add_argument("--out", default="out_card", help="Output folder")
    parser.add_argument("--dpi", type=int, default=300, help="PNG DPI (print quality)")
    parser.add_argument("--qr-mm", type=float, default=24.0, help="QR code size on card in mm")

    parser.add_argument("--name", default="Omar AbedelKader")
    parser.add_argument("--headline", default="AI Researcher • Ph.D. Candidate")
    parser.add_argument("--org", default="University of Lille")

    parser.add_argument(
        "--mode",
        choices=["both", "github", "domain"],
        default="both",
        help="Which URL(s) to generate cards for",
    )

    args = parser.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    github_url = "https://omarabedelkader.github.io"
    domain_url = "http://www.omarabedelkader.com"

    if args.mode in ("both", "github"):
        info = CardInfo(
            name=args.name,
            headline=args.headline,
            organization=args.org,
            website=github_url,
        )
        build_outputs("github", info, out_dir, dpi=args.dpi, qr_mm=args.qr_mm)

    if args.mode in ("both", "domain"):
        info = CardInfo(
            name=args.name,
            headline=args.headline,
            organization=args.org,
            website=domain_url,
        )
        build_outputs("domain", info, out_dir, dpi=args.dpi, qr_mm=args.qr_mm)


if __name__ == "__main__":
    main()