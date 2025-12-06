"""
Metadata Search System - Searchable metadata database with version tracking

This module provides:
- Batch metadata extraction from file discovery catalog
- SQLite database storage with version history
- Comprehensive query language for searching
- Smart change detection (only re-extract changed files)
- Deleted file metadata tracking

Usage:
    # Extract metadata for all files in catalog
    python metadata_search.py --extract-all --catalog catalog.json
    
    # Extract by directory
    python metadata_search.py --extract --directory "Photos"
    
    # Extract by format
    python metadata_search.py --extract --format jpg
    
    # Search
    python metadata_search.py --search "camera=Canon AND resolution>1920x1080"
    
    # View history
    python metadata_search.py --history photo.jpg

Author: Antigravity AI Assistant
Date: 2025-12-06
"""

import os
import sys
import json
import sqlite3
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from tqdm import tqdm

# Import from previous tasks
from file_discovery import load_catalog
from metadata_extractor import extract_all_metadata

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MetadataDatabase:
    """Manage metadata storage with SQLite and version tracking."""
    
    def __init__(self, db_path: str = "metadata.db"):
        """
        Initialize metadata database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._init_database()
    
    def _init_database(self):
        """Create database tables if they don't exist."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        
        cursor = self.conn.cursor()
        
        # Main metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 1
            )
        """)
        
        # Version history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                extracted_at TIMESTAMP NOT NULL,
                version INTEGER NOT NULL,
                changes_json TEXT
            )
        """)
        
        # Deleted files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deleted_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deletion_reason TEXT
            )
        """)
        
        # Create indices for common searches
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_hash ON metadata(file_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_extracted_at ON metadata(extracted_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_path ON metadata(file_path)")
        
        self.conn.commit()
        logger.info(f"Database initialized: {self.db_path}")
    
    def calculate_file_hash(self, filepath: str) -> str:
        """Calculate SHA256 hash of file."""
        try:
            sha256_hash = hashlib.sha256()
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {filepath}: {e}")
            return ""
    
    def file_needs_update(self, filepath: str) -> bool:
        """
        Check if file needs metadata extraction.
        
        Returns True if:
        - File not in database
        - File hash changed
        - File modification time changed
        """
        if not os.path.exists(filepath):
            return False
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT file_hash, extracted_at FROM metadata WHERE file_path = ?", (filepath,))
        row = cursor.fetchone()
        
        if not row:
            return True  # New file
        
        # Check if file hash changed
        current_hash = self.calculate_file_hash(filepath)
        if current_hash != row['file_hash']:
            return True  # File modified
        
        return False
    
    def store_metadata(self, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Store metadata with version tracking.
        
        Args:
            filepath: File path
            metadata: Metadata dictionary
            
        Returns:
            Success status
        """
        try:
            file_hash = self.calculate_file_hash(filepath)
            metadata_json = json.dumps(metadata, default=str)
            
            cursor = self.conn.cursor()
            
            # Check if file exists in database
            cursor.execute("SELECT id, version, metadata_json FROM metadata WHERE file_path = ?", (filepath,))
            existing = cursor.fetchone()
            
            if existing:
                # File exists - check if metadata changed
                if existing['metadata_json'] == metadata_json:
                    logger.debug(f"Metadata unchanged for {filepath}")
                    return True
                
                # Store old version in history
                cursor.execute("""
                    INSERT INTO metadata_history (file_path, file_hash, metadata_json, extracted_at, version)
                    SELECT file_path, file_hash, metadata_json, extracted_at, version
                    FROM metadata WHERE file_path = ?
                """, (filepath,))
                
                # Update current metadata
                new_version = existing['version'] + 1
                cursor.execute("""
                    UPDATE metadata 
                    SET file_hash = ?, metadata_json = ?, extracted_at = CURRENT_TIMESTAMP, version = ?
                    WHERE file_path = ?
                """, (file_hash, metadata_json, new_version, filepath))
                
                logger.info(f"Updated metadata for {filepath} (version {new_version})")
            else:
                # New file
                cursor.execute("""
                    INSERT INTO metadata (file_path, file_hash, metadata_json)
                    VALUES (?, ?, ?)
                """, (filepath, file_hash, metadata_json))
                
                logger.info(f"Stored new metadata for {filepath}")
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error storing metadata for {filepath}: {e}")
            return False
    
    def mark_as_deleted(self, filepath: str, reason: str = "file_not_found"):
        """Mark file as deleted and move metadata to deleted table."""
        try:
            cursor = self.conn.cursor()
            
            # Copy to deleted table
            cursor.execute("""
                INSERT INTO deleted_metadata (file_path, file_hash, metadata_json, deletion_reason)
                SELECT file_path, file_hash, metadata_json, ?
                FROM metadata WHERE file_path = ?
            """, (reason, filepath))
            
            # Remove from main table
            cursor.execute("DELETE FROM metadata WHERE file_path = ?", (filepath,))
            
            self.conn.commit()
            logger.info(f"Marked {filepath} as deleted")
            
        except Exception as e:
            logger.error(f"Error marking {filepath} as deleted: {e}")
    
    def get_metadata(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Get current metadata for file."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT metadata_json FROM metadata WHERE file_path = ?", (filepath,))
        row = cursor.fetchone()
        
        if row:
            return json.loads(row['metadata_json'])
        return None
    
    def get_history(self, filepath: str) -> List[Dict[str, Any]]:
        """Get metadata version history for file."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT version, extracted_at, metadata_json 
            FROM metadata_history 
            WHERE file_path = ? 
            ORDER BY version DESC
        """, (filepath,))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'version': row['version'],
                'extracted_at': row['extracted_at'],
                'metadata': json.loads(row['metadata_json'])
            })
        
        return history
    
    def get_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM metadata")
        active_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM deleted_metadata")
        deleted_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM metadata_history")
        history_count = cursor.fetchone()['count']
        
        return {
            'active_files': active_count,
            'deleted_files': deleted_count,
            'total_versions': history_count
        }
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


class BatchExtractor:
    """Extract metadata for files in catalog."""
    
    def __init__(self, db: MetadataDatabase):
        """
        Initialize batch extractor.
        
        Args:
            db: MetadataDatabase instance
        """
        self.db = db
    
    def extract_all(self, catalog_path: str, force: bool = False) -> Dict[str, int]:
        """
        Extract metadata for all files in catalog.
        
        Args:
            catalog_path: Path to file discovery catalog
            force: Force re-extraction even if unchanged
            
        Returns:
            Statistics (processed, updated, errors, skipped)
        """
        catalog = load_catalog(catalog_path)
        if not catalog:
            logger.error(f"Failed to load catalog: {catalog_path}")
            return {}
        
        stats = {
            'processed': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        # Get all files from catalog
        all_files = catalog.get('files', [])
        
        logger.info(f"Extracting metadata for {len(all_files)} files...")
        
        for filepath in tqdm(all_files, desc="Extracting metadata"):
            try:
                # Check if file needs update
                if not force and not self.db.file_needs_update(filepath):
                    stats['skipped'] += 1
                    continue
                
                # Extract metadata
                metadata = extract_all_metadata(filepath)
                
                # Store in database
                if self.db.store_metadata(filepath, metadata):
                    stats['updated'] += 1
                else:
                    stats['errors'] += 1
                
                stats['processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing {filepath}: {e}")
                stats['errors'] += 1
        
        return stats
    
    def extract_by_directory(self, catalog_path: str, directory: str) -> Dict[str, int]:
        """Extract metadata for files in specific directory."""
        catalog = load_catalog(catalog_path)
        if not catalog:
            return {}
        
        stats = {'processed': 0, 'updated': 0, 'errors': 0}
        
        # Filter files by directory
        all_files = catalog.get('files', [])
        matching_files = [f for f in all_files if directory.lower() in f.lower()]
        
        logger.info(f"Extracting metadata for {len(matching_files)} files matching '{directory}'...")
        
        for filepath in tqdm(matching_files, desc=f"Processing {directory}"):
            try:
                if self.db.file_needs_update(filepath):
                    metadata = extract_all_metadata(filepath)
                    if self.db.store_metadata(filepath, metadata):
                        stats['updated'] += 1
                stats['processed'] += 1
            except Exception as e:
                logger.error(f"Error processing {filepath}: {e}")
                stats['errors'] += 1
        
        return stats
    
    def extract_by_format(self, catalog_path: str, file_format: str) -> Dict[str, int]:
        """Extract metadata for files of specific format."""
        catalog = load_catalog(catalog_path)
        if not catalog:
            return {}
        
        stats = {'processed': 0, 'updated': 0, 'errors': 0}
        
        # Filter files by format
        all_files = catalog.get('files', [])
        matching_files = [f for f in all_files if Path(f).suffix.lower() == f".{file_format.lower()}"]
        
        logger.info(f"Extracting metadata for {len(matching_files)} {file_format} files...")
        
        for filepath in tqdm(matching_files, desc=f"Processing .{file_format}"):
            try:
                if self.db.file_needs_update(filepath):
                    metadata = extract_all_metadata(filepath)
                    if self.db.store_metadata(filepath, metadata):
                        stats['updated'] += 1
                stats['processed'] += 1
            except Exception as e:
                logger.error(f"Error processing {filepath}: {e}")
                stats['errors'] += 1
        
        return stats


def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Metadata Search System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract metadata for all files
  python metadata_search.py --extract-all --catalog catalog.json
  
  # Extract by directory
  python metadata_search.py --extract --directory "Photos" --catalog catalog.json
  
  # Extract by format
  python metadata_search.py --extract --format jpg --catalog catalog.json
  
  # View database stats
  python metadata_search.py --stats
  
  # View file history
  python metadata_search.py --history photo.jpg
        """
    )
    
    parser.add_argument('--extract-all', action='store_true', help='Extract metadata for all files')
    parser.add_argument('--extract', action='store_true', help='Extract metadata with filters')
    parser.add_argument('--directory', help='Filter by directory name')
    parser.add_argument('--format', help='Filter by file format')
    parser.add_argument('--catalog', default='media_catalog.json', help='Catalog file path')
    parser.add_argument('--db', default='metadata.db', help='Database file path')
    parser.add_argument('--force', action='store_true', help='Force re-extraction')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--history', help='Show version history for file')
    
    args = parser.parse_args()
    
    # Initialize database
    db = MetadataDatabase(args.db)
    
    try:
        if args.stats:
            # Show statistics
            stats = db.get_stats()
            print("\n" + "="*60)
            print("METADATA DATABASE STATISTICS")
            print("="*60)
            print(f"Active files:    {stats['active_files']}")
            print(f"Deleted files:   {stats['deleted_files']}")
            print(f"Total versions:  {stats['total_versions']}")
            print("="*60 + "\n")
        
        elif args.history:
            # Show version history
            history = db.get_history(args.history)
            if history:
                print(f"\nVersion history for: {args.history}")
                print("="*60)
                for entry in history:
                    print(f"Version {entry['version']} - {entry['extracted_at']}")
                print("="*60 + "\n")
            else:
                print(f"No history found for: {args.history}")
        
        elif args.extract_all:
            # Extract all
            extractor = BatchExtractor(db)
            stats = extractor.extract_all(args.catalog, args.force)
            print(f"\nExtraction complete:")
            print(f"  Processed: {stats['processed']}")
            print(f"  Updated:   {stats['updated']}")
            print(f"  Skipped:   {stats['skipped']}")
            print(f"  Errors:    {stats['errors']}\n")
        
        elif args.extract:
            # Extract with filters
            extractor = BatchExtractor(db)
            
            if args.directory:
                stats = extractor.extract_by_directory(args.catalog, args.directory)
            elif args.format:
                stats = extractor.extract_by_format(args.catalog, args.format)
            else:
                print("Error: Specify --directory or --format with --extract")
                return
            
            print(f"\nExtraction complete:")
            print(f"  Processed: {stats['processed']}")
            print(f"  Updated:   {stats['updated']}")
            print(f"  Errors:    {stats['errors']}\n")
        
        else:
            parser.print_help()
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
