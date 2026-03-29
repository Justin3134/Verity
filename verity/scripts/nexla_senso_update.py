"""
Nexla → Senso Live Intelligence Updater
========================================
Runs on a schedule (cron / GitHub Actions every 15 min).

Flow:
  1. Fetch latest breaking news from Nexla automated feed
     → Falls back to Tavily real-time search if Nexla unavailable
  2. Save each article as a .md file in intelligence/live/
  3. Git-commit the new files (GitHub Actions will detect them and
     trigger the auggie review workflow automatically)
  4. Upload articles directly to Senso so agents always have fresh data

Usage:
  python scripts/nexla_senso_update.py              # full run
  python scripts/nexla_senso_update.py --dry-run    # fetch only, no upload
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

# ── Load env ──────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent.parent / ".env")

NEXLA_API_URL = os.environ.get("NEXLA_API_URL", "")
NEXLA_API_KEY = os.environ.get("NEXLA_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
SENSO_API_KEY = os.environ.get("SENSO_API_KEY", "")

INTEL_DIR = Path(__file__).parent.parent / "intelligence" / "live"
BATCH_TOPICS = [
    "breaking geopolitical news today",
    "US foreign policy news today",
    "Iran nuclear war news today",
    "Russia Ukraine war update today",
    "China Taiwan military news today",
    "Middle East conflict news today",
    "NATO security news today",
]


# ── Nexla fetch ───────────────────────────────────────────────────────────────

def fetch_nexla_articles() -> list[dict]:
    """Pull live articles from Nexla automated news pipeline."""
    if not NEXLA_API_URL or not NEXLA_API_KEY:
        print("  ⚠  Nexla: credentials not configured")
        return []
    try:
        resp = httpx.post(
            f"{NEXLA_API_URL}?api_key={NEXLA_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            articles = data if isinstance(data, list) else data.get("articles", [])
            print(f"  ✓  Nexla: {len(articles)} articles received")
            return articles
        else:
            print(f"  ⚠  Nexla returned {resp.status_code} — falling back to Tavily")
    except Exception as e:
        print(f"  ⚠  Nexla unavailable ({e}) — falling back to Tavily")
    return []


# ── Tavily fallback ───────────────────────────────────────────────────────────

def fetch_tavily_articles() -> list[dict]:
    """Fetch breaking news via Tavily (fallback when Nexla is unavailable)."""
    if not TAVILY_API_KEY:
        print("  ✗  Tavily: API key not set")
        return []

    articles: list[dict] = []
    seen_urls: set[str] = set()

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)

        for topic in BATCH_TOPICS[:4]:  # limit to 4 searches to stay within quota
            try:
                resp = client.search(
                    f"latest news {topic}",
                    max_results=5,
                    search_depth="basic",
                    topic="news",
                )
                for r in resp.get("results", []):
                    url = r.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        domain = url.split("/")[2] if url.startswith("http") else "Web"
                        articles.append({
                            "title": r.get("title", ""),
                            "content": r.get("content", ""),
                            "description": r.get("content", "")[:300],
                            "url": url,
                            "source": {"name": domain},
                            "publishedAt": r.get("published_date", ""),
                        })
                time.sleep(0.5)
            except Exception as e:
                print(f"  ⚠  Tavily search '{topic}': {e}")

    except ImportError:
        print("  ✗  tavily-python not installed: pip install tavily-python")

    print(f"  ✓  Tavily: {len(articles)} articles retrieved")
    return articles


# ── Markdown serialisation ────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Turn a title into a filesystem-safe slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:80].strip("-")


def article_to_markdown(article: dict, source_label: str) -> str:
    title = article.get("title", "Untitled")
    url = article.get("url", "")
    source = article.get("source", {})
    source_name = source.get("name", "Unknown") if isinstance(source, dict) else str(source)
    published = article.get("publishedAt", "")
    content = article.get("content") or article.get("description") or ""

    lines = [
        f"# {title}",
        "",
        f"**Source:** {source_name}  ",
        f"**URL:** {url}  ",
        f"**Published:** {published}  ",
        f"**Retrieved via:** {source_label}  ",
        f"**Ingested:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        "---",
        "",
        content.strip(),
    ]
    return "\n".join(lines)


# ── Senso upload ──────────────────────────────────────────────────────────────

def upload_to_senso(filepath: Path) -> bool:
    """Upload a single markdown file to the Senso knowledge base."""
    try:
        result = subprocess.run(
            ["senso", "ingest", "upload", str(filepath)],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "SENSO_API_KEY": SENSO_API_KEY},
        )
        if result.returncode == 0:
            print(f"    ✓  Senso: uploaded {filepath.name}")
            return True
        output = (result.stdout + result.stderr).strip()
        if "422" in output:
            print(f"    ~  Senso: already exists {filepath.name}")
            return True
        print(f"    ✗  Senso upload failed: {output[:120]}")
        return False
    except FileNotFoundError:
        print("    ✗  senso CLI not found — install: npm install -g @senso-ai/cli")
        return False
    except Exception as e:
        print(f"    ✗  Senso error: {e}")
        return False


# ── Git commit (triggers GitHub Actions auggie review) ───────────────────────

def git_commit_new_files(new_files: list[Path], timestamp: str) -> bool:
    """
    Commit new intelligence files to git.
    GitHub Actions will detect the push and trigger the auggie review workflow.
    """
    repo_root = Path(__file__).parent.parent
    try:
        # Stage the new files
        subprocess.run(
            ["git", "add"] + [str(f) for f in new_files],
            cwd=repo_root, check=True, capture_output=True,
        )
        # Commit
        msg = f"[nexla] Live intelligence update {timestamp} ({len(new_files)} articles)"
        result = subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=repo_root, capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"  ✓  Git: committed {len(new_files)} files")
            return True
        if "nothing to commit" in result.stdout:
            print("  ~  Git: no new files to commit")
            return False
        print(f"  ⚠  Git commit: {result.stderr.strip()[:120]}")
        return False
    except Exception as e:
        print(f"  ⚠  Git unavailable: {e} (skipping commit)")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    print("=" * 60)
    print("VERITY — Nexla → Senso Live Intelligence Update")
    print(f"Timestamp: {timestamp}")
    print("=" * 60)

    # 1. Fetch articles
    print("\n[1/4] Fetching live intelligence...")
    articles = fetch_nexla_articles()
    source_label = "Nexla"
    if not articles:
        articles = fetch_tavily_articles()
        source_label = "Tavily (Nexla fallback)"

    if not articles:
        print("  ✗  No articles retrieved. Exiting.")
        sys.exit(1)

    print(f"  →  {len(articles)} articles from {source_label}")

    # 2. Save as markdown files
    print(f"\n[2/4] Saving to {INTEL_DIR}/...")
    INTEL_DIR.mkdir(parents=True, exist_ok=True)
    saved_files: list[Path] = []

    for article in articles:
        title = article.get("title", "")
        if not title:
            continue
        slug = slugify(title)
        filename = f"{timestamp[:10]}_{slug}.md"
        filepath = INTEL_DIR / filename

        # Skip if file already exists (duplicate run protection)
        if filepath.exists():
            continue

        md = article_to_markdown(article, source_label)
        filepath.write_text(md, encoding="utf-8")
        saved_files.append(filepath)
        print(f"  ✓  Saved: {filename}")

    if not saved_files:
        print("  ~  All articles already saved — nothing new.")
        return

    print(f"  →  {len(saved_files)} new files saved")

    if dry_run:
        print("\n[DRY RUN] Skipping git commit and Senso upload.")
        return

    # 3. Git commit (triggers GitHub Actions → auggie review)
    print("\n[3/4] Committing to git (triggers auggie review workflow)...")
    git_commit_new_files(saved_files, timestamp)

    # 4. Upload to Senso
    print("\n[4/4] Uploading to Senso knowledge base...")
    uploaded = 0
    for filepath in saved_files:
        if upload_to_senso(filepath):
            uploaded += 1
        time.sleep(0.5)

    print()
    print("=" * 60)
    print(f"Done: {len(saved_files)} articles saved, {uploaded} uploaded to Senso")
    print(f"Source: {source_label}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nexla → Senso live intelligence updater")
    parser.add_argument("--dry-run", action="store_true", help="Fetch only, no upload or commit")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
