"""
Video Content Analysis & Search

Comprehensive video analysis system that provides:
- Keyframe extraction for visual analysis
- Scene detection and segmentation
- Video OCR for text overlay detection
- Frame-based semantic search
- Video thumbnail generation
- Motion analysis and object tracking

This extends the existing photo search capabilities to video content,
enabling users to search within video files using natural language.
"""

import os
import sys
import json
import sqlite3
import hashlib
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timezone
import logging

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("OpenCV not available - video analysis will be limited")

try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False
    print("ffmpeg-python not available - video processing will be limited")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL not available - image processing will be limited")

# Import existing modules for integration
try:
    from src.ocr_search import OCRSearch
    from src.metadata_extractor import extract_all_metadata
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("OCR modules not available - text detection will be disabled")


class VideoAnalyzer:
    """
    Main video analysis class that orchestrates all video processing tasks.
    """
    
    def __init__(self, db_path: str = "video_analysis.db", cache_dir: str = "cache/video"):
        """
        Initialize the video analyzer.
        
        Args:
            db_path: Path to SQLite database for storing analysis results
            cache_dir: Directory for caching extracted frames and thumbnails
        """
        self.db_path = db_path
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Initialize OCR if available
        self.ocr_search = OCRSearch() if OCR_AVAILABLE else None
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
        
        # Video processing settings
        self.keyframe_interval = 30  # Extract keyframe every 30 seconds
        self.scene_threshold = 0.3   # Scene change detection threshold
        self.max_frames_per_video = 100  # Limit frames to prevent excessive processing
        
    def _init_database(self):
        """Initialize the video analysis database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Video metadata table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS video_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_path TEXT UNIQUE NOT NULL,
                duration_seconds REAL,
                fps REAL,
                width INTEGER,
                height INTEGER,
                codec TEXT,
                bitrate INTEGER,
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Keyframes table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS video_keyframes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_path TEXT NOT NULL,
                frame_number INTEGER,
                timestamp_seconds REAL,
                frame_path TEXT,
                scene_id INTEGER,
                is_scene_boundary BOOLEAN DEFAULT FALSE,
                visual_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_path) REFERENCES video_metadata (video_path)
            )
        """)
        
        # Video OCR results table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS video_ocr (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_path TEXT NOT NULL,
                frame_number INTEGER,
                timestamp_seconds REAL,
                detected_text TEXT,
                confidence REAL,
                bounding_box TEXT,  -- JSON: [x, y, width, height]
                language TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_path) REFERENCES video_metadata (video_path)
            )
        """)
        
        # Scene detection table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS video_scenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_path TEXT NOT NULL,
                scene_number INTEGER,
                start_timestamp REAL,
                end_timestamp REAL,
                duration_seconds REAL,
                keyframe_count INTEGER,
                scene_description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_path) REFERENCES video_metadata (video_path)
            )
        """)
        
        # Create indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_video_keyframes_path ON video_keyframes (video_path)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_video_keyframes_timestamp ON video_keyframes (timestamp_seconds)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_video_ocr_path ON video_ocr (video_path)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_video_ocr_text ON video_ocr (detected_text)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_video_scenes_path ON video_scenes (video_path)")
        
        conn.commit()
        conn.close()
        
    def analyze_video(self, video_path: str, force_reprocess: bool = False) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a video file.
        
        Args:
            video_path: Path to the video file
            force_reprocess: If True, reprocess even if already analyzed
            
        Returns:
            Dictionary containing analysis results
        """
        video_path = str(Path(video_path).resolve())
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        # Check if already processed
        if not force_reprocess and self._is_video_processed(video_path):
            self.logger.info(f"Video already processed: {video_path}")
            return self.get_video_analysis(video_path)
            
        self.logger.info(f"Starting video analysis: {video_path}")
        
        try:
            # Step 1: Extract basic video metadata
            metadata = self._extract_video_metadata(video_path)
            
            # Step 2: Extract keyframes
            keyframes = self._extract_keyframes(video_path, metadata)
            
            # Step 3: Detect scenes
            scenes = self._detect_scenes(video_path, keyframes)
            
            # Step 4: Perform OCR on keyframes
            ocr_results = self._perform_video_ocr(video_path, keyframes)
            
            # Step 5: Store results in database
            self._store_analysis_results(video_path, metadata, keyframes, scenes, ocr_results)
            
            analysis_result = {
                "video_path": video_path,
                "metadata": metadata,
                "keyframes_count": len(keyframes),
                "scenes_count": len(scenes),
                "ocr_detections": len(ocr_results),
                "status": "completed",
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            
            self.logger.info(f"Video analysis completed: {video_path}")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Video analysis failed for {video_path}: {str(e)}")
            return {
                "video_path": video_path,
                "status": "failed",
                "error": str(e),
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
    
    def _extract_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """Extract basic video metadata using ffprobe."""
        if not FFMPEG_AVAILABLE:
            raise RuntimeError("ffmpeg-python not available for video metadata extraction")
            
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            
            if not video_stream:
                raise ValueError("No video stream found in file")
                
            metadata = {
                "duration": float(probe['format'].get('duration', 0)),
                "fps": eval(video_stream.get('r_frame_rate', '0/1')),  # Convert fraction to float
                "width": int(video_stream.get('width', 0)),
                "height": int(video_stream.get('height', 0)),
                "codec": video_stream.get('codec_name', 'unknown'),
                "bitrate": int(probe['format'].get('bit_rate', 0)),
                "file_size": int(probe['format'].get('size', 0))
            }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to extract video metadata: {str(e)}")
            raise
    
    def _extract_keyframes(self, video_path: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract keyframes from video at regular intervals."""
        if not CV2_AVAILABLE:
            self.logger.warning("OpenCV not available - using ffmpeg for frame extraction")
            return self._extract_keyframes_ffmpeg(video_path, metadata)
            
        keyframes = []
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video file: {video_path}")
            
        try:
            fps = metadata.get('fps', 30)
            duration = metadata.get('duration', 0)
            frame_interval = int(fps * self.keyframe_interval)  # Frames between keyframes
            
            frame_number = 0
            extracted_count = 0
            
            while cap.isOpened() and extracted_count < self.max_frames_per_video:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Extract keyframe at intervals
                if frame_number % frame_interval == 0:
                    timestamp = frame_number / fps
                    
                    # Save frame to cache
                    frame_filename = f"{Path(video_path).stem}_frame_{frame_number:06d}.jpg"
                    frame_path = self.cache_dir / frame_filename
                    
                    cv2.imwrite(str(frame_path), frame)
                    
                    # Calculate visual hash for similarity detection
                    visual_hash = self._calculate_frame_hash(frame)
                    
                    keyframes.append({
                        "frame_number": frame_number,
                        "timestamp": timestamp,
                        "frame_path": str(frame_path),
                        "visual_hash": visual_hash
                    })
                    
                    extracted_count += 1
                    
                frame_number += 1
                
        finally:
            cap.release()
            
        self.logger.info(f"Extracted {len(keyframes)} keyframes from {video_path}")
        return keyframes
    
    def _extract_keyframes_ffmpeg(self, video_path: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fallback keyframe extraction using ffmpeg."""
        keyframes: List[Dict[str, Any]] = []
        duration = metadata.get('duration', 0)
        
        if duration == 0:
            return keyframes
            
        # Calculate timestamps for keyframe extraction
        timestamps: List[float] = []
        current_time = 0
        while current_time < duration and len(timestamps) < self.max_frames_per_video:
            timestamps.append(current_time)
            current_time += self.keyframe_interval
            
        # Extract frames at specified timestamps
        for i, timestamp in enumerate(timestamps):
            try:
                frame_filename = f"{Path(video_path).stem}_frame_{i:06d}.jpg"
                frame_path = self.cache_dir / frame_filename
                
                # Use ffmpeg to extract frame at specific timestamp
                (
                    ffmpeg
                    .input(video_path, ss=timestamp)
                    .output(str(frame_path), vframes=1, format='image2', vcodec='mjpeg')
                    .overwrite_output()
                    .run(quiet=True)
                )
                
                if frame_path.exists():
                    keyframes.append({
                        "frame_number": i * int(metadata.get('fps', 30) * self.keyframe_interval),
                        "timestamp": timestamp,
                        "frame_path": str(frame_path),
                        "visual_hash": self._calculate_image_hash(str(frame_path))
                    })
                    
            except Exception as e:
                self.logger.warning(f"Failed to extract frame at {timestamp}s: {str(e)}")
                continue
                
        return keyframes
    
    def _calculate_frame_hash(self, frame: np.ndarray) -> str:
        """Calculate perceptual hash of a video frame."""
        if not CV2_AVAILABLE:
            return ""
            
        # Resize to small size for hashing
        small_frame = cv2.resize(frame, (8, 8))
        gray_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate average pixel value
        avg = gray_frame.mean()
        
        # Create binary hash
        hash_bits = []
        for pixel in gray_frame.flatten():
            hash_bits.append('1' if pixel > avg else '0')
            
        return ''.join(hash_bits)
    
    def _calculate_image_hash(self, image_path: str) -> str:
        """Calculate perceptual hash of an image file."""
        if not PIL_AVAILABLE:
            return ""
            
        try:
            with Image.open(image_path) as img:
                # Convert to grayscale and resize
                img = img.convert('L').resize((8, 8))
                pixels = list(img.getdata())
                
                # Calculate average
                avg = sum(pixels) / len(pixels)
                
                # Create binary hash
                hash_bits = ['1' if pixel > avg else '0' for pixel in pixels]
                return ''.join(hash_bits)
                
        except Exception:
            return ""
    
    def _detect_scenes(self, video_path: str, keyframes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect scene boundaries using frame similarity analysis."""
        if len(keyframes) < 2:
            return []
            
        scenes = []
        current_scene_start = 0
        scene_number = 0
        
        # Compare consecutive frames for scene changes
        for i in range(1, len(keyframes)):
            prev_hash = keyframes[i-1]['visual_hash']
            curr_hash = keyframes[i]['visual_hash']
            
            # Calculate Hamming distance between hashes
            if prev_hash and curr_hash:
                similarity = self._calculate_hash_similarity(prev_hash, curr_hash)
                
                # If similarity is below threshold, it's a scene boundary
                if similarity < self.scene_threshold:
                    # End current scene
                    scene_end_time = keyframes[i-1]['timestamp']
                    scene_start_time = keyframes[current_scene_start]['timestamp']
                    
                    scenes.append({
                        "scene_number": scene_number,
                        "start_timestamp": scene_start_time,
                        "end_timestamp": scene_end_time,
                        "duration": scene_end_time - scene_start_time,
                        "keyframe_count": i - current_scene_start
                    })
                    
                    # Mark frame as scene boundary
                    keyframes[i]['is_scene_boundary'] = True
                    keyframes[i]['scene_id'] = scene_number + 1
                    
                    # Start new scene
                    current_scene_start = i
                    scene_number += 1
                else:
                    keyframes[i]['scene_id'] = scene_number
            else:
                keyframes[i]['scene_id'] = scene_number
        
        # Add final scene
        if current_scene_start < len(keyframes) - 1:
            scene_start_time = keyframes[current_scene_start]['timestamp']
            scene_end_time = keyframes[-1]['timestamp']
            
            scenes.append({
                "scene_number": scene_number,
                "start_timestamp": scene_start_time,
                "end_timestamp": scene_end_time,
                "duration": scene_end_time - scene_start_time,
                "keyframe_count": len(keyframes) - current_scene_start
            })
        
        self.logger.info(f"Detected {len(scenes)} scenes in {video_path}")
        return scenes
    
    def _calculate_hash_similarity(self, hash1: str, hash2: str) -> float:
        """Calculate similarity between two perceptual hashes."""
        if len(hash1) != len(hash2):
            return 0.0
            
        # Calculate Hamming distance
        different_bits = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
        
        # Convert to similarity (0 = completely different, 1 = identical)
        similarity = 1.0 - (different_bits / len(hash1))
        return similarity
    
    def _perform_video_ocr(self, video_path: str, keyframes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform OCR on extracted keyframes to detect text overlays."""
        if not self.ocr_search:
            self.logger.warning("OCR not available - skipping text detection")
            return []
            
        ocr_results = []
        
        for keyframe in keyframes:
            frame_path = keyframe['frame_path']
            
            if not os.path.exists(frame_path):
                continue
                
            try:
                # Use existing OCR system to extract text
                text_results = self.ocr_search.extract_text_from_images([frame_path])
                
                if frame_path in text_results and text_results[frame_path]['text']:
                    ocr_results.append({
                        "frame_number": keyframe['frame_number'],
                        "timestamp": keyframe['timestamp'],
                        "detected_text": text_results[frame_path]['text'],
                        "confidence": text_results[frame_path].get('confidence', 0.0),
                        "language": text_results[frame_path].get('language', 'unknown')
                    })
                    
            except Exception as e:
                self.logger.warning(f"OCR failed for frame {frame_path}: {str(e)}")
                continue
                
        self.logger.info(f"Performed OCR on {len(keyframes)} frames, found text in {len(ocr_results)} frames")
        return ocr_results
    
    def _store_analysis_results(self, video_path: str, metadata: Dict[str, Any], 
                              keyframes: List[Dict[str, Any]], scenes: List[Dict[str, Any]], 
                              ocr_results: List[Dict[str, Any]]):
        """Store all analysis results in the database."""
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Store video metadata
            conn.execute("""
                INSERT OR REPLACE INTO video_metadata 
                (video_path, duration_seconds, fps, width, height, codec, bitrate, file_size, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                video_path,
                metadata.get('duration', 0),
                metadata.get('fps', 0),
                metadata.get('width', 0),
                metadata.get('height', 0),
                metadata.get('codec', ''),
                metadata.get('bitrate', 0),
                metadata.get('file_size', 0)
            ))
            
            # Clear existing keyframes for this video
            conn.execute("DELETE FROM video_keyframes WHERE video_path = ?", (video_path,))
            
            # Store keyframes
            for keyframe in keyframes:
                conn.execute("""
                    INSERT INTO video_keyframes 
                    (video_path, frame_number, timestamp_seconds, frame_path, scene_id, is_scene_boundary, visual_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    video_path,
                    keyframe['frame_number'],
                    keyframe['timestamp'],
                    keyframe['frame_path'],
                    keyframe.get('scene_id', 0),
                    keyframe.get('is_scene_boundary', False),
                    keyframe.get('visual_hash', '')
                ))
            
            # Clear existing scenes for this video
            conn.execute("DELETE FROM video_scenes WHERE video_path = ?", (video_path,))
            
            # Store scenes
            for scene in scenes:
                conn.execute("""
                    INSERT INTO video_scenes 
                    (video_path, scene_number, start_timestamp, end_timestamp, duration_seconds, keyframe_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    video_path,
                    scene['scene_number'],
                    scene['start_timestamp'],
                    scene['end_timestamp'],
                    scene['duration'],
                    scene['keyframe_count']
                ))
            
            # Clear existing OCR results for this video
            conn.execute("DELETE FROM video_ocr WHERE video_path = ?", (video_path,))
            
            # Store OCR results
            for ocr_result in ocr_results:
                conn.execute("""
                    INSERT INTO video_ocr 
                    (video_path, frame_number, timestamp_seconds, detected_text, confidence, language)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    video_path,
                    ocr_result['frame_number'],
                    ocr_result['timestamp'],
                    ocr_result['detected_text'],
                    ocr_result['confidence'],
                    ocr_result['language']
                ))
            
            conn.commit()
            
        finally:
            conn.close()
    
    def _is_video_processed(self, video_path: str) -> bool:
        """Check if video has already been processed."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM video_metadata WHERE video_path = ?",
                (video_path,)
            )
            result = cursor.fetchone()
            return result['count'] > 0
            
        finally:
            conn.close()
    
    def get_video_analysis(self, video_path: str) -> Dict[str, Any]:
        """Retrieve complete analysis results for a video."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Get metadata
            cursor = conn.execute(
                "SELECT * FROM video_metadata WHERE video_path = ?",
                (video_path,)
            )
            metadata = cursor.fetchone()
            
            if not metadata:
                return {"error": "Video not found in database"}
            
            # Get keyframes
            cursor = conn.execute(
                "SELECT * FROM video_keyframes WHERE video_path = ? ORDER BY timestamp_seconds",
                (video_path,)
            )
            keyframes = [dict(row) for row in cursor.fetchall()]
            
            # Get scenes
            cursor = conn.execute(
                "SELECT * FROM video_scenes WHERE video_path = ? ORDER BY scene_number",
                (video_path,)
            )
            scenes = [dict(row) for row in cursor.fetchall()]
            
            # Get OCR results
            cursor = conn.execute(
                "SELECT * FROM video_ocr WHERE video_path = ? ORDER BY timestamp_seconds",
                (video_path,)
            )
            ocr_results = [dict(row) for row in cursor.fetchall()]
            
            return {
                "video_path": video_path,
                "metadata": dict(metadata),
                "keyframes": keyframes,
                "scenes": scenes,
                "ocr_results": ocr_results,
                "summary": {
                    "keyframes_count": len(keyframes),
                    "scenes_count": len(scenes),
                    "text_detections": len(ocr_results),
                    "duration": metadata['duration_seconds']
                }
            }
            
        finally:
            conn.close()
    
    def search_video_content(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search video content using text query.
        
        Searches through:
        - OCR detected text in video frames
        - Video file names and paths
        - Scene descriptions (if available)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Search OCR text
            cursor = conn.execute("""
                SELECT DISTINCT 
                    vo.video_path,
                    vo.timestamp_seconds,
                    vo.detected_text,
                    vo.confidence,
                    vm.duration_seconds,
                    vm.width,
                    vm.height
                FROM video_ocr vo
                JOIN video_metadata vm ON vo.video_path = vm.video_path
                WHERE vo.detected_text LIKE ?
                ORDER BY vo.confidence DESC, vo.timestamp_seconds ASC
                LIMIT ?
            """, (f"%{query}%", limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "video_path": row['video_path'],
                    "timestamp": row['timestamp_seconds'],
                    "matched_text": row['detected_text'],
                    "confidence": row['confidence'],
                    "duration": row['duration_seconds'],
                    "resolution": f"{row['width']}x{row['height']}",
                    "match_type": "ocr_text"
                })
            
            return results
            
        finally:
            conn.close()
    
    def get_video_statistics(self) -> Dict[str, Any]:
        """Get statistics about processed videos."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Total videos processed
            cursor = conn.execute("SELECT COUNT(*) as count FROM video_metadata")
            total_videos = cursor.fetchone()['count']
            
            # Total keyframes extracted
            cursor = conn.execute("SELECT COUNT(*) as count FROM video_keyframes")
            total_keyframes = cursor.fetchone()['count']
            
            # Total scenes detected
            cursor = conn.execute("SELECT COUNT(*) as count FROM video_scenes")
            total_scenes = cursor.fetchone()['count']
            
            # Total OCR detections
            cursor = conn.execute("SELECT COUNT(*) as count FROM video_ocr")
            total_ocr = cursor.fetchone()['count']
            
            # Total duration processed
            cursor = conn.execute("SELECT SUM(duration_seconds) as total FROM video_metadata")
            total_duration = cursor.fetchone()['total'] or 0
            
            return {
                "total_videos": total_videos,
                "total_keyframes": total_keyframes,
                "total_scenes": total_scenes,
                "total_ocr_detections": total_ocr,
                "total_duration_hours": round(total_duration / 3600, 2),
                "average_keyframes_per_video": round(total_keyframes / max(total_videos, 1), 1),
                "average_scenes_per_video": round(total_scenes / max(total_videos, 1), 1)
            }
            
        finally:
            conn.close()


def main():
    """Command-line interface for video analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Video Content Analysis Tool")
    parser.add_argument("video_path", help="Path to video file to analyze")
    parser.add_argument("--force", action="store_true", help="Force reprocessing even if already analyzed")
    parser.add_argument("--search", help="Search for text in processed videos")
    parser.add_argument("--stats", action="store_true", help="Show video analysis statistics")
    parser.add_argument("--db", default="video_analysis.db", help="Database path")
    parser.add_argument("--cache", default="cache/video", help="Cache directory")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    analyzer = VideoAnalyzer(db_path=args.db, cache_dir=args.cache)
    
    if args.stats:
        stats = analyzer.get_video_statistics()
        print("\n=== Video Analysis Statistics ===")
        for key, value in stats.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
        return
    
    if args.search:
        results = analyzer.search_video_content(args.search)
        print(f"\n=== Search Results for '{args.search}' ===")
        for result in results:
            print(f"Video: {result['video_path']}")
            print(f"  Time: {result['timestamp']:.1f}s")
            print(f"  Text: {result['matched_text']}")
            print(f"  Confidence: {result['confidence']:.2f}")
            print()
        return
    
    if not os.path.exists(args.video_path):
        print(f"Error: Video file not found: {args.video_path}")
        return
    
    # Analyze video
    print(f"Analyzing video: {args.video_path}")
    result = analyzer.analyze_video(args.video_path, force_reprocess=args.force)
    
    if result['status'] == 'completed':
        print(f"✅ Analysis completed successfully!")
        print(f"   Keyframes extracted: {result['keyframes_count']}")
        print(f"   Scenes detected: {result['scenes_count']}")
        print(f"   Text detections: {result['ocr_detections']}")
    else:
        print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
