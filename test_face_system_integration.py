"""
Comprehensive Face Recognition System Integration Tests

Tests the complete face recognition system including all phases:
1. FAISS Performance Foundation
2. Advanced Intelligence Features
3. Analytics and Smart Organization
4. Enhanced Search and Natural Language Processing
5. Enhanced Video Processing
6. Privacy and Security Framework
7. Model Management and Versioning
8. Mobile and Cross-Platform Features
9. User Experience Enhancements

This test suite validates end-to-end functionality and integration
between all components of the advanced face recognition system.
"""

import os
import pytest
import tempfile
import sqlite3
import numpy as np
from pathlib import Path
from datetime import datetime

# Import all the face recognition components that exist
try:
    from server.clustering.faiss_face_clusterer import FAISSFaceClusterer
except ImportError:
    FAISSFaceClusterer = None

try:
    from server.face_embedding_index import FAISSIndex
except ImportError:
    FAISSIndex = None

try:
    from server.face_attribute_analyzer import AdvancedFaceQualityAssessor, FaceAttributeAnalyzer
except ImportError:
    FaceAttributeAnalyzer = None

try:
    from server.face_analytics_service import FaceAnalyticsEngine
except ImportError:
    FaceAnalyticsEngine = None

try:
    from server.smart_organization_service import SmartOrganizationService
except ImportError:
    SmartOrganizationService = None

try:
    from server.advanced_face_search import AdvancedFaceSearchEngine
except ImportError:
    AdvancedFaceSearchEngine = None

try:
    from server.natural_language_search import NaturalLanguageQueryParser
except ImportError:
    NaturalLanguageQueryParser = None

try:
    from server.video_face_tracker import VideoFaceTracker
except ImportError:
    VideoFaceTracker = None

try:
    from server.enhanced_video_face_processor import EnhancedVideoFaceProcessor
except ImportError:
    EnhancedVideoFaceProcessor = None

try:
    from server.privacy_controls import PrivacyControlsManager, ConsentType, PrivacyLevel
except ImportError:
    PrivacyControlsManager = None
    ConsentType = None
    PrivacyLevel = None

try:
    from server.privacy_aware_face_processor import PrivacyAwareFaceProcessor
except ImportError:
    PrivacyAwareFaceProcessor = None

try:
    from server.model_manager import ModelManager
except ImportError:
    ModelManager = None

try:
    from server.mobile_face_service import MobileFaceService
except ImportError:
    MobileFaceService = None

try:
    from server.face_onboarding_service import FaceOnboardingService
except ImportError:
    FaceOnboardingService = None


class TestFaceSystemIntegration:
    """Comprehensive integration tests for the face recognition system"""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            yield tmp.name
        Path(tmp.name).unlink(missing_ok=True)

    @pytest.fixture
    def sample_embeddings(self):
        """Generate sample face embeddings for testing"""
        np.random.seed(42)  # For reproducible tests
        return {
            "person_1": [np.random.rand(512).astype(np.float32) for _ in range(5)],
            "person_2": [np.random.rand(512).astype(np.float32) for _ in range(3)],
            "person_3": [np.random.rand(512).astype(np.float32) for _ in range(7)],
        }

    @pytest.fixture
    def sample_face_data(self):
        """Generate sample face detection data"""
        return [
            {
                "detection_id": f"face_{i}",
                "image_path": f"/test/image_{i}.jpg",
                "bbox": [100 + i * 10, 100 + i * 10, 150, 150],
                "confidence": 0.9 - i * 0.05,
                "embedding": np.random.rand(512).astype(np.float32),
                "attributes": {
                    "age": 25 + i * 5,
                    "emotion": ["happy", "neutral", "sad"][i % 3],
                    "gender": "male" if i % 2 == 0 else "female",
                    "pose": "frontal",
                    "quality_score": 0.8 + i * 0.02,
                },
            }
            for i in range(15)
        ]

    @staticmethod
    def _create_face_schema(db_path: str) -> None:
        """Create the face schema the server services actually query."""
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS face_clusters (
                    cluster_id INTEGER PRIMARY KEY,
                    label TEXT
                )
            """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS face_detections (
                    detection_id TEXT PRIMARY KEY,
                    image_path TEXT,
                    age_estimate INTEGER,
                    emotion TEXT,
                    quality_score REAL,
                    overall_quality REAL,
                    pose_type TEXT,
                    age_confidence REAL,
                    emotion_confidence REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS photo_person_associations (
                    detection_id TEXT,
                    cluster_id INTEGER,
                    photo_path TEXT,
                    confidence REAL
                )
            """
            )

    def test_phase_1_faiss_performance_foundation(self, temp_db_path, sample_embeddings):
        """Test Phase 1: FAISS High-Performance Foundation"""
        print("\n=== Testing Phase 1: FAISS Performance Foundation ===")

        # Test FAISS Face Clusterer
        FAISSFaceClusterer(embedding_dim=512)

        # Test embedding index creation
        embedding_index = FAISSIndex()

        # Add embeddings for each person
        for person_id, embeddings in sample_embeddings.items():
            for i, embedding in enumerate(embeddings):
                detection_id = f"{person_id}_face_{i}"
                embedding_index.add_prototype(detection_id, embedding, person_id)

        # Test high-performance search
        query_embedding = sample_embeddings["person_1"][0]
        similar_faces = embedding_index.search(query_embedding, k=5, threshold=0.5)

        assert len(similar_faces) > 0, "FAISS search should return similar faces"
        assert similar_faces[0].similarity > 0.5, "Top result should have high similarity"

        # Test incremental updates
        new_embedding = np.random.rand(512).astype(np.float32)
        embedding_index.add_prototype("new_face_1", new_embedding, "person_1")

        # Verify the new embedding is searchable
        updated_results = embedding_index.search(new_embedding, k=3)
        assert len(updated_results) > 0, "New embedding should be searchable"

        print("✅ Phase 1: FAISS Performance Foundation - PASSED")

    def test_phase_2_advanced_intelligence_features(self, temp_db_path, sample_face_data):
        """Test Phase 2: Advanced Intelligence Features"""
        print("\n=== Testing Phase 2: Advanced Intelligence Features ===")

        # Test Face Attribute Analyzer
        attribute_analyzer = FaceAttributeAnalyzer()

        # Test attribute analysis on sample data
        for face_data in sample_face_data[:3]:  # Test first 3 faces
            # Simulate attribute analysis
            attributes = attribute_analyzer.analyze_attributes(face_crop=np.random.rand(150, 150, 3))

            assert "age_estimate" in attributes, "Should have age field in contract"
            assert "emotion" in attributes, "Should have emotion field in contract"
            assert "pose_type" in attributes, "Should have pose field in contract"

        # Test quality assessment on genuinely different imagery: random noise
        # crops all score identically, so use distinct patterns (sharp edges,
        # smooth gradient, flat field) that the blur/lighting metrics can tell
        # apart.
        patterns = [
            np.tile(np.concatenate([np.zeros((75, 150, 3)), np.full((75, 150, 3), 255)]), (1, 1, 1)).astype(np.uint8),
            np.linspace(0, 255, 150 * 150 * 3, dtype=np.uint8).reshape(150, 150, 3),
            np.full((150, 150, 3), 128, dtype=np.uint8),
        ]
        quality_scores = []
        for i, face_data in enumerate(sample_face_data):
            quality = AdvancedFaceQualityAssessor().assess_comprehensive_quality(face_crop=patterns[i % len(patterns)])
            quality_scores.append(quality["overall_quality"])

            assert 0 <= quality["overall_quality"] <= 1, "Quality score should be between 0 and 1"
            assert "blur_score" in quality, "Should assess blur"
            assert "lighting_score" in quality, "Should assess lighting"

        # Test that quality scores vary (not all the same)
        assert len(set(quality_scores)) > 1, "Quality scores should vary across faces"

        print("✅ Phase 2: Advanced Intelligence Features - PASSED")

    def test_phase_3_analytics_and_smart_organization(self, temp_db_path, sample_face_data):
        """Test Phase 3: Analytics and Smart Organization"""
        print("\n=== Testing Phase 3: Analytics and Smart Organization ===")

        # Initialize services
        analytics_engine = FaceAnalyticsEngine(temp_db_path)
        organization_service = SmartOrganizationService(temp_db_path)

        # Set up test data in the schema the analytics engine actually queries
        self._create_face_schema(temp_db_path)
        with sqlite3.connect(temp_db_path) as conn:
            # Insert test clusters
            for i in range(3):
                conn.execute("INSERT INTO face_clusters (cluster_id, label) VALUES (?, ?)", (i + 1, f"Person {i+1}"))

            # Insert test faces and assign to clusters
            for i, face_data in enumerate(sample_face_data):
                conn.execute(
                    """
                    INSERT INTO face_detections (
                        detection_id, image_path, age_estimate, emotion,
                        quality_score, overall_quality, pose_type, age_confidence, emotion_confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        face_data["detection_id"],
                        face_data["image_path"],
                        face_data["attributes"]["age"],
                        face_data["attributes"]["emotion"],
                        # High, varied quality: every cluster gets >=3 photos at
                        # or above the 0.8 smart-album threshold the service applies.
                        round(0.95 - (i % 5) * 0.03, 2),
                        round(0.95 - (i % 5) * 0.03, 2),
                        face_data["attributes"]["pose"],
                        0.9,
                        0.9,
                    ),
                )
                cluster_id = (i % 3) + 1
                conn.execute(
                    "INSERT INTO photo_person_associations (detection_id, cluster_id, photo_path, confidence)"
                    " VALUES (?, ?, ?, ?)",
                    (face_data["detection_id"], cluster_id, face_data["image_path"], face_data["confidence"]),
                )

        # Test person timeline generation
        timeline = analytics_engine.generate_person_timeline("1")
        assert "person_id" in timeline, "Timeline should include person ID"
        assert "timeline" in timeline, "Timeline should include events"

        # Test relationship detection
        relationships = analytics_engine.detect_photo_relationships()
        assert "relationships" in relationships, "Should detect relationships"

        # Test event detection
        events = analytics_engine.detect_events(min_people=2, time_window_hours=24)
        assert isinstance(events, list), "Events should be a list"

        # Test smart album creation
        smart_albums = organization_service.create_smart_albums()
        assert isinstance(smart_albums, list), "Smart albums should be a list"
        assert len(smart_albums) > 0, "Should create at least one smart album"

        # Test duplicate person detection
        duplicates = organization_service.detect_duplicate_people(similarity_threshold=0.8)
        assert isinstance(duplicates, list), "Duplicates should be a list"

        print("✅ Phase 3: Analytics and Smart Organization - PASSED")

    def test_phase_4_enhanced_search_and_nlp(self, temp_db_path):
        """Test Phase 4: Enhanced Search and Natural Language Processing"""
        print("\n=== Testing Phase 4: Enhanced Search and NLP ===")

        # Test Natural Language Query Parser
        parser = NaturalLanguageQueryParser()

        # Test various query types
        test_queries = [
            "happy family photos from 2023",
            "photos with John but not Mary",
            "everyone smiling in the last summer",
            "photos with exactly 3 people",
            "children under 10 years old",
        ]

        for query in test_queries:
            parsed = parser.parse(query)
            assert parsed is not None, f"Should parse query: {query}"
            assert hasattr(parsed, "person_constraints"), "Should have person constraints"
            assert hasattr(parsed, "emotion_constraints"), "Should have emotion constraints"
            assert hasattr(parsed, "temporal_constraint"), "Should have temporal constraints"

        # Test Advanced Face Search Engine (real query-based search surface)
        self._create_face_schema(temp_db_path)
        search_engine = AdvancedFaceSearchEngine(temp_db_path)

        search_results = search_engine.search("happy family")
        assert isinstance(search_results, list), "Should return a result list"

        print("✅ Phase 4: Enhanced Search and NLP - PASSED")

    def test_phase_5_enhanced_video_processing(self, temp_db_path):
        """Test Phase 5: Enhanced Video Processing"""
        print("\n=== Testing Phase 5: Enhanced Video Processing ===")

        # Test Video Face Tracker via its real track-consolidation machinery
        video_tracker = VideoFaceTracker(Path(temp_db_path))

        active_tracks: dict = {}
        next_track_id = 1
        for i in range(30):  # 1 second of video at 30fps
            faces = [
                {
                    "detection_id": f"frame_{i}_face_0",
                    "bbox": [100 + i, 100, 150, 150],
                    "confidence": 0.9,
                }
            ]
            active_tracks = video_tracker._update_tracks(active_tracks, faces, frame_number=i, timestamp=i * 0.033)
            # Start new tracks for unmatched faces — same as track_faces_in_video
            for face in faces:
                if not face.get("matched"):
                    track_id = f"track_{next_track_id}"
                    next_track_id += 1
                    active_tracks[track_id] = {
                        "track_id": track_id,
                        "video_path": "synthetic",
                        "start_frame": i,
                        "start_time": i * 0.033,
                        "detections": [face],
                        "last_seen": i,
                    }

        assert len(active_tracks) == 1, "One moving face should consolidate into one track"
        track = next(iter(active_tracks.values()))
        assert len(track["detections"]) == 30, "All 30 detections should join one track"

        # Test Enhanced Video Face Processor against a real synthesized video
        import cv2

        video_path = str(Path(tempfile.gettempdir()) / f"face_integration_{os.getpid()}.mp4")
        writer = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*"mp4v"), 10, (100, 100))
        for i in range(20):
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            frame[40:60, 10 + i * 2 : 30 + i * 2] = 255
            writer.write(frame)
        writer.release()

        video_processor = EnhancedVideoFaceProcessor(temp_db_path)
        video_analysis = video_processor.process_video(video_path, extract_highlights=True)
        assert video_analysis.get("video_path") == video_path, "Should include video path"
        assert video_analysis.get("status") == "completed", "Should complete processing"
        assert "highlights" in video_analysis, "Should include highlights section"
        Path(video_path).unlink(missing_ok=True)

        print("✅ Phase 5: Enhanced Video Processing - PASSED")

    def test_phase_6_privacy_and_security(self, temp_db_path):
        """Test Phase 6: Privacy and Security Framework"""
        print("\n=== Testing Phase 6: Privacy and Security ===")

        # Test Privacy Controls Manager
        privacy_manager = PrivacyControlsManager(temp_db_path)

        # Test consent management
        consent_id = privacy_manager.request_consent(
            user_id="test_user",
            consent_type=ConsentType.FACE_RECOGNITION,
            purpose="Face recognition for photo organization",
        )
        assert consent_id is not None, "Should create consent request"

        # Grant consent
        success = privacy_manager.grant_consent(consent_id, "test_user")
        assert success, "Should grant consent"

        # Check consent status
        has_consent = privacy_manager.check_consent("test_user", ConsentType.FACE_RECOGNITION)
        assert has_consent, "Should have valid consent"

        # Test data export
        export_id = privacy_manager.export_user_data(user_id="test_user", export_types=["consent", "audit_logs"])
        assert export_id is not None, "Should create export request"

        # Test Privacy-Aware Face Processor
        privacy_processor = PrivacyAwareFaceProcessor(
            face_clusterer=None,  # Mock clusterer
            privacy_manager=privacy_manager,
        )

        # Test privacy-compliant processing
        result = privacy_processor.process_with_privacy_controls(image_path="/test/image.jpg", user_id="test_user")
        assert result.processing_allowed, "Should allow processing with consent"
        assert result.privacy_level == PrivacyLevel.FULL_PROCESSING, "Should use full processing"

        # Test consent withdrawal
        success = privacy_manager.withdraw_consent("test_user", ConsentType.FACE_RECOGNITION)
        assert success, "Should withdraw consent"

        # Verify processing is blocked after withdrawal
        result_after_withdrawal = privacy_processor.process_with_privacy_controls(
            image_path="/test/image2.jpg", user_id="test_user"
        )
        assert not result_after_withdrawal.processing_allowed, "Should block processing without consent"

        print("✅ Phase 6: Privacy and Security - PASSED")

    def test_phase_7_model_management(self, temp_db_path):
        """Test Phase 7: Model Management and Versioning"""
        print("\n=== Testing Phase 7: Model Management ===")

        # Test Model Manager (real ctor: models_dir + face_db_path)
        models_dir = tempfile.mkdtemp()
        model_manager = ModelManager(models_dir, temp_db_path)

        # Real model registry surface
        available_models = model_manager.get_available_models()
        assert isinstance(available_models, list), "Should list available models"
        assert len(available_models) > 0, "Default registry should define models"

        # Real embedding migration surface (covered deeper by migration property tests)
        migration = model_manager.migrate_embeddings("1.0.0", "1.1.0")
        assert migration["status"] in ("started", "completed", "error", "queued"), "Should report migration status"

        print("✅ Phase 7: Model Management - PASSED")

    def test_phase_8_mobile_and_cross_platform(self, temp_db_path):
        """Test Phase 8: Mobile and Cross-Platform Features"""
        print("\n=== Testing Phase 8: Mobile Features ===")

        # Test Mobile Face Service
        mobile_service = MobileFaceService(
            face_clusterer=None,  # Mock clusterer
            db_path=temp_db_path,
        )

        # Test device registration
        registration_result = mobile_service.register_mobile_device(
            device_id="test_device_001",
            device_name="Test iPhone",
            device_type="ios",
            user_id="test_user",
            push_token="mock_push_token",
        )
        assert registration_result["status"] == "registered", "Should register device"
        assert "sync_token" in registration_result, "Should provide sync token"

        # Test mobile face detection
        mock_image_data = b"mock_image_data"
        detection_result = mobile_service.detect_faces_mobile(
            image_data=mock_image_data, device_id="test_device_001", offline_mode=True
        )
        assert detection_result.device_id == "test_device_001", "Should match device ID"
        assert detection_result.offline_mode, "Should be in offline mode"

        # Test sync status
        sync_status = mobile_service.get_device_sync_status("test_device_001")
        assert sync_status.device_id == "test_device_001", "Should match device ID"
        assert sync_status.sync_token is not None, "Should have sync token"

        # Test face tagging
        tag_result = mobile_service.tag_face_mobile(
            device_id="test_device_001", detection_id="test_detection_001", person_name="John Doe"
        )
        assert tag_result["status"] == "tagged", "Should tag face successfully"

        # Test mobile suggestions
        suggestions = mobile_service.get_mobile_face_suggestions("test_device_001", limit=5)
        assert isinstance(suggestions, list), "Should return suggestions list"

        print("✅ Phase 8: Mobile and Cross-Platform - PASSED")

    def test_phase_9_user_experience_enhancements(self, temp_db_path):
        """Test Phase 9: User Experience Enhancements"""
        print("\n=== Testing Phase 9: UX Enhancements ===")

        # Test Face Onboarding Service
        onboarding_service = FaceOnboardingService(temp_db_path)

        # Test onboarding flow creation
        flow = onboarding_service.create_onboarding_flow(
            user_id="test_user", personalization={"experience_level": "beginner"}
        )
        assert flow.user_id == "test_user", "Should match user ID"
        assert len(flow.steps) > 0, "Should have onboarding steps"
        assert flow.status.value == "not_started", "Should start as not started"

        # Test starting onboarding
        start_result = onboarding_service.start_onboarding("test_user")
        assert start_result["status"] == "started", "Should start onboarding"

        # Test step progress tracking
        progress_result = onboarding_service.track_step_progress(
            user_id="test_user", step_id="welcome", action="completed", data={"time_spent": 30}
        )
        assert progress_result["status"] == "tracked", "Should track progress"

        # Test contextual help
        help_content = onboarding_service.provide_contextual_help(
            user_id="test_user", context="face_detection_failed", specific_issue="No faces found in photo"
        )
        assert "help_content" in help_content, "Should provide help content"
        assert help_content["context"] == "face_detection_failed", "Should match context"

        # Test onboarding status
        status = onboarding_service.get_onboarding_status("test_user")
        assert status["status"] == "in_progress", "Should be in progress"
        assert "step_progress" in status, "Should include step progress"

        print("✅ Phase 9: UX Enhancements - PASSED")

    def test_end_to_end_integration(self, temp_db_path, sample_face_data):
        """Test complete end-to-end integration of all components"""
        print("\n=== Testing End-to-End Integration ===")

        # Initialize all major components
        privacy_manager = PrivacyControlsManager(temp_db_path)
        mobile_service = MobileFaceService(None, temp_db_path)
        onboarding_service = FaceOnboardingService(temp_db_path)
        self._create_face_schema(temp_db_path)
        with sqlite3.connect(temp_db_path) as conn:
            conn.execute("INSERT INTO face_clusters (cluster_id, label) VALUES (1, 'Integration Person')")
            conn.execute(
                "INSERT INTO photo_person_associations (detection_id, cluster_id, photo_path, confidence)"
                " VALUES ('e2e_face_1', 1, '/test/integration.jpg', 0.9)"
            )
        analytics_engine = FaceAnalyticsEngine(temp_db_path)

        # Simulate complete user journey
        user_id = "integration_test_user"

        # 1. User onboarding
        onboarding_service.create_onboarding_flow(user_id)
        onboarding_service.start_onboarding(user_id)

        # 2. Privacy consent
        consent_id = privacy_manager.request_consent(
            user_id=user_id, consent_type=ConsentType.FACE_RECOGNITION, purpose="Complete face recognition system"
        )
        privacy_manager.grant_consent(consent_id, user_id)

        # 3. Mobile device registration
        mobile_service.register_mobile_device(
            device_id="integration_device", device_name="Integration Test Device", device_type="test", user_id=user_id
        )

        # 4. Face processing simulation
        for face_data in sample_face_data[:5]:  # Process first 5 faces
            # Simulate mobile face detection
            detection_result = mobile_service.detect_faces_mobile(
                image_data=b"mock_image", device_id="integration_device", offline_mode=False
            )
            assert detection_result.device_id == "integration_device"

        # 5. Analytics generation
        timeline = analytics_engine.generate_person_timeline("1")
        assert "person_id" in timeline

        # 6. Complete onboarding
        completion_result = onboarding_service.complete_onboarding(
            user_id=user_id, feedback={"rating": 5, "comments": "Great system!"}
        )
        assert completion_result["status"] == "completed"

        # 7. Verify system state
        onboarding_status = onboarding_service.get_onboarding_status(user_id)
        assert onboarding_status["status"] == "completed"

        privacy_dashboard = privacy_manager.get_privacy_dashboard(user_id)
        assert privacy_dashboard["user_id"] == user_id

        device_status = mobile_service.get_device_sync_status("integration_device")
        assert device_status.device_id == "integration_device"

        print("✅ End-to-End Integration - PASSED")

    def test_performance_and_scalability(self, temp_db_path):
        """Test system performance and scalability characteristics"""
        print("\n=== Testing Performance and Scalability ===")

        # Test FAISS performance with larger dataset
        embedding_index = FAISSIndex()

        # Add many embeddings to test scalability
        start_time = datetime.now()
        for i in range(1000):
            embedding = np.random.rand(512).astype(np.float32)
            embedding_index.add_prototype(f"perf_test_{i}", embedding, f"person_{i % 100}")

        index_build_time = (datetime.now() - start_time).total_seconds()
        assert index_build_time < 30, f"Index building should be fast, took {index_build_time}s"

        # Test search performance
        query_embedding = np.random.rand(512).astype(np.float32)
        start_time = datetime.now()

        for _ in range(100):  # 100 search queries
            results = embedding_index.search(query_embedding, k=10)
            assert len(results) <= 10, "Should return at most k results"

        search_time = (datetime.now() - start_time).total_seconds()
        avg_search_time = search_time / 100
        assert avg_search_time < 0.1, f"Average search should be fast, took {avg_search_time}s"

        # Test memory usage (basic check)
        stats = embedding_index.get_stats()
        assert "memory_usage_mb" in stats, "Should report memory usage"
        assert stats["memory_usage_mb"] > 0, "Should use some memory"

        print(f"✅ Performance Test - Index: {index_build_time:.2f}s, Search: {avg_search_time:.4f}s avg")

    def test_error_handling_and_resilience(self, temp_db_path):
        """Test error handling and system resilience"""
        print("\n=== Testing Error Handling and Resilience ===")

        # Test invalid inputs
        privacy_manager = PrivacyControlsManager(temp_db_path)

        # Test invalid consent type
        try:
            privacy_manager.request_consent(
                user_id="test_user",
                consent_type="invalid_consent_type",  # This should fail
                purpose="Test",
            )
            assert False, "Should raise error for invalid consent type"
        except (ValueError, TypeError):
            pass  # Expected error

        # Test missing user
        has_consent = privacy_manager.check_consent("nonexistent_user", ConsentType.FACE_RECOGNITION)
        assert not has_consent, "Should return False for nonexistent user"

        # Test mobile service with invalid device
        mobile_service = MobileFaceService(None, temp_db_path)

        sync_status = mobile_service.get_device_sync_status("nonexistent_device")
        assert sync_status.device_id == "nonexistent_device", "Should handle missing device gracefully"
        assert sync_status.sync_token == "", "Should have empty sync token"

        # Test onboarding with invalid user
        onboarding_service = FaceOnboardingService(temp_db_path)

        try:
            onboarding_service.start_onboarding("nonexistent_user")
            assert False, "Should raise error for nonexistent user"
        except ValueError:
            pass  # Expected error

        print("✅ Error Handling and Resilience - PASSED")

    def test_data_consistency_and_integrity(self, temp_db_path):
        """Test data consistency and integrity across all components"""
        print("\n=== Testing Data Consistency and Integrity ===")

        # Test database schema consistency
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()

            # Check that all required tables exist after component initialization
            privacy_manager = PrivacyControlsManager(temp_db_path, privacy_db_path=temp_db_path)
            mobile_service = MobileFaceService(None, temp_db_path)
            onboarding_service = FaceOnboardingService(temp_db_path)

            # Verify privacy tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%consent%'")
            privacy_tables = cursor.fetchall()
            assert len(privacy_tables) > 0, "Should have privacy-related tables"

            # Verify mobile tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%mobile%'")
            mobile_tables = cursor.fetchall()
            assert len(mobile_tables) > 0, "Should have mobile-related tables"

            # Verify onboarding tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%onboarding%'")
            onboarding_tables = cursor.fetchall()
            assert len(onboarding_tables) > 0, "Should have onboarding-related tables"

        # Test cross-component data consistency
        user_id = "consistency_test_user"

        # Create data in multiple components
        privacy_manager.request_consent(
            user_id=user_id, consent_type=ConsentType.FACE_RECOGNITION, purpose="Consistency test"
        )

        mobile_service.register_mobile_device(
            device_id="consistency_device", device_name="Consistency Test Device", device_type="test", user_id=user_id
        )

        onboarding_flow = onboarding_service.create_onboarding_flow(user_id)

        # Verify data consistency across components
        privacy_dashboard = privacy_manager.get_privacy_dashboard(user_id)
        assert len(privacy_dashboard["consents"]) > 0, "Should have consent records"

        device_status = mobile_service.get_device_sync_status("consistency_device")
        assert device_status.device_id == "consistency_device", "Should maintain device consistency"

        onboarding_status = onboarding_service.get_onboarding_status(user_id)
        assert onboarding_status["flow_id"] == onboarding_flow.flow_id, "Should maintain onboarding consistency"

        print("✅ Data Consistency and Integrity - PASSED")


def run_comprehensive_tests():
    """Run all comprehensive integration tests"""
    print("🚀 Starting Comprehensive Face Recognition System Integration Tests")
    print("=" * 80)

    # Create test instance
    test_instance = TestFaceSystemIntegration()

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db_path = tmp.name

    try:
        # Generate test data
        sample_embeddings = test_instance.sample_embeddings()
        sample_face_data = test_instance.sample_face_data()

        # Run all test phases
        test_instance.test_phase_1_faiss_performance_foundation(temp_db_path, sample_embeddings)
        test_instance.test_phase_2_advanced_intelligence_features(temp_db_path, sample_face_data)
        test_instance.test_phase_3_analytics_and_smart_organization(temp_db_path, sample_face_data)
        test_instance.test_phase_4_enhanced_search_and_nlp(temp_db_path)
        test_instance.test_phase_5_enhanced_video_processing(temp_db_path)
        test_instance.test_phase_6_privacy_and_security(temp_db_path)
        test_instance.test_phase_7_model_management(temp_db_path)
        test_instance.test_phase_8_mobile_and_cross_platform(temp_db_path)
        test_instance.test_phase_9_user_experience_enhancements(temp_db_path)

        # Run integration tests
        test_instance.test_end_to_end_integration(temp_db_path, sample_face_data)
        test_instance.test_performance_and_scalability(temp_db_path)
        test_instance.test_error_handling_and_resilience(temp_db_path)
        test_instance.test_data_consistency_and_integrity(temp_db_path)

        print("\n" + "=" * 80)
        print("🎉 ALL TESTS PASSED! Face Recognition System Integration Complete")
        print("=" * 80)

        # Print summary
        print("\n📊 Test Summary:")
        print("✅ Phase 1: FAISS Performance Foundation")
        print("✅ Phase 2: Advanced Intelligence Features")
        print("✅ Phase 3: Analytics and Smart Organization")
        print("✅ Phase 4: Enhanced Search and NLP")
        print("✅ Phase 5: Enhanced Video Processing")
        print("✅ Phase 6: Privacy and Security Framework")
        print("✅ Phase 7: Model Management and Versioning")
        print("✅ Phase 8: Mobile and Cross-Platform Features")
        print("✅ Phase 9: User Experience Enhancements")
        print("✅ End-to-End Integration")
        print("✅ Performance and Scalability")
        print("✅ Error Handling and Resilience")
        print("✅ Data Consistency and Integrity")

        print("\n🏆 Total: 13/13 test suites passed")
        print("🚀 Face Recognition System is ready for production!")

        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Cleanup
        Path(temp_db_path).unlink(missing_ok=True)


if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit(0 if success else 1)
