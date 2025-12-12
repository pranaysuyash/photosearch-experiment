"""
Format Analyzer - Media File Format Analysis and Search

This module extends the file discovery system (Task 1) with format-based
analysis and search capabilities. It provides directory-wise format statistics,
format-specific search, and format existence checking.

Features:
- Directory-wise format statistics (e.g., "Photos: 4 JPG, 3 PNG")
- Search folders by format type
- Check format existence in specific directory
- Format summary across all directories
- List files by format
- Reuses Task 1's catalog

Usage:
    # Interactive mode
    python format_analyzer.py
    
    # Command line
    python format_analyzer.py --stats
    python format_analyzer.py --find-format jpg
    python format_analyzer.py --check-format jpg --directory Photos
    python format_analyzer.py --summary

Dependencies:
    - file_discovery.py (Task 1)

Author: Antigravity AI Assistant
Date: 2025-12-06
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# Import catalog loading from Task 1
from src.file_discovery import load_catalog

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_format_statistics(catalog: Dict) -> Dict[str, Dict[str, int]]:
    """
    Analyze catalog and generate format statistics per directory.
    
    Args:
        catalog: Catalog data from Task 1
        
    Returns:
        Dictionary mapping directories to format counts
        
    Example:
        >>> stats = get_format_statistics(catalog)
        >>> print(stats['/Users/pranay/Photos'])
        {'jpg': 4, 'png': 3, 'gif': 2}
    """
    format_stats = defaultdict(lambda: defaultdict(int))
    catalog_data = catalog.get('catalog', {})
    
    for directory, files in catalog_data.items():
        for file_info in files:
            # Extract format from filename
            ext = Path(file_info['name']).suffix.lower().lstrip('.')
            if ext:
                format_stats[directory][ext] += 1
    
    return dict(format_stats)


def display_directory_formats(catalog: Dict, directory: str = None):
    """
    Display format breakdown for specific directory or all directories.
    
    Args:
        catalog: Catalog data from Task 1
        directory: Optional directory path (partial match supported)
    """
    stats = get_format_statistics(catalog)
    
    if not stats:
        print("\nNo media files found in catalog.")
        return
    
    print("\n" + "="*60)
    print("FORMAT STATISTICS BY DIRECTORY")
    print("="*60 + "\n")
    
    # Filter by directory if specified
    if directory:
        matching_dirs = [d for d in stats.keys() if directory.lower() in d.lower()]
        if not matching_dirs:
            print(f"No directories matching '{directory}' found.")
            return
        dirs_to_show = matching_dirs
    else:
        dirs_to_show = sorted(stats.keys())
    
    for dir_path in dirs_to_show:
        formats = stats[dir_path]
        print(f"{dir_path}")
        
        # Sort formats by count (descending) then alphabetically
        sorted_formats = sorted(formats.items(), key=lambda x: (-x[1], x[0]))
        
        for fmt, count in sorted_formats:
            plural = "file" if count == 1 else "files"
            print(f"  {fmt}: {count} {plural}")
        
        print()
    
    print("="*60 + "\n")


def search_by_format(catalog: Dict, format: str) -> List[Tuple[str, int]]:
    """
    Find all directories containing files of specific format.
    
    Args:
        catalog: Catalog data from Task 1
        format: File format to search for (e.g., 'jpg', 'mp4')
        
    Returns:
        List of tuples (directory_path, file_count)
        
    Example:
        >>> results = search_by_format(catalog, 'jpg')
        >>> for dir_path, count in results:
        ...     print(f"{dir_path}: {count} files")
    """
    format = format.lower().lstrip('.')
    stats = get_format_statistics(catalog)
    
    results = []
    for directory, formats in stats.items():
        if format in formats:
            results.append((directory, formats[format]))
    
    # Sort by count (descending) then directory name
    results.sort(key=lambda x: (-x[1], x[0]))
    
    return results


def check_format_in_directory(catalog: Dict, format: str, directory: str) -> Tuple[bool, List[str]]:
    """
    Check if specific format exists in specific directory.
    
    Args:
        catalog: Catalog data from Task 1
        format: File format to check (e.g., 'jpg')
        directory: Directory name (partial match supported)
        
    Returns:
        Tuple of (exists: bool, files: List[str])
        
    Example:
        >>> exists, files = check_format_in_directory(catalog, 'jpg', 'Photos')
        >>> if exists:
        ...     print(f"Found {len(files)} JPG files")
    """
    format = format.lower().lstrip('.')
    catalog_data = catalog.get('catalog', {})
    
    # Find matching directory
    matching_dirs = [d for d in catalog_data.keys() if directory.lower() in d.lower()]
    
    if not matching_dirs:
        return (False, [])
    
    # Use first matching directory
    dir_path = matching_dirs[0]
    files = catalog_data[dir_path]
    
    # Find files with matching format
    matching_files = []
    for file_info in files:
        ext = Path(file_info['name']).suffix.lower().lstrip('.')
        if ext == format:
            matching_files.append(file_info['name'])
    
    return (len(matching_files) > 0, matching_files)


def get_format_summary(catalog: Dict) -> Dict[str, int]:
    """
    Overall format statistics across all directories.
    
    Args:
        catalog: Catalog data from Task 1
        
    Returns:
        Dictionary mapping formats to total counts
        
    Example:
        >>> summary = get_format_summary(catalog)
        >>> print(summary)
        {'jpg': 150, 'png': 89, 'mp4': 45}
    """
    format_totals = defaultdict(int)
    stats = get_format_statistics(catalog)
    
    for directory, formats in stats.items():
        for fmt, count in formats.items():
            format_totals[fmt] += count
    
    return dict(format_totals)


def list_files_by_format(catalog: Dict, format: str, directory: str = None) -> List[Dict]:
    """
    List all files of specific format.
    
    Args:
        catalog: Catalog data from Task 1
        format: File format to list (e.g., 'jpg')
        directory: Optional directory filter (partial match)
        
    Returns:
        List of file info dictionaries with full paths
        
    Example:
        >>> files = list_files_by_format(catalog, 'jpg')
        >>> for file in files:
        ...     print(file['path'])
    """
    format = format.lower().lstrip('.')
    catalog_data = catalog.get('catalog', {})
    
    results = []
    
    for dir_path, files in catalog_data.items():
        # Filter by directory if specified
        if directory and directory.lower() not in dir_path.lower():
            continue
        
        for file_info in files:
            ext = Path(file_info['name']).suffix.lower().lstrip('.')
            if ext == format:
                result = file_info.copy()
                result['folder'] = dir_path
                result['path'] = os.path.join(dir_path, file_info['name'])
                results.append(result)
    
    return results


def display_format_summary(catalog: Dict):
    """
    Display overall format summary.
    
    Args:
        catalog: Catalog data from Task 1
    """
    summary = get_format_summary(catalog)
    
    if not summary:
        print("\nNo media files found in catalog.")
        return
    
    print("\n" + "="*60)
    print("FORMAT SUMMARY (All Directories)")
    print("="*60 + "\n")
    
    # Sort by count (descending) then format name
    sorted_formats = sorted(summary.items(), key=lambda x: (-x[1], x[0]))
    
    total_files = 0
    for fmt, count in sorted_formats:
        plural = "file" if count == 1 else "files"
        print(f"{fmt}: {count} {plural}")
        total_files += count
    
    print(f"\nTotal: {total_files} files across {len(summary)} formats")
    print("="*60 + "\n")


def main():
    """
    Main CLI interface for format analyzer.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Media File Format Analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python format_analyzer.py
  
  # Show format stats for all directories
  python format_analyzer.py --stats
  
  # Show format stats for specific directory
  python format_analyzer.py --stats --directory Photos
  
  # Find all folders with JPG files
  python format_analyzer.py --find-format jpg
  
  # Check if JPG exists in Photos directory
  python format_analyzer.py --check-format jpg --directory Photos
  
  # List all MP4 files
  python format_analyzer.py --list-format mp4
  
  # Format summary
  python format_analyzer.py --summary
        """
    )
    
    parser.add_argument('--stats', action='store_true', 
                       help='Show format statistics by directory')
    parser.add_argument('--find-format', type=str, 
                       help='Find all directories with specific format')
    parser.add_argument('--check-format', type=str, 
                       help='Check if format exists in directory')
    parser.add_argument('--list-format', type=str, 
                       help='List all files of specific format')
    parser.add_argument('--summary', action='store_true', 
                       help='Show format summary across all directories')
    parser.add_argument('--directory', type=str, 
                       help='Directory name (partial match supported)')
    parser.add_argument('--catalog', type=str, default='media_catalog.json',
                       help='Catalog file path (default: media_catalog.json)')
    
    args = parser.parse_args()
    
    # If no arguments, run interactive mode
    if not any([args.stats, args.find_format, args.check_format, 
                args.list_format, args.summary]):
        interactive_mode(args.catalog)
        return
    
    # Load catalog
    catalog = load_catalog(args.catalog)
    if not catalog:
        print(f"Error: Could not load catalog from {args.catalog}")
        print("Please run file_discovery.py --scan first to create a catalog.")
        return
    
    # Handle command-line arguments
    if args.stats:
        display_directory_formats(catalog, args.directory)
    
    elif args.find_format:
        results = search_by_format(catalog, args.find_format)
        
        if results:
            fmt_upper = args.find_format.upper()
            print(f"\nFound {fmt_upper} files in {len(results)} directories:\n")
            for dir_path, count in results:
                plural = "file" if count == 1 else "files"
                print(f"  {dir_path} ({count} {plural})")
            print()
        else:
            print(f"\nNo {args.find_format.upper()} files found in any directory.\n")
    
    elif args.check_format:
        if not args.directory:
            print("Error: --directory required with --check-format")
            return
        
        exists, files = check_format_in_directory(catalog, args.check_format, args.directory)
        
        fmt_upper = args.check_format.upper()
        
        if exists:
            # Find the actual directory path for display
            catalog_data = catalog.get('catalog', {})
            matching_dirs = [d for d in catalog_data.keys() 
                           if args.directory.lower() in d.lower()]
            dir_path = matching_dirs[0] if matching_dirs else args.directory
            
            print(f"\n✓ {fmt_upper} files found in {dir_path}\n")
            print("Files:")
            for filename in files:
                print(f"  - {filename}")
            plural = "file" if len(files) == 1 else "files"
            print(f"\nTotal: {len(files)} {plural}\n")
        else:
            print(f"\n✗ No {fmt_upper} files found in directories matching '{args.directory}'\n")
    
    elif args.list_format:
        files = list_files_by_format(catalog, args.list_format, args.directory)
        
        if files:
            fmt_upper = args.list_format.upper()
            plural = "file" if len(files) == 1 else "files"
            print(f"\n{fmt_upper} {plural} ({len(files)} total):\n")
            for file_info in files:
                size_kb = file_info['size'] / 1024 if file_info['size'] > 0 else 0
                if size_kb > 0:
                    print(f"  {file_info['path']} ({size_kb:.1f} KB)")
                else:
                    print(f"  {file_info['path']} ({file_info['size']} bytes)")
            print()
        else:
            filter_msg = f" in '{args.directory}'" if args.directory else ""
            print(f"\nNo {args.list_format.upper()} files found{filter_msg}.\n")
    
    elif args.summary:
        display_format_summary(catalog)


def interactive_mode(catalog_file: str = 'media_catalog.json'):
    """
    Interactive CLI menu.
    
    Args:
        catalog_file: Path to catalog file
    """
    # Load catalog once
    catalog = load_catalog(catalog_file)
    if not catalog:
        print(f"\nError: Could not load catalog from {catalog_file}")
        print("Please run file_discovery.py --scan first to create a catalog.\n")
        return
    
    while True:
        print("\n" + "="*60)
        print("MEDIA FILE FORMAT ANALYZER")
        print("="*60)
        print("1. Show format statistics (all directories)")
        print("2. Show format statistics (specific directory)")
        print("3. Search folders by format")
        print("4. Check format in specific directory")
        print("5. List all files of specific format")
        print("6. Display format summary")
        print("7. Exit")
        print("="*60)
        
        choice = input("\nEnter your choice (1-7): ").strip()
        
        if choice == '1':
            display_directory_formats(catalog)
        
        elif choice == '2':
            directory = input("\nEnter directory name (partial match): ").strip()
            if directory:
                display_directory_formats(catalog, directory)
            else:
                print("\nDirectory name cannot be empty.")
        
        elif choice == '3':
            format_type = input("\nEnter format to search (e.g., jpg, mp4): ").strip()
            if format_type:
                results = search_by_format(catalog, format_type)
                
                if results:
                    fmt_upper = format_type.upper()
                    print(f"\nFound {fmt_upper} files in {len(results)} directories:\n")
                    for dir_path, count in results:
                        plural = "file" if count == 1 else "files"
                        print(f"  {dir_path} ({count} {plural})")
                else:
                    print(f"\nNo {format_type.upper()} files found in any directory.")
            else:
                print("\nFormat cannot be empty.")
        
        elif choice == '4':
            format_type = input("\nEnter format (e.g., jpg, mp4): ").strip()
            directory = input("Enter directory name (partial match): ").strip()
            
            if format_type and directory:
                exists, files = check_format_in_directory(catalog, format_type, directory)
                
                fmt_upper = format_type.upper()
                
                if exists:
                    # Find the actual directory path
                    catalog_data = catalog.get('catalog', {})
                    matching_dirs = [d for d in catalog_data.keys() 
                                   if directory.lower() in d.lower()]
                    dir_path = matching_dirs[0] if matching_dirs else directory
                    
                    print(f"\n✓ {fmt_upper} files found in {dir_path}\n")
                    print("Files:")
                    for filename in files:
                        print(f"  - {filename}")
                    plural = "file" if len(files) == 1 else "files"
                    print(f"\nTotal: {len(files)} {plural}")
                else:
                    print(f"\n✗ No {fmt_upper} files found in directories matching '{directory}'")
            else:
                print("\nBoth format and directory are required.")
        
        elif choice == '5':
            format_type = input("\nEnter format to list (e.g., jpg, mp4): ").strip()
            directory = input("Enter directory filter (optional, press Enter to skip): ").strip()
            directory = directory if directory else None
            
            if format_type:
                files = list_files_by_format(catalog, format_type, directory)
                
                if files:
                    fmt_upper = format_type.upper()
                    plural = "file" if len(files) == 1 else "files"
                    print(f"\n{fmt_upper} {plural} ({len(files)} total):\n")
                    
                    # Limit display to first 50 files
                    for file_info in files[:50]:
                        size_kb = file_info['size'] / 1024 if file_info['size'] > 0 else 0
                        if size_kb > 0:
                            print(f"  {file_info['path']} ({size_kb:.1f} KB)")
                        else:
                            print(f"  {file_info['path']} ({file_info['size']} bytes)")
                    
                    if len(files) > 50:
                        print(f"\n  ... and {len(files) - 50} more files")
                else:
                    filter_msg = f" in '{directory}'" if directory else ""
                    print(f"\nNo {format_type.upper()} files found{filter_msg}.")
            else:
                print("\nFormat cannot be empty.")
        
        elif choice == '6':
            display_format_summary(catalog)
        
        elif choice == '7':
            print("\nGoodbye!")
            break
        
        else:
            print("\nInvalid choice. Please enter 1-7.")


if __name__ == "__main__":
    main()
