#!/usr/bin/env python3
"""
RSS Feed Fetcher

This script fetches content from multiple RSS feeds and saves them as JSON
for the Astro static site generator to consume.
"""

import json
import os
import sys
from datetime import datetime
from html import unescape
import re
from pathlib import Path

# Try to import feedparser, install if not available
try:
    import feedparser
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "feedparser"])
    import feedparser

# RSS feed sources to fetch
RSS_FEEDS = [
    {
        "name": "Hacker News",
        "url": "https://hnrss.org/frontpage"
    },
    {
        "name": "BBC News",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml"
    },
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/"
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

def fetch_feeds() -> list:
    """Fetch all RSS feeds and return a list of feed entries."""
    all_entries = []
    
    for feed_config in RSS_FEEDS:
        print(f"Fetching: {feed_config['name']} ({feed_config['url']})")
        try:
            feed = feedparser.parse(feed_config['url'])
            
            if feed.bozo and not feed.entries:
                print(f"  Warning: Failed to parse {feed_config['name']}")
                continue
            
            for entry in feed.entries[:10]:  # Limit to 10 entries per feed
                # Extract publication date
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6]).isoformat()
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6]).isoformat()
                
                # Extract description
                description = ""
                if hasattr(entry, 'summary'):
                    description = clean_html(entry.summary)
                elif hasattr(entry, 'description'):
                    description = clean_html(entry.description)
                
                all_entries.append({
                    "title": entry.get('title', 'No Title'),
                    "link": entry.get('link', ''),
                    "pubDate": pub_date,
                    "description": description,
                    "source": feed_config['name']
                })
            
            print(f"  Fetched {len(feed.entries[:10])} entries")
            
        except Exception as e:
            print(f"  Error fetching {feed_config['name']}: {e}")
    
    return all_entries

def main():
    """Main function to fetch feeds and save to JSON."""
    print("Starting RSS feed fetch...")
    print(f"Current time: {datetime.now().isoformat()}")
    
    # Fetch all feeds
    entries = fetch_feeds()
    
    # Create the data directory if it doesn't exist
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    # Prepare the output data
    output_data = {
        "lastUpdated": datetime.now().isoformat(),
        "feeds": entries
    }
    
    # Save to JSON file
    output_path = data_dir / "rss_feeds.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved {len(entries)} entries to {output_path}")
    print("RSS feed fetch completed!")

if __name__ == "__main__":
    main()
