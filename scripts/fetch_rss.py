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

# Timeout for fetching a single feed (in seconds)
FEED_TIMEOUT = 30

# RSSHub base URL (can be overridden via environment variable)
RSSHUB_BASE_URL = os.environ.get("RSSHUB_BASE_URL", "https://rsshub.app")

# RSSHub fallback domains to try if the primary domain fails
RSSHUB_FALLBACK_DOMAINS = [
    "https://rsshub.app",
    "https://rsshub.rssforever.com",
    "https://hub.slarker.me",
    "https://rsshub.pseudoyu.com",
    "https://rsshub.rss.tips",
    "https://rsshub.ktachibana.party",
    "https://rss.owo.nz",
    "https://rss.wudifeixue.com",
    "https://rss.littlebaby.life",
    "https://rsshub.henry.wang",
    "https://holoxx.f5.si",
    "https://rsshub.umzzz.com",
    "https://rsshub.isrss.com",
    "https://rsshub.email-once.com",
    "https://rss.datuan.dev",
    "https://rsshub.asailor.org",
    "https://rsshub2.asailor.org",
    "https://rss.4040940.xyz",
    "https://rsshub.cups.moe"
]

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
                "name": "麦肯锡洞见",
                "url": "rsshub://mckinsey/cn"
            },
            {
                "name": "毕马威洞察",
                "url": "http://139.162.74.205/kpmg/insights"
            },
            {
                "name": "MIT 科技评论",
                "url": "rsshub://mittrchina/hot"
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
                "name": "北京大学国家发展研究院",
                "url": "rsshub://pku/nsd/gd"
            },
            {
                "name": "中国科技网",
                "url": "rsshub://stdaily/digitalpaper"
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


def resolve_url(url: str, base_url: str = None) -> str:
    """Resolve rsshub:// URLs to actual HTTP URLs."""
    if url.startswith("rsshub://"):
        path = url[9:]  # Remove "rsshub://" prefix
        base = base_url if base_url else RSSHUB_BASE_URL
        return f"{base}/{path}"
    return url


def is_rsshub_url(url: str) -> bool:
    """Check if the URL is a RSSHub URL."""
    return url.startswith("rsshub://")


def fetch_feed_entries(feed_config: dict, days_filter: int) -> list:
    """Fetch entries from a single RSS feed with fallback support for RSSHub domains."""
    entries = []
    original_url = feed_config['url']
    cutoff_date = datetime.now() - timedelta(days=days_filter)
    
    # Determine the list of URLs to try
    urls_to_try = []
    if is_rsshub_url(original_url):
        # For RSSHub URLs, try all fallback domains
        for domain in RSSHUB_FALLBACK_DOMAINS:
            urls_to_try.append(resolve_url(original_url, domain))
    else:
        # For non-RSSHub URLs, only try the original URL
        urls_to_try.append(resolve_url(original_url))
    
    # Try each URL until one succeeds
    last_error = None
    for i, url in enumerate(urls_to_try):
        if i == 0:
            print(f"Fetching: {feed_config['name']} ({url})")
        else:
            print(f"  Retrying with fallback domain ({i+1}/{len(urls_to_try)}): {url}")
        
        try:
            # Set timeout for feedparser
            import socket
            socket.setdefaulttimeout(FEED_TIMEOUT)
            feed = feedparser.parse(url)
            
            # Check if we got valid data
            if feed.bozo and not feed.entries:
                last_error = f"Failed to parse feed (bozo)"
                continue
            
            if not feed.entries:
                last_error = "No entries found in feed"
                continue
            
            # Successfully fetched entries, process them
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
            
            print(f"  ✓ Fetched {len(entries)} entries (within {days_filter} days)")
            return entries  # Success! Return the entries
            
        except Exception as e:
            last_error = str(e)
            continue
    
    # If we get here, all URLs failed
    print(f"  ✗ Error: Failed to fetch {feed_config['name']} after trying {len(urls_to_try)} URL(s). Last error: {last_error}")
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
