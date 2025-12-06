"""
Photo Search - Unified interface for photo discovery, metadata extraction, and search

This module provides:
- One-command scanning and indexing
- Interactive search mode
- Integration of all previous tasks
- Comprehensive search by all metadata fields

Usage:
    # Scan and index a directory
    python photo_search.py --scan ~/Photos
    
    # Interactive search
    python photo_search.py --search
    
    # Quick search
    python photo_search.py --quick-search "camera=Canon"
    
    # Show statistics
    python photo_search.py --stats

Author: Antigravity AI Assistant
Date: 2025-12-06
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import from previous tasks
from file_discovery import scan_directories, save_catalog, load_catalog
from metadata_extractor import extract_all_metadata
from metadata_search import MetadataDatabase, BatchExtractor, QueryEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PhotoSearch:
    """Unified photo search system."""
    
    def __init__(self, catalog_path: str = "photo_catalog.json", db_path: str = "photo_metadata.db"):
        """
        Initialize photo search system.
        
        Args:
            catalog_path: Path to file catalog
            db_path: Path to metadata database
        """
        self.catalog_path = catalog_path
        self.db_path = db_path
        self.db = MetadataDatabase(db_path)
        self.extractor = BatchExtractor(self.db)
        self.query_engine = QueryEngine(self.db)
    
    def scan(self, path: str, force: bool = False) -> Dict[str, Any]:
        """
        Scan directory and index all files.
        
        Args:
            path: Directory path to scan
            force: Force re-extraction of metadata
            
        Returns:
            Summary statistics
        """
        print("\n" + "="*60)
        print(f"Scanning: {path}")
        print("="*60 + "\n")
        
        # Stage 1: Discover files
        print("Stage 1/3: Discovering files...")
        
        # Scan directories - returns dict of {directory: [files]}
        catalog = scan_directories(path)
        
        if not catalog:
            logger.error("No files found")
            return {}
        
        # Save catalog
        save_catalog(catalog, self.catalog_path)
        
        # Count total files
        file_count = sum(len(files) for files in catalog.values())
        print(f"  ✓ Found {file_count} files\n")
        
        # Stage 2: Extract metadata
        print("Stage 2/3: Extracting metadata...")
        stats = self.extractor.extract_all(self.catalog_path, force=force)
        print(f"  ✓ Processed: {stats.get('processed', 0)}")
        print(f"  ✓ Updated: {stats.get('updated', 0)}")
        print(f"  ✓ Skipped: {stats.get('skipped', 0)}")
        print(f"  ✓ Errors: {stats.get('errors', 0)}\n")
        
        # Stage 3: Build search index (already done by extractor)
        print("Stage 3/3: Building search index...")
        print("  ✓ Index ready\n")
        
        # Summary
        db_stats = self.db.get_stats()
        print("="*60)
        print("SCAN COMPLETE")
        print("="*60)
        print(f"Total files: {file_count}")
        print(f"Indexed: {db_stats['active_files']}")
        print(f"Ready to search!")
        print("="*60 + "\n")
        
        return {
            'files_found': file_count,
            'files_indexed': db_stats['active_files'],
            **stats
        }
    
    def interactive_search(self):
        """Interactive search menu."""
        while True:
            print("\n" + "="*60)
            print("PHOTO SEARCH")
            print("="*60)
            print("\nSearch by Metadata:")
            print("  1. Camera (make/model)")
            print("  2. Date range (created/modified)")
            print("  3. Resolution (width/height)")
            print("  4. File size")
            print("  5. GPS location")
            print("  6. EXIF data (ISO, aperture, etc.)")
            print("  7. Video properties (duration, codec, fps)")
            print("\nSearch by File Properties:")
            print("  8. Filename")
            print("  9. File type/format")
            print(" 10. Directory/location")
            print("\nAdvanced:")
            print(" 11. Custom query")
            print(" 12. View recent results")
            print(" 13. Export results")
            print("\n  0. Exit")
            print("="*60)
            
            try:
                choice = input("\nEnter choice: ").strip()
                
                if choice == '0':
                    print("Goodbye!")
                    break
                elif choice == '1':
                    self._search_by_camera()
                elif choice == '2':
                    self._search_by_date()
                elif choice == '3':
                    self._search_by_resolution()
                elif choice == '4':
                    self._search_by_size()
                elif choice == '5':
                    self._search_by_gps()
                elif choice == '6':
                    self._search_by_exif()
                elif choice == '7':
                    self._search_by_video()
                elif choice == '8':
                    self._search_by_filename()
                elif choice == '9':
                    self._search_by_format()
                elif choice == '10':
                    self._search_by_directory()
                elif choice == '11':
                    self._custom_query()
                elif choice == '13':
                    self._export_results()
                else:
                    print("Invalid choice. Please try again.")
            
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
    
    def _search_by_camera(self):
        """Search by camera make/model."""
        camera = input("Camera make/model: ").strip()
        if camera:
            results = self.query_engine.search(f"exif.image.Make LIKE {camera}")
            self._display_results(results, f"Camera: {camera}")
    
    def _search_by_date(self):
        """Search by date range."""
        print("Date format: YYYY-MM-DD")
        start_date = input("Start date (or press Enter to skip): ").strip()
        end_date = input("End date (or press Enter to skip): ").strip()
        
        conditions = []
        if start_date:
            conditions.append(f"filesystem.created>={start_date}")
        if end_date:
            conditions.append(f"filesystem.created<={end_date}")
        
        if conditions:
            query = " AND ".join(conditions)
            results = self.query_engine.search(query)
            self._display_results(results, f"Date range: {start_date or 'any'} to {end_date or 'any'}")
    
    def _search_by_resolution(self):
        """Search by resolution."""
        min_width = input("Minimum width (or press Enter to skip): ").strip()
        min_height = input("Minimum height (or press Enter to skip): ").strip()
        
        conditions = []
        if min_width:
            conditions.append(f"image.width>={min_width}")
        if min_height:
            conditions.append(f"image.height>={min_height}")
        
        if conditions:
            query = " AND ".join(conditions)
            results = self.query_engine.search(query)
            self._display_results(results, f"Resolution: {min_width or 'any'}x{min_height or 'any'}+")
    
    def _search_by_size(self):
        """Search by file size."""
        print("Size in MB (e.g., 5 for 5MB)")
        min_size = input("Minimum size (or press Enter to skip): ").strip()
        max_size = input("Maximum size (or press Enter to skip): ").strip()
        
        conditions = []
        if min_size:
            size_bytes = int(float(min_size) * 1024 * 1024)
            conditions.append(f"filesystem.size_bytes>={size_bytes}")
        if max_size:
            size_bytes = int(float(max_size) * 1024 * 1024)
            conditions.append(f"filesystem.size_bytes<={size_bytes}")
        
        if conditions:
            query = " AND ".join(conditions)
            results = self.query_engine.search(query)
            self._display_results(results, f"Size: {min_size or '0'}MB - {max_size or '∞'}MB")
    
    def _search_by_gps(self):
        """Search by GPS location."""
        print("GPS coordinates (decimal degrees)")
        lat = input("Latitude (or press Enter to skip): ").strip()
        lon = input("Longitude (or press Enter to skip): ").strip()
        
        conditions = []
        if lat:
            conditions.append(f"gps.latitude={lat}")
        if lon:
            conditions.append(f"gps.longitude={lon}")
        
        if conditions:
            query = " AND ".join(conditions)
            results = self.query_engine.search(query)
            self._display_results(results, f"GPS: {lat}, {lon}")
    
    def _search_by_exif(self):
        """Search by EXIF data."""
        print("\nCommon EXIF fields:")
        print("  - exif.exif.ISO")
        print("  - exif.exif.FNumber (aperture)")
        print("  - exif.exif.ExposureTime")
        print("  - exif.exif.FocalLength")
        
        field = input("\nEXIF field: ").strip()
        value = input("Value: ").strip()
        
        if field and value:
            query = f"{field}={value}"
            results = self.query_engine.search(query)
            self._display_results(results, f"EXIF: {field}={value}")
    
    def _search_by_video(self):
        """Search by video properties."""
        print("\nVideo properties:")
        print("  1. Duration")
        print("  2. Codec")
        print("  3. Frame rate")
        
        choice = input("Choose property: ").strip()
        
        if choice == '1':
            min_duration = input("Minimum duration (seconds): ").strip()
            if min_duration:
                query = f"video.format.duration>={min_duration}"
                results = self.query_engine.search(query)
                self._display_results(results, f"Duration >= {min_duration}s")
        elif choice == '2':
            codec = input("Codec (e.g., h264): ").strip()
            if codec:
                query = f"video.streams.codec_name LIKE {codec}"
                results = self.query_engine.search(query)
                self._display_results(results, f"Codec: {codec}")
        elif choice == '3':
            min_fps = input("Minimum FPS: ").strip()
            if min_fps:
                query = f"video.streams.r_frame_rate>={min_fps}"
                results = self.query_engine.search(query)
                self._display_results(results, f"FPS >= {min_fps}")
    
    def _search_by_filename(self):
        """Search by filename."""
        filename = input("Filename (partial match): ").strip()
        if filename:
            query = f"file.path LIKE {filename}"
            results = self.query_engine.search(query)
            self._display_results(results, f"Filename: {filename}")
    
    def _search_by_format(self):
        """Search by file format."""
        file_format = input("Format (e.g., jpg, png, mp4): ").strip()
        if file_format:
            query = f"image.format={file_format.upper()}"
            results = self.query_engine.search(query)
            self._display_results(results, f"Format: {file_format}")
    
    def _search_by_directory(self):
        """Search by directory."""
        directory = input("Directory path (partial match): ").strip()
        if directory:
            query = f"file.path LIKE {directory}"
            results = self.query_engine.search(query)
            self._display_results(results, f"Directory: {directory}")
    
    def _custom_query(self):
        """Custom query."""
        print("\nQuery examples:")
        print("  camera=Canon AND resolution>1920")
        print("  size>5000000")
        print("  filesystem.created>2024-01-01")
        
        query = input("\nEnter query: ").strip()
        if query:
            results = self.query_engine.search(query)
            self._display_results(results, f"Custom: {query}")
    
    def _display_results(self, results: List[Dict], search_desc: str = ""):
        """Display search results."""
        print("\n" + "="*60)
        if search_desc:
            print(f"Search: {search_desc}")
        print(f"Found {len(results)} results")
        print("="*60 + "\n")
        
        if not results:
            print("No results found.")
            return
        
        # Store for export
        self.last_results = results
        
        # Display first 10
        for i, result in enumerate(results[:10], 1):
            print(f"{i}. {result['file_path']}")
            metadata = result['metadata']
            
            # Show key info
            if 'image' in metadata and metadata['image']:
                img = metadata['image']
                print(f"   Resolution: {img.get('width')}x{img.get('height')}")
            if 'filesystem' in metadata:
                fs = metadata['filesystem']
                print(f"   Size: {fs.get('size_human')}")
                print(f"   Created: {fs.get('created', 'N/A')[:10]}")
            print()
        
        if len(results) > 10:
            print(f"... and {len(results) - 10} more results")
            print("(Use option 13 to export all results)\n")
    
    def _export_results(self):
        """Export last search results."""
        if not hasattr(self, 'last_results') or not self.last_results:
            print("No results to export. Run a search first.")
            return
        
        filename = input("Export filename (e.g., results.json): ").strip()
        if not filename:
            filename = f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        format_choice = input("Format (json/csv) [json]: ").strip().lower() or 'json'
        
        self.query_engine.export_results(self.last_results, filename, format_choice)
        print(f"\n✓ Exported {len(self.last_results)} results to {filename}")
    
    def show_stats(self):
        """Show system statistics."""
        stats = self.db.get_stats()
        
        print("\n" + "="*60)
        print("PHOTO SEARCH STATISTICS")
        print("="*60)
        print(f"Active files:    {stats['active_files']}")
        print(f"Deleted files:   {stats['deleted_files']}")
        print(f"Total versions:  {stats['total_versions']}")
        print(f"Database:        {self.db_path}")
        print(f"Catalog:         {self.catalog_path}")
        print("="*60 + "\n")
    
    def quick_search(self, query: str, limit: int = 10):
        """Quick command-line search."""
        results = self.query_engine.search(query, limit=limit)
        self._display_results(results, query)
    
    def close(self):
        """Close database connection."""
        self.db.close()


def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Photo Search - Unified photo discovery and search',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan and index a directory
  python photo_search.py --scan ~/Photos
  
  # Interactive search
  python photo_search.py --search
  
  # Quick search
  python photo_search.py --quick-search "camera=Canon"
  
  # Show statistics
  python photo_search.py --stats
        """
    )
    
    parser.add_argument('--scan', metavar='PATH', help='Scan and index directory')
    parser.add_argument('--rescan', action='store_true', help='Force re-scan (re-extract metadata)')
    parser.add_argument('--search', action='store_true', help='Interactive search mode')
    parser.add_argument('--quick-search', metavar='QUERY', help='Quick command-line search')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--catalog', default='photo_catalog.json', help='Catalog file path')
    parser.add_argument('--db', default='photo_metadata.db', help='Database file path')
    parser.add_argument('--limit', type=int, default=10, help='Result limit for quick search')
    
    args = parser.parse_args()
    
    # Initialize system
    ps = PhotoSearch(catalog_path=args.catalog, db_path=args.db)
    
    try:
        if args.scan:
            ps.scan(args.scan, force=args.rescan)
        elif args.search:
            ps.interactive_search()
        elif args.quick_search:
            ps.quick_search(args.quick_search, limit=args.limit)
        elif args.stats:
            ps.show_stats()
        else:
            parser.print_help()
    
    finally:
        ps.close()


if __name__ == "__main__":
    main()
