"""
Enhanced OCR Search System with Text Highlighting

This module provides comprehensive OCR functionality with:
1. Multi-language text extraction and recognition
2. Text region detection with bounding boxes
3. Confidence scoring and quality assessment
4. Handwriting recognition support
5. Text highlighting in search results
6. Progressive language model loading
7. Integration with image search

Features:
- Tesseract OCR with multiple languages
- Handwriting text recognition
- Text region detection and highlighting
- Language auto-detection
- Confidence-based filtering
- Progressive model loading
- Search result highlighting
- Batch processing with progress tracking

Usage:
    ocr_search = EnhancedOCRSearch()

    # Extract text from images
    results = ocr_search.extract_text_batch('/photos', show_progress=True)

    # Search for images containing text
    matches = ocr_search.search_text('hello world', language='en')

    # Get text regions for highlighting
    regions = ocr_search.get_text_regions('image1.jpg')
"""

import os
import json
import sqlite3
import numpy as np
import threading
import logging
from typing import List, Dict, Optional, Any, Tuple, Callable
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import cv2
from PIL import Image
import requests

# Configure logging
logger = logging.getLogger(__name__)

# Optional OCR dependency (handled gracefully if missing)
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    pytesseract = None  # type: ignore
    logger.warning("pytesseract not available. Install with: pip install pytesseract and ensure Tesseract OCR is installed on the system")
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Handwriting recognition libraries (optional)
try:
    import easyocr
    HANDWRITING_AVAILABLE = True
except ImportError:
    HANDWRITING_AVAILABLE = False
    logger.warning("EasyOCR not available. Install with: pip install easyocr")

# Language support configuration
SUPPORTED_LANGUAGES = {
    'en': {'name': 'English', 'code': 'eng', 'tesseract': 'eng'},
    'es': {'name': 'Spanish', 'code': 'spa', 'tesseract': 'spa'},
    'fr': {'name': 'French', 'code': 'fra', 'tesseract': 'fra'},
    'de': {'name': 'German', 'code': 'deu', 'tesseract': 'deu'},
    'it': {'name': 'Italian', 'code': 'ita', 'tesseract': 'ita'},
    'pt': {'name': 'Portuguese', 'code': 'por', 'tesseract': 'por'},
    'ru': {'name': 'Russian', 'code': 'rus', 'tesseract': 'rus'},
    'ja': {'name': 'Japanese', 'code': 'jpn', 'tesseract': 'jpn'},
    'zh': {'name': 'Chinese', 'code': 'chi_sim', 'tesseract': 'chi_sim'},
    'ko': {'name': 'Korean', 'code': 'kor', 'tesseract': 'kor'},
    'ar': {'name': 'Arabic', 'code': 'ara', 'tesseract': 'ara'},
    'hi': {'name': 'Hindi', 'code': 'hin', 'tesseract': 'hin'}
}

@dataclass
class TextRegion:
    """Text region with bounding box and metadata"""
    id: str
    photo_path: str
    text_content: str
    confidence_score: float
    language_code: str
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    text_type: str  # printed, handwritten, mixed
    font_detected: Optional[str]
    reading_order: int
    created_at: str

@dataclass
class OCRResult:
    """Complete OCR extraction result"""
    photo_path: str
    text_regions: List[TextRegion]
    full_text: str
    languages_detected: List[str]
    processing_time_ms: int
    confidence_average: float
    created_at: str

class EnhancedOCRSearch:
    """Enhanced OCR search with multi-language and highlighting support"""

    def __init__(self,
                 db_path: str = "ocr_search.db",
                 models_dir: str = "ocr_models",
                 progress_callback: Optional[Callable] = None,
                 enable_handwriting: bool = True):
        """
        Initialize enhanced OCR search.

        Args:
            db_path: Path to SQLite database
            models_dir: Directory for OCR model files
            progress_callback: Callback for progress updates
            enable_handwriting: Enable handwriting recognition
        """
        self.db_path = db_path
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.progress_callback = progress_callback
        self.enable_handwriting = enable_handwriting and HANDWRITING_AVAILABLE

        # Threading and caching
        self.cache_lock = threading.Lock()
        self.ocr_cache = {}
        self.language_models = {}

        # OCR engines
        self.tesseract_available = False
        self.easyocr_reader = None

        # Performance tracking
        self.stats = {
            'images_processed': 0,
            'text_regions_extracted': 0,
            'total_characters': 0,
            'processing_time_ms': 0
        }

        # Initialize components
        self._initialize_database()
        self._initialize_ocr_engines()
        self._download_missing_models()

    def _initialize_database(self):
        """Initialize database with OCR schema"""
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
        self.conn.execute("PRAGMA cache_size=10000")

    def _initialize_ocr_engines(self):
        """Initialize OCR engines"""
        # Check Tesseract availability
        if PYTESSERACT_AVAILABLE:
            try:
                pytesseract.get_tesseract_version()
                self.tesseract_available = True
                logger.info("Tesseract OCR initialized")
            except Exception as e:
                logger.warning(f"Tesseract not available: {e}")
        else:
            logger.warning("Tesseract not available: pytesseract not installed")

        # Initialize EasyOCR for handwriting
        if self.enable_handwriting:
            try:
                self.easyocr_reader = easyocr.Reader(['en'])  # Start with English
                logger.info("EasyOCR initialized for handwriting recognition")
            except Exception as e:
                logger.warning(f"EasyOCR initialization failed: {e}")
                self.enable_handwriting = False

    def _download_missing_models(self):
        """Download missing OCR language models"""
        if not self.tesseract_available:
            return

        # Check available Tesseract languages
        try:
            available_langs = pytesseract.get_languages(config='')
            missing_langs = set(SUPPORTED_LANGUAGES.keys()) - set(available_langs)

            if missing_langs and self.progress_callback:
                self.progress_callback(f"Note: {len(missing_langs)} OCR languages not available")

            # Note: In a real implementation, you would download missing language data
            # For now, we'll just log what's missing
            if missing_langs:
                logger.info(f"Missing OCR languages: {', '.join(missing_langs)}")
                logger.info("Install with: apt-get install tesseract-ocr-<lang> (Linux) or brew install tesseract-lang (Mac)")

        except Exception as e:
            logger.warning(f"Could not check Tesseract languages: {e}")

    def _detect_language(self, text: str) -> List[str]:
        """Detect language(s) in text using character analysis"""
        if not text or len(text.strip()) < 10:
            return ['unknown']

        # Simple character-based language detection
        # In production, use libraries like langdetect or polyglot

        language_scores = {}

        for lang_code, lang_info in SUPPORTED_LANGUAGES.items():
            score = 0
            text_lower = text.lower()

            # Character set detection
            if lang_code in ['ru', 'ja', 'zh', 'ko', 'ar', 'hi']:
                if lang_code == 'ru' and any(ord(c) in range(1024, 1279) for c in text):
                    score += 10
                elif lang_code == 'ja' and any(ord(c) in range(0x3040, 0x309F) for c in text):
                    score += 10
                elif lang_code == 'zh' and any(ord(c) in range(0x4E00, 0x9FFF) for c in text):
                    score += 10
                elif lang_code == 'ko' and any(ord(c) in range(0xAC00, 0xD7AF) for c in text):
                    score += 10
                elif lang_code == 'ar' and any(ord(c) in range(0x0600, 0x06FF) for c in text):
                    score += 10
                elif lang_code == 'hi' and any(ord(c) in range(0x0900, 0x097F) for c in text):
                    score += 10
            else:
                # Latin-based languages - use common words as heuristics
                common_words = {
                    'en': ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'that'],
                    'es': ['el', 'la', 'de', 'que', 'y', 'a', 'en', 'un'],
                    'fr': ['le', 'de', 'et', 'à', 'un', 'il', 'être', 'et'],
                    'de': ['der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das'],
                    'it': ['il', 'di', 'che', 'e', 'la', 'un', 'a', 'per'],
                    'pt': ['o', 'de', 'a', 'e', 'do', 'da', 'em', 'um']
                }

                if lang_code in common_words:
                    word_count = sum(1 for word in common_words[lang_code] if word in text_lower)
                    score += word_count * 2

            language_scores[lang_code] = score

        # Return languages with scores
        detected_langs = [lang for lang, score in language_scores.items() if score > 0]
        return detected_langs if detected_langs else ['unknown']

    def _extract_text_tesseract(self, image_path: str, languages: List[str] = None) -> List[TextRegion]:
        """Extract text using Tesseract OCR with region detection"""
        if not self.tesseract_available:
            return []

        try:
            # Configure Tesseract
            lang_string = '+'.join([SUPPORTED_LANGUAGES[lang]['tesseract'] for lang in languages if lang in SUPPORTED_LANGUAGES]) if languages else 'eng'

            # Get detailed OCR data
            img = Image.open(image_path)
            data = pytesseract.image_to_data(img, lang=lang_string, output_type=pytesseract.Output.DICT)

            text_regions = []
            current_text = ""
            current_conf = 0
            bbox_start = None

            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                conf = int(data['conf'][i])

                if text:  # Non-empty text
                    if not current_text:  # Start of new text block
                        bbox_start = (data['left'][i], data['top'][i])

                    current_text += text + " "
                    current_conf = max(current_conf, conf)
                else:  # Empty text - end of block
                    if current_text.strip():
                        bbox_end = (data['left'][i-1] + data['width'][i-1], data['top'][i-1] + data['height'][i-1])

                        if bbox_start and bbox_end:
                            region = TextRegion(
                                id=f"tess_{hashlib.md5(f'{image_path}_{i}'.encode()).hexdigest()}",
                                photo_path=image_path,
                                text_content=current_text.strip(),
                                confidence_score=current_conf / 100.0,
                                language_code=languages[0] if languages else 'en',
                                bbox_x=bbox_start[0],
                                bbox_y=bbox_start[1],
                                bbox_width=bbox_end[0] - bbox_start[0],
                                bbox_height=bbox_end[1] - bbox_start[1],
                                text_type='printed',
                                font_detected=None,
                                reading_order=len(text_regions),
                                created_at=datetime.now().isoformat()
                            )
                            text_regions.append(region)

                    current_text = ""
                    current_conf = 0
                    bbox_start = None

            return text_regions

        except Exception as e:
            logger.error(f"Error extracting text with Tesseract from {image_path}: {e}")
            return []

    def _extract_text_handwriting(self, image_path: str) -> List[TextRegion]:
        """Extract handwritten text using EasyOCR"""
        if not self.enable_handwriting or not self.easyocr_reader:
            return []

        try:
            results = self.easyocr_reader.readtext(image_path)

            text_regions = []
            for (bbox, text, confidence) in results:
                if confidence > 0.5:  # Filter low confidence results
                    # bbox is in format [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]

                    region = TextRegion(
                        id=f"hw_{hashlib.md5(f'{image_path}_{len(text_regions)}'.encode()).hexdigest()}",
                        photo_path=image_path,
                        text_content=text.strip(),
                        confidence_score=confidence,
                        language_code='unknown',  # EasyOCR doesn't provide language per result
                        bbox_x=int(min(x_coords)),
                        bbox_y=int(min(y_coords)),
                        bbox_width=int(max(x_coords) - min(x_coords)),
                        bbox_height=int(max(y_coords) - min(y_coords)),
                        text_type='handwritten',
                        font_detected=None,
                        reading_order=len(text_regions),
                        created_at=datetime.now().isoformat()
                    )
                    text_regions.append(region)

            return text_regions

        except Exception as e:
            logger.error(f"Error extracting handwriting from {image_path}: {e}")
            return []

    def extract_text(self, image_path: str, languages: List[str] = None) -> OCRResult:
        """
        Extract text from a single image with multiple engines.

        Args:
            image_path: Path to image file
            languages: Preferred languages for OCR

        Returns:
            OCRResult with all extracted text regions
        """
        start_time = time.time()

        if not languages:
            languages = ['en']  # Default to English

        try:
            # Extract text with Tesseract
            tesseract_regions = self._extract_text_tesseract(image_path, languages)

            # Extract handwriting if enabled
            handwriting_regions = []
            if self.enable_handwriting:
                handwriting_regions = self._extract_text_handwriting(image_path)

            # Combine all regions
            all_regions = tesseract_regions + handwriting_regions

            # Sort by reading order and y-coordinate
            all_regions.sort(key=lambda r: (r.reading_order, r.bbox_y))

            # Create full text
            full_text = " ".join(region.text_content for region in all_regions)

            # Detect languages in extracted text
            detected_langs = list(set(region.language_code for region in all_regions if region.language_code != 'unknown'))
            if not detected_langs:
                detected_langs = self._detect_language(full_text)

            # Calculate average confidence
            avg_confidence = np.mean([region.confidence_score for region in all_regions]) if all_regions else 0.0

            processing_time = (time.time() - start_time) * 1000

            result = OCRResult(
                photo_path=image_path,
                text_regions=all_regions,
                full_text=full_text,
                languages_detected=detected_langs,
                processing_time_ms=int(processing_time),
                confidence_average=avg_confidence,
                created_at=datetime.now().isoformat()
            )

            # Update stats
            self.stats['images_processed'] += 1
            self.stats['text_regions_extracted'] += len(all_regions)
            self.stats['total_characters'] += len(full_text)
            self.stats['processing_time_ms'] += processing_time

            return result

        except Exception as e:
            logger.error(f"Error extracting text from {image_path}: {e}")
            return OCRResult(
                photo_path=image_path,
                text_regions=[],
                full_text="",
                languages_detected=[],
                processing_time_ms=int((time.time() - start_time) * 1000),
                confidence_average=0.0,
                created_at=datetime.now().isoformat()
            )

    def extract_text_batch(self,
                          directory_path: str,
                          max_workers: int = 4,
                          show_progress: bool = False,
                          languages: List[str] = None) -> Dict[str, Any]:
        """
        Extract text from all images in a directory.

        Args:
            directory_path: Directory containing images
            max_workers: Number of parallel processing threads
            show_progress: Show progress updates
            languages: Preferred languages for OCR

        Returns:
            Dictionary with batch processing results
        """
        start_time = time.time()
        results = {
            'total_images': 0,
            'processed_images': 0,
            'text_regions_found': 0,
            'total_characters': 0,
            'languages_detected': set(),
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
            self.progress_callback(f"Processing {len(image_files)} images for text extraction...")

        # Process images in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self.extract_text, str(img_path), languages): img_path
                for img_path in image_files
            }

            for i, future in enumerate(as_completed(future_to_file)):
                img_path = future_to_file[future]
                try:
                    ocr_result = future.result()
                    if ocr_result.text_regions:
                        self._store_ocr_result(ocr_result)
                        results['text_regions_found'] += len(ocr_result.text_regions)
                        results['total_characters'] += len(ocr_result.full_text)
                        results['languages_detected'].update(ocr_result.languages_detected)

                    results['processed_images'] += 1

                    if show_progress and (i + 1) % 10 == 0:
                        progress = ((i + 1) / len(image_files)) * 100
                        self.progress_callback(f"Progress: {progress:.1f}% - {results['text_regions_found']} text regions")

                except Exception as e:
                    error_msg = f"Error processing {img_path}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)

        # Convert set to list for JSON serialization
        results['languages_detected'] = list(results['languages_detected'])
        results['processing_time_ms'] = int((time.time() - start_time) * 1000)

        if show_progress:
            self.progress_callback(f"Completed: {results['processed_images']} images, {results['text_regions_found']} text regions")

        return results

    def _store_ocr_result(self, ocr_result: OCRResult):
        """Store OCR result in database"""
        try:
            # Store processing status
            self.conn.execute("""
                INSERT OR REPLACE INTO ocr_processing_status
                (photo_path, status, text_regions_count, total_confidence, languages_detected, processing_model, last_processed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ocr_result.photo_path,
                'completed',
                len(ocr_result.text_regions),
                ocr_result.confidence_average,
                json.dumps(ocr_result.languages_detected),
                'tesseract+easyocr' if self.enable_handwriting else 'tesseract',
                ocr_result.created_at
            ))

            # Store text regions
            for region in ocr_result.text_regions:
                self.conn.execute("""
                    INSERT OR REPLACE INTO ocr_text_regions
                    (id, photo_path, text_content, confidence_score, language_code,
                     bbox_x, bbox_y, bbox_width, bbox_height, text_type, reading_order, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    region.id,
                    region.photo_path,
                    region.text_content,
                    region.confidence_score,
                    region.language_code,
                    region.bbox_x,
                    region.bbox_y,
                    region.bbox_width,
                    region.bbox_height,
                    region.text_type,
                    region.reading_order,
                    region.created_at
                ))

            self.conn.commit()

        except Exception as e:
            logger.error(f"Error storing OCR result for {ocr_result.photo_path}: {e}")
            self.conn.rollback()

    def search_text(self,
                   query: str,
                   language: Optional[str] = None,
                   min_confidence: float = 0.5,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search for images containing specific text.

        Args:
            query: Text to search for
            language: Filter by language
            min_confidence: Minimum confidence score
            limit: Maximum results

        Returns:
            List of matching images with highlighted text regions
        """
        try:
            # Build query conditions
            conditions = ["MATCH(text_content) AGAINST(? IN NATURAL LANGUAGE MODE)"]
            params = [query]

            if language:
                conditions.append("language_code = ?")
                params.append(language)

            conditions.append("confidence_score >= ?")
            params.append(min_confidence)

            # Search for text regions
            cursor = self.conn.execute(f"""
                SELECT
                    otr.photo_path,
                    otr.text_content,
                    otr.confidence_score,
                    otr.language_code,
                    otr.bbox_x,
                    otr.bbox_y,
                    otr.bbox_width,
                    otr.bbox_height,
                    otr.text_type,
                    created_at
                FROM ocr_text_regions otr
                WHERE {' AND '.join(conditions)}
                ORDER BY otr.confidence_score DESC
                LIMIT ?
            """, params + [limit])

            results = []
            for row in cursor.fetchall():
                # Calculate highlighting positions
                highlighted_text = self._highlight_text(row['text_content'], query)

                result = {
                    'photo_path': row['photo_path'],
                    'text_content': row['text_content'],
                    'highlighted_text': highlighted_text,
                    'confidence_score': row['confidence_score'],
                    'language_code': row['language_code'],
                    'bbox': {
                        'x': row['bbox_x'],
                        'y': row['bbox_y'],
                        'width': row['bbox_width'],
                        'height': row['bbox_height']
                    },
                    'text_type': row['text_type'],
                    'created_at': row['created_at']
                }
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error searching for text '{query}': {e}")
            return []

    def _highlight_text(self, text: str, query: str) -> str:
        """Highlight query terms in text for UI display"""
        if not text or not query:
            return text

        query_words = [word.lower() for word in query.split() if len(word) > 2]
        text_lower = text.lower()

        highlighted = text
        offset = 0

        for word in query_words:
            start = text_lower.find(word)
            while start != -1:
                # Insert highlight markers
                insert_pos = start + offset
                highlighted = highlighted[:insert_pos] + f"<mark>{highlighted[insert_pos:insert_pos+len(word)]}</mark>" + highlighted[insert_pos+len(word):]
                offset += len("<mark></mark>")

                # Find next occurrence
                start = text_lower.find(word, start + 1)

        return highlighted

    def get_text_regions(self, image_path: str) -> List[Dict[str, Any]]:
        """Get all text regions for an image with highlighting info"""
        try:
            cursor = self.conn.execute("""
                SELECT *
                FROM ocr_text_regions
                WHERE photo_path = ?
                ORDER BY reading_order, bbox_y
            """, (image_path,))

            regions = []
            for row in cursor.fetchall():
                region = {
                    'id': row['id'],
                    'text_content': row['text_content'],
                    'confidence_score': row['confidence_score'],
                    'language_code': row['language_code'],
                    'bbox': {
                        'x': row['bbox_x'],
                        'y': row['bbox_y'],
                        'width': row['bbox_width'],
                        'height': row['bbox_height']
                    },
                    'text_type': row['text_type'],
                    'reading_order': row['reading_order'],
                    'created_at': row['created_at']
                }
                regions.append(region)

            return regions

        except Exception as e:
            logger.error(f"Error getting text regions for {image_path}: {e}")
            return []

    def get_supported_languages(self) -> Dict[str, Dict[str, str]]:
        """Get list of supported OCR languages"""
        return SUPPORTED_LANGUAGES.copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get OCR processing statistics"""
        stats = self.stats.copy()

        # Add database stats
        try:
            cursor = self.conn.execute("SELECT COUNT(*) FROM ocr_text_regions")
            stats['total_text_regions_in_db'] = cursor.fetchone()[0]

            cursor = self.conn.execute("SELECT COUNT(DISTINCT photo_path) FROM ocr_text_regions")
            stats['images_with_text_in_db'] = cursor.fetchone()[0]

            # Language distribution
            cursor = self.conn.execute("""
                SELECT language_code, COUNT(*) as count
                FROM ocr_text_regions
                GROUP BY language_code
                ORDER BY count DESC
            """)
            stats['language_distribution'] = dict(cursor.fetchall())

        except Exception as e:
            logger.error(f"Error getting database stats: {e}")

        stats['tesseract_available'] = self.tesseract_available
        stats['handwriting_available'] = self.enable_handwriting

        return stats

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()