"""
Adapter to make the unified recommendation engine compatible with the existing YouTube frontend
"""
import sys
import os

# Add the shared models to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from shared_models.unified_recommendation import unified_recommendation_engine

class YouTubeRecommendationAdapter:
    """
    Adapter class that provides the same interface as the old recommendation engine
    but uses the unified system underneath
    """
    
    def __init__(self):
        self.unified_engine = unified_recommendation_engine
    
    def record_watch(self, video_id, title, author, timestamp=None, interaction_type='clicked'):
        """Record that a user watched a video"""
        self.unified_engine.record_interaction(
            video_id, 'youtube', title, author, 'video', 
            'watched', interaction_type, timestamp
        )
    
    def record_star(self, video_id, title, author, timestamp=None):
        """Record that a user starred a video"""
        self.unified_engine.record_interaction(
            video_id, 'youtube', title, author, 'video', 
            'starred', None, timestamp
        )
    
    def record_unstar(self, video_id, title, author):
        """Record that a user unstarred a video"""
        # The unified system doesn't have explicit unstar - it's handled by absence
        # We could implement this by removing the starred interaction if needed
        pass
    
    def record_dislike(self, video_id, title, author, timestamp=None):
        """Record that a user dislikes a video"""
        self.unified_engine.record_interaction(
            video_id, 'youtube', title, author, 'video', 
            'disliked', None, timestamp
        )
    
    def record_undislike(self, video_id, title, author):
        """Record that a user removed dislike from a video"""
        # Similar to unstar - handled by absence in unified system
        pass
    
    def record_skip(self, video_id, title, author):
        """Record that a user skipped a video"""
        # Could implement as a negative signal in the unified system
        # For now, we'll skip this as the unified system doesn't have explicit skip tracking
        pass
    
    def calculate_video_score(self, video):
        """Calculate recommendation score for a video"""
        return self.unified_engine.calculate_content_score(video, 'youtube')
    
    def get_recommendations(self, videos, limit=None):
        """Sort videos by recommendation score"""
        return self.unified_engine.get_recommendations(videos, 'youtube', limit)
    
    def get_stats(self):
        """Get recommendation engine statistics"""
        stats = self.unified_engine.get_stats('youtube')
        
        # Map unified stats to the expected YouTube format
        return {
            'total_watched': stats.get('total_consumed', 0),
            'total_starred': stats.get('total_starred', 0),
            'total_disliked': stats.get('total_disliked', 0),
            'clicked_to_watch': stats.get('clicked_to_consume', 0),
            'marked_as_watched': stats.get('marked_as_consumed', 0),
            'top_channels': stats.get('top_sources', {}),
            'top_keywords': stats.get('top_keywords', {}),
            'active_hours': {},  # Not implemented in unified system yet
            'last_updated': stats.get('last_updated', 0)
        }
    
    def cleanup_old_data(self, days_to_keep=90):
        """Clean up old data"""
        self.unified_engine.cleanup_old_data(days_to_keep)
    
    def train_neural_network(self, force_retrain=False):
        """Train neural network - not implemented in unified system yet"""
        return False
    
    def get_neural_insights(self, title):
        """Get neural insights - not implemented in unified system yet"""
        return {}
    
    def get_neural_stats(self):
        """Get neural stats - not implemented in unified system yet"""
        return {'neural_available': False}

# Create the adapter instance
recommendation_engine = YouTubeRecommendationAdapter()