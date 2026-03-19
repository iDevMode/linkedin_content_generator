#!/usr/bin/env python3
"""
Branded Carousel Image Generator for LinkedIn Posts.

Programmatically generates carousel slide images using Pillow with Nukode's
brand guidelines. More reliable than AI image generation for precise text
placement and brand consistency.

Brand: Dark premium aesthetic — dark backgrounds (#1A1A1A), white serif
headlines (Playfair Display), gray sans-serif body (Inter), gold accents (#C4A35A).

Usage:
  python execution/generate_carousel_images.py '{"content_file": ".tmp/carousel_content.json"}'
  python execution/generate_carousel_images.py '{"content_file": ".tmp/carousel_content.json", "output_dir": ".tmp/carousel_output"}'
"""

import json
import math
import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

# Brand colors
COLOR_BG = "#1A1A1A"
COLOR_CARD = "#1C1C1C"
COLOR_CARD_BORDER = "#2A2A2A"
COLOR_WHITE = "#FFFFFF"
COLOR_BODY = "#9B9B9B"
COLOR_ACCENT = "#C4A35A"
COLOR_SUBTLE = "#444444"

# Dimensions (LinkedIn carousel optimal)
SLIDE_WIDTH = 1080
SLIDE_HEIGHT = 1350
PADDING_X = 80
PADDING_TOP = 100
PADDING_BOTTOM = 100

# Font paths
FONT_DIR = Path("assets/fonts")
FONTS = {
    "headline": FONT_DIR / "PlayfairDisplay-Bold.ttf",
    "headline_italic": FONT_DIR / "PlayfairDisplay-BoldItalic.ttf",
    "body": FONT_DIR / "Inter-Regular.ttf",
    "body_bold": FONT_DIR / "Inter-Bold.ttf",
}


def load_fonts() -> Dict[str, Dict[int, ImageFont.FreeTypeFont]]:
    """Load Playfair Display + Inter from assets/fonts/ at multiple sizes."""
    loaded = {}

    for name, path in FONTS.items():
        loaded[name] = {}
        if path.exists():
            for size in [32, 36, 40, 48, 56, 64, 72, 80]:
                loaded[name][size] = ImageFont.truetype(str(path), size)
        else:
            print(f"[WARN] Font not found: {path} — using default", file=sys.stderr)
            for size in [32, 36, 40, 48, 56, 64, 72, 80]:
                loaded[name][size] = ImageFont.load_default()

    return loaded


def create_slide_base(width: int = SLIDE_WIDTH, height: int = SLIDE_HEIGHT) -> Image.Image:
    """Create dark background with subtle radial gradient."""
    img = Image.new("RGB", (width, height), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Subtle radial gradient from center — slight lightening
    cx, cy = width // 2, height // 2
    max_radius = math.sqrt(cx**2 + cy**2)

    for r in range(0, int(max_radius), 4):
        factor = 1.0 - (r / max_radius) * 0.3
        gray = int(26 * (1 + factor * 0.08))  # Very subtle
        gray = min(gray, 30)
        color = (gray, gray, gray)
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=color,
        )

    return img


def draw_text_wrapped(
    draw: ImageDraw.Draw,
    text: str,
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    max_width: int,
    fill: str,
    line_spacing: float = 1.3,
) -> int:
    """Draw wrapped text and return the Y position after the last line."""
    # Estimate characters per line
    avg_char_width = font.getlength("M")
    chars_per_line = max(1, int(max_width / avg_char_width))
    lines = textwrap.wrap(text, width=chars_per_line)

    current_y = y
    for line in lines:
        draw.text((x, current_y), line, font=font, fill=fill)
        bbox = font.getbbox(line)
        line_height = bbox[3] - bbox[1]
        current_y += int(line_height * line_spacing)

    return current_y


def add_branding(
    img: Image.Image,
    draw: ImageDraw.Draw,
    fonts: Dict,
    slide_num: int,
    total: int,
) -> None:
    """Add Nukode watermark, slide counter, and subtle border."""
    w, h = img.size

    # Subtle border
    draw.rectangle(
        [2, 2, w - 3, h - 3],
        outline=COLOR_CARD_BORDER,
        width=1,
    )

    # Slide counter — bottom-right
    counter_font = fonts["body"].get(32, ImageFont.load_default())
    counter_text = f"{slide_num}/{total}"
    bbox = counter_font.getbbox(counter_text)
    text_width = bbox[2] - bbox[0]
    draw.text(
        (w - PADDING_X - text_width, h - PADDING_BOTTOM + 10),
        counter_text,
        font=counter_font,
        fill=COLOR_SUBTLE,
    )

    # Nukode watermark — bottom-left
    watermark_font = fonts["body"].get(32, ImageFont.load_default())
    draw.text(
        (PADDING_X, h - PADDING_BOTTOM + 10),
        "<> Nukode",
        font=watermark_font,
        fill=COLOR_SUBTLE,
    )


def render_hook_slide(content: Dict, fonts: Dict, total_slides: int) -> Image.Image:
    """Render slide 1: large serif headline with accent underline."""
    img = create_slide_base()
    draw = ImageDraw.Draw(img)

    headline = content.get("headline", "")
    subtext = content.get("subtext", "")

    # Center the headline vertically
    headline_font = fonts["headline"].get(72, ImageFont.load_default())
    content_area_top = SLIDE_HEIGHT // 3

    # Gold accent line above headline
    accent_y = content_area_top - 40
    draw.line(
        [(PADDING_X, accent_y), (PADDING_X + 120, accent_y)],
        fill=COLOR_ACCENT,
        width=4,
    )

    # Headline
    y_after = draw_text_wrapped(
        draw, headline, headline_font,
        PADDING_X, content_area_top,
        SLIDE_WIDTH - 2 * PADDING_X,
        COLOR_WHITE,
        line_spacing=1.2,
    )

    # Gold accent underline below headline
    draw.line(
        [(PADDING_X, y_after + 20), (PADDING_X + 200, y_after + 20)],
        fill=COLOR_ACCENT,
        width=3,
    )

    # Subtext
    if subtext:
        subtext_font = fonts["body"].get(36, ImageFont.load_default())
        draw_text_wrapped(
            draw, subtext, subtext_font,
            PADDING_X, y_after + 50,
            SLIDE_WIDTH - 2 * PADDING_X,
            COLOR_BODY,
        )

    add_branding(img, draw, fonts, 1, total_slides)
    return img


def render_content_slide(
    content: Dict, fonts: Dict, slide_num: int, total_slides: int
) -> Image.Image:
    """Render insight/content slide with headline + body + optional data point."""
    img = create_slide_base()
    draw = ImageDraw.Draw(img)

    headline = content.get("headline", "")
    body = content.get("body", "")
    data_point = content.get("data_point", "")

    content_y = PADDING_TOP + 60

    # Slide number with accent color
    num_font = fonts["headline"].get(48, ImageFont.load_default())
    draw.text(
        (PADDING_X, content_y),
        f"0{slide_num}" if slide_num < 10 else str(slide_num),
        font=num_font,
        fill=COLOR_ACCENT,
    )
    content_y += 80

    # Gold divider
    draw.line(
        [(PADDING_X, content_y), (PADDING_X + 60, content_y)],
        fill=COLOR_ACCENT,
        width=3,
    )
    content_y += 30

    # Headline
    headline_font = fonts["headline"].get(56, ImageFont.load_default())
    content_y = draw_text_wrapped(
        draw, headline, headline_font,
        PADDING_X, content_y,
        SLIDE_WIDTH - 2 * PADDING_X,
        COLOR_WHITE,
        line_spacing=1.25,
    )
    content_y += 30

    # Data point highlight (if present)
    if data_point:
        # Card background for data point
        card_left = PADDING_X
        card_right = SLIDE_WIDTH - PADDING_X
        card_top = content_y
        card_bottom = content_y + 120

        draw.rounded_rectangle(
            [card_left, card_top, card_right, card_bottom],
            radius=12,
            fill=COLOR_CARD,
            outline=COLOR_CARD_BORDER,
        )

        data_font = fonts["body_bold"].get(36, ImageFont.load_default())
        draw_text_wrapped(
            draw, data_point, data_font,
            card_left + 24, card_top + 20,
            (card_right - card_left) - 48,
            COLOR_ACCENT,
        )
        content_y = card_bottom + 30

    # Body text
    if body:
        body_font = fonts["body"].get(36, ImageFont.load_default())
        draw_text_wrapped(
            draw, body, body_font,
            PADDING_X, content_y,
            SLIDE_WIDTH - 2 * PADDING_X,
            COLOR_BODY,
            line_spacing=1.5,
        )

    add_branding(img, draw, fonts, slide_num, total_slides)
    return img


def render_data_slide(
    content: Dict, fonts: Dict, slide_num: int, total_slides: int
) -> Image.Image:
    """Render a data-focused slide with large data point + context."""
    img = create_slide_base()
    draw = ImageDraw.Draw(img)

    headline = content.get("headline", "")
    data_point = content.get("data_point", "")
    body = content.get("body", "")

    # Large data point centered
    if data_point:
        data_font = fonts["headline"].get(80, ImageFont.load_default())
        data_y = SLIDE_HEIGHT // 3 - 40
        bbox = data_font.getbbox(data_point)
        text_w = bbox[2] - bbox[0]
        x_centered = max(PADDING_X, (SLIDE_WIDTH - text_w) // 2)
        draw.text((x_centered, data_y), data_point, font=data_font, fill=COLOR_ACCENT)
        data_y += (bbox[3] - bbox[1]) + 40
    else:
        data_y = SLIDE_HEIGHT // 3

    # Headline
    headline_font = fonts["headline"].get(48, ImageFont.load_default())
    data_y = draw_text_wrapped(
        draw, headline, headline_font,
        PADDING_X, data_y,
        SLIDE_WIDTH - 2 * PADDING_X,
        COLOR_WHITE,
    )
    data_y += 30

    # Body
    if body:
        body_font = fonts["body"].get(36, ImageFont.load_default())
        draw_text_wrapped(
            draw, body, body_font,
            PADDING_X, data_y,
            SLIDE_WIDTH - 2 * PADDING_X,
            COLOR_BODY,
        )

    add_branding(img, draw, fonts, slide_num, total_slides)
    return img


def render_cta_slide(content: Dict, fonts: Dict, total_slides: int) -> Image.Image:
    """Render final CTA slide with Nukode branding."""
    img = create_slide_base()
    draw = ImageDraw.Draw(img)

    headline = content.get("headline", "")
    subtext = content.get("subtext", "Follow Nukode for more AI automation insights")

    # Centered layout
    center_y = SLIDE_HEIGHT // 3

    # Gold accent bar
    bar_width = 80
    bar_x = (SLIDE_WIDTH - bar_width) // 2
    draw.line(
        [(bar_x, center_y - 40), (bar_x + bar_width, center_y - 40)],
        fill=COLOR_ACCENT,
        width=4,
    )

    # Headline
    headline_font = fonts["headline"].get(64, ImageFont.load_default())
    draw_text_wrapped(
        draw, headline, headline_font,
        PADDING_X, center_y,
        SLIDE_WIDTH - 2 * PADDING_X,
        COLOR_WHITE,
        line_spacing=1.2,
    )

    # Subtext
    subtext_font = fonts["body"].get(36, ImageFont.load_default())
    sub_y = center_y + 250
    draw_text_wrapped(
        draw, subtext, subtext_font,
        PADDING_X, sub_y,
        SLIDE_WIDTH - 2 * PADDING_X,
        COLOR_ACCENT,
    )

    # Nukode brand mark
    brand_font = fonts["body_bold"].get(40, ImageFont.load_default())
    brand_y = SLIDE_HEIGHT - PADDING_BOTTOM - 120
    brand_text = "<> Nukode"
    bbox = brand_font.getbbox(brand_text)
    brand_x = (SLIDE_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((brand_x, brand_y), brand_text, font=brand_font, fill=COLOR_ACCENT)

    # Website
    site_font = fonts["body"].get(32, ImageFont.load_default())
    site_text = "nukode.co.uk"
    bbox = site_font.getbbox(site_text)
    site_x = (SLIDE_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((site_x, brand_y + 60), site_text, font=site_font, fill=COLOR_BODY)

    add_branding(img, draw, fonts, total_slides, total_slides)
    return img


def generate_carousel(content_file: str, output_dir: Optional[str] = None) -> dict:
    """
    Generate all carousel slide images from content JSON.

    Args:
        content_file: Path to carousel_content.json.
        output_dir: Output directory for images. Auto-generated if not provided.

    Returns:
        dict with status, image paths, and PDF path.
    """
    content_path = Path(content_file)
    if not content_path.exists():
        return {"status": "error", "message": f"Content file not found: {content_file}"}

    content = json.loads(content_path.read_text())
    slides = content.get("slides", [])

    if not slides:
        return {"status": "error", "message": "No slides found in content file."}

    # Determine output directory
    if not output_dir:
        topic_slug = re.sub(r'[^a-z0-9]+', '_', content.get("topic", "carousel").lower())[:50]
        output_dir = f".tmp/carousel_{topic_slug}"

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load fonts
    fonts = load_fonts()

    total_slides = len(slides)
    image_paths = []

    print(f"[INFO] Generating {total_slides} carousel slides...", file=sys.stderr)

    for slide in slides:
        slide_num = slide.get("slide_num", 1)
        slide_type = slide.get("type", "insight")

        if slide_type == "hook":
            img = render_hook_slide(slide, fonts, total_slides)
        elif slide_type == "cta":
            img = render_cta_slide(slide, fonts, total_slides)
        elif slide_type == "data":
            img = render_data_slide(slide, fonts, slide_num, total_slides)
        else:
            img = render_content_slide(slide, fonts, slide_num, total_slides)

        filename = f"slide_{slide_num:02d}.png"
        filepath = output_path / filename
        img.save(str(filepath), "PNG", quality=95)
        image_paths.append(str(filepath))
        print(f"[INFO] Generated {filename}", file=sys.stderr)

    # Generate combined PDF
    pdf_path = str(output_path / "carousel.pdf")
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas

        # Use slide dimensions for PDF page size
        page_w = SLIDE_WIDTH * 0.75  # Points (72 per inch, roughly)
        page_h = SLIDE_HEIGHT * 0.75

        c = canvas.Canvas(pdf_path, pagesize=(page_w, page_h))
        for img_path in image_paths:
            c.drawImage(img_path, 0, 0, width=page_w, height=page_h)
            c.showPage()
        c.save()
        print(f"[INFO] Generated PDF: {pdf_path}", file=sys.stderr)
    except ImportError:
        print("[WARN] reportlab not installed — skipping PDF generation.", file=sys.stderr)
        pdf_path = None

    return {
        "status": "success",
        "data": {
            "slides_generated": total_slides,
            "image_paths": image_paths,
            "pdf_path": pdf_path,
            "output_dir": str(output_path),
        },
    }


def main(content_file: str, output_dir: Optional[str] = None) -> dict:
    """Main entry point."""
    return generate_carousel(content_file, output_dir)


if __name__ == "__main__":
    args = {}
    if len(sys.argv) > 1:
        try:
            args = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            print(f"[ERROR] Invalid JSON argument: {sys.argv[1]}", file=sys.stderr)
            sys.exit(1)

    content_file = args.get("content_file", ".tmp/carousel_content.json")
    output_dir = args.get("output_dir")

    result = main(content_file, output_dir)
    print(json.dumps(result, indent=2))
