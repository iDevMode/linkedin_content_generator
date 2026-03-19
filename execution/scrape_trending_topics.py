#!/usr/bin/env python3
"""
AI Agent News Scraper for LinkedIn Carousel Content.

Scrapes multiple sources for AI agent / agentic workflow stories and developments,
filtering out general tech noise. Outputs a ranked list of topics relevant to
Nukode's positioning as an authority on agentic workflows and chatbots.

Sources (priority order, no-API-key sources first):
  - HackerNews (public API)
  - RSS feeds (AI-focused blogs and publications)
  - Reddit (r/artificial, r/MachineLearning, etc. — requires API key)

Usage:
  python execution/scrape_trending_topics.py
  python execution/scrape_trending_topics.py '{"max_topics": 10, "sources": ["hackernews", "rss", "reddit"]}'
"""

import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import atoma
import requests
from dotenv import load_dotenv

load_dotenv()

# AI agent keyword filter — applied across all sources
AGENT_KEYWORDS = [
    "agent", "agentic", "workflow", "automation", "chatbot",
    "ai assistant", "tool use", "function calling", "rag", "retrieval",
    "orchestration", "multi-agent", "autonomous", "langchain", "crewai",
    "autogen", "claude", "gpt", "no-code ai", "ai roi",
    "business automation", "ai pipeline", "llm", "large language model",
    "prompt engineering", "ai integration",
]

# RSS feed URLs for AI-focused sources
DEFAULT_RSS_FEEDS = [
    # AI/Agent blogs
    "https://blog.langchain.dev/rss/",
    "https://www.anthropic.com/news/rss",
    "https://openai.com/blog/rss.xml",
    # Business AI / Tech publications
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml",
]

# Reddit subreddits for AI content
DEFAULT_SUBREDDITS = [
    "artificial",
    "MachineLearning",
    "LangChain",
    "LocalLLaMA",
]


def is_agent_relevant(title: str, summary: str = "") -> bool:
    """Check if content is relevant to AI agents / agentic workflows."""
    text = f"{title} {summary}".lower()
    return any(kw in text for kw in AGENT_KEYWORDS)


def scrape_hackernews(max_items: int = 50) -> List[Dict]:
    """Fetch top HackerNews stories, filtered by AI agent keywords."""
    topics = []
    try:
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=15,
        )
        resp.raise_for_status()
        story_ids = resp.json()[:max_items]

        for story_id in story_ids:
            try:
                item_resp = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    timeout=10,
                )
                item_resp.raise_for_status()
                item = item_resp.json()
                if not item:
                    continue

                title = item.get("title", "")
                url = item.get("url", "")
                score = item.get("score", 0)
                timestamp = item.get("time", 0)

                if is_agent_relevant(title):
                    topics.append({
                        "title": title,
                        "url": url,
                        "source": "hackernews",
                        "score": score,
                        "timestamp": datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat() if timestamp else None,
                        "summary": "",
                        "engagement": score,
                    })
            except requests.RequestException:
                continue

    except requests.RequestException as e:
        print(f"[WARN] HackerNews scrape failed: {e}", file=sys.stderr)

    return topics


def scrape_rss_feeds(feeds: Optional[List[str]] = None) -> List[Dict]:
    """Parse AI-focused RSS feeds for relevant stories."""
    feeds = feeds or DEFAULT_RSS_FEEDS
    topics = []

    for feed_url in feeds:
        try:
            resp = requests.get(feed_url, timeout=15)
            resp.raise_for_status()
            content = resp.content

            # Try Atom first, then RSS
            entries = []
            try:
                feed = atoma.parse_atom_bytes(content)
                for item in feed.entries[:20]:
                    title = item.title.value if item.title else ""
                    summary = ""
                    if item.summary:
                        summary = item.summary.value
                    elif item.content:
                        summary = item.content.value if hasattr(item.content, 'value') else str(item.content)
                    link = ""
                    if item.links:
                        link = item.links[0].href
                    elif item.id_:
                        link = item.id_
                    timestamp = None
                    if item.updated:
                        timestamp = item.updated.isoformat()
                    elif item.published:
                        timestamp = item.published.isoformat()
                    entries.append((title, summary, link, timestamp))
            except Exception:
                try:
                    feed = atoma.parse_rss_bytes(content)
                    for item in feed.items[:20]:
                        title = item.title or ""
                        summary = item.description or ""
                        link = item.link or ""
                        timestamp = None
                        if item.pub_date:
                            timestamp = item.pub_date.isoformat()
                        entries.append((title, summary, link, timestamp))
                except Exception:
                    continue

            for title, summary, link, timestamp in entries:
                if is_agent_relevant(title, summary):
                    clean_summary = re.sub(r"<[^>]+>", "", summary)[:500]
                    topics.append({
                        "title": title,
                        "url": link,
                        "source": f"rss:{feed_url.split('/')[2]}",
                        "score": 0,
                        "timestamp": timestamp,
                        "summary": clean_summary,
                        "engagement": 0,
                    })
        except Exception as e:
            print(f"[WARN] RSS feed failed ({feed_url}): {e}", file=sys.stderr)

    return topics


def scrape_reddit(subreddits: Optional[List[str]] = None) -> List[Dict]:
    """Scrape AI/agent subreddits for trending topics. Requires Reddit API credentials."""
    subreddits = subreddits or DEFAULT_SUBREDDITS
    topics = []

    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "nukode_carousel_bot/1.0")

    if not client_id or not client_secret:
        print("[INFO] Reddit API keys not set — skipping Reddit scrape.", file=sys.stderr)
        return topics

    try:
        import praw

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

        for sub_name in subreddits:
            try:
                subreddit = reddit.subreddit(sub_name)
                for post in subreddit.hot(limit=25):
                    title = post.title
                    selftext = post.selftext[:500] if post.selftext else ""

                    if is_agent_relevant(title, selftext):
                        topics.append({
                            "title": title,
                            "url": f"https://reddit.com{post.permalink}",
                            "source": f"reddit:r/{sub_name}",
                            "score": post.score,
                            "timestamp": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat(),
                            "summary": selftext[:500],
                            "engagement": post.score + post.num_comments,
                        })
            except Exception as e:
                print(f"[WARN] Reddit r/{sub_name} failed: {e}", file=sys.stderr)

    except ImportError:
        print("[WARN] praw not installed — skipping Reddit scrape.", file=sys.stderr)
    except Exception as e:
        print(f"[WARN] Reddit scrape failed: {e}", file=sys.stderr)

    return topics


def score_topic(topic: Dict) -> float:
    """Score a topic by recency, engagement, and business relevance."""
    score = 0.0

    # Engagement score (normalized)
    engagement = topic.get("engagement", 0)
    if engagement > 0:
        score += min(engagement / 100, 10.0)  # Cap at 10 points

    # Recency score
    if topic.get("timestamp"):
        try:
            pub_time = datetime.fromisoformat(topic["timestamp"])
            hours_ago = (datetime.now(timezone.utc) - pub_time).total_seconds() / 3600
            if hours_ago < 6:
                score += 10
            elif hours_ago < 24:
                score += 7
            elif hours_ago < 72:
                score += 4
            elif hours_ago < 168:
                score += 2
        except (ValueError, TypeError):
            pass

    # Business relevance boost — stories about AI solving real problems score highest
    text = f"{topic.get('title', '')} {topic.get('summary', '')}".lower()
    business_keywords = [
        "business", "enterprise", "roi", "revenue", "productivity",
        "automate", "workflow", "integration", "deploy", "production",
        "customer", "saas", "startup", "company", "industry",
    ]
    business_hits = sum(1 for kw in business_keywords if kw in text)
    score += business_hits * 2

    # Source priority bonus
    source = topic.get("source", "")
    if "hackernews" in source:
        score += 3
    elif "reddit" in source:
        score += 2
    elif "rss" in source:
        score += 1

    return round(score, 2)


def deduplicate_topics(topics: List[Dict]) -> List[Dict]:
    """Merge similar topics based on title similarity."""
    if not topics:
        return topics

    seen_titles = []
    unique_topics = []

    for topic in topics:
        title_words = set(topic["title"].lower().split())
        is_duplicate = False

        for seen in seen_titles:
            overlap = len(title_words & seen) / max(len(title_words | seen), 1)
            if overlap > 0.6:
                is_duplicate = True
                break

        if not is_duplicate:
            seen_titles.append(title_words)
            unique_topics.append(topic)

    return unique_topics


def main(sources: Optional[List[str]] = None, max_topics: int = 15) -> dict:
    """
    Run the full scraping pipeline.

    Args:
        sources: List of sources to scrape. Options: "hackernews", "rss", "reddit".
                 Defaults to all available sources.
        max_topics: Maximum number of topics to return.

    Returns:
        dict with status, data (list of scored topics), and metadata.
    """
    if sources is None:
        sources = ["hackernews", "rss", "reddit"]

    all_topics = []
    source_counts = {}

    print("[INFO] Starting AI agent topic scrape...", file=sys.stderr)

    if "hackernews" in sources:
        print("[INFO] Scraping HackerNews...", file=sys.stderr)
        hn_topics = scrape_hackernews()
        source_counts["hackernews"] = len(hn_topics)
        all_topics.extend(hn_topics)

    if "rss" in sources:
        print("[INFO] Scraping RSS feeds...", file=sys.stderr)
        rss_topics = scrape_rss_feeds()
        source_counts["rss"] = len(rss_topics)
        all_topics.extend(rss_topics)

    if "reddit" in sources:
        print("[INFO] Scraping Reddit...", file=sys.stderr)
        reddit_topics = scrape_reddit()
        source_counts["reddit"] = len(reddit_topics)
        all_topics.extend(reddit_topics)

    print(f"[INFO] Found {len(all_topics)} raw topics across all sources.", file=sys.stderr)

    # Deduplicate
    all_topics = deduplicate_topics(all_topics)
    print(f"[INFO] {len(all_topics)} unique topics after deduplication.", file=sys.stderr)

    # Score and sort
    for topic in all_topics:
        topic["relevance_score"] = score_topic(topic)

    all_topics.sort(key=lambda t: t["relevance_score"], reverse=True)
    top_topics = all_topics[:max_topics]

    # Save result
    output_dir = Path(".tmp")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "trending_topics.json"

    result = {
        "status": "success",
        "data": top_topics,
        "metadata": {
            "total_scraped": sum(source_counts.values()),
            "unique_after_dedup": len(all_topics),
            "returned": len(top_topics),
            "sources": source_counts,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    output_file.write_text(json.dumps(result, indent=2))
    print(f"[INFO] Saved {len(top_topics)} topics to {output_file}", file=sys.stderr)

    return result


if __name__ == "__main__":
    args = {}
    if len(sys.argv) > 1:
        try:
            args = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            print(f"[ERROR] Invalid JSON argument: {sys.argv[1]}", file=sys.stderr)
            sys.exit(1)

    result = main(
        sources=args.get("sources"),
        max_topics=args.get("max_topics", 15),
    )
    print(json.dumps(result, indent=2))
