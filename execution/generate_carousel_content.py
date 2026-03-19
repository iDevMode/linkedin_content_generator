#!/usr/bin/env python3
"""
AI Content Generator for LinkedIn Carousel Posts.

Takes a trending AI agent topic and uses Claude API to generate structured
carousel slide content. Content is framed to position Nukode as the authority
on agentic workflows — educating businesses, sharing insights, and
demonstrating expertise.

Usage:
  python execution/generate_carousel_content.py '{"topic_file": ".tmp/trending_topics.json", "topic_index": 0}'
  python execution/generate_carousel_content.py '{"topic": "Multi-agent systems are replacing traditional SaaS workflows", "num_slides": 6}'
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import anthropic
from dotenv import load_dotenv

load_dotenv()

NUKODE_CONTEXT = """
You are a content strategist for Nukode (nukode.co.uk), a company that builds
agentic workflows and chatbots for businesses. Nukode is positioned as a leading
authority on AI agents, agentic workflows, and AI automation for business.

Nukode's expertise:
- Building custom AI agents and multi-agent systems for businesses
- Designing agentic workflows that automate complex business processes
- Developing intelligent chatbots that go beyond simple Q&A
- No-code/low-code AI automation solutions
- Measuring and delivering ROI from AI automation

Write from an authoritative but approachable perspective. Share genuine insights
and frameworks — not salesy pitches. The goal is to educate business leaders on
how agentic workflows solve real problems, making them want to learn more from
Nukode naturally.
""".strip()

CAROUSEL_PROMPT_TEMPLATE = """
{nukode_context}

Create a LinkedIn carousel post about this topic:
"{topic}"

Additional context (if available): {summary}

Style: {style}

Generate a {num_slides}-slide carousel with this structure:

Slide 1 (Hook): A bold, attention-grabbing headline that makes people stop scrolling.
  - Use the {style} approach for the hook
  - Keep it under 10 words
  - Add a short subtext (1 line) that creates curiosity

Slides 2-{mid_slide} (Content): Each slide should deliver ONE clear insight.
  - Short headline (under 8 words)
  - Body text (2-3 concise sentences)
  - Include a data point or specific example where possible
  - Each slide should build on the previous one

Slide {num_slides} (CTA): End with a call-to-action slide.
  - Headline that wraps up the key message
  - Subtext: "Follow Nukode for more AI automation insights"

Also generate a LinkedIn caption (the text that accompanies the post):
  - 3-5 short paragraphs
  - Start with a hook line that mirrors the carousel's opening
  - End with a question to drive engagement
  - Include 5-8 relevant hashtags at the end

Content angle guidelines by style:
- contrarian: Challenge a popular belief. "Everyone thinks X, but actually Y"
- framework: Present a structured approach. "The N-step framework for X"
- data: Lead with a compelling statistic or ROI figure
- question: Open with a provocative question that the carousel answers
- story: Share a specific scenario/case study of AI agents solving a problem
- education: Explain a concept clearly with comparisons and examples

Respond in this exact JSON format (no markdown, no code blocks, just raw JSON):
{{
  "topic": "{topic}",
  "hook_type": "{style}",
  "linkedin_caption": "...",
  "slides": [
    {{"slide_num": 1, "type": "hook", "headline": "...", "subtext": "..."}},
    {{"slide_num": 2, "type": "insight", "headline": "...", "body": "...", "data_point": "..."}},
    {{"slide_num": 3, "type": "insight", "headline": "...", "body": "...", "data_point": "..."}},
    ...
    {{"slide_num": {num_slides}, "type": "cta", "headline": "...", "subtext": "Follow Nukode for more AI automation insights"}}
  ]
}}
"""

HOOK_STYLES = ["contrarian", "framework", "data", "question", "story", "education"]


def generate_carousel(
    topic: Dict,
    num_slides: int = 6,
    style: str = "contrarian",
) -> Dict:
    """
    Generate structured carousel content using Claude API.

    Args:
        topic: Dict with at least 'title' key, optionally 'summary'.
        num_slides: Number of slides (4-10).
        style: Hook style — one of contrarian, framework, data, question, story, education.

    Returns:
        Dict with carousel content (slides, caption, metadata).
    """
    if style not in HOOK_STYLES:
        style = "contrarian"

    num_slides = max(4, min(10, num_slides))
    mid_slide = num_slides - 1

    topic_title = topic.get("title", topic) if isinstance(topic, dict) else str(topic)
    topic_summary = topic.get("summary", "") if isinstance(topic, dict) else ""

    prompt = CAROUSEL_PROMPT_TEMPLATE.format(
        nukode_context=NUKODE_CONTEXT,
        topic=topic_title,
        summary=topic_summary or "No additional context.",
        style=style,
        num_slides=num_slides,
        mid_slide=mid_slide,
    )

    client = anthropic.Anthropic()

    print(f"[INFO] Generating carousel content for: {topic_title}", file=sys.stderr)
    print(f"[INFO] Style: {style}, Slides: {num_slides}", file=sys.stderr)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    # Parse JSON from response — handle potential markdown wrapping
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    try:
        carousel_content = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            carousel_content = json.loads(json_match.group())
        else:
            raise ValueError(f"Failed to parse carousel JSON from Claude response: {response_text[:200]}")

    # Add metadata
    carousel_content["metadata"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "claude-sonnet-4-20250514",
        "style": style,
        "num_slides": num_slides,
        "source_topic": topic if isinstance(topic, dict) else {"title": topic},
    }

    return carousel_content


def main(
    topic_file: Optional[str] = None,
    topic_index: int = 0,
    topic: Optional[str] = None,
    num_slides: int = 6,
    style: str = "contrarian",
    output_file: Optional[str] = None,
) -> dict:
    """
    Generate carousel content from a topic file or direct topic string.

    Args:
        topic_file: Path to trending_topics.json.
        topic_index: Index of topic to use from the file.
        topic: Direct topic string (overrides topic_file).
        num_slides: Number of slides.
        style: Hook style.
        output_file: Custom output path.

    Returns:
        dict with status and carousel data.
    """
    # Resolve topic
    if topic:
        topic_data = {"title": topic, "summary": ""}
    elif topic_file:
        topics_path = Path(topic_file)
        if not topics_path.exists():
            return {"status": "error", "message": f"Topic file not found: {topic_file}"}

        topics_json = json.loads(topics_path.read_text())
        topics_list = topics_json.get("data", [])

        if not topics_list:
            return {"status": "error", "message": "No topics found in file."}

        if topic_index >= len(topics_list):
            topic_index = 0

        topic_data = topics_list[topic_index]
    else:
        return {"status": "error", "message": "Provide either topic_file or topic."}

    # Generate content
    carousel_content = generate_carousel(
        topic=topic_data,
        num_slides=num_slides,
        style=style,
    )

    # Save output
    output_dir = Path(".tmp")
    output_dir.mkdir(exist_ok=True)

    if not output_file:
        output_file = str(output_dir / "carousel_content.json")

    Path(output_file).write_text(json.dumps(carousel_content, indent=2))
    print(f"[INFO] Saved carousel content to {output_file}", file=sys.stderr)

    return {
        "status": "success",
        "data": carousel_content,
        "output_file": output_file,
    }


if __name__ == "__main__":
    args = {}
    if len(sys.argv) > 1:
        try:
            args = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            print(f"[ERROR] Invalid JSON argument: {sys.argv[1]}", file=sys.stderr)
            sys.exit(1)

    result = main(
        topic_file=args.get("topic_file"),
        topic_index=args.get("topic_index", 0),
        topic=args.get("topic"),
        num_slides=args.get("num_slides", 6),
        style=args.get("style", "contrarian"),
        output_file=args.get("output_file"),
    )
    print(json.dumps(result, indent=2))
