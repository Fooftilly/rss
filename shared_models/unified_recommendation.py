import sqlite3
import os
import time
import threading
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from contextlib import contextmanager

class UnifiedRecommendationEngine:
    """
    Unified recommendation engine that learns user preferences across platforms:
    - YouTube videos and news articles
    - Cross-platform keyword learning
    - Unified preference scoring
    - Platform-specific adaptations
    """
    
    def __init__(self, rss_base_dir=None):
        if rss_base_dir is None:
            rss_base_dir = os.path.expanduser("~/rss")
        
        self.db_path = os.path.join(rss_base_dir, "recommendations.db")
        self._lock = threading.RLock()
        self._init_database()
    
    def _init_database(self):
        """Initialize the unified database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Enable foreign keys and WAL mode for better concurrency
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = NORMAL")
            
            # Check if we have old schema
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('videos', 'channel_scores')
            """)
            has_old_schema = len(cursor.fetchall()) > 0
            
            if has_old_schema:
                # Migrate old schema to new unified schema
                self._migrate_old_schema(cursor)
            else:
                # Create new unified schema
                self._create_unified_schema(cursor)
            
            conn.commit()
    
    def _create_unified_schema(self, cursor):
        """Create the new unified schema"""
        cursor.executescript("""
        -- Content table to store both videos and articles
        CREATE TABLE IF NOT EXISTS content (
            content_id TEXT PRIMARY KEY,
            platform TEXT NOT NULL, -- 'youtube' or 'news'
            title TEXT NOT NULL,
            author TEXT NOT NULL, -- channel name or news source
            content_type TEXT NOT NULL, -- 'video' or 'article'
            first_seen_timestamp REAL NOT NULL,
            last_updated REAL NOT NULL
        );
        
        -- User interactions with content (unified table)
        CREATE TABLE IF NOT EXISTS unified_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            interaction_type TEXT NOT NULL, -- 'watched'/'read', 'starred', 'disliked'
            interaction_subtype TEXT, -- 'clicked', 'marked' for watched/read
            timestamp REAL NOT NULL,
            FOREIGN KEY (content_id) REFERENCES content (content_id),
            UNIQUE(content_id, interaction_type) -- One record per interaction type per content
        );
        
        -- Source scores (channels/news sources) with platform awareness
        CREATE TABLE IF NOT EXISTS source_scores (
            source_name TEXT NOT NULL,
            platform TEXT NOT NULL,
            score REAL NOT NULL DEFAULT 0.0,
            cross_platform_boost REAL NOT NULL DEFAULT 0.0, -- boost from other platforms
            last_updated REAL NOT NULL,
            PRIMARY KEY (source_name, platform)
        );
        
        -- Unified keyword scores (shared across platforms)
        CREATE TABLE IF NOT EXISTS unified_keyword_scores (
            keyword TEXT PRIMARY KEY,
            score REAL NOT NULL DEFAULT 0.0,
            last_updated REAL NOT NULL
        );
        
        -- Platform-specific time patterns
        CREATE TABLE IF NOT EXISTS unified_time_patterns (
            platform TEXT NOT NULL,
            hour INTEGER NOT NULL CHECK (hour >= 0 AND hour <= 23),
            count INTEGER NOT NULL DEFAULT 0,
            last_updated REAL NOT NULL,
            PRIMARY KEY (platform, hour)
        );
        
        -- Cross-platform correlation tracking
        CREATE TABLE IF NOT EXISTS cross_correlations (
            keyword1 TEXT NOT NULL,
            keyword2 TEXT NOT NULL,
            platform1 TEXT NOT NULL,
            platform2 TEXT NOT NULL,
            correlation_strength REAL NOT NULL DEFAULT 0.0,
            last_updated REAL NOT NULL,
            PRIMARY KEY (keyword1, keyword2, platform1, platform2)
        );
        
        -- Indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_unified_interactions_content_id ON unified_interactions(content_id);
        CREATE INDEX IF NOT EXISTS idx_unified_interactions_platform ON unified_interactions(platform);
        CREATE INDEX IF NOT EXISTS idx_unified_interactions_type ON unified_interactions(interaction_type);
        CREATE INDEX IF NOT EXISTS idx_unified_interactions_timestamp ON unified_interactions(timestamp);
        CREATE INDEX IF NOT EXISTS idx_content_platform ON content(platform);
        CREATE INDEX IF NOT EXISTS idx_content_author ON content(author);
        CREATE INDEX IF NOT EXISTS idx_source_scores_platform ON source_scores(platform);
        CREATE INDEX IF NOT EXISTS idx_source_scores_score ON source_scores(score DESC);
        CREATE INDEX IF NOT EXISTS idx_unified_keyword_scores_score ON unified_keyword_scores(score DESC);
        """)
    
    def _migrate_old_schema(self, cursor):
        """Migrate old YouTube-only schema to unified schema"""
        print("🔄 Migrating existing schema to unified system...")
        
        # Create new unified tables alongside old ones
        self._create_unified_schema(cursor)
        
        # Migrate videos to content table
        cursor.execute("""
            INSERT OR IGNORE INTO content 
            (content_id, platform, title, author, content_type, first_seen_timestamp, last_updated)
            SELECT video_id, 'youtube', title, author, 'video', first_seen_timestamp, last_updated
            FROM videos
        """)
        
        # Migrate user_interactions to unified_interactions
        cursor.execute("""
            INSERT OR IGNORE INTO unified_interactions 
            (content_id, platform, interaction_type, interaction_subtype, timestamp)
            SELECT video_id, 'youtube', interaction_type, interaction_subtype, timestamp
            FROM user_interactions
        """)
        
        # Migrate channel_scores to source_scores
        cursor.execute("""
            INSERT OR IGNORE INTO source_scores 
            (source_name, platform, score, last_updated)
            SELECT channel_name, 'youtube', score, last_updated
            FROM channel_scores
        """)
        
        # Migrate keyword_scores to unified_keyword_scores
        cursor.execute("""
            INSERT OR IGNORE INTO unified_keyword_scores 
            (keyword, score, last_updated)
            SELECT keyword, score, last_updated
            FROM keyword_scores
        """)
        
        print("✅ Schema migration completed")
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def _ensure_content_exists(self, cursor, content_id, platform, title, author, content_type, timestamp=None):
        """Ensure a content record exists in the database"""
        if timestamp is None:
            timestamp = time.time()
        
        cursor.execute("""
            INSERT OR IGNORE INTO content 
            (content_id, platform, title, author, content_type, first_seen_timestamp, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (content_id, platform, title, author, content_type, timestamp, timestamp))
        
        # Update title/author if they've changed
        cursor.execute("""
            UPDATE content 
            SET title = ?, author = ?, last_updated = ?
            WHERE content_id = ? AND (title != ? OR author != ?)
        """, (title, author, timestamp, content_id, title, author))
    
    def _update_source_score(self, cursor, source_name, platform, score_delta):
        """Update source score with cross-platform influence"""
        cursor.execute("""
            INSERT INTO source_scores (source_name, platform, score, last_updated)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(source_name, platform) DO UPDATE SET
                score = score + ?,
                last_updated = ?
        """, (source_name, platform, score_delta, time.time(), score_delta, time.time()))
        
        # Apply cross-platform boost (smaller influence from other platforms)
        other_platform = 'news' if platform == 'youtube' else 'youtube'
        cross_boost = score_delta * 0.2  # 20% cross-platform influence
        
        cursor.execute("""
            UPDATE source_scores 
            SET cross_platform_boost = cross_platform_boost + ?,
                last_updated = ?
            WHERE source_name = ? AND platform = ?
        """, (cross_boost, time.time(), source_name, other_platform))
    
    def _update_keyword_scores(self, cursor, title, platform, score_delta):
        """Update keyword scores with platform-specific weights"""
        keywords = self._extract_keywords(title)
        current_time = time.time()
        
        for keyword in keywords:
            # Update unified keyword score
            cursor.execute("""
                INSERT INTO unified_keyword_scores (keyword, score, last_updated)
                VALUES (?, ?, ?)
                ON CONFLICT(keyword) DO UPDATE SET
                    score = score + ?,
                    last_updated = ?
            """, (keyword, score_delta, current_time, score_delta, current_time))
            
            # No platform-specific weights needed - unified scoring
    
    def record_interaction(self, content_id, platform, title, author, content_type, 
                          interaction_type, interaction_subtype=None, timestamp=None):
        """
        Record user interaction with content
        
        Args:
            content_id: Unique identifier for the content
            platform: 'youtube' or 'news'
            title: Content title
            author: Channel name or news source
            content_type: 'video' or 'article'
            interaction_type: 'watched'/'read', 'starred', 'disliked'
            interaction_subtype: 'clicked', 'marked' for watched/read
            timestamp: When the interaction occurred
        """
        if timestamp is None:
            timestamp = time.time()
        
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # Ensure content exists
                    self._ensure_content_exists(cursor, content_id, platform, title, author, content_type, timestamp)
                    
                    # Record interaction
                    cursor.execute("""
                        INSERT OR REPLACE INTO unified_interactions 
                        (content_id, platform, interaction_type, interaction_subtype, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (content_id, platform, interaction_type, interaction_subtype, timestamp))
                    
                    # Calculate score deltas based on interaction
                    if interaction_type in ['watched', 'read']:
                        if interaction_subtype == 'clicked':
                            source_boost = 1.0
                            keyword_boost = 0.5
                        else:  # 'marked'
                            source_boost = 0.3
                            keyword_boost = 0.15
                    elif interaction_type == 'starred':
                        source_boost = 2.0
                        keyword_boost = 1.5
                    elif interaction_type == 'disliked':
                        source_boost = -2.0
                        keyword_boost = -1.0
                    else:
                        source_boost = 0.0
                        keyword_boost = 0.0
                    
                    # Update scores
                    if source_boost != 0:
                        self._update_source_score(cursor, author, platform, source_boost)
                    if keyword_boost != 0:
                        self._update_keyword_scores(cursor, title, platform, keyword_boost)
                    
                    # Update cross-platform correlations
                    self._update_cross_correlations(cursor, title, platform)
                    
                    conn.commit()
                    
                except sqlite3.Error as e:
                    conn.rollback()
                    raise e
    
    def _update_cross_correlations(self, cursor, title, platform):
        """Update cross-platform keyword correlations"""
        keywords = self._extract_keywords(title)
        if len(keywords) < 2:
            return
        
        # Find recent interactions from other platform
        other_platform = 'news' if platform == 'youtube' else 'youtube'
        recent_cutoff = time.time() - (7 * 24 * 3600)  # Last 7 days
        
        cursor.execute("""
            SELECT c.title FROM unified_interactions ui
            JOIN content c ON ui.content_id = c.content_id
            WHERE ui.platform = ? AND ui.timestamp > ?
            AND ui.interaction_type IN ('watched', 'read', 'starred')
            ORDER BY ui.timestamp DESC
            LIMIT 50
        """, (other_platform, recent_cutoff))
        
        recent_titles = [row[0] for row in cursor.fetchall()]
        
        # Calculate correlations
        for recent_title in recent_titles:
            recent_keywords = self._extract_keywords(recent_title)
            
            for kw1 in keywords:
                for kw2 in recent_keywords:
                    if kw1 != kw2:
                        cursor.execute("""
                            INSERT INTO cross_correlations 
                            (keyword1, keyword2, platform1, platform2, correlation_strength, last_updated)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT(keyword1, keyword2, platform1, platform2) DO UPDATE SET
                                correlation_strength = correlation_strength + 0.1,
                                last_updated = ?
                        """, (kw1, kw2, platform, other_platform, 0.1, time.time(), time.time()))
    
    def _extract_keywords(self, title):
        """Extract meaningful keywords from content title"""
        import re
        
        # Common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we',
            'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her',
            'its', 'our', 'their', 'how', 'what', 'when', 'where', 'why', 'who', 
            'about', 'than', 'not', 'part', 'all', 'can', 'new', 'first', 'last',
            'one', 'two', 'three', 'get', 'make', 'take', 'come', 'go', 'see', 'know'
        }
        
        # Clean and split title
        words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
        keywords = [word for word in words if word not in stop_words]
        
        return keywords[:10]  # Limit to top 10 keywords
    
    def calculate_content_score(self, content_item, platform):
        """Calculate unified recommendation score for content"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            score = 0.0
            content_id = content_item.get('video_id') or content_item.get('article_id') or content_item.get('url')
            
            # Source preference score (30% weight)
            cursor.execute("""
                SELECT score, cross_platform_boost FROM source_scores 
                WHERE source_name = ? AND platform = ?
            """, (content_item['author'], platform))
            row = cursor.fetchone()
            if row:
                source_score = row[0] + (row[1] * 0.5)  # Include cross-platform boost
                normalized_source_score = source_score / (1 + abs(source_score) * 0.1)
                score += normalized_source_score * 0.30
            
            # Keyword matching score (40% weight)
            keywords = self._extract_keywords(content_item['title'])
            if keywords:
                cursor.execute(f"""
                    SELECT SUM(score + cross_platform_boost * 0.3) FROM unified_keyword_scores 
                    WHERE keyword IN ({','.join(['?'] * len(keywords))})
                """, keywords)
                row = cursor.fetchone()
                if row and row[0]:
                    keyword_score = row[0]
                    score += keyword_score * 0.40
            
            # Cross-platform correlation bonus (10% weight)
            other_platform = 'news' if platform == 'youtube' else 'youtube'
            if keywords:
                cursor.execute(f"""
                    SELECT AVG(correlation_strength) FROM cross_correlations
                    WHERE keyword1 IN ({','.join(['?'] * len(keywords))})
                    AND platform1 = ? AND platform2 = ?
                """, keywords + [platform, other_platform])
                row = cursor.fetchone()
                if row and row[0]:
                    correlation_score = row[0]
                    score += correlation_score * 0.10
            
            # Recency bonus (20% weight)
            try:
                content_age_days = (time.time() - int(content_item['timestamp'])) / (24 * 3600)
                recency_score = max(0, 1 - (content_age_days / 30))  # Decay over 30 days
                score += recency_score * 0.20
            except (ValueError, TypeError):
                pass
            
            # Handle starred, disliked, and consumed content
            if content_id:
                cursor.execute("""
                    SELECT interaction_type FROM unified_interactions 
                    WHERE content_id = ? AND platform = ?
                """, (content_id, platform))
                interactions = {row[0] for row in cursor.fetchall()}
                
                # Heavy penalty for disliked content
                if 'disliked' in interactions:
                    score *= 0.01
                # Bonus for starred content
                elif 'starred' in interactions:
                    score *= 1.5
                # Penalty for already consumed content
                elif 'watched' in interactions or 'read' in interactions:
                    score *= 0.1
            
            return max(0, score)
    
    def get_recommendations(self, content_items, platform, limit=None):
        """Sort content by unified recommendation score"""
        if not content_items:
            return content_items
        
        # Calculate scores for all content
        scored_content = []
        for item in content_items:
            score = self.calculate_content_score(item, platform)
            scored_content.append((score, item))
        
        # Sort by score (descending)
        scored_content.sort(key=lambda x: x[0], reverse=True)
        
        # Return just the content items
        recommended = [item for score, item in scored_content]
        
        return recommended[:limit] if limit else recommended
    
    def get_stats(self, platform=None):
        """Get recommendation engine statistics"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Platform filter
                platform_filter = ""
                params = []
                if platform:
                    platform_filter = "WHERE platform = ?"
                    params = [platform]
                
                # Count interactions by type
                cursor.execute(f"""
                    SELECT interaction_type, COUNT(*) 
                    FROM unified_interactions 
                    {platform_filter}
                    GROUP BY interaction_type
                """, params)
                interaction_counts = dict(cursor.fetchall())
                
                # Count interaction subtypes for consumed content
                cursor.execute(f"""
                    SELECT interaction_subtype, COUNT(*) 
                    FROM unified_interactions 
                    WHERE interaction_type IN ('watched', 'read') {' AND platform = ?' if platform else ''}
                    GROUP BY interaction_subtype
                """, params)
                consumption_subtypes = dict(cursor.fetchall())
                
                # Top sources
                cursor.execute(f"""
                    SELECT source_name, score + cross_platform_boost * 0.5 as total_score
                    FROM source_scores 
                    WHERE total_score > 0 {' AND platform = ?' if platform else ''}
                    ORDER BY total_score DESC 
                    LIMIT 10
                """, params)
                top_sources = dict(cursor.fetchall())
                
                # Top keywords
                cursor.execute("""
                    SELECT keyword, score
                    FROM unified_keyword_scores 
                    WHERE score > 0
                    ORDER BY score DESC 
                    LIMIT 10
                """)
                top_keywords = dict(cursor.fetchall())
                
                # Cross-platform correlations
                cursor.execute("""
                    SELECT keyword1, keyword2, correlation_strength
                    FROM cross_correlations
                    WHERE correlation_strength > 0.5
                    ORDER BY correlation_strength DESC
                    LIMIT 5
                """)
                correlations = [(f"{row[0]} ↔ {row[1]}", row[2]) for row in cursor.fetchall()]
                
                return {
                    'total_consumed': interaction_counts.get('watched', 0) + interaction_counts.get('read', 0),
                    'total_starred': interaction_counts.get('starred', 0),
                    'total_disliked': interaction_counts.get('disliked', 0),
                    'clicked_to_consume': consumption_subtypes.get('clicked', 0),
                    'marked_as_consumed': consumption_subtypes.get('marked', 0),
                    'top_sources': top_sources,
                    'top_keywords': top_keywords,
                    'cross_correlations': dict(correlations),
                    'platform': platform or 'unified',
                    'last_updated': time.time()
                }
                
        except Exception as e:
            print(f"Error in get_stats: {e}")
            return {
                'total_consumed': 0,
                'total_starred': 0,
                'total_disliked': 0,
                'clicked_to_consume': 0,
                'marked_as_consumed': 0,
                'top_sources': {},
                'top_keywords': {},
                'cross_correlations': {},
                'platform': platform or 'unified',
                'last_updated': time.time()
            }
    
    def cleanup_old_data(self, days_to_keep=90):
        """Clean up old interaction data"""
        cutoff_time = time.time() - (days_to_keep * 24 * 3600)
        
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # Remove old interactions (but keep starred and disliked)
                    cursor.execute("""
                        DELETE FROM unified_interactions 
                        WHERE timestamp < ? AND interaction_type IN ('watched', 'read')
                    """, (cutoff_time,))
                    
                    # Remove orphaned content
                    cursor.execute("""
                        DELETE FROM content 
                        WHERE content_id NOT IN (
                            SELECT DISTINCT content_id FROM unified_interactions
                        )
                    """)
                    
                    # Clean up zero/negative scores
                    cursor.execute("DELETE FROM source_scores WHERE score <= 0 AND cross_platform_boost <= 0")
                    cursor.execute("DELETE FROM unified_keyword_scores WHERE score <= 0 AND cross_platform_boost <= 0")
                    
                    # Clean up old correlations
                    cursor.execute("""
                        DELETE FROM cross_correlations 
                        WHERE last_updated < ? AND correlation_strength < 0.1
                    """, (cutoff_time,))
                    
                    # Vacuum to reclaim space
                    cursor.execute("VACUUM")
                    
                    conn.commit()
                    
                except sqlite3.Error as e:
                    conn.rollback()
                    raise e

# Global instance
unified_recommendation_engine = UnifiedRecommendationEngine()