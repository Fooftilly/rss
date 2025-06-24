#!/usr/bin/env python3

import os
import sys
import csv
import random
import subprocess
import webbrowser
from datetime import datetime

# Configuration - matching the web app
FEEDS_DIR = os.path.expanduser("~/rss/news/feeds")
URLS_FILE = os.path.expanduser("~/rss/urls")

# Increase CSV field size limit to handle large RSS fields
try:
    csv.field_size_limit(10 * 1024 * 1024)  # 10 MB
except OverflowError:
    max_limit = 2147483647
    csv.field_size_limit(max_limit)

def read_urls_file():
    """Read the list of read URLs"""
    if not os.path.exists(URLS_FILE):
        return set()

    with open(URLS_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def parse_feed_file(filepath):
    """Parse a single sfeed TSV file"""
    items = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            for row_num, row in enumerate(reader, 1):
                try:
                    if len(row) >= 8:
                        timestamp, title, link, content, content_type, guid, author, enclosure = row[:8]

                        # Convert timestamp to readable format
                        try:
                            dt = datetime.fromtimestamp(int(timestamp))
                            formatted_date = dt.strftime('%Y-%m-%d %H:%M')
                        except (ValueError, TypeError):
                            formatted_date = "Unknown"

                        items.append({
                            'timestamp': timestamp,
                            'title': title,
                            'link': link,
                            'date': formatted_date,
                            'feed_name': os.path.basename(filepath)
                        })
                except Exception as row_error:
                    print(f"Warning: Error parsing row {row_num} in {filepath}: {row_error}")
                    continue
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")

    return items

def get_unread_articles():
    """Get all unread articles from all feeds"""
    if not os.path.exists(FEEDS_DIR):
        print(f"Error: Feeds directory {FEEDS_DIR} does not exist")
        return []

    all_items = []
    read_urls = read_urls_file()

    for filename in os.listdir(FEEDS_DIR):
        filepath = os.path.join(FEEDS_DIR, filename)
        if os.path.isfile(filepath):
            items = parse_feed_file(filepath)
            # Filter out read articles
            unread_items = [item for item in items if item['link'] not in read_urls]
            all_items.extend(unread_items)

    # Sort by timestamp (newest first)
    all_items.sort(key=lambda x: int(x['timestamp']) if x['timestamp'].isdigit() else 0, reverse=True)
    return all_items

def mark_articles_read(urls):
    """Mark articles as read using sfeed_markread"""
    if not urls:
        return True

    try:
        # Format URLs with newlines for sfeed_markread
        urls_input = '\n'.join(urls) + '\n'

        # Use sfeed_markread to mark the URLs as read
        process = subprocess.Popen(
            ['sfeed_markread', 'read', URLS_FILE],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate(input=urls_input)

        if process.returncode == 0:
            return True
        else:
            print(f"Error marking articles as read: {stderr}")
            return False
    except Exception as e:
        print(f"Error running sfeed_markread: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: sfeed_random <number_of_articles>")
        print("Example: sfeed_random 15")
        sys.exit(1)

    try:
        num_articles = int(sys.argv[1])
        if num_articles <= 0:
            print("Error: Number of articles must be positive")
            sys.exit(1)
    except ValueError:
        print("Error: Please provide a valid number")
        sys.exit(1)

    # Get unread articles
    print("Reading unread articles...")
    unread_articles = get_unread_articles()

    if not unread_articles:
        print("No unread articles found")
        sys.exit(0)

    print(f"Found {len(unread_articles)} unread articles")

    # Select random articles
    if len(unread_articles) <= num_articles:
        selected_articles = unread_articles
        print(f"Selecting all {len(selected_articles)} available articles")
    else:
        selected_articles = random.sample(unread_articles, num_articles)
        print(f"Randomly selected {num_articles} articles")

    # Extract URLs for marking as read
    urls_to_mark = [article['link'] for article in selected_articles]

    # Open articles in browser
    print("\nOpening articles:")
    for i, article in enumerate(selected_articles, 1):
        print(f"{i:2d}. {article['title'][:80]}{'...' if len(article['title']) > 80 else ''}")
        print(f"     {article['link']}")
        print(f"     [{article['feed_name']}] {article['date']}")

        try:
            webbrowser.open(article['link'])
        except Exception as e:
            print(f"     Warning: Could not open URL: {e}")

        print()

    # Mark articles as read
    print("Marking articles as read...")
    if mark_articles_read(urls_to_mark):
        print(f"Successfully marked {len(urls_to_mark)} articles as read")
    else:
        print("Warning: Some articles may not have been marked as read")

if __name__ == '__main__':
    main()
