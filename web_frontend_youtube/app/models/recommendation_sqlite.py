import sqlite3
import os
import time
import threading
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from contextlib import contextmanager
from ..config import RSS_BASE_DIR

# Import neural network components
try:
    from .keyword_neural_net import NeuralRecommendationEngine
    NEURAL_NET_AVAILABLE = True
except ImportError as e:
    print(f"Neural network not available: {e}")
    NEURAL_NET_AVAILABLE = False

class RecommendationEngine:
    """
    SQLite-based recommendation engine that learns user preferences based on:
    - Watch patterns (what they actually watch vs skip)
    - Channel preferences (which channels they watch more)
    - Time-based patterns (when they watch videos)
    - Content keywords (from titles)
    """
    
    def __init__(self):
        self.db_path = os.path.join(RSS_BASE_DIR, "recommendations.db")
        self._lock = threading.RLock()  # Thread-safe operations
        self._init_database()
        
        # Initialize neural network engine if available
        self.neural_engine = None
        if NEURAL_NET_AVAILABLE:
            try:
                self.neural_engine = NeuralRecommendationEngine(self.db_path)
                print("✅ Neural network engine initialized")
            except Exception as e:
                print(f"⚠️  Neural network initialization failed: {e}")
                self.neural_engine = None
    
    def _init_database(self):
        """Initialize the database schema if it doesn't exist"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Enable foreign keys and WAL mode for better concurrency
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = NORMAL")
            
            # Create tables
            cursor.executescript("""
            -- Videos table to store video metadata
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                first_seen_timestamp REAL NOT NULL,
                last_updated REAL NOT NULL
            );
            
            -- User interactions with videos
            CREATE TABLE IF NOT EXISTS user_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                interaction_type TEXT NOT NULL, -- 'watched', 'starred', 'disliked'
                interaction_subtype TEXT, -- 'clicked', 'marked' for watched
                timestamp REAL NOT NULL,
                FOREIGN KEY (video_id) REFERENCES videos (video_id),
                UNIQUE(video_id, interaction_type) -- One record per interaction type per video
            );
            
            -- Channel scores (derived from interactions)
            CREATE TABLE IF NOT EXISTS channel_scores (
                channel_name TEXT PRIMARY KEY,
                score REAL NOT NULL DEFAULT 0.0,
                last_updated REAL NOT NULL
            );
            
            -- Keyword scores (derived from video titles)
            CREATE TABLE IF NOT EXISTS keyword_scores (
                keyword TEXT PRIMARY KEY,
                score REAL NOT NULL DEFAULT 0.0,
                last_updated REAL NOT NULL
            );
            
            -- Time patterns (optional, for future use)
            CREATE TABLE IF NOT EXISTS time_patterns (
                hour INTEGER PRIMARY KEY CHECK (hour >= 0 AND hour <= 23),
                count INTEGER NOT NULL DEFAULT 0,
                last_updated REAL NOT NULL
            );
            
            -- Indexes for better performance
            CREATE INDEX IF NOT EXISTS idx_interactions_video_id ON user_interactions(video_id);
            CREATE INDEX IF NOT EXISTS idx_interactions_type ON user_interactions(interaction_type);
            CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON user_interactions(timestamp);
            CREATE INDEX IF NOT EXISTS idx_videos_author ON videos(author);
            CREATE INDEX IF NOT EXISTS idx_channel_scores_score ON channel_scores(score DESC);
            CREATE INDEX IF NOT EXISTS idx_keyword_scores_score ON keyword_scores(score DESC);
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def _ensure_video_exists(self, cursor, video_id, title, author, timestamp=None):
        """Ensure a video record exists in the database"""
        if timestamp is None:
            timestamp = time.time()
        
        cursor.execute("""
            INSERT OR IGNORE INTO videos 
            (video_id, title, author, first_seen_timestamp, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (video_id, title, author, timestamp, timestamp))
        
        # Update title/author if they've changed
        cursor.execute("""
            UPDATE videos 
            SET title = ?, author = ?, last_updated = ?
            WHERE video_id = ? AND (title != ? OR author != ?)
        """, (title, author, timestamp, video_id, title, author))
    
    def _update_channel_score(self, cursor, channel_name, score_delta):
        """Update channel score atomically"""
        cursor.execute("""
            INSERT INTO channel_scores (channel_name, score, last_updated)
            VALUES (?, ?, ?)
            ON CONFLICT(channel_name) DO UPDATE SET
                score = score + ?,
                last_updated = ?
        """, (channel_name, score_delta, time.time(), score_delta, time.time()))
    
    def _update_keyword_scores(self, cursor, title, score_delta):
        """Update keyword scores from video title"""
        keywords = self._extract_keywords(title)
        current_time = time.time()
        
        for keyword in keywords:
            cursor.execute("""
                INSERT INTO keyword_scores (keyword, score, last_updated)
                VALUES (?, ?, ?)
                ON CONFLICT(keyword) DO UPDATE SET
                    score = score + ?,
                    last_updated = ?
            """, (keyword, score_delta, current_time, score_delta, current_time))
    
    def record_watch(self, video_id, title, author, timestamp=None, interaction_type='clicked'):
        """Record that a user watched a video
        
        Args:
            interaction_type: 'clicked' (opened video) or 'marked' (just marked as watched)
        """
        if timestamp is None:
            timestamp = time.time()
        
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # Ensure video exists
                    self._ensure_video_exists(cursor, video_id, title, author, timestamp)
                    
                    # Record interaction
                    cursor.execute("""
                        INSERT OR REPLACE INTO user_interactions 
                        (video_id, interaction_type, interaction_subtype, timestamp)
                        VALUES (?, ?, ?, ?)
                    """, (video_id, 'watched', interaction_type, timestamp))
                    
                    # Different reinforcement based on interaction type
                    if interaction_type == 'clicked':
                        channel_boost = 1.0
                        keyword_boost = 0.5
                    else:  # 'marked'
                        channel_boost = 0.3
                        keyword_boost = 0.15
                    
                    # Update scores
                    self._update_channel_score(cursor, author, channel_boost)
                    self._update_keyword_scores(cursor, title, keyword_boost)
                    
                    conn.commit()
                    
                except sqlite3.Error as e:
                    conn.rollback()
                    raise e
    
    def record_star(self, video_id, title, author, timestamp=None):
        """Record that a user starred a video (higher preference)"""
        if timestamp is None:
            timestamp = time.time()
        
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # Ensure video exists
                    self._ensure_video_exists(cursor, video_id, title, author, timestamp)
                    
                    # Record interaction
                    cursor.execute("""
                        INSERT OR REPLACE INTO user_interactions 
                        (video_id, interaction_type, interaction_subtype, timestamp)
                        VALUES (?, ?, ?, ?)
                    """, (video_id, 'starred', None, timestamp))
                    
                    # Higher positive reinforcement for starred videos
                    self._update_channel_score(cursor, author, 2.0)
                    self._update_keyword_scores(cursor, title, 1.5)
                    
                    conn.commit()
                    
                except sqlite3.Error as e:
                    conn.rollback()
                    raise e
    
    def record_unstar(self, video_id, title, author):
        """Record that a user unstarred a video"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # Remove starred interaction
                    cursor.execute("""
                        DELETE FROM user_interactions 
                        WHERE video_id = ? AND interaction_type = 'starred'
                    """, (video_id,))
                    
                    # Reduce the bonus scores (but don't go too negative)
                    cursor.execute("""
                        UPDATE channel_scores 
                        SET score = MAX(0, score - 1.0), last_updated = ?
                        WHERE channel_name = ?
                    """, (time.time(), author))
                    
                    # Reduce keyword scores
                    keywords = self._extract_keywords(title)
                    for keyword in keywords:
                        cursor.execute("""
                            UPDATE keyword_scores 
                            SET score = MAX(0, score - 1.0), last_updated = ?
                            WHERE keyword = ?
                        """, (time.time(), keyword))
                    
                    conn.commit()
                    
                except sqlite3.Error as e:
                    conn.rollback()
                    raise e
    
    def record_dislike(self, video_id, title, author, timestamp=None):
        """Record that a user dislikes a video/channel (decrease preference)"""
        if timestamp is None:
            timestamp = time.time()
        
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # Ensure video exists
                    self._ensure_video_exists(cursor, video_id, title, author, timestamp)
                    
                    # Record interaction
                    cursor.execute("""
                        INSERT OR REPLACE INTO user_interactions 
                        (video_id, interaction_type, interaction_subtype, timestamp)
                        VALUES (?, ?, ?, ?)
                    """, (video_id, 'disliked', None, timestamp))
                    
                    # Significant negative reinforcement
                    self._update_channel_score(cursor, author, -2.0)
                    self._update_keyword_scores(cursor, title, -1.0)
                    
                    conn.commit()
                    
                except sqlite3.Error as e:
                    conn.rollback()
                    raise e
    
    def record_undislike(self, video_id, title, author):
        """Record that a user removed dislike from a video"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # Remove disliked interaction
                    cursor.execute("""
                        DELETE FROM user_interactions 
                        WHERE video_id = ? AND interaction_type = 'disliked'
                    """, (video_id,))
                    
                    # Restore some of the negative scores (but cap at reasonable values)
                    cursor.execute("""
                        UPDATE channel_scores 
                        SET score = MIN(score + 1.5, 0.5), last_updated = ?
                        WHERE channel_name = ?
                    """, (time.time(), author))
                    
                    # Restore keyword scores
                    keywords = self._extract_keywords(title)
                    for keyword in keywords:
                        cursor.execute("""
                            UPDATE keyword_scores 
                            SET score = MIN(score + 0.75, 0.25), last_updated = ?
                            WHERE keyword = ?
                        """, (time.time(), keyword))
                    
                    conn.commit()
                    
                except sqlite3.Error as e:
                    conn.rollback()
                    raise e
    
    def record_skip(self, video_id, title, author):
        """Record that a user skipped/ignored a video"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # Slight negative reinforcement
                    self._update_channel_score(cursor, author, -0.1)
                    self._update_keyword_scores(cursor, title, -0.05)
                    
                    conn.commit()
                    
                except sqlite3.Error as e:
                    conn.rollback()
                    raise e
    
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
            'about', 'than', 'not', 'part', 'all', 'can'
        }
        
        # Clean and split title
        words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
        keywords = [word for word in words if word not in stop_words]
        
        return keywords[:10]  # Limit to top 10 keywords
    
    def calculate_video_score(self, video):
        """Calculate recommendation score for a video using both traditional and neural methods"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            score = 0.0
            video_id = video.get('video_id')
            
            # Traditional scoring components
            
            # Channel preference score (3% weight, reduced to make room for neural)
            cursor.execute("SELECT score FROM channel_scores WHERE channel_name = ?", (video['author'],))
            row = cursor.fetchone()
            if row:
                channel_score = row[0]
                # Apply diminishing returns
                normalized_channel_score = channel_score / (1 + abs(channel_score) * 0.1)
                score += normalized_channel_score * 0.03
            
            # Traditional keyword matching score (40% weight, reduced)
            keywords = self._extract_keywords(video['title'])
            if keywords:
                cursor.execute(f"""
                    SELECT SUM(score) FROM keyword_scores 
                    WHERE keyword IN ({','.join(['?'] * len(keywords))})
                """, keywords)
                row = cursor.fetchone()
                if row and row[0]:
                    keyword_score = row[0]
                    score += keyword_score * 0.40
            
            # Neural network score (35% weight - NEW!)
            if self.neural_engine:
                try:
                    neural_score = self.neural_engine.get_neural_score(video['title'])
                    score += neural_score * 0.35
                except Exception as e:
                    print(f"Neural scoring failed: {e}")
            
            # Recency bonus (22% weight, slightly reduced)
            try:
                video_age_days = (time.time() - int(video['timestamp'])) / (24 * 3600)
                recency_score = max(0, 1 - (video_age_days / 30))  # Decay over 30 days
                score += recency_score * 0.22
            except (ValueError, TypeError):
                pass
            
            # Handle starred, disliked, and watched videos
            if video_id:
                cursor.execute("""
                    SELECT interaction_type FROM user_interactions 
                    WHERE video_id = ?
                """, (video_id,))
                interactions = {row[0] for row in cursor.fetchall()}
                
                # Heavy penalty for disliked videos
                if 'disliked' in interactions:
                    score *= 0.01
                # Bonus for starred videos (even if watched)
                elif 'starred' in interactions:
                    score *= 1.5
                # Penalty for watched but not starred videos
                elif 'watched' in interactions:
                    score *= 0.1
            
            return max(0, score)
    
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
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Count interactions by type
                cursor.execute("""
                    SELECT interaction_type, COUNT(*) 
                    FROM user_interactions 
                    GROUP BY interaction_type
                """)
                interaction_counts = dict(cursor.fetchall())
                
                # Count interaction subtypes for watched videos
                cursor.execute("""
                    SELECT interaction_subtype, COUNT(*) 
                    FROM user_interactions 
                    WHERE interaction_type = 'watched'
                    GROUP BY interaction_subtype
                """)
                watch_subtypes = dict(cursor.fetchall())
                
                # Top channels
                cursor.execute("""
                    SELECT channel_name, score 
                    FROM channel_scores 
                    WHERE score > 0
                    ORDER BY score DESC 
                    LIMIT 10
                """)
                top_channels = dict(cursor.fetchall())
                
                # Top keywords
                cursor.execute("""
                    SELECT keyword, score 
                    FROM keyword_scores 
                    WHERE score > 0
                    ORDER BY score DESC 
                    LIMIT 10
                """)
                top_keywords = dict(cursor.fetchall())
                
                # Time patterns
                cursor.execute("""
                    SELECT hour, count 
                    FROM time_patterns 
                    WHERE count > 0
                    ORDER BY count DESC 
                    LIMIT 5
                """)
                active_hours = dict(cursor.fetchall())
                
                return {
                    'total_watched': interaction_counts.get('watched', 0),
                    'total_starred': interaction_counts.get('starred', 0),
                    'total_disliked': interaction_counts.get('disliked', 0),
                    'clicked_to_watch': watch_subtypes.get('clicked', 0),
                    'marked_as_watched': watch_subtypes.get('marked', 0),
                    'top_channels': top_channels,
                    'top_keywords': top_keywords,
                    'active_hours': active_hours,
                    'last_updated': time.time()
                }
                
        except Exception as e:
            print(f"Error in get_stats: {e}")
            return {
                'total_watched': 0,
                'total_starred': 0,
                'total_disliked': 0,
                'clicked_to_watch': 0,
                'marked_as_watched': 0,
                'top_channels': {},
                'top_keywords': {},
                'active_hours': {},
                'last_updated': time.time()
            }
    
    def cleanup_old_data(self, days_to_keep=90):
        """Clean up old interaction data to keep database size manageable"""
        cutoff_time = time.time() - (days_to_keep * 24 * 3600)
        
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # Remove old interactions (but keep starred and disliked)
                    cursor.execute("""
                        DELETE FROM user_interactions 
                        WHERE timestamp < ? AND interaction_type = 'watched'
                    """, (cutoff_time,))
                    
                    # Remove orphaned videos
                    cursor.execute("""
                        DELETE FROM videos 
                        WHERE video_id NOT IN (
                            SELECT DISTINCT video_id FROM user_interactions
                        )
                    """)
                    
                    # Clean up zero/negative scores
                    cursor.execute("DELETE FROM channel_scores WHERE score <= 0")
                    cursor.execute("DELETE FROM keyword_scores WHERE score <= 0")
                    
                    # Vacuum to reclaim space
                    cursor.execute("VACUUM")
                    
                    conn.commit()
                    
                except sqlite3.Error as e:
                    conn.rollback()
                    raise e
    
    def train_neural_network(self, force_retrain=False):
        """Train the neural network model"""
        if not self.neural_engine:
            return False
        
        return self.neural_engine.train_model(force_retrain=force_retrain)
    
    def get_neural_insights(self, title):
        """Get neural network insights for a video title"""
        if not self.neural_engine:
            return {}
        
        return self.neural_engine.get_keyword_insights(title)
    
    def get_neural_stats(self):
        """Get neural network model statistics"""
        if not self.neural_engine:
            return {'neural_available': False}
        
        stats = self.neural_engine.get_model_stats()
        stats['neural_available'] = True
        return stats

# Global instance
recommendation_engine = RecommendationEngine()