from flask import Blueprint, render_template, request, jsonify, abort
import subprocess
import os
from .utils import (
    get_all_feeds,
    format_url_for_sfeed_markread,
    parse_sfeedrc,
    update_sfeedrc
)
from .config import URLS_FILE, BOOKMARKS_FILE, STARRED_FILE, DISLIKED_FILE, ITEMS_PER_PAGE, SFEEDRC_FILE
from .models.unified_adapter import recommendation_engine

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
        elif view == 'discover':
            # Show recommended videos that haven't been starred
            filtered_items = [item for item in all_items if not item.get('starred', False)]
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
        # For discover view, always use recommendations unless explicitly overridden
        if view == 'discover' and sort_by == 'date-desc':
            # Default to recommendation sorting for discover view
            try:
                filtered_items = recommendation_engine.get_recommendations(filtered_items)
            except Exception as e:
                print(f"Error in recommendation sorting: {e}")
                # Fallback to date sorting if recommendations fail
                filtered_items.sort(key=lambda x: int(x['timestamp']) if str(x.get('timestamp')).isdigit() else 0, reverse=True)
        elif sort_by == 'date-asc':
            filtered_items.sort(key=lambda x: int(x['timestamp']) if str(x.get('timestamp')).isdigit() else 0)
        elif sort_by == 'title-asc':
            filtered_items.sort(key=lambda x: x.get('title', '').lower())
        elif sort_by == 'author-asc':
            filtered_items.sort(key=lambda x: x.get('author', '').lower())
        elif sort_by == 'recommended':
            # Use recommendation engine to sort videos
            try:
                filtered_items = recommendation_engine.get_recommendations(filtered_items)
            except Exception as e:
                print(f"Error in recommendation sorting: {e}")
                # Fallback to date sorting if recommendations fail
                filtered_items.sort(key=lambda x: int(x['timestamp']) if str(x.get('timestamp')).isdigit() else 0, reverse=True)
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
            # Record interaction for recommendation engine
            if action == 'read':
                video_id = data.get('video_id')
                title = data.get('title', '')
                author = data.get('author', '')
                interaction_type = data.get('interaction_type', 'marked')  # 'clicked' or 'marked'
                if video_id and title and author:
                    recommendation_engine.record_watch(video_id, title, author, interaction_type=interaction_type)
            
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
        # Ensure the bookmarks file exists
        if not os.path.exists(BOOKMARKS_FILE):
            with open(BOOKMARKS_FILE, 'w') as f:
                pass  # Create empty file

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

@bp.route('/api/track_interaction', methods=['POST'])
def track_interaction():
    """Track user interactions for recommendation learning"""
    data = request.get_json()
    interaction_type = data.get('type')  # 'skip', 'view', 'click'
    video_id = data.get('video_id')
    title = data.get('title', '')
    author = data.get('author', '')
    
    if not all([interaction_type, video_id, title, author]):
        return jsonify({'success': False, 'error': 'Missing required data'}), 400
    
    try:
        if interaction_type == 'skip':
            recommendation_engine.record_skip(video_id, title, author)
        elif interaction_type == 'view':
            recommendation_engine.record_watch(video_id, title, author, interaction_type='clicked')
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/star_video', methods=['POST'])
def star_video():
    """Star or unstar a video for higher preference"""
    data = request.get_json()
    video_id = data.get('video_id')
    title = data.get('title', '')
    author = data.get('author', '')
    action = data.get('action', 'star')  # 'star' or 'unstar'
    
    if not all([video_id, title, author]):
        return jsonify({'success': False, 'error': 'Missing required data'}), 400
    
    try:
        if action == 'star':
            recommendation_engine.record_star(video_id, title, author)
        elif action == 'unstar':
            recommendation_engine.record_unstar(video_id, title, author)
        
        return jsonify({'success': True, 'action': action})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/recommendation_stats')
def recommendation_stats():
    """Get recommendation engine statistics"""
    try:
        print("Getting recommendation stats...")
        stats = recommendation_engine.get_stats()
        
        # Add neural network stats
        neural_stats = recommendation_engine.get_neural_stats()
        stats.update(neural_stats)
        
        print(f"Stats retrieved: {stats}")
        
        # Ensure all values are JSON serializable
        safe_stats = {}
        for key, value in stats.items():
            if isinstance(value, dict):
                # Convert any non-string keys to strings and ensure values are serializable
                safe_stats[key] = {str(k): float(v) if isinstance(v, (int, float)) else v 
                                 for k, v in value.items()}
            else:
                safe_stats[key] = float(value) if isinstance(value, (int, float)) else value
        
        print(f"Safe stats: {safe_stats}")
        return jsonify(safe_stats)
    except Exception as e:
        print(f"Error in recommendation_stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/neural/train', methods=['POST'])
def train_neural_network():
    """Train the neural network model"""
    try:
        data = request.get_json() or {}
        force_retrain = data.get('force_retrain', False)
        
        success = recommendation_engine.train_neural_network(force_retrain=force_retrain)
        
        if success:
            stats = recommendation_engine.get_neural_stats()
            return jsonify({
                'success': True,
                'message': 'Neural network training completed',
                'stats': stats
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Neural network training failed'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/neural/insights', methods=['POST'])
def get_neural_insights():
    """Get neural network insights for a video title"""
    try:
        data = request.get_json()
        title = data.get('title', '')
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400
        
        insights = recommendation_engine.get_neural_insights(title)
        
        return jsonify({
            'success': True,
            'title': title,
            'insights': insights
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/neural/stats')
def neural_stats():
    """Get neural network model statistics"""
    try:
        stats = recommendation_engine.get_neural_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'API is working'})

@bp.route('/favicon.ico')
def favicon():
    """Serve favicon.ico"""
    from flask import send_from_directory
    return send_from_directory('static', 'favicon.ico')

@bp.route('/favicon-test')
def favicon_test():
    """Serve favicon test page"""
    from flask import send_from_directory
    return send_from_directory('static', 'favicon-test.html')

@bp.route('/star', methods=['POST'])
def star():
    """Stars or unstars a video."""
    data = request.get_json()
    url = data.get('url')
    action = data.get('action', 'star')  # 'star' or 'unstar'
    video_id = data.get('video_id', '')
    title = data.get('title', '')
    author = data.get('author', '')
    
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        # Ensure the starred file exists
        if not os.path.exists(STARRED_FILE):
            with open(STARRED_FILE, 'w') as f:
                pass  # Create empty file

        # Read all current starred videos
        with open(STARRED_FILE, 'r') as f:
            starred = set(line.strip() for line in f)

        # Add or remove the URL
        if action == 'star':
            starred.add(url)
            # Also record in recommendation engine
            if video_id and title and author:
                recommendation_engine.record_star(video_id, title, author)
        elif action == 'unstar':
            starred.discard(url)
            # Also record in recommendation engine
            if video_id and title and author:
                recommendation_engine.record_unstar(video_id, title, author)

        # Write the updated set back to the file
        with open(STARRED_FILE, 'w') as f:
            for starred_url in sorted(list(starred)):
                f.write(starred_url + '\n')

        return jsonify({'success': True, 'action': action})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/dislike', methods=['POST'])
def dislike():
    """Dislikes or removes dislike from a video."""
    data = request.get_json()
    url = data.get('url')
    video_id = data.get('video_id', '')
    title = data.get('title', '')
    author = data.get('author', '')
    action = data.get('action', 'dislike')  # 'dislike' or 'undislike'
    
    if not all([url, video_id, title, author]):
        return jsonify({'success': False, 'error': 'Missing required data'}), 400

    try:
        # Ensure the disliked file exists
        if not os.path.exists(DISLIKED_FILE):
            with open(DISLIKED_FILE, 'w') as f:
                pass  # Create empty file

        # Read all current disliked videos
        with open(DISLIKED_FILE, 'r') as f:
            disliked = set(line.strip() for line in f)

        # Add or remove the URL
        if action == 'dislike':
            disliked.add(url)
            # Also record in recommendation engine
            recommendation_engine.record_dislike(video_id, title, author)
        elif action == 'undislike':
            disliked.discard(url)
            # Also record in recommendation engine
            recommendation_engine.record_undislike(video_id, title, author)

        # Write the updated set back to the file
        with open(DISLIKED_FILE, 'w') as f:
            for disliked_url in sorted(list(disliked)):
                f.write(disliked_url + '\n')

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
