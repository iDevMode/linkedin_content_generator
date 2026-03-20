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

# Dimensions (LinkedIn carousel optimal — 4:5 portrait)
SLIDE_WIDTH = 1080
SLIDE_HEIGHT = 1350
PADDING_LEFT = 80
PADDING_RIGHT = 120  # Extra right padding for LinkedIn nav arrow overlay
PADDING_TOP = 120    # Safe zone for status bar / LinkedIn header
PADDING_BOTTOM = 160  # Safe zone for LinkedIn profile overlay / page counter

# Progress bar settings
PROGRESS_BAR_HEIGHT = 4
PROGRESS_BAR_Y = 50  # Top of slide, within top safe zone
PROGRESS_BAR_MARGIN = 80

# Font paths
FONT_DIR = Path("assets/fonts")
FONTS = {
    "headline": FONT_DIR / "PlayfairDisplay-Bold.ttf",
    "headline_italic": FONT_DIR / "PlayfairDisplay-BoldItalic.ttf",
    "body": FONT_DIR / "Inter-Regular.ttf",
    "body_bold": FONT_DIR / "Inter-Bold.ttf",
}


def content_width() -> int:
    """Usable content width between left and right padding."""
    return SLIDE_WIDTH - PADDING_LEFT - PADDING_RIGHT


def load_fonts() -> Dict[str, Dict[int, ImageFont.FreeTypeFont]]:
    """Load Playfair Display + Inter from assets/fonts/ at multiple sizes."""
    loaded = {}

    for name, path in FONTS.items():
        loaded[name] = {}
        if path.exists():
            for size in [24, 28, 32, 36, 40, 48, 56, 64, 72, 80]:
                loaded[name][size] = ImageFont.truetype(str(path), size)
        else:
            print(f"[WARN] Font not found: {path} — using default", file=sys.stderr)
            for size in [24, 28, 32, 36, 40, 48, 56, 64, 72, 80]:
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


def measure_wrapped_text(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    line_spacing: float = 1.3,
) -> Tuple[List[str], int]:
    """Measure wrapped text height without drawing. Returns (lines, total_height)."""
    avg_char_width = font.getlength("M")
    chars_per_line = max(1, int(max_width / avg_char_width))
    lines = textwrap.wrap(text, width=chars_per_line)

    total_height = 0
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        line_height = bbox[3] - bbox[1]
        if i < len(lines) - 1:
            total_height += int(line_height * line_spacing)
        else:
            total_height += line_height
    return lines, total_height


def draw_text_wrapped(
    draw: ImageDraw.Draw,
    text: str,
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    max_width: int,
    fill: str,
    line_spacing: float = 1.3,
    align: str = "left",
) -> int:
    """Draw wrapped text and return the Y position after the last line.

    align: 'left', 'center', or 'right'
    """
    avg_char_width = font.getlength("M")
    chars_per_line = max(1, int(max_width / avg_char_width))
    lines = textwrap.wrap(text, width=chars_per_line)

    current_y = y
    for line in lines:
        if align == "center":
            line_w = font.getlength(line)
            line_x = x + (max_width - line_w) / 2
        elif align == "right":
            line_w = font.getlength(line)
            line_x = x + max_width - line_w
        else:
            line_x = x
        draw.text((line_x, current_y), line, font=font, fill=fill)
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
    """Add progress bar, Nukode watermark, slide counter, and subtle border."""
    w, h = img.size

    # Subtle border
    draw.rectangle(
        [2, 2, w - 3, h - 3],
        outline=COLOR_CARD_BORDER,
        width=1,
    )

    # Progress bar at top — shows swipe progression
    bar_total_width = w - 2 * PROGRESS_BAR_MARGIN
    segment_gap = 6
    segment_width = (bar_total_width - (total - 1) * segment_gap) / total

    for i in range(total):
        seg_x = PROGRESS_BAR_MARGIN + i * (segment_width + segment_gap)
        seg_color = COLOR_ACCENT if i < slide_num else COLOR_SUBTLE
        draw.rounded_rectangle(
            [seg_x, PROGRESS_BAR_Y, seg_x + segment_width, PROGRESS_BAR_Y + PROGRESS_BAR_HEIGHT],
            radius=2,
            fill=seg_color,
        )

    # Slide counter — bottom-right (inside safe zone)
    counter_font = fonts["body"].get(28, ImageFont.load_default())
    counter_text = f"{slide_num}/{total}"
    bbox = counter_font.getbbox(counter_text)
    text_width = bbox[2] - bbox[0]
    draw.text(
        (w - PADDING_RIGHT - text_width, h - PADDING_BOTTOM + 20),
        counter_text,
        font=counter_font,
        fill=COLOR_SUBTLE,
    )

    # Nukode watermark — bottom-left (inside safe zone)
    watermark_font = fonts["body"].get(28, ImageFont.load_default())
    draw.text(
        (PADDING_LEFT, h - PADDING_BOTTOM + 20),
        "<> Nukode",
        font=watermark_font,
        fill=COLOR_SUBTLE,
    )


def render_hook_slide(content: Dict, fonts: Dict, total_slides: int) -> Image.Image:
    """Render slide 1: large serif headline with accent underline, centered."""
    img = create_slide_base()
    draw = ImageDraw.Draw(img)

    headline = content.get("headline", "")
    subtext = content.get("subtext", "")
    cw = content_width()

    headline_font = fonts["headline"].get(64, ImageFont.load_default())
    subtext_font = fonts["body"].get(32, ImageFont.load_default())

    # Measure total content height to center vertically
    _, headline_h = measure_wrapped_text(headline, headline_font, cw, 1.2)
    accent_top_h = 40 + 4  # gap + line width
    accent_bottom_h = 20 + 3  # gap + line width
    subtext_h = 0
    subtext_gap = 0
    if subtext:
        _, subtext_h = measure_wrapped_text(subtext, subtext_font, cw, 1.3)
        subtext_gap = 50

    total_h = accent_top_h + headline_h + accent_bottom_h + subtext_gap + subtext_h
    available_h = SLIDE_HEIGHT - PADDING_TOP - PADDING_BOTTOM
    content_area_top = PADDING_TOP + (available_h - total_h) // 2

    # Gold accent line above headline
    accent_y = content_area_top
    accent_line_x = (SLIDE_WIDTH - 120) // 2
    draw.line(
        [(accent_line_x, accent_y), (accent_line_x + 120, accent_y)],
        fill=COLOR_ACCENT,
        width=4,
    )

    # Headline — centered
    headline_y = accent_y + accent_top_h
    y_after = draw_text_wrapped(
        draw, headline, headline_font,
        PADDING_LEFT, headline_y,
        cw,
        COLOR_WHITE,
        line_spacing=1.2,
        align="center",
    )

    # Gold accent underline below headline
    underline_x = (SLIDE_WIDTH - 200) // 2
    draw.line(
        [(underline_x, y_after + 20), (underline_x + 200, y_after + 20)],
        fill=COLOR_ACCENT,
        width=3,
    )

    # Subtext — centered
    if subtext:
        draw_text_wrapped(
            draw, subtext, subtext_font,
            PADDING_LEFT, y_after + 50,
            cw,
            COLOR_BODY,
            align="center",
        )

    add_branding(img, draw, fonts, 1, total_slides)
    return img


def render_content_slide(
    content: Dict, fonts: Dict, slide_num: int, total_slides: int
) -> Image.Image:
    """Render insight/content slide with headline + body + optional data point, centered."""
    img = create_slide_base()
    draw = ImageDraw.Draw(img)

    headline = content.get("headline", "")
    body = content.get("body", "")
    data_point = content.get("data_point", "")
    cw = content_width()

    num_font = fonts["headline"].get(40, ImageFont.load_default())
    headline_font = fonts["headline"].get(48, ImageFont.load_default())
    body_font = fonts["body"].get(32, ImageFont.load_default())
    data_font = fonts["body_bold"].get(32, ImageFont.load_default())

    # Measure total content height
    num_text = f"0{slide_num}" if slide_num < 10 else str(slide_num)
    num_bbox = num_font.getbbox(num_text)
    num_h = num_bbox[3] - num_bbox[1]

    divider_gap = 70 + 3 + 30  # num spacing + divider + gap
    _, headline_h = measure_wrapped_text(headline, headline_font, cw, 1.25)
    headline_gap = 30

    data_h = 0
    if data_point:
        data_h = 110 + 30  # card height + gap

    body_h = 0
    if body:
        _, body_h = measure_wrapped_text(body, body_font, cw, 1.5)

    total_h = num_h + divider_gap + headline_h + headline_gap + data_h + body_h
    available_h = SLIDE_HEIGHT - PADDING_TOP - PADDING_BOTTOM
    content_y = PADDING_TOP + (available_h - total_h) // 2

    # Slide number with accent color — centered
    num_w = num_font.getlength(num_text)
    draw.text(
        ((SLIDE_WIDTH - num_w) // 2, content_y),
        num_text,
        font=num_font,
        fill=COLOR_ACCENT,
    )
    content_y += 70

    # Gold divider — centered
    draw.line(
        [((SLIDE_WIDTH - 60) // 2, content_y), ((SLIDE_WIDTH + 60) // 2, content_y)],
        fill=COLOR_ACCENT,
        width=3,
    )
    content_y += 30

    # Headline — centered
    content_y = draw_text_wrapped(
        draw, headline, headline_font,
        PADDING_LEFT, content_y,
        cw,
        COLOR_WHITE,
        line_spacing=1.25,
        align="center",
    )
    content_y += 30

    # Data point highlight (if present)
    if data_point:
        card_left = PADDING_LEFT
        card_right = SLIDE_WIDTH - PADDING_RIGHT
        card_top = content_y
        card_bottom = content_y + 110

        draw.rounded_rectangle(
            [card_left, card_top, card_right, card_bottom],
            radius=12,
            fill=COLOR_CARD,
            outline=COLOR_CARD_BORDER,
        )

        draw_text_wrapped(
            draw, data_point, data_font,
            card_left + 24, card_top + 20,
            (card_right - card_left) - 48,
            COLOR_ACCENT,
            align="center",
        )
        content_y = card_bottom + 30

    # Body text — centered
    if body:
        draw_text_wrapped(
            draw, body, body_font,
            PADDING_LEFT, content_y,
            cw,
            COLOR_BODY,
            line_spacing=1.5,
            align="center",
        )

    add_branding(img, draw, fonts, slide_num, total_slides)
    return img


def render_data_slide(
    content: Dict, fonts: Dict, slide_num: int, total_slides: int
) -> Image.Image:
    """Render a data-focused slide with large data point + context, centered."""
    img = create_slide_base()
    draw = ImageDraw.Draw(img)

    headline = content.get("headline", "")
    data_point = content.get("data_point", "")
    body = content.get("body", "")
    cw = content_width()

    data_font = fonts["headline"].get(72, ImageFont.load_default())
    headline_font = fonts["headline"].get(48, ImageFont.load_default())
    body_font = fonts["body"].get(32, ImageFont.load_default())

    # Measure total height
    total_h = 0
    data_point_h = 0
    if data_point:
        _, data_point_h = measure_wrapped_text(data_point, data_font, cw, 1.2)
        total_h += data_point_h + 40

    _, headline_h = measure_wrapped_text(headline, headline_font, cw, 1.3)
    total_h += headline_h + 30

    body_h = 0
    if body:
        _, body_h = measure_wrapped_text(body, body_font, cw, 1.3)
        total_h += body_h

    available_h = SLIDE_HEIGHT - PADDING_TOP - PADDING_BOTTOM
    data_y = PADDING_TOP + (available_h - total_h) // 2

    # Large data point centered
    if data_point:
        data_y = draw_text_wrapped(
            draw, data_point, data_font,
            PADDING_LEFT, data_y,
            cw,
            COLOR_ACCENT,
            line_spacing=1.2,
            align="center",
        )
        data_y += 40

    # Headline — centered
    data_y = draw_text_wrapped(
        draw, headline, headline_font,
        PADDING_LEFT, data_y,
        cw,
        COLOR_WHITE,
        align="center",
    )
    data_y += 30

    # Body — centered
    if body:
        draw_text_wrapped(
            draw, body, body_font,
            PADDING_LEFT, data_y,
            cw,
            COLOR_BODY,
            align="center",
        )

    add_branding(img, draw, fonts, slide_num, total_slides)
    return img


def render_cta_slide(content: Dict, fonts: Dict, total_slides: int) -> Image.Image:
    """Render final CTA slide with Nukode branding, fully centered."""
    img = create_slide_base()
    draw = ImageDraw.Draw(img)

    headline = content.get("headline", "")
    subtext = content.get("subtext", "Follow Nukode for more AI automation insights")
    cw = content_width()

    headline_font = fonts["headline"].get(56, ImageFont.load_default())
    subtext_font = fonts["body"].get(32, ImageFont.load_default())
    brand_font = fonts["body_bold"].get(36, ImageFont.load_default())
    site_font = fonts["body"].get(28, ImageFont.load_default())

    # Measure total content height
    accent_h = 4 + 40  # bar + gap
    _, headline_h = measure_wrapped_text(headline, headline_font, cw, 1.2)
    subtext_gap = 40
    _, subtext_h = measure_wrapped_text(subtext, subtext_font, cw, 1.3)
    brand_gap = 60
    brand_bbox = brand_font.getbbox("<> Nukode")
    brand_h = brand_bbox[3] - brand_bbox[1]
    site_gap = 10
    site_bbox = site_font.getbbox("nukode.co.uk")
    site_h = site_bbox[3] - site_bbox[1]

    total_h = accent_h + headline_h + subtext_gap + subtext_h + brand_gap + brand_h + site_gap + site_h
    available_h = SLIDE_HEIGHT - PADDING_TOP - PADDING_BOTTOM
    start_y = PADDING_TOP + (available_h - total_h) // 2

    # Gold accent bar — centered
    bar_width = 80
    bar_x = (SLIDE_WIDTH - bar_width) // 2
    draw.line(
        [(bar_x, start_y), (bar_x + bar_width, start_y)],
        fill=COLOR_ACCENT,
        width=4,
    )
    current_y = start_y + accent_h

    # Headline — centered
    current_y = draw_text_wrapped(
        draw, headline, headline_font,
        PADDING_LEFT, current_y,
        cw,
        COLOR_WHITE,
        line_spacing=1.2,
        align="center",
    )
    current_y += subtext_gap

    # Subtext — centered
    current_y = draw_text_wrapped(
        draw, subtext, subtext_font,
        PADDING_LEFT, current_y,
        cw,
        COLOR_ACCENT,
        align="center",
    )
    current_y += brand_gap

    # Nukode brand mark — centered
    brand_text = "<> Nukode"
    brand_w = brand_font.getlength(brand_text)
    brand_x = (SLIDE_WIDTH - brand_w) // 2
    draw.text((brand_x, current_y), brand_text, font=brand_font, fill=COLOR_ACCENT)
    current_y += brand_h + site_gap

    # Website — centered
    site_text = "nukode.co.uk"
    site_w = site_font.getlength(site_text)
    site_x = (SLIDE_WIDTH - site_w) // 2
    draw.text((site_x, current_y), site_text, font=site_font, fill=COLOR_BODY)

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
