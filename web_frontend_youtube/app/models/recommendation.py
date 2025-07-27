import json
import os
import time
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from ..config import RSS_BASE_DIR

class RecommendationEngine:
    """
    A simple recommendation engine that learns user preferences based on:
    - Watch patterns (what they actually watch vs skip)
    - Channel preferences (which channels they watch more)
    - Time-based patterns (when they watch videos)
    - Content keywords (from titles)
    """
    
    def __init__(self):
        self.data_file = os.path.join(RSS_BASE_DIR, "recommendations.json")
        self.user_data = self._load_user_data()
    
    def _load_user_data(self):
        """Load user preference data from file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    # Ensure starred_videos exists
                    if 'starred_videos' not in data:
                        data['starred_videos'] = {}
                    # Convert to defaultdicts for easier usage
                    data['channel_scores'] = defaultdict(float, data.get('channel_scores', {}))
                    data['keyword_scores'] = defaultdict(float, data.get('keyword_scores', {}))
                    data['time_patterns'] = defaultdict(int, data.get('time_patterns', {}))
                    return data
            except (json.JSONDecodeError, IOError):
                pass
        
        # Default structure
        data = {
            'watched_videos': {},  # video_id: {'timestamp': int, 'title': str, 'author': str}
            'starred_videos': {},  # video_id: {'timestamp': int, 'title': str, 'author': str}
            'channel_scores': {},  # author: score
            'keyword_scores': {},  # keyword: score
            'time_patterns': {},  # hour: count
            'last_updated': time.time()
        }
        
        # Convert to defaultdicts for easier usage
        data['channel_scores'] = defaultdict(float, data['channel_scores'])
        data['keyword_scores'] = defaultdict(float, data['keyword_scores'])
        data['time_patterns'] = defaultdict(int, data['time_patterns'])
        
        return data
    
    def _save_user_data(self):
        """Save user preference data to file"""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            # Convert defaultdict to regular dict for JSON serialization
            data_to_save = {
                'watched_videos': self.user_data['watched_videos'],
                'starred_videos': self.user_data.get('starred_videos', {}),
                'channel_scores': dict(self.user_data['channel_scores']),
                'keyword_scores': dict(self.user_data['keyword_scores']),
                'time_patterns': dict(self.user_data['time_patterns']),
                'last_updated': time.time()
            }
            with open(self.data_file, 'w') as f:
                json.dump(data_to_save, f, indent=2)
        except IOError as e:
            print(f"Error saving recommendation data: {e}")
    
    def record_watch(self, video_id, title, author, timestamp=None, interaction_type='clicked'):
        """Record that a user watched a video
        
        Args:
            interaction_type: 'clicked' (opened video) or 'marked' (just marked as watched)
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Store watch record with interaction type
        self.user_data['watched_videos'][video_id] = {
            'timestamp': timestamp,
            'title': title,
            'author': author,
            'interaction_type': interaction_type
        }
        
        # Different reinforcement based on interaction type
        if interaction_type == 'clicked':
            # Full positive reinforcement for actually clicking to watch
            channel_boost = 1.0
            keyword_boost = 0.5
            time_boost = 1
        else:  # 'marked'
            # Lower reinforcement for just marking as watched
            channel_boost = 0.3
            keyword_boost = 0.15
            time_boost = 0
        
        # Update channel preference
        self.user_data['channel_scores'][author] += channel_boost
        
        # Update keyword scores from title
        keywords = self._extract_keywords(title)
        for keyword in keywords:
            self.user_data['keyword_scores'][keyword] += keyword_boost
        
        # Update time pattern (only for clicked videos)
        if time_boost > 0:
            hour = datetime.fromtimestamp(timestamp).hour
            self.user_data['time_patterns'][hour] += time_boost
        
        self._save_user_data()
    
    def record_star(self, video_id, title, author, timestamp=None):
        """Record that a user starred a video (higher preference)"""
        if timestamp is None:
            timestamp = time.time()
        
        # Store starred video record
        if 'starred_videos' not in self.user_data:
            self.user_data['starred_videos'] = {}
        
        self.user_data['starred_videos'][video_id] = {
            'timestamp': timestamp,
            'title': title,
            'author': author
        }
        
        # Higher positive reinforcement for starred videos
        self.user_data['channel_scores'][author] += 2.0  # Double the normal score
        
        # Higher keyword scores from starred video titles
        keywords = self._extract_keywords(title)
        for keyword in keywords:
            self.user_data['keyword_scores'][keyword] += 1.5  # Triple the normal score
        
        # Update time pattern with higher weight
        hour = datetime.fromtimestamp(timestamp).hour
        self.user_data['time_patterns'][hour] += 2
        
        self._save_user_data()
    
    def record_unstar(self, video_id, title, author):
        """Record that a user unstarred a video"""
        # Remove from starred videos
        if 'starred_videos' in self.user_data and video_id in self.user_data['starred_videos']:
            del self.user_data['starred_videos'][video_id]
        
        # Reduce the bonus scores (but don't go negative)
        self.user_data['channel_scores'][author] = max(0, self.user_data['channel_scores'][author] - 1.0)
        
        keywords = self._extract_keywords(title)
        for keyword in keywords:
            self.user_data['keyword_scores'][keyword] = max(0, self.user_data['keyword_scores'][keyword] - 1.0)
        
        self._save_user_data()
    
    def record_skip(self, video_id, title, author):
        """Record that a user skipped/ignored a video"""
        # Slight negative reinforcement for channels/keywords of skipped videos
        self.user_data['channel_scores'][author] -= 0.1
        
        keywords = self._extract_keywords(title)
        for keyword in keywords:
            self.user_data['keyword_scores'][keyword] -= 0.05
        
        self._save_user_data()
    
    def _extract_keywords(self, title):
        """Extract meaningful keywords from video title"""
        import re
        
        # Remove common words and extract meaningful terms
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we',
            'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her',
            'its', 'our', 'their', 'how', 'what', 'when', 'where', 'why', 'who', 
            'about', 'than'
        }
        
        # Clean and split title
        words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
        keywords = [word for word in words if word not in stop_words]
        
        return keywords[:10]  # Limit to top 10 keywords
    
    def calculate_video_score(self, video):
        """Calculate recommendation score for a video"""
        score = 0.0
        
        # Channel preference score (40% weight)
        channel_score = self.user_data['channel_scores'].get(video['author'], 0)
        score += channel_score * 0.4
        
        # Keyword matching score (30% weight)
        keywords = self._extract_keywords(video['title'])
        keyword_score = sum(self.user_data['keyword_scores'].get(kw, 0) for kw in keywords)
        score += keyword_score * 0.3
        
        # Recency bonus (20% weight) - newer videos get slight boost
        try:
            video_age_days = (time.time() - int(video['timestamp'])) / (24 * 3600)
            recency_score = max(0, 1 - (video_age_days / 30))  # Decay over 30 days
            score += recency_score * 0.2
        except (ValueError, TypeError):
            pass
        
        # Time pattern bonus (10% weight) - videos posted at user's active hours
        try:
            video_hour = datetime.fromtimestamp(int(video['timestamp'])).hour
            time_score = self.user_data['time_patterns'].get(video_hour, 0) / 10.0
            score += min(time_score, 1.0) * 0.1
        except (ValueError, TypeError):
            pass
        
        # Handle starred and watched videos
        video_id = video.get('video_id')
        if video_id:
            # Bonus for starred videos (even if watched)
            if video_id in self.user_data.get('starred_videos', {}):
                score *= 1.5  # 50% bonus for starred videos
            # Penalty for watched but not starred videos
            elif video_id in self.user_data['watched_videos']:
                score *= 0.1  # Heavy penalty for already watched
        
        return max(0, score)  # Ensure non-negative score
    
    def get_recommendations(self, videos, limit=None):
        """Sort videos by recommendation score"""
        if not videos:
            return videos
        
        # Calculate scores for all videos
        scored_videos = []
        for video in videos:
            score = self.calculate_video_score(video)
            scored_videos.append((score, video))
        
        # Sort by score (descending)
        scored_videos.sort(key=lambda x: x[0], reverse=True)
        
        # Return just the videos
        recommended = [video for score, video in scored_videos]
        
        return recommended[:limit] if limit else recommended
    
    def get_stats(self):
        """Get recommendation engine statistics"""
        try:
            # Convert defaultdicts to regular dicts and filter out zero/negative values
            channel_scores = {k: v for k, v in dict(self.user_data['channel_scores']).items() if v > 0}
            keyword_scores = {k: v for k, v in dict(self.user_data['keyword_scores']).items() if v > 0}
            time_patterns = {k: v for k, v in dict(self.user_data['time_patterns']).items() if v > 0}
            
            # Count different interaction types
            clicked_count = sum(1 for v in self.user_data['watched_videos'].values() 
                              if v.get('interaction_type') == 'clicked')
            marked_count = sum(1 for v in self.user_data['watched_videos'].values() 
                             if v.get('interaction_type') == 'marked')
            
            return {
                'total_watched': len(self.user_data['watched_videos']),
                'total_starred': len(self.user_data.get('starred_videos', {})),
                'clicked_to_watch': clicked_count,
                'marked_as_watched': marked_count,
                'top_channels': dict(Counter(channel_scores).most_common(10)),
                'top_keywords': dict(Counter(keyword_scores).most_common(10)),
                'active_hours': dict(Counter(time_patterns).most_common(5)),
                'last_updated': self.user_data.get('last_updated', time.time())
            }
        except Exception as e:
            print(f"Error in get_stats: {e}")
            # Return safe defaults
            return {
                'total_watched': 0,
                'total_starred': 0,
                'clicked_to_watch': 0,
                'marked_as_watched': 0,
                'top_channels': {},
                'top_keywords': {},
                'active_hours': {},
                'last_updated': time.time()
            }

# Global instance
recommendation_engine = RecommendationEngine()