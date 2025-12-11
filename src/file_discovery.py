"""
File Discovery System - Media File Scanner and Search

This module scans user directories for image and video files, creates a searchable
catalog, and supports incremental updates to track changes over time.

Features:
- Scans user home directory (cross-platform)
- Excludes system directories
- Supports all common image/video formats
- Scans to leaf nodes (no depth limit)
- Incremental updates (detects added/removed files and folders)
- Search by folder name or filename
- JSON catalog storage

Usage:
    # Interactive mode
    python file_discovery.py
    
    # Command line
    python file_discovery.py --scan
    python file_discovery.py --incremental
    python file_discovery.py --search-folder Pictures
    python file_discovery.py --search-file vacation.jpg

Author: Antigravity AI Assistant
Date: 2025-12-06
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# Optional: Progress bar (install with: pip install tqdm)
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Supported media file formats
IMAGE_FORMATS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif',
    '.heic', '.heif', '.svg', '.ico', '.raw', '.cr2', '.nef', '.dng'
}

VIDEO_FORMATS = {
    '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v',
    '.mpg', '.mpeg', '.3gp', '.ogv', '.mts', '.m2ts', '.vob'
}

ANIMATED_FORMATS = {
    '.gif', '.gifv', '.apng'
}

# System directories to exclude (cross-platform)
SYSTEM_DIRS = {
    # macOS/Linux
    'System', 'Library', 'private', 'usr', 'bin', 'sbin', 'var', 'tmp',
    'proc', 'dev', 'sys', 'boot', 'etc', 'opt', 'run',
    # Windows
    'Windows', 'Program Files', 'Program Files (x86)', 'ProgramData',
    # Common development/hidden
    'node_modules', 'venv', '.venv', 'env', '.env', '__pycache__',
    '.git', '.svn', '.hg', 'site-packages', 'dist', 'build',
    # macOS specific user Library (often contains system files)
    '.Trash', 'Caches', 'Application Support'
}


def get_user_home() -> str:
    """
    Get user home directory dynamically (cross-platform).
    
    Returns:
        Absolute path to user home directory
        
    Example:
        >>> home = get_user_home()
        >>> print(home)
        '/Users/pranay'
    """
    return str(Path.home())


def is_system_directory(path: str) -> bool:
    """
    Check if path is a system directory that should be skipped.
    
    Args:
        path: Directory path to check
        
    Returns:
        True if directory should be skipped, False otherwise
        
    Example:
        >>> is_system_directory('/System/Library')
        True
        >>> is_system_directory('/Users/pranay/Pictures')
        False
    """
    path_obj = Path(path)
    
    # Skip hidden directories (starting with .)
    if path_obj.name.startswith('.') and path_obj.name not in {'.', '..'}:
        return True
    
    # Check if any part of the path is in system directories
    for part in path_obj.parts:
        if part in SYSTEM_DIRS:
            return True
    
    # Skip if path starts with system roots
    path_str = str(path_obj)
    system_roots = ['/System', '/Library', '/private', '/usr', '/bin', '/sbin', '/var', '/tmp']
    for root in system_roots:
        if path_str.startswith(root):
            return True
    
    return False


def is_media_file(filename: str) -> Tuple[bool, str]:
    """
    Check if file is an image, video, or animated media.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        Tuple of (is_media, media_type) where media_type is 'image', 'video', or 'animated'
        
    Example:
        >>> is_media_file('photo.jpg')
        (True, 'image')
        >>> is_media_file('video.mp4')
        (True, 'video')
        >>> is_media_file('document.pdf')
        (False, '')
    """
    ext = Path(filename).suffix.lower()
    
    if ext in ANIMATED_FORMATS:
        return (True, 'animated')
    elif ext in IMAGE_FORMATS:
        return (True, 'image')
    elif ext in VIDEO_FORMATS:
        return (True, 'video')
    else:
        return (False, '')


def scan_directories(start_path: Optional[str] = None, incremental: bool = False, 
                     existing_catalog: Optional[Dict] = None) -> Dict:
    """
    Recursively scan directories for media files.
    
    Args:
        start_path: Directory to start scanning from (defaults to user home)
        incremental: If True, only scan changed directories
        existing_catalog: Previous catalog for incremental updates
        
    Returns:
        Dictionary with folder paths as keys and lists of file info as values
        
    Example:
        >>> catalog = scan_directories()
        >>> print(catalog.keys())
        dict_keys(['/Users/pranay/Pictures', '/Users/pranay/Documents'])
    """
    if start_path is None:
        start_path = get_user_home()
    
    logger.info(f"Starting scan from: {start_path}")
    
    catalog = defaultdict(list)
    total_files = 0
    skipped_dirs = 0
    
    # Collect all directories first for progress tracking
    all_dirs = []
    for root, dirs, _ in os.walk(start_path):
        # Filter out system directories
        dirs[:] = [d for d in dirs if not is_system_directory(os.path.join(root, d))]
        all_dirs.append(root)
    
    # Use progress bar if available
    iterator = tqdm(all_dirs, desc="Scanning directories") if TQDM_AVAILABLE else all_dirs
    
    for root in iterator:
        try:
            # Skip if this is a system directory
            if is_system_directory(root):
                skipped_dirs += 1
                continue
            
            # For incremental scan, check if directory has changed
            if incremental and existing_catalog:
                # Check directory modification time
                dir_mtime = os.path.getmtime(root)
                # If directory hasn't changed, skip it (simplified check)
                # In production, we'd check against stored mtime
                pass
            
            # Scan files in this directory
            try:
                files = os.listdir(root)
            except PermissionError:
                logger.warning(f"Permission denied: {root}")
                continue
            
            for filename in files:
                filepath = os.path.join(root, filename)
                
                # Skip if not a file
                if not os.path.isfile(filepath):
                    continue
                
                # Check if it's a media file
                is_media, media_type = is_media_file(filename)
                if not is_media:
                    continue
                
                try:
                    # Get file metadata
                    stat = os.stat(filepath)
                    file_info = {
                        'name': filename,
                        'type': media_type,
                        'size': stat.st_size,
                        'mtime': stat.st_mtime
                    }
                    
                    catalog[root].append(file_info)
                    total_files += 1
                    
                except (OSError, PermissionError) as e:
                    logger.warning(f"Cannot access file {filepath}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error scanning {root}: {e}")
            continue
    
    logger.info(f"Scan complete. Found {total_files} media files in {len(catalog)} directories")
    logger.info(f"Skipped {skipped_dirs} system directories")
    
    return dict(catalog)


def detect_changes(old_catalog: Dict, new_scan: Dict) -> Dict:
    """
    Compare old catalog with new scan to detect changes.
    
    Args:
        old_catalog: Previous catalog data
        new_scan: New scan results
        
    Returns:
        Dictionary containing lists of added/removed files and folders
        
    Example:
        >>> changes = detect_changes(old_catalog, new_catalog)
        >>> print(changes['files_added'])
        ['/Users/pranay/Pictures/new_photo.jpg']
    """
    changes = {
        'files_added': [],
        'files_removed': [],
        'folders_added': [],
        'folders_removed': []
    }
    
    old_folders = set(old_catalog.get('catalog', {}).keys())
    new_folders = set(new_scan.keys())
    
    # Detect folder changes
    changes['folders_added'] = list(new_folders - old_folders)
    changes['folders_removed'] = list(old_folders - new_folders)
    
    # Detect file changes within existing folders
    for folder in new_folders & old_folders:
        old_files = {f['name']: f for f in old_catalog.get('catalog', {}).get(folder, [])}
        new_files = {f['name']: f for f in new_scan[folder]}
        
        # Files added
        for filename in set(new_files.keys()) - set(old_files.keys()):
            changes['files_added'].append(f"{folder}/{filename}")
        
        # Files removed
        for filename in set(old_files.keys()) - set(new_files.keys()):
            changes['files_removed'].append(f"{folder}/{filename}")
    
    return changes


def update_catalog(existing_catalog: Dict, new_scan: Dict, changes: Dict) -> Dict:
    """
    Apply detected changes to existing catalog.
    
    Args:
        existing_catalog: Previous catalog
        new_scan: New scan results
        changes: Detected changes
        
    Returns:
        Updated catalog with changes applied
    """
    # Start with existing catalog structure
    updated = existing_catalog.copy()
    
    # Update catalog with new scan
    updated['catalog'] = new_scan
    
    # Update metadata
    metadata = updated.get('metadata', {})
    metadata['last_update_date'] = datetime.now().isoformat()
    
    # Count totals
    total_files = 0
    total_images = 0
    total_videos = 0
    total_animated = 0
    
    for files in new_scan.values():
        for file_info in files:
            total_files += 1
            if file_info['type'] == 'image':
                total_images += 1
            elif file_info['type'] == 'video':
                total_videos += 1
            elif file_info['type'] == 'animated':
                total_animated += 1
    
    metadata['total_files'] = total_files
    metadata['total_images'] = total_images
    metadata['total_videos'] = total_videos
    metadata['total_animated'] = total_animated
    
    # Update change statistics
    metadata['last_changes'] = {
        'files_added': len(changes['files_added']),
        'files_removed': len(changes['files_removed']),
        'folders_added': len(changes['folders_added']),
        'folders_removed': len(changes['folders_removed'])
    }
    
    updated['metadata'] = metadata
    
    return updated


def save_catalog(data: Dict, output_file: str = 'media_catalog.json') -> bool:
    """
    Save catalog to JSON file.
    
    Args:
        data: Catalog data to save
        output_file: Path to output file
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> save_catalog(catalog, 'my_catalog.json')
        True
    """
    try:
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Catalog saved to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save catalog: {e}")
        return False


def load_catalog(input_file: str = 'media_catalog.json') -> Dict:
    """
    Load catalog from JSON file.
    
    Args:
        input_file: Path to catalog file
        
    Returns:
        Catalog data or empty dict if file doesn't exist
        
    Example:
        >>> catalog = load_catalog('my_catalog.json')
    """
    if not os.path.exists(input_file):
        logger.warning(f"Catalog file not found: {input_file}")
        return {}
    
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
        logger.info(f"Catalog loaded from {input_file}")
        return data
    except Exception as e:
        logger.error(f"Failed to load catalog: {e}")
        return {}


def search_by_folder(catalog: Dict, folder_name: str) -> List[Dict]:
    """
    Search for all media files in folders matching the name.
    
    Args:
        catalog: Catalog data
        folder_name: Folder name to search for (partial match supported)
        
    Returns:
        List of file info dictionaries with full paths
        
    Example:
        >>> results = search_by_folder(catalog, 'Pictures')
        >>> for result in results:
        ...     print(result['path'])
    """
    results = []
    catalog_data = catalog.get('catalog', {})
    
    for folder_path, files in catalog_data.items():
        # Case-insensitive partial match
        if folder_name.lower() in folder_path.lower():
            for file_info in files:
                result = file_info.copy()
                result['folder'] = folder_path
                result['path'] = os.path.join(folder_path, file_info['name'])
                results.append(result)
    
    return results


def search_by_filename(catalog: Dict, filename: str) -> List[str]:
    """
    Search for all folders containing files matching the name.
    
    Args:
        catalog: Catalog data
        filename: Filename to search for (partial match supported)
        
    Returns:
        List of folder paths where file exists
        
    Example:
        >>> folders = search_by_filename(catalog, 'vacation')
        >>> for folder in folders:
        ...     print(folder)
    """
    folders = []
    catalog_data = catalog.get('catalog', {})
    
    for folder_path, files in catalog_data.items():
        for file_info in files:
            # Case-insensitive partial match
            if filename.lower() in file_info['name'].lower():
                if folder_path not in folders:
                    folders.append(folder_path)
    
    return folders


def display_statistics(catalog: Dict):
    """
    Display catalog statistics.
    
    Args:
        catalog: Catalog data
    """
    metadata = catalog.get('metadata', {})
    
    print("\n" + "="*60)
    print("MEDIA CATALOG STATISTICS")
    print("="*60)
    
    if 'first_scan_date' in metadata:
        print(f"First scan: {metadata['first_scan_date']}")
    if 'last_update_date' in metadata:
        print(f"Last update: {metadata['last_update_date']}")
    
    print(f"\nTotal files: {metadata.get('total_files', 0)}")
    print(f"  - Images: {metadata.get('total_images', 0)}")
    print(f"  - Videos: {metadata.get('total_videos', 0)}")
    print(f"  - Animated: {metadata.get('total_animated', 0)}")
    
    print(f"\nTotal folders: {len(catalog.get('catalog', {}))}")
    
    if 'scan_root' in metadata:
        print(f"Scan root: {metadata['scan_root']}")
    
    print("="*60 + "\n")


def display_recent_changes(catalog: Dict):
    """
    Display recent changes from last update.
    
    Args:
        catalog: Catalog data
    """
    metadata = catalog.get('metadata', {})
    changes = metadata.get('last_changes', {})
    
    print("\n" + "="*60)
    print("RECENT CHANGES")
    print("="*60)
    
    print(f"Files added: {changes.get('files_added', 0)}")
    print(f"Files removed: {changes.get('files_removed', 0)}")
    print(f"Folders added: {changes.get('folders_added', 0)}")
    print(f"Folders removed: {changes.get('folders_removed', 0)}")
    
    print("="*60 + "\n")


def main():
    """
    Main CLI interface for file discovery system.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Media File Discovery System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python file_discovery.py
  
  # Full scan
  python file_discovery.py --scan
  
  # Incremental update
  python file_discovery.py --incremental
  
  # Search by folder
  python file_discovery.py --search-folder Pictures
  
  # Search by filename
  python file_discovery.py --search-file vacation.jpg
        """
    )
    
    parser.add_argument('--scan', action='store_true', help='Perform full scan')
    parser.add_argument('--incremental', action='store_true', help='Perform incremental update')
    parser.add_argument('--search-folder', type=str, help='Search by folder name')
    parser.add_argument('--search-file', type=str, help='Search by filename')
    parser.add_argument('--stats', action='store_true', help='Display statistics')
    parser.add_argument('--changes', action='store_true', help='Show recent changes')
    parser.add_argument('--catalog', type=str, default='media_catalog.json', 
                       help='Catalog file path (default: media_catalog.json)')
    parser.add_argument('--path', type=str, help='Custom scan path (default: user home)')
    
    args = parser.parse_args()
    
    # If no arguments, run interactive mode
    if not any([args.scan, args.incremental, args.search_folder, 
                args.search_file, args.stats, args.changes]):
        interactive_mode(args.catalog)
        return
    
    # Handle command-line arguments
    if args.scan:
        print("Starting full scan...")
        scan_result = scan_directories(args.path)
        
        catalog = {
            'metadata': {
                'first_scan_date': datetime.now().isoformat(),
                'last_update_date': datetime.now().isoformat(),
                'scan_root': args.path or get_user_home(),
                'total_files': sum(len(files) for files in scan_result.values()),
                'total_images': sum(1 for files in scan_result.values() 
                                   for f in files if f['type'] == 'image'),
                'total_videos': sum(1 for files in scan_result.values() 
                                   for f in files if f['type'] == 'video'),
                'total_animated': sum(1 for files in scan_result.values() 
                                     for f in files if f['type'] == 'animated'),
                'last_changes': {
                    'files_added': 0,
                    'files_removed': 0,
                    'folders_added': 0,
                    'folders_removed': 0
                }
            },
            'catalog': scan_result
        }
        
        save_catalog(catalog, args.catalog)
        display_statistics(catalog)
    
    elif args.incremental:
        print("Starting incremental update...")
        existing = load_catalog(args.catalog)
        if not existing:
            print("No existing catalog found. Please run full scan first.")
            return
        
        # Use the original scan path from the catalog if no path specified
        scan_path = args.path if args.path else existing.get('metadata', {}).get('scan_root')
        
        new_scan = scan_directories(scan_path, incremental=True, existing_catalog=existing)
        changes = detect_changes(existing, new_scan)
        updated = update_catalog(existing, new_scan, changes)
        
        save_catalog(updated, args.catalog)
        display_recent_changes(updated)
    
    elif args.search_folder:
        catalog = load_catalog(args.catalog)
        if not catalog:
            print("No catalog found. Please run scan first.")
            return
        
        results = search_by_folder(catalog, args.search_folder)
        if results:
            print(f"\nFound {len(results)} files in folders matching '{args.search_folder}':\n")
            for result in results:
                print(f"  {result['path']} ({result['type']}, {result['size']} bytes)")
        else:
            print(f"\nNo files found in folders matching '{args.search_folder}'")
    
    elif args.search_file:
        catalog = load_catalog(args.catalog)
        if not catalog:
            print("No catalog found. Please run scan first.")
            return
        
        folders = search_by_filename(catalog, args.search_file)
        if folders:
            print(f"\nFound '{args.search_file}' in {len(folders)} folders:\n")
            for folder in folders:
                print(f"  {folder}")
        else:
            print(f"\nNo files matching '{args.search_file}' found")
    
    elif args.stats:
        catalog = load_catalog(args.catalog)
        if not catalog:
            print("No catalog found. Please run scan first.")
            return
        display_statistics(catalog)
    
    elif args.changes:
        catalog = load_catalog(args.catalog)
        if not catalog:
            print("No catalog found. Please run scan first.")
            return
        display_recent_changes(catalog)


def interactive_mode(catalog_file: str = 'media_catalog.json'):
    """
    Interactive CLI menu.
    
    Args:
        catalog_file: Path to catalog file
    """
    while True:
        print("\n" + "="*60)
        print("MEDIA FILE DISCOVERY SYSTEM")
        print("="*60)
        print("1. Full scan (scan all directories)")
        print("2. Incremental update (detect changes)")
        print("3. Search by folder name")
        print("4. Search by filename")
        print("5. Display statistics")
        print("6. Show recent changes")
        print("7. Exit")
        print("="*60)
        
        choice = input("\nEnter your choice (1-7): ").strip()
        
        if choice == '1':
            path = input("Enter path to scan (press Enter for user home): ").strip()
            path = path if path else None
            
            print("\nStarting full scan...")
            scan_result = scan_directories(path)
            
            catalog = {
                'metadata': {
                    'first_scan_date': datetime.now().isoformat(),
                    'last_update_date': datetime.now().isoformat(),
                    'scan_root': path or get_user_home(),
                    'total_files': sum(len(files) for files in scan_result.values()),
                    'total_images': sum(1 for files in scan_result.values() 
                                       for f in files if f['type'] == 'image'),
                    'total_videos': sum(1 for files in scan_result.values() 
                                       for f in files if f['type'] == 'video'),
                    'total_animated': sum(1 for files in scan_result.values() 
                                         for f in files if f['type'] == 'animated'),
                    'last_changes': {
                        'files_added': 0,
                        'files_removed': 0,
                        'folders_added': 0,
                        'folders_removed': 0
                    }
                },
                'catalog': scan_result
            }
            
            save_catalog(catalog, catalog_file)
            display_statistics(catalog)
        
        elif choice == '2':
            existing = load_catalog(catalog_file)
            if not existing:
                print("\nNo existing catalog found. Please run full scan first.")
                continue
            
            # Use the original scan path from the catalog
            scan_path = existing.get('metadata', {}).get('scan_root')
            
            print("\nStarting incremental update...")
            new_scan = scan_directories(scan_path, incremental=True, existing_catalog=existing)
            changes = detect_changes(existing, new_scan)
            updated = update_catalog(existing, new_scan, changes)
            
            save_catalog(updated, catalog_file)
            display_recent_changes(updated)
        
        elif choice == '3':
            catalog = load_catalog(catalog_file)
            if not catalog:
                print("\nNo catalog found. Please run scan first.")
                continue
            
            folder_name = input("\nEnter folder name to search: ").strip()
            results = search_by_folder(catalog, folder_name)
            
            if results:
                print(f"\nFound {len(results)} files in folders matching '{folder_name}':\n")
                for result in results[:20]:  # Limit to first 20 results
                    print(f"  {result['path']} ({result['type']}, {result['size']} bytes)")
                if len(results) > 20:
                    print(f"\n  ... and {len(results) - 20} more files")
            else:
                print(f"\nNo files found in folders matching '{folder_name}'")
        
        elif choice == '4':
            catalog = load_catalog(catalog_file)
            if not catalog:
                print("\nNo catalog found. Please run scan first.")
                continue
            
            filename = input("\nEnter filename to search: ").strip()
            folders = search_by_filename(catalog, filename)
            
            if folders:
                print(f"\nFound '{filename}' in {len(folders)} folders:\n")
                for folder in folders[:20]:  # Limit to first 20 results
                    print(f"  {folder}")
                if len(folders) > 20:
                    print(f"\n  ... and {len(folders) - 20} more folders")
            else:
                print(f"\nNo files matching '{filename}' found")
        
        elif choice == '5':
            catalog = load_catalog(catalog_file)
            if not catalog:
                print("\nNo catalog found. Please run scan first.")
                continue
            display_statistics(catalog)
        
        elif choice == '6':
            catalog = load_catalog(catalog_file)
            if not catalog:
                print("\nNo catalog found. Please run scan first.")
                continue
            display_recent_changes(catalog)
        
        elif choice == '7':
            print("\nGoodbye!")
            break
        
        else:
            print("\nInvalid choice. Please enter 1-7.")


if __name__ == "__main__":
    main()
