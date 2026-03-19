# Generate LinkedIn Carousel — SOP

## Goal

Generate branded LinkedIn carousel posts about AI agents and agentic workflows to position Nukode as the authority in this space. The pipeline scrapes trending topics, generates structured slide content via Claude, and produces branded PNG/PDF images ready for LinkedIn upload.

## Inputs

- **Trending AI agent topics** — scraped from HackerNews, RSS feeds, and Reddit
- **Content style** — contrarian, framework, data, question, story, or education
- **Number of slides** — typically 6 (range: 4–10)
- **Brand assets** — Playfair Display + Inter fonts in `assets/fonts/`

## Tools / Scripts

| Script | Purpose |
|--------|---------|
| `execution/scrape_trending_topics.py` | Scrape and rank AI agent topics from multiple sources |
| `execution/generate_carousel_content.py` | Generate structured carousel content via Claude API |
| `execution/generate_carousel_images.py` | Generate branded PNG slide images + PDF |
| `execution/run_carousel_workflow.py` | Run the full pipeline end-to-end |

## Process Flow

### 1. Scrape Trending Topics

```bash
python execution/scrape_trending_topics.py
```

- Scrapes HackerNews (public API, no key needed), RSS feeds, and Reddit (needs API key)
- Filters for AI agent/agentic workflow relevance using keyword matching
- Scores by recency, engagement, and business relevance
- Deduplicates similar stories
- Outputs ranked list to `.tmp/trending_topics.json`

### 2. Generate Carousel Content

```bash
python execution/generate_carousel_content.py '{"topic_file": ".tmp/trending_topics.json", "topic_index": 0}'
```

- Takes the top-ranked topic (or specified index)
- Sends to Claude API with Nukode context and brand voice
- Generates structured JSON: hook slide, insight slides, CTA slide, LinkedIn caption
- Outputs to `.tmp/carousel_content.json`

### 3. Generate Carousel Images

```bash
python execution/generate_carousel_images.py '{"content_file": ".tmp/carousel_content.json"}'
```

- Renders each slide as a 1080×1350 PNG using Pillow
- Applies Nukode brand: dark background, white serif headlines, gray body, gold accents
- Adds branding (Nukode watermark, slide counter)
- Generates combined PDF for easy upload
- Outputs to `.tmp/carousel_{topic_slug}/`

### 4. Full Pipeline (Recommended)

```bash
python execution/run_carousel_workflow.py
python execution/run_carousel_workflow.py '{"topic_index": 2, "num_slides": 8, "style": "framework"}'
```

Options:
- `skip_scraping`: Reuse existing topics file (default: false)
- `topic_index`: Which topic to use (default: 0 = top-ranked)
- `num_slides`: Number of slides (default: 6)
- `style`: Content angle — contrarian, framework, data, question, story, education
- `output_format`: "png" or "pdf" (both are always generated)

## Outputs

| Output | Location |
|--------|----------|
| Trending topics | `.tmp/trending_topics.json` |
| Carousel content | `.tmp/carousel_content.json` |
| Slide images | `.tmp/carousel_{topic_slug}/slide_01.png` ... |
| Combined PDF | `.tmp/carousel_{topic_slug}/carousel.pdf` |

## Brand Guidelines

- **Background**: `#1A1A1A` with subtle radial gradient
- **Headlines**: Playfair Display Bold, white `#FFFFFF`, 64–80px
- **Body text**: Inter Regular, gray `#9B9B9B`, 32–40px
- **Accent**: Gold `#C4A35A` for dividers, highlights, numbering
- **Cards**: `#1C1C1C` backgrounds with `#2A2A2A` borders
- **Slide size**: 1080×1350px (LinkedIn carousel optimal)
- **Padding**: 80px sides, 100px top/bottom

## Edge Cases

- **No trending topics found**: The scraper may return 0 results if HackerNews/RSS have no AI agent content at scrape time. In this case, provide a manual topic via the `topic` parameter.
- **Reddit API keys missing**: Reddit scraping is skipped gracefully. HackerNews + RSS still work without any API keys.
- **Font files missing**: Falls back to Pillow's default font. Visual quality will be degraded — ensure fonts are downloaded first.
- **Claude API failure**: Content generation requires `ANTHROPIC_API_KEY`. Check `.env` file.
- **Very long headlines**: Text wrapping handles overflow, but manually review slides with headlines > 10 words.

## Learnings

- LinkedIn carousel optimal size is 1080×1350px (portrait format)
- Hook slide is the most important — determines scroll-stop rate
- Contrarian hooks ("Everyone thinks X, but actually Y") tend to perform best
- 6 slides is the sweet spot — enough to deliver value, short enough to retain attention
- Gold accent color on dark background creates premium feel and draws the eye
- Always end with a CTA slide that includes a clear follow/engage prompt
- Business-relevant AI stories (ROI, automation, case studies) outperform pure tech content on LinkedIn
