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
DEFAULT_DAYS_FILTER = 180

# Maximum number of entries to fetch per feed
MAX_ENTRIES_PER_FEED = 30

# RSSHub base URL (can be overridden via environment variable)
RSSHUB_BASE_URL = os.environ.get("RSSHUB_BASE_URL", "https://rsshub.rssforever.com")

# RSS feed sources organized by groups
RSS_FEED_GROUPS = [
    {
        "groupName": "国家政策",
        "feeds": [
            {
                "name": "工信部政策文件",
                "url": "https://www.miit.gov.cn/api-gateway/jpaas-plugins-web-server/front/rss/getinfo?webId=8d828e408d90447786ddbe128d495e9e&columnIds=925fa8f4afd44e53818794ed96d9876e%2C30f92eeafcfd4685984dfb793a2c5fff"
            },
            {
                "name": "发改委发展改革板块",
                "url": "rsshub://gov/ndrc/fggz"
            }
        ]
    },
    {
        "groupName": "咨询机构",
        "feeds": [
            {
                "name": "麦肯锡全球研究院",
                "url": "rsshub://mckinsey/cn/25"
            },
            {
                "name": "毕马威洞察",
                "url": "http://139.162.74.205/kpmg/insights"
            },
            {
                "name": "The Batch",
                "url": "https://rsshub.bestblogs.dev/deeplearning/the-batch"
            },
            {
                "name": "Gartner",
                "url": "https://rss.diffbot.com/atom?url=https://www.gartner.com/en/newsroom/archive"
            }
        ]
    },
    {
        "groupName": "研究院所",
        "feeds": [
            {
                "name": "中国科学院科研进展",
                "url": "https://www.cas.cn/rss1/rss_kyjz/rss.xml"
            },
            {
                "name": "阿里研究院",
                "url": "https://wechat2rss.bestblogs.dev/feed/e2f1190c120f7f3d74b630bfcfe9e58296bd535c.xml"
            },
            {
                "name": "MIT Technology Review",
                "url": "https://www.technologyreview.com/feed/"
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


def load_cached_data(data_path: Path) -> dict:
    """Load previously cached RSS feed data."""
    if data_path.exists():
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load cached data: {e}")
    return {"groups": []}


def merge_with_cache(new_groups: list, cached_data: dict) -> list:
    """
    Merge new feed data with cached data.
    If a source has no new entries, use cached entries.
    """
    # Create a lookup map for cached sources
    cache_map = {}
    for cached_group in cached_data.get('groups', []):
        group_name = cached_group.get('groupName')
        if not group_name:
            continue
        for cached_source in cached_group.get('sources', []):
            source_name = cached_source.get('name')
            if not source_name:
                continue
            source_key = f"{group_name}::{source_name}"
            cache_map[source_key] = cached_source.get('entries', [])
    
    # Merge new data with cache
    merged_groups = []
    for new_group in new_groups:
        group_name = new_group.get('groupName')
        if not group_name:
            continue
        merged_sources = []
        
        for new_source in new_group.get('sources', []):
            source_name = new_source.get('name')
            if not source_name:
                continue
            source_key = f"{group_name}::{source_name}"
            
            # If new source has no entries, try to use cached entries
            if len(new_source.get('entries', [])) == 0 and source_key in cache_map:
                cached_entries = cache_map[source_key]
                if cached_entries:
                    print(f"  Using cached data for {source_name} ({len(cached_entries)} entries)")
                    # Create a new source dictionary to avoid mutation
                    merged_source = {**new_source, 'entries': cached_entries.copy()}
                    merged_sources.append(merged_source)
                else:
                    merged_sources.append(new_source)
            else:
                merged_sources.append(new_source)
        
        # Create a new group dictionary instead of modifying in place
        merged_group = {**new_group, 'sources': merged_sources}
        merged_groups.append(merged_group)
    
    return merged_groups


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
    
    # Create the data directory if it doesn't exist
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    output_path = data_dir / "rss_feeds.json"
    
    # Load cached data before fetching
    print("\nLoading cached data...")
    cached_data = load_cached_data(output_path)
    
    # Fetch all feeds with grouping
    print("\nFetching new RSS feed data...")
    groups = fetch_grouped_feeds(args.days)
    
    # Merge with cached data
    print("\nMerging with cached data...")
    merged_groups = merge_with_cache(groups, cached_data)
    
    # Prepare the output data
    output_data = {
        "lastUpdated": datetime.now().isoformat(),
        "daysFilter": args.days,
        "groups": merged_groups
    }
    
    # Save to JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    # Count total entries
    total_entries = sum(
        len(source['entries'])
        for group in merged_groups
        for source in group['sources']
    )
    
    print(f"\nSaved {total_entries} entries across {len(merged_groups)} groups to {output_path}")
    print("RSS feed fetch completed!")

if __name__ == "__main__":
    main()
