"""
Database Schema Extensions for Advanced Features

This module extends the existing database schema to support:
1. Face Recognition & People Clustering
2. Enhanced Duplicate Detection
3. OCR Text Search with Regions
4. Smart Albums Rules
5. Analytics & Usage Tracking
"""

import sqlite3
from pathlib import Path
import json


class SchemaExtensions:
    """Manages database schema extensions for advanced features"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def extend_schema(self) -> None:
        """Apply all schema extensions"""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Face Recognition Tables
            self._create_face_tables(conn)

            # Enhanced Duplicate Detection
            self._create_enhanced_duplicate_tables(conn)

            # OCR with Text Regions
            self._create_ocr_tables(conn)

            # Smart Albums Rules
            self._create_smart_albums_tables(conn)

            # Analytics & Usage
            self._create_analytics_tables(conn)

            conn.commit()

    def _create_face_tables(self, conn: sqlite3.Connection) -> None:
        """Create tables for face recognition and people clustering"""

        # Face clusters (groups of similar faces)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS face_clusters (
                id TEXT PRIMARY KEY,
                cluster_label TEXT NULL,  -- User-assigned person name
                representative_face_id TEXT NULL,  -- ID of the best face in cluster
                face_count INTEGER DEFAULT 1,
                confidence_score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_protected BOOLEAN DEFAULT FALSE,  -- User marked as important person
                privacy_level TEXT DEFAULT 'standard'  -- standard, sensitive, private
            )
        """)

        # Individual face detections
        conn.execute("""
            CREATE TABLE IF NOT EXISTS face_detections (
                id TEXT PRIMARY KEY,
                photo_path TEXT NOT NULL,
                cluster_id TEXT NULL,
                embedding BLOB NOT NULL,  -- Face embedding vector
                bbox_x INTEGER NOT NULL,
                bbox_y INTEGER NOT NULL,
                bbox_width INTEGER NOT NULL,
                bbox_height INTEGER NOT NULL,
                confidence REAL NOT NULL,
                face_size INTEGER NOT NULL,  -- Approximate face size in pixels
                quality_score REAL DEFAULT 0.0,  -- Image quality assessment
                pose_angles TEXT NULL,  -- JSON: {yaw, pitch, roll}
                blur_score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cluster_id) REFERENCES face_clusters(id)
            )
        """)

        # Create indexes separately
        conn.execute("CREATE INDEX IF NOT EXISTS idx_face_photo_path ON face_detections(photo_path)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_face_cluster ON face_detections(cluster_id)")

        # Face recognition training data
        conn.execute("""
            CREATE TABLE IF NOT EXISTS face_training (
                id TEXT PRIMARY KEY,
                cluster_id TEXT NOT NULL,
                face_detection_id TEXT NOT NULL,
                is_positive BOOLEAN DEFAULT TRUE,  -- Positive/negative example
                training_weight REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cluster_id) REFERENCES face_clusters(id),
                FOREIGN KEY (face_detection_id) REFERENCES face_detections(id)
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_training_cluster ON face_training(cluster_id)")

    def _create_enhanced_duplicate_tables(self, conn: sqlite3.Connection) -> None:
        """Enhance existing duplicate detection with more sophisticated features"""

        # Perceptual hash with multiple algorithms
        conn.execute("""
            CREATE TABLE IF NOT EXISTS perceptual_hashes (
                id TEXT PRIMARY KEY,
                photo_path TEXT NOT NULL UNIQUE,
                phash INTEGER NOT NULL,  -- Perceptual hash
                dhash INTEGER NOT NULL,  -- Difference hash
                ahash INTEGER NOT NULL,  -- Average hash
                whash INTEGER NOT NULL,  -- Wavelet hash
                color_histogram BLOB NULL,  -- Color distribution
                dominant_colors TEXT NULL,  -- JSON: [hex colors]
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_phash ON perceptual_hashes(phash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dhash ON perceptual_hashes(dhash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ahash ON perceptual_hashes(ahash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_whash ON perceptual_hashes(whash)")

        # Enhanced duplicate groups with similarity scoring
        conn.execute("""
            CREATE TABLE IF NOT EXISTS duplicate_groups_enhanced (
                id TEXT PRIMARY KEY,
                group_type TEXT NOT NULL,  -- exact, near, similar, visual
                similarity_threshold REAL NOT NULL,
                primary_photo_id TEXT NULL,  -- Best quality photo in group
                total_size_bytes INTEGER DEFAULT 0,
                resolved_count INTEGER DEFAULT 0,
                resolution_strategy TEXT NULL,  -- keep_best, keep_largest, keep_all
                auto_resolvable BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Individual duplicate relationships
        conn.execute("""
            CREATE TABLE IF NOT EXISTS duplicate_relationships (
                id TEXT PRIMARY KEY,
                group_id TEXT NOT NULL,
                photo_path TEXT NOT NULL,
                similarity_score REAL NOT NULL,
                is_primary BOOLEAN DEFAULT FALSE,
                resolution_action TEXT NULL,  -- keep, delete, move
                resolution_reason TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES duplicate_groups_enhanced(id)
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_relationship_group ON duplicate_relationships(group_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relationship_photo ON duplicate_relationships(photo_path)")

    def _create_ocr_tables(self, conn: sqlite3.Connection) -> None:
        """Create tables for OCR with text regions and confidence"""

        # OCR text extraction with regions
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ocr_text_regions (
                id TEXT PRIMARY KEY,
                photo_path TEXT NOT NULL,
                text_content TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                language_code TEXT DEFAULT 'en',
                bbox_x INTEGER NOT NULL,
                bbox_y INTEGER NOT NULL,
                bbox_width INTEGER NOT NULL,
                bbox_height INTEGER NOT NULL,
                text_type TEXT DEFAULT 'printed',  -- printed, handwritten, mixed
                font_detected TEXT NULL,
                reading_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_ocr_photo ON ocr_text_regions(photo_path)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ocr_text ON ocr_text_regions(text_content)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ocr_language ON ocr_text_regions(language_code)")

        # OCR processing status and metadata
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ocr_processing_status (
                photo_path TEXT PRIMARY KEY,
                status TEXT NOT NULL,  -- pending, processing, completed, failed, skipped
                processing_time_ms INTEGER NULL,
                text_regions_count INTEGER DEFAULT 0,
                total_confidence REAL DEFAULT 0.0,
                languages_detected TEXT NULL,  -- JSON array
                processing_model TEXT NULL,
                error_message TEXT NULL,
                last_processed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_ocr_status ON ocr_processing_status(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ocr_last_processed ON ocr_processing_status(last_processed)")

        # Handwriting recognition (separate from printed OCR)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS handwriting_recognition (
                id TEXT PRIMARY KEY,
                photo_path TEXT NOT NULL,
                text_content TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                bbox_x INTEGER NOT NULL,
                bbox_y INTEGER NOT NULL,
                bbox_width INTEGER NOT NULL,
                bbox_height INTEGER NOT NULL,
                stroke_data TEXT NULL,  -- JSON: stroke points for recognition
                handwriting_style TEXT NULL,  -- cursive, print, mixed
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_handwriting_photo ON handwriting_recognition(photo_path)")

    def _create_smart_albums_tables(self, conn: sqlite3.Connection) -> None:
        """Create tables for advanced smart albums with AI suggestions"""

        # Enhanced smart album rules
        conn.execute("""
            CREATE TABLE IF NOT EXISTS smart_album_rules_enhanced (
                id TEXT PRIMARY KEY,
                album_id TEXT NOT NULL,
                rule_type TEXT NOT NULL,  -- condition, operator, template, ai_suggestion
                rule_data TEXT NOT NULL,  -- JSON rule configuration
                priority INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                is_ai_generated BOOLEAN DEFAULT FALSE,
                confidence_score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (album_id) REFERENCES albums(id)
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_album_rules ON smart_album_rules_enhanced(album_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rule_type ON smart_album_rules_enhanced(rule_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_generated ON smart_album_rules_enhanced(is_ai_generated)")

        # Rule templates for common use cases
        conn.execute("""
            CREATE TABLE IF NOT EXISTS smart_album_templates (
                id TEXT PRIMARY KEY,
                template_name TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,  -- events, people, places, content, technical
                rule_definition TEXT NOT NULL,  -- JSON template
                usage_count INTEGER DEFAULT 0,
                rating_average REAL DEFAULT 0.0,
                is_featured BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_template_category ON smart_album_templates(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_template_featured ON smart_album_templates(is_featured)")

        # AI album suggestions
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_album_suggestions (
                id TEXT PRIMARY KEY,
                suggestion_type TEXT NOT NULL,  -- auto_album, rule_suggestion, photo_grouping
                suggestion_data TEXT NOT NULL,  -- JSON: album definition or photos
                confidence_score REAL NOT NULL,
                user_feedback TEXT NULL,  -- accepted, rejected, modified
                feedback_reason TEXT NULL,
                expires_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_suggestion_type ON ai_album_suggestions(suggestion_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_suggestion_confidence ON ai_album_suggestions(confidence_score)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_suggestion_feedback ON ai_album_suggestions(user_feedback)")

    def _create_analytics_tables(self, conn: sqlite3.Connection) -> None:
        """Create tables for analytics and usage tracking"""

        # Library analytics
        conn.execute("""
            CREATE TABLE IF NOT EXISTS library_analytics (
                date DATE PRIMARY KEY,
                total_photos INTEGER DEFAULT 0,
                total_size_bytes INTEGER DEFAULT 0,
                new_photos INTEGER DEFAULT 0,
                duplicates_found INTEGER DEFAULT 0,
                faces_detected INTEGER DEFAULT 0,
                ocr_processed INTEGER DEFAULT 0,
                albums_created INTEGER DEFAULT 0,
                search_queries INTEGER DEFAULT 0,
                unique_search_terms INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Content insights
        conn.execute("""
            CREATE TABLE IF NOT EXISTS content_insights (
                id TEXT PRIMARY KEY,
                insight_type TEXT NOT NULL,  -- subject, location, time, color, composition
                insight_value TEXT NOT NULL,
                photo_count INTEGER DEFAULT 0,
                confidence_score REAL DEFAULT 0.0,
                metadata JSON NULL,  -- Additional insight data
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_insight_type ON content_insights(insight_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_insight_value ON content_insights(insight_value)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_photo_count ON content_insights(photo_count)")

        # Search analytics
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_analytics (
                id TEXT PRIMARY KEY,
                query_text TEXT NOT NULL,
                search_type TEXT NOT NULL,  -- text, image, hybrid, face, ocr, metadata
                results_count INTEGER DEFAULT 0,
                results_clicked INTEGER DEFAULT 0,
                search_duration_ms INTEGER DEFAULT 0,
                user_id TEXT NULL,
                session_id TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_search_date ON search_analytics(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_search_type ON search_analytics(search_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_query_text ON search_analytics(query_text)")

        # User behavior analytics
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_behavior (
                id TEXT PRIMARY KEY,
                action_type TEXT NOT NULL,  -- view, favorite, delete, share, export
                target_type TEXT NOT NULL,  -- photo, album, cluster, duplicate_group
                target_id TEXT NOT NULL,
                context_data TEXT NULL,  -- JSON: additional context
                session_duration_ms INTEGER NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_action_type ON user_behavior(action_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_target_type ON user_behavior(target_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_behavior_date ON user_behavior(created_at)")

        # Performance metrics
        conn.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id TEXT PRIMARY KEY,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_unit TEXT NULL,
                operation_type TEXT NOT NULL,  -- search, index, ocr, face_detection, duplicate_detection
                photo_count INTEGER NULL,
                processing_time_ms INTEGER NULL,
                memory_usage_mb INTEGER NULL,
                cpu_usage_percent REAL NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_metric_name ON performance_metrics(metric_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_operation_type ON performance_metrics(operation_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_metric_date ON performance_metrics(created_at)")

        # Photo notes/captions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS photo_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_path TEXT NOT NULL UNIQUE,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Photo versions table for version stacks
        conn.execute("""
            CREATE TABLE IF NOT EXISTS photo_versions (
                id TEXT PRIMARY KEY,
                original_path TEXT NOT NULL,
                version_path TEXT NOT NULL UNIQUE,
                version_type TEXT NOT NULL,  -- 'original', 'edited', 'variant'
                version_name TEXT,  -- User-friendly name for the version
                version_description TEXT,  -- Description of changes made
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                editing_instructions TEXT,  -- JSON of editing operations applied
                parent_version_id TEXT,  -- For chain of edits
                FOREIGN KEY (parent_version_id) REFERENCES photo_versions(id)
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_original_path ON photo_versions(original_path)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_version_path ON photo_versions(version_path)")

    def insert_default_data(self) -> None:
        """Insert default templates and initial data"""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Default smart album templates
            templates = [
                {
                    "id": "template_recent_photos",
                    "template_name": "Recent Photos",
                    "description": "Photos from the last 30 days",
                    "category": "time",
                    "rule_definition": json.dumps(
                        {
                            "conditions": [
                                {
                                    "field": "created_at",
                                    "operator": "greater_than",
                                    "value": "30_days_ago",
                                }
                            ],
                            "sort": "created_at_desc",
                        }
                    ),
                },
                {
                    "id": "template_favorites",
                    "template_name": "Favorites",
                    "description": "All marked as favorite",
                    "category": "content",
                    "rule_definition": json.dumps(
                        {
                            "conditions": [
                                {
                                    "field": "is_favorite",
                                    "operator": "equals",
                                    "value": True,
                                }
                            ],
                            "sort": "created_at_desc",
                        }
                    ),
                },
                {
                    "id": "template_large_files",
                    "template_name": "Large Files",
                    "description": "Photos larger than 10MB",
                    "category": "technical",
                    "rule_definition": json.dumps(
                        {
                            "conditions": [
                                {
                                    "field": "file_size",
                                    "operator": "greater_than",
                                    "value": 10485760,  # 10MB
                                }
                            ],
                            "sort": "file_size_desc",
                        }
                    ),
                },
                {
                    "id": "template_screenshots",
                    "template_name": "Screenshots",
                    "description": "Screenshots and screen captures",
                    "category": "content",
                    "rule_definition": json.dumps(
                        {
                            "conditions": [
                                {
                                    "field": "filename",
                                    "operator": "contains",
                                    "value": "screenshot",
                                    "case_sensitive": False,
                                },
                                {
                                    "field": "dimensions",
                                    "operator": "matches_device",
                                    "value": "screen",
                                },
                            ],
                            "sort": "created_at_desc",
                        }
                    ),
                },
            ]

            for template in templates:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO smart_album_templates
                    (id, template_name, description, category, rule_definition, is_featured)
                    VALUES (?, ?, ?, ?, ?, 1)
                """,
                    (
                        template["id"],
                        template["template_name"],
                        template["description"],
                        template["category"],
                        template["rule_definition"],
                    ),
                )

            conn.commit()
