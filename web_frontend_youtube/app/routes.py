from flask import Blueprint, render_template, request, jsonify, abort
import subprocess
import os
from .utils import (
    get_all_feeds,
    format_url_for_sfeed_markread,
    parse_sfeedrc,
    update_sfeedrc
)
from .config import URLS_FILE, BOOKMARKS_FILE, ITEMS_PER_PAGE, SFEEDRC_FILE

bp = Blueprint('routes', __name__)

@bp.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@bp.route('/api/feeds')
def api_feeds():
    """
    This is the main API endpoint for fetching videos.
    It handles filtering, searching, sorting, and pagination on the server-side.
    """
    try:
        # --- 1. Get query parameters from the request ---
        page = request.args.get('page', 1, type=int)
        view = request.args.get('view', 'unwatched').lower()
        search_query = request.args.get('search', '').lower()
        sort_by = request.args.get('sort_by', 'date-desc')

        # --- 2. Get all video items from the utility function (uses caching) ---
        all_items = get_all_feeds()

        # --- 3. Apply filtering based on the 'view' parameter ---
        if view == 'unwatched':
            filtered_items = [item for item in all_items if not item['watched']]
        elif view == 'watched':
            filtered_items = [item for item in all_items if item['watched']]
        elif view == 'bookmarked':
            filtered_items = [item for item in all_items if item['bookmarked']]
        else:  # 'all' view
            filtered_items = all_items

        # --- 4. Apply search filter if a query is provided ---
        if search_query:
            filtered_items = [
                item for item in filtered_items
                if search_query in item['title'].lower() or search_query in item['author'].lower()
            ]

        # --- 5. Apply sorting ---
        # The default sort is by timestamp descending (newest first).
        if sort_by == 'date-asc':
            filtered_items.sort(key=lambda x: int(x['timestamp']) if str(x.get('timestamp')).isdigit() else 0)
        elif sort_by == 'title-asc':
            filtered_items.sort(key=lambda x: x.get('title', '').lower())
        elif sort_by == 'author-asc':
            filtered_items.sort(key=lambda x: x.get('author', '').lower())
        else:  # 'date-desc' is the default
            filtered_items.sort(key=lambda x: int(x['timestamp']) if str(x.get('timestamp')).isdigit() else 0, reverse=True)

        # --- 6. Apply pagination to the final, filtered list ---
        total_items = len(filtered_items)
        start_index = (page - 1) * ITEMS_PER_PAGE
        end_index = start_index + ITEMS_PER_PAGE
        paginated_items = filtered_items[start_index:end_index]

        # --- 7. Return the data as JSON ---
        return jsonify({
            'feeds': paginated_items,
            'total': total_items,
            'page': page,
            'per_page': ITEMS_PER_PAGE,
            'has_more': end_index < total_items
        })
    except Exception as e:
        print(f"Error in /api/feeds: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/mark_watched', methods=['POST'])
def mark_watched():
    """Marks or unmarks a video as watched by calling an external script."""
    data = request.get_json()
    url = data.get('url')
    action = data.get('action', 'read')  # 'read' or 'unread'
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        formatted_url = format_url_for_sfeed_markread(url)
        # Using an external command 'sfeed_markread'
        process = subprocess.Popen(
            ['sfeed_markread', action, URLS_FILE],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=formatted_url)
        if process.returncode == 0:
            return jsonify({'success': True, 'action': action})
        else:
            return jsonify({'success': False, 'error': stderr}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/bookmark', methods=['POST'])
def bookmark():
    """Adds or removes a bookmark."""
    data = request.get_json()
    url = data.get('url')
    action = data.get('action', 'add')  # 'add' or 'remove'
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        # Read all current bookmarks
        with open(BOOKMARKS_FILE, 'r') as f:
            bookmarks = set(line.strip() for line in f)

        # Add or remove the URL
        if action == 'add':
            bookmarks.add(url)
        elif action == 'remove':
            bookmarks.discard(url)

        # Write the updated set back to the file
        with open(BOOKMARKS_FILE, 'w') as f:
            for bookmark_url in sorted(list(bookmarks)):
                f.write(bookmark_url + '\n')

        return jsonify({'success': True, 'action': action})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# --- Subscription Management Routes ---

@bp.route('/api/subscriptions', methods=['GET'])
def get_subscriptions():
    """API endpoint to get the list of current subscriptions."""
    try:
        subscriptions = parse_sfeedrc()
        return jsonify(subscriptions)
    except Exception as e:
        print(f"Error in /api/subscriptions: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/subscriptions', methods=['POST'])
def update_subscriptions():
    """API endpoint to update the entire list of subscriptions."""
    data = request.get_json()
    if 'subscriptions' not in data:
        return jsonify({'success': False, 'error': 'No subscriptions data provided'}), 400

    try:
        success = update_sfeedrc(data['subscriptions'])
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to update sfeedrc file.'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
