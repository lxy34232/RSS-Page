#!/usr/bin/env python3
"""
RSS Feed Fetcher

This script fetches content from multiple RSS feeds and saves them as JSON
for the Astro static site generator to consume.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from html import unescape
import re
from pathlib import Path
import argparse

# Try to import feedparser, install if not available
try:
    import feedparser
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "feedparser"])
    import feedparser

# Default time filter in days
DEFAULT_DAYS_FILTER = 14

# Maximum number of entries to fetch per feed
MAX_ENTRIES_PER_FEED = 20

# RSSHub base URL (can be overridden via environment variable)
RSSHUB_BASE_URL = os.environ.get("RSSHUB_BASE_URL", "https://rsshub.app")

# RSS feed sources organized by groups
RSS_FEED_GROUPS = [
    {
        "groupName": "国家政策",
        "feeds": [
            {
                "name": "中国科学院科研进展",
                "url": "https://www.cas.cn/rss1/rss_kyjz/rss.xml"
            }
        ]
    },
    {
        "groupName": "咨询机构",
        "feeds": [
            {
                "name": "Github 趋势",
                "url": "https://rsshub.app/github/trending/daily/javascript"
            }
        ]
    },
    {
        "groupName": "研究院所",
        "feeds": [
            {
                "name": "Forrester Blogs",
                "url": "https://www.forrester.com/blogs/feed/"
            }
        ]
    },
    {
        "groupName": "行业信息",
        "feeds": [
            {
                "name": "NASA APOD",
                "url": "rsshub://nasa/apod"
            }
        ]
    }
]

def clean_html(html_content: str) -> str:
    """Remove HTML tags and clean up the content."""
    if not html_content:
        return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', html_content)
    # Unescape HTML entities
    clean = unescape(clean)
    # Remove extra whitespace
    clean = ' '.join(clean.split())
    # Limit description length
    if len(clean) > 300:
        clean = clean[:297] + "..."
    return clean


def resolve_url(url: str) -> str:
    """Resolve rsshub:// URLs to actual HTTP URLs."""
    if url.startswith("rsshub://"):
        path = url[9:]  # Remove "rsshub://" prefix
        return f"{RSSHUB_BASE_URL}/{path}"
    return url


def fetch_feed_entries(feed_config: dict, days_filter: int) -> list:
    """Fetch entries from a single RSS feed."""
    entries = []
    url = resolve_url(feed_config['url'])
    print(f"Fetching: {feed_config['name']} ({url})")
    
    cutoff_date = datetime.now() - timedelta(days=days_filter)
    
    try:
        feed = feedparser.parse(url)
        
        if feed.bozo and not feed.entries:
            print(f"  Warning: Failed to parse {feed_config['name']}")
            return entries
        
        for entry in feed.entries[:MAX_ENTRIES_PER_FEED]:  # Limit entries per feed
            # Extract publication date
            pub_date = None
            pub_datetime = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_datetime = datetime(*entry.published_parsed[:6])
                pub_date = pub_datetime.isoformat()
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_datetime = datetime(*entry.updated_parsed[:6])
                pub_date = pub_datetime.isoformat()
            
            # Filter by date if we have a publication date
            if pub_datetime and pub_datetime < cutoff_date:
                continue
            
            # Extract description
            description = ""
            if hasattr(entry, 'summary'):
                description = clean_html(entry.summary)
            elif hasattr(entry, 'description'):
                description = clean_html(entry.description)
            
            entries.append({
                "title": entry.get('title', 'No Title'),
                "link": entry.get('link', ''),
                "pubDate": pub_date,
                "description": description
            })
        
        print(f"  Fetched {len(entries)} entries (within {days_filter} days)")
        
    except Exception as e:
        print(f"  Error fetching {feed_config['name']}: {e}")
    
    return entries


def fetch_grouped_feeds(days_filter: int = DEFAULT_DAYS_FILTER) -> list:
    """Fetch all RSS feeds organized by groups."""
    groups = []
    
    for group_config in RSS_FEED_GROUPS:
        group = {
            "groupName": group_config['groupName'],
            "sources": []
        }
        
        for feed_config in group_config['feeds']:
            entries = fetch_feed_entries(feed_config, days_filter)
            
            # Sort entries by publication date (newest first)
            entries.sort(key=lambda x: x.get('pubDate') or '', reverse=True)
            
            source = {
                "name": feed_config['name'],
                "url": feed_config['url'],
                "entries": entries
            }
            group['sources'].append(source)
        
        groups.append(group)
    
    return groups

def main():
    """Main function to fetch feeds and save to JSON."""
    parser = argparse.ArgumentParser(description='Fetch RSS feeds and save to JSON.')
    parser.add_argument('--days', type=int, default=DEFAULT_DAYS_FILTER,
                        help=f'Only include entries from the last N days (default: {DEFAULT_DAYS_FILTER})')
    args = parser.parse_args()
    
    print("Starting RSS feed fetch...")
    print(f"Current time: {datetime.now().isoformat()}")
    print(f"Time filter: {args.days} days")
    
    # Fetch all feeds with grouping
    groups = fetch_grouped_feeds(args.days)
    
    # Create the data directory if it doesn't exist
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    # Prepare the output data
    output_data = {
        "lastUpdated": datetime.now().isoformat(),
        "daysFilter": args.days,
        "groups": groups
    }
    
    # Save to JSON file
    output_path = data_dir / "rss_feeds.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    # Count total entries
    total_entries = sum(
        len(source['entries'])
        for group in groups
        for source in group['sources']
    )
    
    print(f"\nSaved {total_entries} entries across {len(groups)} groups to {output_path}")
    print("RSS feed fetch completed!")

if __name__ == "__main__":
    main()
