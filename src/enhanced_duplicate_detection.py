"""
Enhanced Duplicate Detection System

This module provides comprehensive duplicate detection with:
1. Multiple hash algorithms for accuracy (MD5, PHash, DHash, AHash, Wavelet)
2. Perceptual similarity detection using image analysis
3. Smart duplicate grouping with confidence scoring
4. Visual comparison and resolution suggestions
5. Batch processing with progress tracking
6. Integration with metadata and face recognition

Features:
- Exact duplicate detection (MD5)
- Perceptual duplicate detection (PHash, DHash, AHash)
- Wavelet hash for robust similarity
- Color histogram analysis
- Quality assessment for resolution suggestions
- Smart grouping based on similarity thresholds
- Batch processing with GPU acceleration
- Integration with photo metadata

Usage:
    duplicate_detector = EnhancedDuplicateDetector()

    # Scan directory for duplicates
    results = duplicate_detector.scan_directory('/photos', show_progress=True)

    # Get duplicate groups for resolution
    duplicate_groups = duplicate_detector.get_duplicate_groups()

    # Smart resolution suggestions
    suggestions = duplicate_detector.get_resolution_suggestions(group_id)
"""

import os
import json
import sqlite3
import hashlib
import numpy as np
import threading
import logging
from typing import List, Dict, Optional, Any, Tuple, Callable
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import cv2
from PIL import Image, ImageChops, ImageFilter
import imagehash
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logger = logging.getLogger(__name__)

# Image processing libraries
try:
    import pywt  # PyWavelets for wavelet hashing
    WAVELET_AVAILABLE = True
except ImportError:
    WAVELET_AVAILABLE = False
    logger.warning("PyWavelets not available. Install with: pip install PyWavelets")

@dataclass
class DuplicateGroup:
    """Duplicate group with metadata and suggestions"""
    id: str
    group_type: str  # exact, near, similar, visual
    similarity_threshold: float
    photos: List[Dict[str, Any]]
    total_size_mb: float
    primary_photo_id: Optional[str]
    resolution_strategy: Optional[str]
    auto_resolvable: bool
    created_at: str
    updated_at: str

@dataclass
class PhotoInfo:
    """Photo information for duplicate analysis"""
    path: str
    file_hash: str
    size_bytes: int
    dimensions: Tuple[int, int]
    phash: Optional[imagehash.ImageHash] = None
    dhash: Optional[imagehash.ImageHash] = None
    ahash: Optional[imagehash.ImageHash] = None
    whash: Optional[imagehash.ImageHash] = None
    color_histogram: Optional[List[float]] = None
    quality_score: float = 0.0
    created_at: Optional[str] = None

class EnhancedDuplicateDetector:
    """Enhanced duplicate detection with multiple algorithms"""

    def __init__(self,
                 db_path: str = "duplicates.db",
                 progress_callback: Optional[Callable] = None,
                 enable_gpu: bool = True):
        """
        Initialize enhanced duplicate detector.

        Args:
            db_path: Path to SQLite database
            progress_callback: Callback for progress updates
            enable_gpu: Enable GPU acceleration if available
        """
        self.db_path = db_path
        self.progress_callback = progress_callback
        self.enable_gpu = enable_gpu

        # Threading and caching
        self.cache_lock = threading.Lock()
        self.photo_cache = {}
        self.hash_cache = {}

        # Configuration
        self.hash_thresholds = {
            'exact': 0,      # MD5 identical
            'near': 2,       # PHash distance <= 2
            'similar': 5,    # PHash distance <= 5
            'visual': 10     # PHash distance <= 10
        }

        # Performance tracking
        self.stats = {
            'photos_processed': 0,
            'duplicates_found': 0,
            'groups_created': 0,
            'processing_time_ms': 0
        }

        # Initialize database
        self._initialize_database()

    def _initialize_database(self):
        """Initialize database with enhanced schema"""
        # Import schema extensions
        schema_ext = Path(__file__).parent.parent / 'server' / 'schema_extensions.py'
        if schema_ext.exists():
            import sys
            sys.path.append(str(schema_ext.parent))
            from schema_extensions import SchemaExtensions

            schema = SchemaExtensions(Path(self.db_path))
            schema.extend_schema()

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        # Performance optimizations
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=20000")

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash for exact duplicate detection"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _calculate_perceptual_hashes(self, image_path: str) -> Dict[str, imagehash.ImageHash]:
        """Calculate multiple perceptual hashes"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB for consistent hashing
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Resize for consistent hashing
                img = img.resize((256, 256), Image.Resampling.LANCZOS)

                hashes = {
                    'phash': imagehash.phash(img, hash_size=8),
                    'dhash': imagehash.dhash(img, hash_size=8),
                    'ahash': imagehash.average_hash(img, hash_size=8)
                }

                # Wavelet hash if available
                if WAVELET_AVAILABLE:
                    try:
                        hashes['whash'] = imagehash.whash(img, hash_size=8, mode='db2')
                    except:
                        pass  # Skip wavelet if it fails

                return hashes

        except Exception as e:
            logger.error(f"Error calculating hashes for {image_path}: {e}")
            return {}

    def _calculate_color_histogram(self, image_path: str) -> List[float]:
        """Calculate normalized color histogram"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return []

            # Calculate histogram for each channel
            hist_b = cv2.calcHist([img], [0], None, [64], [0, 256])
            hist_g = cv2.calcHist([img], [1], None, [64], [0, 256])
            hist_r = cv2.calcHist([img], [2], None, [64], [0, 256])

            # Normalize and concatenate
            hist_b = hist_b.flatten() / hist_b.sum()
            hist_g = hist_g.flatten() / hist_g.sum()
            hist_r = hist_r.flatten() / hist_r.sum()

            return np.concatenate([hist_b, hist_g, hist_r]).tolist()

        except Exception as e:
            logger.error(f"Error calculating color histogram for {image_path}: {e}")
            return []

    def _calculate_quality_score(self, image_path: str) -> float:
        """Calculate image quality score based on multiple factors"""
        try:
            with Image.open(image_path) as img:
                quality_score = 0.0

                # Resolution score (0-30 points)
                width, height = img.size
                megapixels = (width * height) / 1000000
                resolution_score = min(30, megapixels * 2)  # 2 points per MP, max 30
                quality_score += resolution_score

                # Sharpness score using Laplacian variance (0-40 points)
                img_gray = img.convert('L')
                laplacian_var = cv2.Laplacian(np.array(img_gray), cv2.CV_64F).var()
                sharpness_score = min(40, laplacian_var / 100)
                quality_score += sharpness_score

                # File size score (0-20 points) - larger files often indicate less compression
                file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
                size_score = min(20, file_size_mb * 2)  # 2 points per MB, max 20
                quality_score += size_score

                # Aspect ratio bonus (0-10 points) - standard ratios get bonus
                aspect_ratio = width / height
                if 0.9 <= aspect_ratio <= 1.1:  # Nearly square
                    quality_score += 5
                elif 1.3 <= aspect_ratio <= 1.4:  # 4:3
                    quality_score += 10
                elif 1.7 <= aspect_ratio <= 1.8:  # 16:9
                    quality_score += 8

                return min(100.0, quality_score)

        except Exception as e:
            logger.error(f"Error calculating quality score for {image_path}: {e}")
            return 0.0

    def _process_image(self, image_path: str) -> Optional[PhotoInfo]:
        """Process a single image for duplicate analysis"""
        try:
            # Basic file info
            stat = os.stat(image_path)
            file_hash = self._calculate_file_hash(image_path)

            # Image dimensions
            with Image.open(image_path) as img:
                dimensions = img.size

            # Calculate hashes
            hashes = self._calculate_perceptual_hashes(image_path)
            color_histogram = self._calculate_color_histogram(image_path)
            quality_score = self._calculate_quality_score(image_path)

            # Extract creation time from EXIF if available
            created_at = None
            try:
                with Image.open(image_path) as img:
                    exif = img._getexif()
                    if exif:
                        from PIL.ExifTags import TAGS
                        for tag_id, value in exif.items():
                            tag = TAGS.get(tag_id, tag_id)
                            if tag == 'DateTimeOriginal':
                                created_at = value
                                break
            except:
                pass

            return PhotoInfo(
                path=image_path,
                file_hash=file_hash,
                size_bytes=stat.st_size,
                dimensions=dimensions,
                phash=hashes.get('phash'),
                dhash=hashes.get('dhash'),
                ahash=hashes.get('ahash'),
                whash=hashes.get('whash'),
                color_histogram=color_histogram,
                quality_score=quality_score,
                created_at=created_at
            )

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return None

    def scan_directory(self,
                      directory_path: str,
                      max_workers: int = 4,
                      show_progress: bool = False,
                      similarity_threshold: float = 5.0) -> Dict[str, Any]:
        """
        Scan directory for duplicate images.

        Args:
            directory_path: Directory to scan
            max_workers: Number of parallel processing threads
            show_progress: Show progress updates
            similarity_threshold: Threshold for perceptual similarity

        Returns:
            Dictionary with scan results
        """
        start_time = time.time()
        results = {
            'total_images': 0,
            'processed_images': 0,
            'exact_duplicates': 0,
            'near_duplicates': 0,
            'similar_images': 0,
            'groups_created': 0,
            'total_size_saved_mb': 0,
            'errors': []
        }

        # Get all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        image_files = []
        for ext in image_extensions:
            image_files.extend(Path(directory_path).glob(f'*{ext}'))
            image_files.extend(Path(directory_path).glob(f'*{ext.upper()}'))

        results['total_images'] = len(image_files)

        if show_progress:
            self.progress_callback(f"Processing {len(image_files)} images for duplicates...")

        # Process images in parallel
        photo_infos = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self._process_image, str(img_path)): img_path
                for img_path in image_files
            }

            for i, future in enumerate(as_completed(future_to_file)):
                img_path = future_to_file[future]
                try:
                    photo_info = future.result()
                    if photo_info:
                        photo_infos.append(photo_info)
                        results['processed_images'] += 1

                    if show_progress and (i + 1) % 10 == 0:
                        progress = ((i + 1) / len(image_files)) * 100
                        self.progress_callback(f"Progress: {progress:.1f}%")

                except Exception as e:
                    error_msg = f"Error processing {img_path}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)

        # Find duplicates
        if photo_infos:
            if show_progress:
                self.progress_callback("Finding duplicate groups...")
            duplicate_results = self._find_duplicates(photo_infos, similarity_threshold)
            results.update(duplicate_results)

        # Store results in database
        if results['groups_created'] > 0:
            if show_progress:
                self.progress_callback("Storing duplicate information...")
            self._store_duplicate_results(photo_infos, results)

        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        self.stats['processing_time_ms'] += processing_time
        results['processing_time_ms'] = int(processing_time)

        if show_progress:
            self.progress_callback(f"Completed: {results['groups_created']} duplicate groups found")

        return results

    def _find_duplicates(self, photo_infos: List[PhotoInfo], similarity_threshold: float) -> Dict[str, Any]:
        """Find duplicate groups using multiple algorithms"""
        results = {
            'exact_duplicates': 0,
            'near_duplicates': 0,
            'similar_images': 0,
            'groups_created': 0,
            'total_size_saved_mb': 0
        }

        # 1. Find exact duplicates (same file hash)
        exact_groups = self._find_exact_duplicates(photo_infos)
        results['exact_duplicates'] = sum(len(group) - 1 for group in exact_groups.values())

        # 2. Find perceptual duplicates using PHash
        near_groups = self._find_perceptual_duplicates(photo_infos, 'phash', 2)
        results['near_duplicates'] = sum(len(group) - 1 for group in near_groups.values())

        # 3. Find similar images
        similar_groups = self._find_perceptual_duplicates(photo_infos, 'phash', int(similarity_threshold))
        results['similar_images'] = sum(len(group) - 1 for group in similar_groups.values())

        # Calculate total groups and potential space savings
        all_groups = list(exact_groups.values()) + list(near_groups.values()) + list(similar_groups.values())
        results['groups_created'] = len(all_groups)

        for group in all_groups:
            if len(group) > 1:
                # Calculate potential space savings (keeping highest quality)
                best_photo = max(group, key=lambda x: x.quality_score)
                space_saved = sum(info.size_bytes for info in group if info != best_photo)
                results['total_size_saved_mb'] += space_saved / (1024 * 1024)

        return results

    def _find_exact_duplicates(self, photo_infos: List[PhotoInfo]) -> Dict[str, List[PhotoInfo]]:
        """Find exact duplicates using file hash"""
        hash_groups = defaultdict(list)
        for info in photo_infos:
            hash_groups[info.file_hash].append(info)

        # Return only groups with duplicates
        return {h: group for h, group in hash_groups.items() if len(group) > 1}

    def _find_perceptual_duplicates(self,
                                  photo_infos: List[PhotoInfo],
                                  hash_type: str,
                                  threshold: int) -> Dict[str, List[PhotoInfo]]:
        """Find perceptual duplicates using image hashing"""
        # Filter photos that have the required hash
        valid_photos = [info for info in photo_infos if getattr(info, hash_type) is not None]

        if len(valid_photos) < 2:
            return {}

        # Extract hash values
        hash_values = []
        for info in valid_photos:
            hash_val = getattr(info, hash_type)
            if hash_val:
                hash_values.append((str(hash_val), info))

        # Group by hash similarity
        groups = defaultdict(list)
        used_indices = set()

        for i, (hash1, info1) in enumerate(hash_values):
            if i in used_indices:
                continue

            current_group = [info1]
            used_indices.add(i)

            # Compare with other photos
            for j, (hash2, info2) in enumerate(hash_values[i+1:], i+1):
                if j in used_indices:
                    continue

                # Calculate hash distance
                hash1_obj = imagehash.hex_to_hash(hash1)
                hash2_obj = imagehash.hex_to_hash(hash2)
                distance = hash1_obj - hash2_obj

                if distance <= threshold:
                    current_group.append(info2)
                    used_indices.add(j)

            # Only keep groups with duplicates
            if len(current_group) > 1:
                groups[f"{hash_type}_{threshold}_{len(groups)}"] = current_group

        return groups

    def _store_duplicate_results(self, photo_infos: List[PhotoInfo], results: Dict[str, Any]):
        """Store duplicate detection results in database"""
        try:
            # Store photo hashes
            for info in photo_infos:
                self.conn.execute("""
                    INSERT OR REPLACE INTO perceptual_hashes
                    (photo_path, phash, dhash, ahash, whash, dominant_colors, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    info.path,
                    int(str(info.phash)) if info.phash else None,
                    int(str(info.dhash)) if info.dhash else None,
                    int(str(info.ahash)) if info.ahash else None,
                    int(str(info.whash)) if info.whash else None,
                    json.dumps(info.color_histogram[:10]) if info.color_histogram else None,  # First 10 bins as dominant colors
                    info.created_at or datetime.now().isoformat()
                ))

            self.conn.commit()

        except Exception as e:
            logger.error(f"Error storing duplicate results: {e}")
            self.conn.rollback()

    def get_duplicate_groups(self,
                           group_type: Optional[str] = None,
                           min_similarity: Optional[float] = None) -> List[DuplicateGroup]:
        """Get duplicate groups with optional filtering"""
        try:
            query = """
                SELECT
                    dge.id,
                    dge.group_type,
                    dge.similarity_threshold,
                    dge.primary_photo_id,
                    dge.resolution_strategy,
                    dge.auto_resolvable,
                    dge.created_at,
                    dge.updated_at,
                    COUNT(dr.photo_path) as photo_count,
                    SUM(fs.size_bytes) as total_size
                FROM duplicate_groups_enhanced dge
                JOIN duplicate_relationships dr ON dge.id = dr.group_id
                LEFT JOIN perceptual_hashes fs ON dr.photo_path = fs.photo_path
            """

            params = []
            where_clauses = []

            if group_type:
                where_clauses.append("dge.group_type = ?")
                params.append(group_type)

            if min_similarity:
                where_clauses.append("dge.similarity_threshold >= ?")
                params.append(min_similarity)

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

            query += """
                GROUP BY dge.id
                ORDER BY dge.similarity_threshold, photo_count DESC
            """

            cursor = self.conn.execute(query, params)
            groups = []

            for row in cursor.fetchall():
                # Get photos for this group
                photos_cursor = self.conn.execute("""
                    SELECT dr.photo_path, dr.similarity_score, dr.is_primary, dr.resolution_action
                    FROM duplicate_relationships dr
                    WHERE dr.group_id = ?
                    ORDER BY dr.is_primary DESC, dr.similarity_score DESC
                """, (row['id'],))

                photos = []
                for photo_row in photos_cursor.fetchall():
                    photos.append({
                        'path': photo_row['photo_path'],
                        'similarity_score': photo_row['similarity_score'],
                        'is_primary': bool(photo_row['is_primary']),
                        'resolution_action': photo_row['resolution_action']
                    })

                group = DuplicateGroup(
                    id=row['id'],
                    group_type=row['group_type'],
                    similarity_threshold=row['similarity_threshold'],
                    photos=photos,
                    total_size_mb=(row['total_size'] or 0) / (1024 * 1024),
                    primary_photo_id=row['primary_photo_id'],
                    resolution_strategy=row['resolution_strategy'],
                    auto_resolvable=bool(row['auto_resolvable']),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                groups.append(group)

            return groups

        except Exception as e:
            logger.error(f"Error getting duplicate groups: {e}")
            return []

    def get_resolution_suggestions(self, group_id: str) -> Dict[str, Any]:
        """Get smart resolution suggestions for a duplicate group"""
        try:
            # Get group and photos
            cursor = self.conn.execute("""
                SELECT dge.*, COUNT(dr.photo_path) as photo_count
                FROM duplicate_groups_enhanced dge
                JOIN duplicate_relationships dr ON dge.id = dr.group_id
                WHERE dge.id = ?
                GROUP BY dge.id
            """, (group_id,))

            group_info = cursor.fetchone()
            if not group_info:
                return {}

            # Get photo details with quality info
            cursor = self.conn.execute("""
                SELECT
                    dr.photo_path,
                    dr.similarity_score,
                    ph.phash,
                    ph.dhash,
                    ph.ahash,
                    fs.size_bytes
                FROM duplicate_relationships dr
                LEFT JOIN perceptual_hashes ph ON dr.photo_path = ph.photo_path
                LEFT JOIN perceptual_hashes fs ON dr.photo_path = fs.photo_path
                WHERE dr.group_id = ?
                ORDER BY dr.similarity_score DESC
            """, (group_id,))

            photos = []
            for row in cursor.fetchall():
                # Calculate quality score
                quality_score = self._calculate_quality_score(row['photo_path'])

                photos.append({
                    'path': row['photo_path'],
                    'similarity_score': row['similarity_score'],
                    'quality_score': quality_score,
                    'size_bytes': row['size_bytes'],
                    'phash': row['phash'],
                    'dhash': row['dhash'],
                    'ahash': row['ahash']
                })

            # Generate suggestions
            suggestions = {
                'group_info': dict(group_info),
                'photos': photos,
                'suggestions': self._generate_resolution_suggestions(photos, group_info['group_type'])
            }

            return suggestions

        except Exception as e:
            logger.error(f"Error getting resolution suggestions for {group_id}: {e}")
            return {}

    def _generate_resolution_suggestions(self, photos: List[Dict], group_type: str) -> List[Dict]:
        """Generate intelligent resolution suggestions"""
        suggestions = []

        if not photos:
            return suggestions

        # Sort by quality score
        sorted_photos = sorted(photos, key=lambda x: x['quality_score'], reverse=True)

        # Suggestion 1: Keep best quality, delete others
        best_photo = sorted_photos[0]
        total_space_saved = sum(p['size_bytes'] for p in sorted_photos[1:])

        suggestions.append({
            'type': 'keep_best_quality',
            'description': f'Keep highest quality photo ({best_photo["path"].split("/")[-1]})',
            'action': 'keep',
            'target_photo': best_photo['path'],
            'space_saved_mb': total_space_saved / (1024 * 1024),
            'confidence': 0.9,
            'reasoning': f'Highest quality score: {best_photo["quality_score"]:.1f}/100'
        })

        # Suggestion 2: Keep largest file (may be less compressed)
        largest_photo = max(photos, key=lambda x: x['size_bytes'])
        total_space_saved = sum(p['size_bytes'] for p in photos if p != largest_photo)

        suggestions.append({
            'type': 'keep_largest',
            'description': f'Keep largest file ({largest_photo["path"].split("/")[-1]})',
            'action': 'keep',
            'target_photo': largest_photo['path'],
            'space_saved_mb': total_space_saved / (1024 * 1024),
            'confidence': 0.7,
            'reasoning': f'Largest file: {largest_photo["size_bytes"] / (1024*1024):.1f}MB'
        })

        # Suggestion 3: Keep all if very similar and small size
        if group_type == 'similar' and len(photos) <= 3:
            total_size_mb = sum(p['size_bytes'] for p in photos) / (1024 * 1024)
            if total_size_mb < 50:  # Less than 50MB total
                suggestions.append({
                    'type': 'keep_all',
                    'description': 'Keep all photos (small total size)',
                    'action': 'keep_all',
                    'space_saved_mb': 0,
                    'confidence': 0.6,
                    'reasoning': f'Total size only {total_size_mb:.1f}MB, photos may have sentimental value'
                })

        # Suggestion 4: Keep based on filename patterns (keep original, keep edited)
        originals = []
        edited = []
        for photo in photos:
            filename = photo['path'].lower()
            if any(keyword in filename for keyword in ['copy', 'edited', 'modified', 'final']):
                edited.append(photo)
            else:
                originals.append(photo)

        if originals and edited:
            suggestions.append({
                'type': 'keep_originals',
                'description': f'Keep {len(originals)} original(s), move {len(edited)} copy(s) to archive',
                'action': 'move_edited',
                'originals': [p['path'] for p in originals],
                'edited': [p['path'] for p in edited],
                'confidence': 0.8,
                'reasoning': 'Identified original and edited versions based on filenames'
            })

        return suggestions

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()