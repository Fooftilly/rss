from flask import Blueprint, render_template, request, jsonify, abort
import subprocess
import os
import sys
from .utils import (
    get_all_feeds,
    format_url_for_sfeed_markread,
    parse_sfeedrc,
    update_sfeedrc,
    extract_article_preview,
    format_timestamp,
    invalidate_cache
)
from .config import URLS_FILE, BOOKMARKS_FILE, STARRED_FILE, DISLIKED_FILE, ITEMS_PER_PAGE, SFEEDRC_FILE

# Import the unified recommendation engine
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from shared_models.unified_recommendation import unified_recommendation_engine

bp = Blueprint('routes', __name__)

@bp.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@bp.route('/api/feeds')
def api_feeds():
    """
    Main API endpoint for fetching articles.
    Handles filtering, searching, sorting, and pagination on the server-side.
    """
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        view = request.args.get('view', 'unread').lower()
        search_query = request.args.get('search', '').lower()
        sort_by = request.args.get('sort_by', 'date-desc')

        # Get all articles
        all_articles = get_all_feeds()

        # Apply filtering based on view
        if view == 'unread':
            # Show unread articles that are not disliked
            filtered_articles = [article for article in all_articles if not article['read'] and not article['disliked']]
        elif view == 'read':
            # Show read articles that are not disliked
            filtered_articles = [article for article in all_articles if article['read'] and not article['disliked']]
        elif view == 'bookmarked':
            # Show bookmarked articles that are not disliked
            filtered_articles = [article for article in all_articles if article['bookmarked'] and not article['disliked']]
        elif view == 'discover':
            # Show recommended articles that haven't been starred and are not disliked
            filtered_articles = [article for article in all_articles if not article.get('starred', False) and not article['disliked']]
        else:  # 'all' view
            filtered_articles = all_articles
        
        # Optional debug (disabled for performance)
        # print(f"View: {view}, Total articles: {len(all_articles)}, Filtered: {len(filtered_articles)}")

        # Apply search filter
        if search_query:
            filtered_articles = [
                article for article in filtered_articles
                if search_query in article['title'].lower() 
                or search_query in article['author'].lower()
                or search_query in article.get('content', '').lower()
            ]

        # Apply sorting
        if view == 'discover' and sort_by == 'date-desc':
            # Default to recommendation sorting for discover view
            try:
                filtered_articles = unified_recommendation_engine.get_recommendations(filtered_articles, 'news')
            except Exception as e:
                print(f"Error in recommendation sorting: {e}")
                # Fallback to date sorting
                filtered_articles.sort(key=lambda x: int(x['timestamp']) if str(x.get('timestamp')).isdigit() else 0, reverse=True)
        elif sort_by == 'date-asc':
            filtered_articles.sort(key=lambda x: int(x['timestamp']) if str(x.get('timestamp')).isdigit() else 0)
        elif sort_by == 'title-asc':
            filtered_articles.sort(key=lambda x: x.get('title', '').lower())
        elif sort_by == 'author-asc':
            filtered_articles.sort(key=lambda x: x.get('author', '').lower())
        elif sort_by == 'recommended':
            # Use unified recommendation engine
            try:
                filtered_articles = unified_recommendation_engine.get_recommendations(filtered_articles, 'news')
            except Exception as e:
                print(f"Error in recommendation sorting: {e}")
                # Fallback to date sorting
                filtered_articles.sort(key=lambda x: int(x['timestamp']) if str(x.get('timestamp')).isdigit() else 0, reverse=True)
        else:  # 'date-desc' is the default
            filtered_articles.sort(key=lambda x: int(x['timestamp']) if str(x.get('timestamp')).isdigit() else 0, reverse=True)

        # Apply pagination first to reduce processing
        total_articles = len(filtered_articles)
        start_index = (page - 1) * ITEMS_PER_PAGE
        end_index = start_index + ITEMS_PER_PAGE
        paginated_articles = filtered_articles[start_index:end_index]

        # Add article previews and format timestamps only for paginated articles
        for article in paginated_articles:
            article['preview'] = extract_article_preview(article.get('content', ''))
            article['formatted_timestamp'] = format_timestamp(article['timestamp'])

        return jsonify({
            'feeds': paginated_articles,
            'total': total_articles,
            'page': page,
            'per_page': ITEMS_PER_PAGE,
            'has_more': end_index < total_articles
        })
    except Exception as e:
        print(f"Error in /api/feeds: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/mark_read', methods=['POST'])
def mark_read():
    """Marks or unmarks an article as read."""
    data = request.get_json()
    url = data.get('url')
    action = data.get('action', 'read')  # 'read' or 'unread'
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        formatted_url = format_url_for_sfeed_markread(url)
        
        # Optional debug (disabled for performance)
        # print(f"Marking URL as {action}: {url}")
        
        # Using sfeed_markread command
        process = subprocess.Popen(
            ['sfeed_markread', action, URLS_FILE],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=formatted_url)
        
        if process.returncode == 0:
            # Debug: Verify the file was updated
            if os.path.exists(URLS_FILE):
                with open(URLS_FILE, 'r') as f:
                    urls_in_file = f.read()
                    # Optional debug (disabled for performance)
                    # if action == 'read' and url in urls_in_file:
                    #     print(f"✅ URL successfully added to read file")
                    # elif action == 'unread' and url not in urls_in_file:
                    #     print(f"✅ URL successfully removed from read file")
            
            # Invalidate cache to ensure fresh data on next request
            invalidate_cache()
            
            # Record interaction for unified recommendation engine
            if action == 'read':
                article_id = data.get('article_id')
                title = data.get('title', '')
                author = data.get('author', '')
                interaction_type = data.get('interaction_type', 'marked')  # 'clicked' or 'marked'
                if article_id and title and author:
                    unified_recommendation_engine.record_interaction(
                        article_id, 'news', title, author, 'article', 
                        'read', interaction_type
                    )
            
            return jsonify({'success': True, 'action': action})
        else:
            print(f"❌ sfeed_markread failed: {stderr}")
            return jsonify({'success': False, 'error': stderr}), 500
    except Exception as e:
        print(f"❌ Error in mark_read: {e}")
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
        # Ensure the bookmarks file exists
        if not os.path.exists(BOOKMARKS_FILE):
            with open(BOOKMARKS_FILE, 'w') as f:
                pass

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

        # Invalidate cache
        invalidate_cache()
        
        return jsonify({'success': True, 'action': action})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/star', methods=['POST'])
def star():
    """Stars or unstars an article."""
    data = request.get_json()
    url = data.get('url')
    action = data.get('action', 'star')  # 'star' or 'unstar'
    article_id = data.get('article_id', '')
    title = data.get('title', '')
    author = data.get('author', '')
    
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        # Ensure the starred file exists
        if not os.path.exists(STARRED_FILE):
            with open(STARRED_FILE, 'w') as f:
                pass

        # Read all current starred articles
        with open(STARRED_FILE, 'r') as f:
            starred = set(line.strip() for line in f)

        # Add or remove the URL
        if action == 'star':
            starred.add(url)
            # Record in unified recommendation engine
            if article_id and title and author:
                unified_recommendation_engine.record_interaction(
                    article_id, 'news', title, author, 'article', 'starred'
                )
        elif action == 'unstar':
            starred.discard(url)
            # Note: We don't have an "unstar" interaction type in the unified engine
            # The system will handle this through the absence of the starred interaction

        # Write the updated set back to the file
        with open(STARRED_FILE, 'w') as f:
            for starred_url in sorted(list(starred)):
                f.write(starred_url + '\n')

        # Invalidate cache
        invalidate_cache()
        
        return jsonify({'success': True, 'action': action})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/dislike', methods=['POST'])
def dislike():
    """Dislikes or removes dislike from an article."""
    data = request.get_json()
    url = data.get('url')
    article_id = data.get('article_id', '')
    title = data.get('title', '')
    author = data.get('author', '')
    action = data.get('action', 'dislike')  # 'dislike' or 'undislike'
    
    if not all([url, article_id, title, author]):
        return jsonify({'success': False, 'error': 'Missing required data'}), 400

    try:
        # Optional debug (disabled for performance)
        # print(f"Processing {action} for URL: {url}")
        
        # Ensure the disliked file exists
        if not os.path.exists(DISLIKED_FILE):
            with open(DISLIKED_FILE, 'w') as f:
                pass

        # Read all current disliked articles
        with open(DISLIKED_FILE, 'r') as f:
            disliked = set(line.strip() for line in f)

        # Add or remove the URL
        if action == 'dislike':
            disliked.add(url)
            # Record in unified recommendation engine
            unified_recommendation_engine.record_interaction(
                article_id, 'news', title, author, 'article', 'disliked'
            )
            # print(f"✅ Added URL to disliked list")
        elif action == 'undislike':
            disliked.discard(url)
            # print(f"✅ Removed URL from disliked list")
            # Note: We don't have an "undislike" interaction type in the unified engine

        # Write the updated set back to the file
        with open(DISLIKED_FILE, 'w') as f:
            for disliked_url in sorted(list(disliked)):
                f.write(disliked_url + '\n')

        # Invalidate cache
        invalidate_cache()
        
        # print(f"✅ Disliked file updated with {len(disliked)} URLs")
        return jsonify({'success': True, 'action': action})
    except Exception as e:
        print(f"❌ Error in dislike: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/track_interaction', methods=['POST'])
def track_interaction():
    """Track user interactions for recommendation learning"""
    data = request.get_json()
    interaction_type = data.get('type')  # 'skip', 'view', 'click'
    article_id = data.get('article_id')
    title = data.get('title', '')
    author = data.get('author', '')
    
    if not all([interaction_type, article_id, title, author]):
        return jsonify({'success': False, 'error': 'Missing required data'}), 400
    
    try:
        if interaction_type == 'skip':
            # For skips, we could implement a negative signal, but for now we'll just ignore
            pass
        elif interaction_type in ['view', 'click']:
            unified_recommendation_engine.record_interaction(
                article_id, 'news', title, author, 'article', 'read', 'clicked'
            )
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/recommendation_stats')
def recommendation_stats():
    """Get unified recommendation engine statistics for news"""
    try:
        stats = unified_recommendation_engine.get_stats('news')
        
        # Ensure all values are JSON serializable
        safe_stats = {}
        for key, value in stats.items():
            if isinstance(value, dict):
                safe_stats[key] = {str(k): float(v) if isinstance(v, (int, float)) else v 
                                 for k, v in value.items()}
            else:
                safe_stats[key] = float(value) if isinstance(value, (int, float)) else value
        
        return jsonify(safe_stats)
    except Exception as e:
        print(f"Error in recommendation_stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/unified_stats')
def unified_stats():
    """Get unified recommendation engine statistics across all platforms"""
    try:
        stats = unified_recommendation_engine.get_stats()  # No platform filter = unified stats
        
        # Ensure all values are JSON serializable
        safe_stats = {}
        for key, value in stats.items():
            if isinstance(value, dict):
                safe_stats[key] = {str(k): float(v) if isinstance(v, (int, float)) else v 
                                 for k, v in value.items()}
            else:
                safe_stats[key] = float(value) if isinstance(value, (int, float)) else value
        
        return jsonify(safe_stats)
    except Exception as e:
        print(f"Error in unified_stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'News API is working'})

@bp.route('/favicon.ico')
def favicon():
    """Serve favicon.ico"""
    from flask import send_from_directory
    return send_from_directory('static', 'favicon.ico')

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