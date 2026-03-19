#!/usr/bin/env python3
"""
LinkedIn Carousel Workflow Orchestrator.

Runs the full pipeline end-to-end:
  1. Scrape trending AI agent topics
  2. Pick the top topic (or user-specified index)
  3. Generate carousel content via Claude API
  4. Generate branded carousel images

Usage:
  python execution/run_carousel_workflow.py
  python execution/run_carousel_workflow.py '{"topic_index": 2, "num_slides": 8, "style": "framework"}'
  python execution/run_carousel_workflow.py '{"skip_scraping": true}'
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def main(
    skip_scraping: bool = False,
    topic_index: int = 0,
    num_slides: int = 6,
    style: str = "contrarian",
    output_format: str = "png",
) -> dict:
    """
    Run the full LinkedIn carousel generation pipeline.

    Args:
        skip_scraping: If True, reuse existing .tmp/trending_topics.json.
        topic_index: Index of topic to use from scraped results.
        num_slides: Number of carousel slides.
        style: Content style (contrarian, framework, data, question, story, education).
        output_format: Output format — "png" or "pdf" (both are always generated).

    Returns:
        dict with status, paths, and summary.
    """
    results = {
        "status": "success",
        "steps": {},
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    topics_file = ".tmp/trending_topics.json"
    content_file = ".tmp/carousel_content.json"

    # Step 1: Scrape trending topics
    if not skip_scraping:
        print("=" * 60, file=sys.stderr)
        print("STEP 1: Scraping trending AI agent topics...", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        from execution.scrape_trending_topics import main as scrape_main

        scrape_result = scrape_main()
        results["steps"]["scrape"] = {
            "status": scrape_result.get("status"),
            "topics_found": scrape_result.get("metadata", {}).get("returned", 0),
        }

        if scrape_result.get("status") != "success":
            results["status"] = "error"
            results["error"] = "Scraping failed"
            return results
    else:
        print("=" * 60, file=sys.stderr)
        print("STEP 1: Skipping scrape — using existing topics file.", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        if not Path(topics_file).exists():
            return {
                "status": "error",
                "error": f"skip_scraping=True but {topics_file} not found.",
            }

        topics_data = json.loads(Path(topics_file).read_text())
        results["steps"]["scrape"] = {
            "status": "skipped",
            "topics_found": len(topics_data.get("data", [])),
        }

    # Step 2: Pick topic
    print("=" * 60, file=sys.stderr)
    print(f"STEP 2: Selecting topic (index={topic_index})...", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    topics_data = json.loads(Path(topics_file).read_text())
    topics_list = topics_data.get("data", [])

    if not topics_list:
        return {"status": "error", "error": "No topics available."}

    if topic_index >= len(topics_list):
        topic_index = 0

    selected_topic = topics_list[topic_index]
    print(f"[INFO] Selected: {selected_topic.get('title', 'Unknown')}", file=sys.stderr)
    results["steps"]["topic_selection"] = {
        "index": topic_index,
        "topic": selected_topic.get("title", ""),
        "score": selected_topic.get("relevance_score", 0),
    }

    # Step 3: Generate carousel content
    print("=" * 60, file=sys.stderr)
    print("STEP 3: Generating carousel content via Claude...", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    from execution.generate_carousel_content import main as content_main

    content_result = content_main(
        topic_file=topics_file,
        topic_index=topic_index,
        num_slides=num_slides,
        style=style,
    )
    results["steps"]["content_generation"] = {
        "status": content_result.get("status"),
        "output_file": content_result.get("output_file"),
    }

    if content_result.get("status") != "success":
        results["status"] = "error"
        results["error"] = "Content generation failed"
        return results

    # Step 4: Generate carousel images
    print("=" * 60, file=sys.stderr)
    print("STEP 4: Generating branded carousel images...", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    from execution.generate_carousel_images import main as images_main

    images_result = images_main(content_file=content_file)
    results["steps"]["image_generation"] = {
        "status": images_result.get("status"),
        "data": images_result.get("data"),
    }

    if images_result.get("status") != "success":
        results["status"] = "error"
        results["error"] = "Image generation failed"
        return results

    # Summary
    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    results["summary"] = {
        "topic": selected_topic.get("title", ""),
        "slides": num_slides,
        "style": style,
        "output_dir": images_result.get("data", {}).get("output_dir"),
        "pdf_path": images_result.get("data", {}).get("pdf_path"),
        "image_count": images_result.get("data", {}).get("slides_generated", 0),
    }

    print("\n" + "=" * 60, file=sys.stderr)
    print("PIPELINE COMPLETE", file=sys.stderr)
    print(f"  Topic: {selected_topic.get('title', '')}", file=sys.stderr)
    print(f"  Slides: {num_slides}", file=sys.stderr)
    print(f"  Output: {images_result.get('data', {}).get('output_dir')}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    return results


if __name__ == "__main__":
    args = {}
    if len(sys.argv) > 1:
        try:
            args = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            print(f"[ERROR] Invalid JSON argument: {sys.argv[1]}", file=sys.stderr)
            sys.exit(1)

    result = main(
        skip_scraping=args.get("skip_scraping", False),
        topic_index=args.get("topic_index", 0),
        num_slides=args.get("num_slides", 6),
        style=args.get("style", "contrarian"),
        output_format=args.get("output_format", "png"),
    )
    print(json.dumps(result, indent=2))
