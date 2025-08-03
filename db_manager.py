#!/usr/bin/env python3
"""
Database management utilities for the SQLite recommendations database
"""

import sqlite3
import os
import sys
import argparse
from datetime import datetime, timedelta

def get_db_path():
    """Get the database path"""
    return "recommendations.db"

def show_stats(db_path):
    """Show database statistics"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("📊 Database Statistics")
        print("=" * 50)
        
        # Table sizes
        tables = ['videos', 'user_interactions', 'channel_scores', 'keyword_scores', 'time_patterns']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{table:20}: {count:>8,} records")
        
        print("\n🎬 Interaction Breakdown")
        print("-" * 30)
        cursor.execute("""
            SELECT interaction_type, COUNT(*) 
            FROM user_interactions 
            GROUP BY interaction_type
            ORDER BY COUNT(*) DESC
        """)
        for interaction_type, count in cursor.fetchall():
            print(f"{interaction_type:15}: {count:>6,}")
        
        print("\n📺 Top Channels (by score)")
        print("-" * 40)
        cursor.execute("""
            SELECT channel_name, score 
            FROM channel_scores 
            ORDER BY score DESC 
            LIMIT 10
        """)
        for channel, score in cursor.fetchall():
            print(f"{channel[:30]:30}: {score:>6.2f}")
        
        print("\n🔍 Top Keywords (by score)")
        print("-" * 40)
        cursor.execute("""
            SELECT keyword, score 
            FROM keyword_scores 
            ORDER BY score DESC 
            LIMIT 10
        """)
        for keyword, score in cursor.fetchall():
            print(f"{keyword:20}: {score:>6.2f}")
        
        # Database file size
        file_size = os.path.getsize(db_path)
        print(f"\n💾 Database file size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        
    finally:
        conn.close()

def cleanup_old_data(db_path, days_to_keep=90):
    """Clean up old data from the database"""
    cutoff_time = (datetime.now() - timedelta(days=days_to_keep)).timestamp()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print(f"🧹 Cleaning up data older than {days_to_keep} days...")
        
        # Count what will be deleted
        cursor.execute("""
            SELECT COUNT(*) FROM user_interactions 
            WHERE timestamp < ? AND interaction_type = 'watched'
        """, (cutoff_time,))
        old_interactions = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM videos 
            WHERE video_id NOT IN (
                SELECT DISTINCT video_id FROM user_interactions
                WHERE timestamp >= ? OR interaction_type IN ('starred', 'disliked')
            )
        """, (cutoff_time,))
        orphaned_videos = cursor.fetchone()[0]
        
        print(f"   Will remove {old_interactions:,} old watched interactions")
        print(f"   Will remove {orphaned_videos:,} orphaned videos")
        
        # Perform cleanup
        cursor.execute("""
            DELETE FROM user_interactions 
            WHERE timestamp < ? AND interaction_type = 'watched'
        """, (cutoff_time,))
        
        cursor.execute("""
            DELETE FROM videos 
            WHERE video_id NOT IN (
                SELECT DISTINCT video_id FROM user_interactions
            )
        """)
        
        # Clean up zero/negative scores
        cursor.execute("DELETE FROM channel_scores WHERE score <= 0")
        cursor.execute("DELETE FROM keyword_scores WHERE score <= 0")
        
        conn.commit()
        
        print("   ✓ Cleanup completed")
        
        # Vacuum to reclaim space
        print("   🗜️  Vacuuming database...")
        cursor.execute("VACUUM")
        print("   ✓ Database vacuumed")
        
    except Exception as e:
        conn.rollback()
        print(f"   ❌ Error during cleanup: {e}")
    finally:
        conn.close()

def backup_database(db_path, backup_path=None):
    """Create a backup of the database"""
    if backup_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        # Use SQLite's backup API for consistent backup
        source = sqlite3.connect(db_path)
        backup = sqlite3.connect(backup_path)
        
        source.backup(backup)
        
        source.close()
        backup.close()
        
        print(f"✅ Database backed up to: {backup_path}")
        return backup_path
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None

def analyze_patterns(db_path):
    """Analyze user behavior patterns"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("📈 User Behavior Analysis")
        print("=" * 50)
        
        # Watch vs click patterns
        cursor.execute("""
            SELECT 
                interaction_subtype,
                COUNT(*) as count,
                AVG(julianday('now') - julianday(timestamp, 'unixepoch')) as avg_days_ago
            FROM user_interactions 
            WHERE interaction_type = 'watched'
            GROUP BY interaction_subtype
        """)
        
        print("\n🎯 Watch Patterns:")
        for subtype, count, avg_days in cursor.fetchall():
            print(f"   {subtype:10}: {count:>4} videos (avg {avg_days:.1f} days ago)")
        
        # Channel diversity
        cursor.execute("""
            SELECT COUNT(DISTINCT v.author) as unique_channels,
                   COUNT(*) as total_interactions
            FROM user_interactions ui
            JOIN videos v ON ui.video_id = v.video_id
            WHERE ui.interaction_type = 'watched'
        """)
        unique_channels, total_interactions = cursor.fetchone()
        
        print(f"\n📺 Channel Diversity:")
        print(f"   Unique channels watched: {unique_channels}")
        print(f"   Total watch interactions: {total_interactions}")
        print(f"   Avg videos per channel: {total_interactions/unique_channels:.1f}")
        
        # Score distribution
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN score < 0 THEN 'Negative'
                    WHEN score = 0 THEN 'Neutral'
                    WHEN score < 1 THEN 'Low Positive'
                    WHEN score < 5 THEN 'Medium Positive'
                    ELSE 'High Positive'
                END as score_range,
                COUNT(*) as count
            FROM channel_scores
            GROUP BY score_range
            ORDER BY MIN(score)
        """)
        
        print(f"\n📊 Channel Score Distribution:")
        for score_range, count in cursor.fetchall():
            print(f"   {score_range:15}: {count:>4} channels")
        
    finally:
        conn.close()

def export_data(db_path, format='csv'):
    """Export data to various formats"""
    import csv
    import json
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == 'csv':
            # Export interactions
            cursor.execute("""
                SELECT v.video_id, v.title, v.author, ui.interaction_type, 
                       ui.interaction_subtype, ui.timestamp
                FROM user_interactions ui
                JOIN videos v ON ui.video_id = v.video_id
                ORDER BY ui.timestamp DESC
            """)
            
            filename = f"interactions_export_{timestamp}.csv"
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['video_id', 'title', 'author', 'interaction_type', 
                               'interaction_subtype', 'timestamp'])
                writer.writerows(cursor.fetchall())
            
            print(f"✅ Interactions exported to: {filename}")
            
        elif format == 'json':
            # Export all data as JSON
            data = {}
            
            # Videos
            cursor.execute("SELECT * FROM videos")
            data['videos'] = [dict(row) for row in cursor.fetchall()]
            
            # Interactions
            cursor.execute("SELECT * FROM user_interactions")
            data['interactions'] = [dict(row) for row in cursor.fetchall()]
            
            # Scores
            cursor.execute("SELECT * FROM channel_scores")
            data['channel_scores'] = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute("SELECT * FROM keyword_scores")
            data['keyword_scores'] = [dict(row) for row in cursor.fetchall()]
            
            filename = f"full_export_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Full data exported to: {filename}")
        
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description='Manage the recommendations database')
    parser.add_argument('--db', default=get_db_path(), help='Database path')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Stats command
    subparsers.add_parser('stats', help='Show database statistics')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old data')
    cleanup_parser.add_argument('--days', type=int, default=90, 
                               help='Keep data newer than N days (default: 90)')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create database backup')
    backup_parser.add_argument('--output', help='Backup file path')
    
    # Analyze command
    subparsers.add_parser('analyze', help='Analyze user behavior patterns')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export data')
    export_parser.add_argument('--format', choices=['csv', 'json'], default='csv',
                              help='Export format (default: csv)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    db_path = args.db
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    if args.command == 'stats':
        show_stats(db_path)
    elif args.command == 'cleanup':
        cleanup_old_data(db_path, args.days)
    elif args.command == 'backup':
        backup_database(db_path, args.output)
    elif args.command == 'analyze':
        analyze_patterns(db_path)
    elif args.command == 'export':
        export_data(db_path, args.format)

if __name__ == "__main__":
    main()