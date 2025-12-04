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

# RSSHub fallback domains to try when rsshub.app fails
RSSHUB_FALLBACK_DOMAINS = [
    "rsshub.app",
    "rsshub.rssforever.com",
    "hub.slarker.me",
    "rsshub.pseudoyu.com",
    "rsshub.rss.tips",
    "rsshub.ktachibana.party",
    "rss.owo.nz",
    "rss.wudifeixue.com",
    "rss.littlebaby.life",
    "rsshub.henry.wang",
    "holoxx.f5.si",
    "rsshub.umzzz.com",
    "rsshub.isrss.com",
    "rsshub.email-once.com",
    "rss.datuan.dev",
    "rsshub.asailor.org",
    "rsshub2.asailor.org",
    "rss.4040940.xyz",
    "rsshub.cups.moe"
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


def resolve_url(url: str, domain: str = None) -> str:
    """Resolve rsshub:// URLs to actual HTTP URLs.
    
    Args:
        url: The URL to resolve (may start with rsshub://)
        domain: Optional specific domain to use for rsshub:// URLs
    """
    if url.startswith("rsshub://"):
        path = url[9:]  # Remove "rsshub://" prefix
        if domain is None:
            domain = RSSHUB_BASE_URL
        elif not domain.startswith("http"):
            domain = f"https://{domain}"
        return f"{domain}/{path}"
    return url


def try_fetch_with_fallback(url: str, original_url: str) -> tuple:
    """Try to fetch a feed, using fallback domains if it's a rsshub:// URL that fails.
    
    Returns: (feed, successful_url)
    """
    # First try the given URL
    feed = feedparser.parse(url)
    if not (feed.bozo and not feed.entries):
        return feed, url
    
    # If the original URL uses rsshub://, try fallback domains
    if original_url.startswith("rsshub://"):
        print(f"    Initial rsshub domain failed, trying fallback domains...")
        for fallback_domain in RSSHUB_FALLBACK_DOMAINS:
            fallback_url = resolve_url(original_url, fallback_domain)
            print(f"    Trying: {fallback_domain}")
            try:
                feed = feedparser.parse(fallback_url)
                if not (feed.bozo and not feed.entries):
                    print(f"    Success with: {fallback_domain}")
                    return feed, fallback_url
            except Exception as e:
                print(f"    Error with {fallback_domain}: {e}")
                continue
    
    # Return the last feed result even if failed
    return feed, url


def fetch_feed_entries(feed_config: dict, days_filter: int) -> list:
    """Fetch entries from a single RSS feed."""
    entries = []
    url = resolve_url(feed_config['url'])
    print(f"Fetching: {feed_config['name']} ({url})")
    
    cutoff_date = datetime.now() - timedelta(days=days_filter)
    
    try:
        feed, successful_url = try_fetch_with_fallback(url, feed_config['url'])
        
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
