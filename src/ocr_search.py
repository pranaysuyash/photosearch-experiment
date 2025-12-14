"""
OCR Text Search System

This module provides OCR (Optical Character Recognition) functionality to:
1. Extract text from images
2. Index OCR text for search
3. Search images by their text content
4. Handle various document types and languages

Features:
- OCR text extraction using Tesseract
- Text indexing and search
- Multi-language support
- Document type detection
- Integration with existing photo search

Note: This requires Tesseract OCR to be installed on the system.
Install with: brew install tesseract (Mac) or apt-get install tesseract-ocr (Linux)

Usage:
    ocr_search = OCRSearch()
    
    # Extract text from images
    ocr_search.extract_text_from_images(['image1.jpg', 'image2.png'])
    
    # Search for images containing specific text
    results = ocr_search.search_text('hello world')
"""

from __future__ import annotations

import os
import json
import sqlite3
import subprocess
import tempfile

from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

from collections import defaultdict

# Try to import OCR libraries
try:
    import pytesseract
    from PIL import Image
    import cv2
    import numpy as np
    OCR_LIBRARIES_AVAILABLE = True
except ImportError:
    OCR_LIBRARIES_AVAILABLE = False
    print("Warning: OCR libraries not available. Install with:")
    print("pip install pytesseract opencv-python pillow numpy")
    print("And install Tesseract OCR on your system")

class OCRSearch:
    """OCR text extraction and search system."""
    
    def __init__(self, db_path: str = "ocr_search.db"):
        """
        Initialize OCR search system.
        
        Args:
            db_path: Path to SQLite database for storing OCR data
        """
        self.db_path = db_path
        self.conn = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database and create tables."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Create OCR text table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ocr_text (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT NOT NULL,
                text_content TEXT,
                language TEXT DEFAULT 'eng',
                confidence REAL,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(image_path)
            )
        """)
        
        # Create OCR search index table
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS ocr_search_index 
            USING fts5(
                image_path,
                text_content,
                language,
                tokenize='porter unicode61'
            )
        """)
        
        # Create OCR statistics table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ocr_stats (
                image_path TEXT PRIMARY KEY,
                word_count INTEGER DEFAULT 0,
                char_count INTEGER DEFAULT 0,
                line_count INTEGER DEFAULT 0,
                languages TEXT,  -- JSON array of detected languages
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ocr_path ON ocr_text(image_path)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ocr_language ON ocr_text(language)")
        
        self.conn.commit()
    
    def _preprocess_image(self, image_path: str) -> Optional[Image.Image]:
        """
        Preprocess image for better OCR results.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Preprocessed PIL Image or None if failed
        """
        try:
            # Open image
            img = Image.open(image_path)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Convert to OpenCV format for processing
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Apply thresholding
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Convert back to PIL Image
            processed_img = Image.fromarray(cv2.cvtColor(thresh, cv2.COLOR_BGR2RGB))
            
            return processed_img
            
        except Exception as e:
            print(f"Error preprocessing {image_path}: {e}")
            return None
    
    def extract_text_from_image(
        self,
        image_path: str,
        language: str = 'eng',
        config: str = '--psm 6'
    ) -> Dict:
        """
        Extract text from a single image using OCR.
        
        Args:
            image_path: Path to image file
            language: Language code (e.g., 'eng', 'fra', 'spa')
            config: Tesseract configuration
            
        Returns:
            Dictionary with extraction results
        """
        if not OCR_LIBRARIES_AVAILABLE:
            return {
                'status': 'error',
                'message': 'OCR libraries not available',
                'text': '',
                'confidence': 0.0
            }
        
        try:
            # Preprocess image
            processed_img = self._preprocess_image(image_path)
            if not processed_img:
                return {
                    'status': 'error',
                    'message': 'Image preprocessing failed',
                    'text': '',
                    'confidence': 0.0
                }
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(
                processed_img,
                lang=language,
                config=config
            )
            
            # Get confidence (approximate)
            # Note: Tesseract doesn't provide per-character confidence in simple mode
            # This is a placeholder - would need more advanced processing for real confidence
            confidence = 0.8 if text.strip() else 0.0
            
            # Calculate statistics
            word_count = len(text.split())
            char_count = len(text)
            line_count = len(text.split('\n'))
            
            return {
                'status': 'success',
                'text': text.strip(),
                'confidence': confidence,
                'language': language,
                'statistics': {
                    'word_count': word_count,
                    'char_count': char_count,
                    'line_count': line_count
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'text': '',
                'confidence': 0.0
            }
    
    def extract_text_from_images(
        self,
        image_paths: List[str],
        language: str = 'eng',
        overwrite: bool = False
    ) -> Dict:
        """
        Extract text from multiple images and store in database.
        
        Args:
            image_paths: List of image file paths
            language: Language code
            overwrite: Whether to overwrite existing OCR data
            
        Returns:
            Dictionary with extraction summary
        """
        if not OCR_LIBRARIES_AVAILABLE:
            return {
                'status': 'error',
                'message': 'OCR libraries not available',
                'processed': 0,
                'successful': 0,
                'failed': 0
            }
        
        cursor = self.conn.cursor()
        
        processed = 0
        successful = 0
        failed = 0
        
        for i, image_path in enumerate(image_paths):
            try:
                print(f"Processing {i+1}/{len(image_paths)}: {image_path}")
                
                # Check if already processed
                if not overwrite:
                    cursor.execute("SELECT id FROM ocr_text WHERE image_path = ?", (image_path,))
                    existing = cursor.fetchone()
                    if existing:
                        print(f"  Skipped (already processed)")
                        continue
                
                # Extract text
                result = self.extract_text_from_image(image_path, language)
                
                if result['status'] == 'success' and result['text']:
                    # Store in database
                    cursor.execute("""
                        INSERT OR REPLACE INTO ocr_text 
                        (image_path, text_content, language, confidence)
                        VALUES (?, ?, ?, ?)
                    """, (
                        image_path,
                        result['text'],
                        language,
                        result['confidence']
                    ))
                    
                    # Update search index
                    cursor.execute("""
                        INSERT OR REPLACE INTO ocr_search_index 
                        (image_path, text_content, language)
                        VALUES (?, ?, ?)
                    """, (
                        image_path,
                        result['text'],
                        language
                    ))
                    
                    # Store statistics
                    stats = result['statistics']
                    cursor.execute("""
                        INSERT OR REPLACE INTO ocr_stats 
                        (image_path, word_count, char_count, line_count, languages)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        image_path,
                        stats['word_count'],
                        stats['char_count'],
                        stats['line_count'],
                        json.dumps([language])
                    ))
                    
                    successful += 1
                    print(f"  Success: {stats['word_count']} words extracted")
                else:
                    # Store empty result
                    cursor.execute("""
                        INSERT OR REPLACE INTO ocr_text 
                        (image_path, text_content, language, confidence)
                        VALUES (?, ?, ?, ?)
                    """, (
                        image_path,
                        '',
                        language,
                        0.0
                    ))
                    
                    failed += 1
                    print(f"  Failed: {result.get('message', 'Unknown error')}")
                
                processed += 1
                
            except Exception as e:
                print(f"  Error: {e}")
                failed += 1
                processed += 1
        
        self.conn.commit()
        
        return {
            'status': 'completed',
            'processed': processed,
            'successful': successful,
            'failed': failed,
            'message': f'Processed {processed} images, {successful} successful, {failed} failed'
        }
    
    def search_text(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        language: Optional[str] = None
    ) -> Dict:
        """
        Search for images containing specific text.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            offset: Pagination offset
            language: Optional language filter
            
        Returns:
            Dictionary with search results
        """
        cursor = self.conn.cursor()
        
        try:
            # Build FTS5 query
            fts_query = f'"{query}"'
            
            params = []
            where_clauses = []
            
            if language:
                where_clauses.append("language = ?")
                params.append(language)
            
            where_clause = " AND ".join(where_clauses)
            if where_clause:
                where_clause = " WHERE " + where_clause
            
            # Execute FTS5 search
            search_query = f"""
                SELECT 
                    image_path,
                    text_content,
                    language,
                    confidence,
                    extracted_at
                FROM ocr_search_index
                {where_clause}
                WHERE ocr_search_index MATCH ?
                ORDER BY rank
                LIMIT ? OFFSET ?
            """
            
            params = [fts_query, limit, offset] if not language else [language, fts_query, limit, offset]
            
            cursor.execute(search_query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    'image_path': row['image_path'],
                    'text_content': row['text_content'],
                    'language': row['language'],
                    'confidence': row['confidence'],
                    'extracted_at': row['extracted_at']
                })
            
            # Get total count
            count_query = f"""
                SELECT COUNT(*) as count 
                FROM ocr_search_index
                {where_clause}
                WHERE ocr_search_index MATCH ?
            """
            
            count_params = [fts_query] if not language else [language, fts_query]
            cursor.execute(count_query, count_params)
            total = cursor.fetchone()['count']
            
            return {
                'status': 'success',
                'query': query,
                'total': total,
                'limit': limit,
                'offset': offset,
                'results': results
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'query': query,
                'total': 0,
                'results': []
            }
    
    def get_ocr_stats(self, image_path: str) -> Dict:
        """
        Get OCR statistics for a specific image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary with OCR statistics
        """
        cursor = self.conn.cursor()
        
        # Get OCR text
        cursor.execute("""
            SELECT text_content, language, confidence, extracted_at
            FROM ocr_text
            WHERE image_path = ?
        """, (image_path,))
        
        text_row = cursor.fetchone()
        
        if not text_row:
            return {
                'image_path': image_path,
                'status': 'not_processed',
                'text_content': '',
                'statistics': {}
            }
        
        # Get statistics
        cursor.execute("""
            SELECT word_count, char_count, line_count, languages
            FROM ocr_stats
            WHERE image_path = ?
        """, (image_path,))
        
        stats_row = cursor.fetchone()
        
        result = {
            'image_path': image_path,
            'status': 'processed',
            'text_content': text_row['text_content'],
            'language': text_row['language'],
            'confidence': text_row['confidence'],
            'extracted_at': text_row['extracted_at'],
            'statistics': {
                'word_count': stats_row['word_count'] if stats_row else 0,
                'char_count': stats_row['char_count'] if stats_row else 0,
                'line_count': stats_row['line_count'] if stats_row else 0,
                'languages': json.loads(stats_row['languages']) if stats_row else []
            }
        }
        
        return result
    
    def get_ocr_summary(self) -> Dict:
        """
        Get summary statistics about OCR processing.
        
        Returns:
            Dictionary with OCR summary
        """
        cursor = self.conn.cursor()
        
        # Total images processed
        cursor.execute("SELECT COUNT(*) as count FROM ocr_text")
        total_images = cursor.fetchone()['count']
        
        # Images with text
        cursor.execute("SELECT COUNT(*) as count FROM ocr_text WHERE text_content != ''")
        images_with_text = cursor.fetchone()['count']
        
        # Total word count
        cursor.execute("SELECT SUM(word_count) as count FROM ocr_stats")
        total_words = cursor.fetchone()['count'] or 0
        
        # Language distribution
        cursor.execute("""
            SELECT language, COUNT(*) as count
            FROM ocr_text
            WHERE text_content != ''
            GROUP BY language
            ORDER BY count DESC
        """)
        
        language_distribution = {}
        for row in cursor.fetchall():
            language_distribution[row['language']] = row['count']
        
        # Images with most text
        cursor.execute("""
            SELECT image_path, word_count
            FROM ocr_stats
            ORDER BY word_count DESC
            LIMIT 5
        """)
        
        images_with_most_text = []
        for row in cursor.fetchall():
            images_with_most_text.append({
                'image_path': row['image_path'],
                'word_count': row['word_count']
            })
        
        # Recent OCR processing
        cursor.execute("""
            SELECT image_path, extracted_at, word_count
            FROM ocr_text
            JOIN ocr_stats ON ocr_text.image_path = ocr_stats.image_path
            ORDER BY extracted_at DESC
            LIMIT 5
        """)
        
        recent_ocr = []
        for row in cursor.fetchall():
            recent_ocr.append({
                'image_path': row['image_path'],
                'extracted_at': row['extracted_at'],
                'word_count': row['word_count']
            })
        
        return {
            'total_images_processed': total_images,
            'images_with_text': images_with_text,
            'images_without_text': total_images - images_with_text,
            'total_words_extracted': total_words,
            'language_distribution': language_distribution,
            'images_with_most_text': images_with_most_text,
            'recent_ocr_processing': recent_ocr,
            'avg_words_per_image': round(total_words / images_with_text, 2) if images_with_text > 0 else 0
        }
    
    def delete_ocr_data(self, image_path: str) -> bool:
        """
        Delete OCR data for a specific image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            True if deleted, False if not found
        """
        cursor = self.conn.cursor()
        
        # Delete from all tables
        cursor.execute("DELETE FROM ocr_text WHERE image_path = ?", (image_path,))
        cursor.execute("DELETE FROM ocr_search_index WHERE image_path = ?", (image_path,))
        cursor.execute("DELETE FROM ocr_stats WHERE image_path = ?", (image_path,))
        
        deleted_count = cursor.rowcount
        self.conn.commit()
        
        return deleted_count > 0
    
    def clear_all_ocr_data(self) -> int:
        """
        Clear all OCR data from the database.
        
        Returns:
            Number of records deleted
        """
        cursor = self.conn.cursor()
        
        # Delete from all tables
        cursor.execute("DELETE FROM ocr_text")
        cursor.execute("DELETE FROM ocr_search_index")
        cursor.execute("DELETE FROM ocr_stats")
        
        deleted_count = cursor.rowcount
        self.conn.commit()
        
        return deleted_count
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def main():
    """CLI interface for testing OCR search."""
    import argparse
    
    parser = argparse.ArgumentParser(description='OCR Text Search System')
    parser.add_argument('--db', default='ocr_search.db', help='Database path')
    parser.add_argument('--images', nargs='+', help='Image files to process')
    parser.add_argument('--search', help='Search for text in images')
    parser.add_argument('--stats', action='store_true', help='Show OCR statistics')
    parser.add_argument('--clear', action='store_true', help='Clear all OCR data')
    parser.add_argument('--language', default='eng', help='Language for OCR')
    
    args = parser.parse_args()
    
    with OCRSearch(args.db) as ocr_search:
        
        if args.images:
            if not OCR_LIBRARIES_AVAILABLE:
                print("Error: OCR libraries not available")
                print("Install with: pip install pytesseract opencv-python pillow numpy")
                print("And install Tesseract OCR on your system")
                return
            
            print(f"Processing {len(args.images)} images for OCR...")
            result = ocr_search.extract_text_from_images(args.images, args.language)
            
            print(f"\nResults:")
            print(f"Status: {result['status']}")
            print(f"Processed: {result['processed']}")
            print(f"Successful: {result['successful']}")
            print(f"Failed: {result['failed']}")
            print(f"Message: {result['message']}")
        
        elif args.search:
            print(f"Searching for: '{args.search}'")
            result = ocr_search.search_text(args.search)
            
            print(f"\nFound {result['total']} results:")
            for i, item in enumerate(result['results'], 1):
                print(f"\n{i}. {item['image_path']}")
                print(f"   Language: {item['language']}")
                print(f"   Confidence: {item['confidence']}")
                print(f"   Text: {item['text_content'][:100]}...")
        
        elif args.stats:
            stats = ocr_search.get_ocr_summary()
            print("OCR Processing Summary:")
            print("=" * 60)
            print(f"Total Images Processed: {stats['total_images_processed']}")
            print(f"Images with Text: {stats['images_with_text']}")
            print(f"Images without Text: {stats['images_without_text']}")
            print(f"Total Words Extracted: {stats['total_words_extracted']}")
            print(f"Avg Words/Image: {stats['avg_words_per_image']}")
            
            print(f"\nLanguage Distribution:")
            for lang, count in stats['language_distribution'].items():
                print(f"  {lang}: {count} images")
            
            print(f"\nImages with Most Text:")
            for item in stats['images_with_most_text']:
                print(f"  {item['image_path']}: {item['word_count']} words")
        
        elif args.clear:
            count = ocr_search.clear_all_ocr_data()
            print(f"Cleared {count} OCR records")
        
        else:
            parser.print_help()


if __name__ == "main":
    main()