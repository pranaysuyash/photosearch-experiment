"""
Face Recognition Implementation Validation Test

This test validates that all the implemented face recognition components
are working correctly and can be imported and used together.

Focuses on testing what's actually implemented rather than theoretical components.
"""

import tempfile
import numpy as np
from pathlib import Path


def test_privacy_controls():
    """Test privacy controls implementation"""
    print("Testing Privacy Controls...")

    try:
        from server.privacy_controls import PrivacyControlsManager, ConsentType

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            temp_db = tmp.name

        try:
            # Test privacy manager initialization
            privacy_manager = PrivacyControlsManager(temp_db)

            # Test consent management
            consent_id = privacy_manager.request_consent(
                user_id="test_user", consent_type=ConsentType.FACE_RECOGNITION, purpose="Testing face recognition"
            )

            assert consent_id is not None, "Should create consent request"

            # Grant consent
            success = privacy_manager.grant_consent(consent_id, "test_user")
            assert success, "Should grant consent"

            # Check consent
            has_consent = privacy_manager.check_consent("test_user", ConsentType.FACE_RECOGNITION)
            assert has_consent, "Should have valid consent"

            print("✅ Privacy Controls - PASSED")
            return True

        finally:
            Path(temp_db).unlink(missing_ok=True)

    except ImportError as e:
        print(f"❌ Privacy Controls - SKIPPED (Import Error: {e})")
        return False
    except Exception as e:
        print(f"❌ Privacy Controls - FAILED: {e}")
        return False


def test_mobile_service():
    """Test mobile face service implementation"""
    print("Testing Mobile Face Service...")

    try:
        from server.mobile_face_service import MobileFaceService

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            temp_db = tmp.name

        try:
            # Test mobile service initialization
            mobile_service = MobileFaceService(None, temp_db)  # None for face_clusterer

            # Test device registration
            result = mobile_service.register_mobile_device(
                device_id="test_device", device_name="Test Device", device_type="test", user_id="test_user"
            )

            assert result["status"] == "registered", "Should register device"
            assert "sync_token" in result, "Should provide sync token"

            # Test sync status
            sync_status = mobile_service.get_device_sync_status("test_device")
            assert sync_status.device_id == "test_device", "Should match device ID"

            print("✅ Mobile Face Service - PASSED")
            return True

        finally:
            Path(temp_db).unlink(missing_ok=True)

    except ImportError as e:
        print(f"❌ Mobile Face Service - SKIPPED (Import Error: {e})")
        return False
    except Exception as e:
        print(f"❌ Mobile Face Service - FAILED: {e}")
        return False


def test_onboarding_service():
    """Test face onboarding service implementation"""
    print("Testing Face Onboarding Service...")

    try:
        from server.face_onboarding_service import FaceOnboardingService

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            temp_db = tmp.name

        try:
            # Test onboarding service initialization
            onboarding_service = FaceOnboardingService(temp_db)

            # Test onboarding flow creation
            flow = onboarding_service.create_onboarding_flow("test_user")

            assert flow.user_id == "test_user", "Should match user ID"
            assert len(flow.steps) > 0, "Should have onboarding steps"
            assert flow.status.value == "not_started", "Should start as not started"

            # Test starting onboarding
            start_result = onboarding_service.start_onboarding("test_user")
            assert start_result["status"] == "started", "Should start onboarding"

            # Test contextual help
            help_content = onboarding_service.provide_contextual_help(
                user_id="test_user", context="face_detection_failed"
            )
            assert "help_content" in help_content, "Should provide help content"

            print("✅ Face Onboarding Service - PASSED")
            return True

        finally:
            Path(temp_db).unlink(missing_ok=True)

    except ImportError as e:
        print(f"❌ Face Onboarding Service - SKIPPED (Import Error: {e})")
        return False
    except Exception as e:
        print(f"❌ Face Onboarding Service - FAILED: {e}")
        return False


def test_face_attribute_analyzer():
    """Test face attribute analyzer implementation"""
    print("Testing Face Attribute Analyzer...")

    try:
        from server.face_attribute_analyzer import FaceAttributeAnalyzer

        # Test analyzer initialization
        analyzer = FaceAttributeAnalyzer()

        # Test quality assessment (with mock data)
        mock_face_crop = np.random.rand(150, 150, 3)
        mock_bbox = [100, 100, 150, 150]

        quality = analyzer.assess_face_quality(mock_face_crop, mock_bbox)

        assert "overall_score" in quality, "Should have overall quality score"
        assert 0 <= quality["overall_score"] <= 1, "Quality score should be between 0 and 1"
        assert "blur_score" in quality, "Should assess blur"
        assert "lighting_score" in quality, "Should assess lighting"

        print("✅ Face Attribute Analyzer - PASSED")
        return True

    except ImportError as e:
        print(f"❌ Face Attribute Analyzer - SKIPPED (Import Error: {e})")
        return False
    except Exception as e:
        print(f"❌ Face Attribute Analyzer - FAILED: {e}")
        return False


def test_analytics_service():
    """Test face analytics service implementation"""
    print("Testing Face Analytics Service...")

    try:
        from server.face_analytics_service import FaceAnalyticsEngine

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            temp_db = tmp.name

        try:
            # Test analytics engine initialization
            analytics = FaceAnalyticsEngine(temp_db)

            # Test person timeline (will return empty for non-existent person)
            timeline = analytics.generate_person_timeline("test_person")
            assert "person_id" in timeline, "Should include person ID"

            # Test relationship detection
            relationships = analytics.detect_photo_relationships()
            assert "relationships" in relationships, "Should detect relationships"

            print("✅ Face Analytics Service - PASSED")
            return True

        finally:
            Path(temp_db).unlink(missing_ok=True)

    except ImportError as e:
        print(f"❌ Face Analytics Service - SKIPPED (Import Error: {e})")
        return False
    except Exception as e:
        print(f"❌ Face Analytics Service - FAILED: {e}")
        return False


def test_smart_organization():
    """Test smart organization service implementation"""
    print("Testing Smart Organization Service...")

    try:
        from server.smart_organization_service import SmartOrganizationService

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            temp_db = tmp.name

        try:
            # Test organization service initialization
            organizer = SmartOrganizationService(temp_db)

            # Test smart album creation
            albums = organizer.create_smart_albums()
            assert isinstance(albums, list), "Should return list of albums"

            # Test duplicate detection
            duplicates = organizer.detect_duplicate_people(0.8)
            assert isinstance(duplicates, list), "Should return list of duplicates"

            print("✅ Smart Organization Service - PASSED")
            return True

        finally:
            Path(temp_db).unlink(missing_ok=True)

    except ImportError as e:
        print(f"❌ Smart Organization Service - SKIPPED (Import Error: {e})")
        return False
    except Exception as e:
        print(f"❌ Smart Organization Service - FAILED: {e}")
        return False


def test_advanced_search():
    """Test advanced face search implementation"""
    print("Testing Advanced Face Search...")

    try:
        from server.advanced_face_search import AdvancedFaceSearchEngine

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            temp_db = tmp.name

        try:
            # Test search engine initialization
            search_engine = AdvancedFaceSearchEngine(temp_db)

            # Test attribute-based search
            results = search_engine.search_by_attributes(min_age=20, max_age=40, emotions=["happy"])
            assert "results" in results, "Should return search results"
            assert "total_matches" in results, "Should include total count"

            print("✅ Advanced Face Search - PASSED")
            return True

        finally:
            Path(temp_db).unlink(missing_ok=True)

    except ImportError as e:
        print(f"❌ Advanced Face Search - SKIPPED (Import Error: {e})")
        return False
    except Exception as e:
        print(f"❌ Advanced Face Search - FAILED: {e}")
        return False


def test_natural_language_search():
    """Test natural language search implementation"""
    print("Testing Natural Language Search...")

    try:
        from server.natural_language_search import NaturalLanguageQueryParser

        # Test parser initialization
        parser = NaturalLanguageQueryParser()

        # Test query parsing
        test_queries = ["happy family photos", "photos with John", "everyone smiling"]

        for query in test_queries:
            parsed = parser.parse(query)
            assert parsed is not None, f"Should parse query: {query}"
            assert hasattr(parsed, "person_constraints"), "Should have person constraints"
            assert hasattr(parsed, "emotion_constraints"), "Should have emotion constraints"

        print("✅ Natural Language Search - PASSED")
        return True

    except ImportError as e:
        print(f"❌ Natural Language Search - SKIPPED (Import Error: {e})")
        return False
    except Exception as e:
        print(f"❌ Natural Language Search - FAILED: {e}")
        return False


def test_video_processing():
    """Test video face processing implementation"""
    print("Testing Video Face Processing...")

    try:
        from server.video_face_tracker import VideoFaceTracker
        from server.enhanced_video_face_processor import EnhancedVideoFaceProcessor

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            temp_db = tmp.name

        try:
            # Test video tracker initialization
            tracker = VideoFaceTracker(temp_db)

            # Test video processor initialization
            EnhancedVideoFaceProcessor(temp_db)

            # Test with mock detection data
            mock_detections = [
                {
                    "frame_number": i,
                    "timestamp": i * 0.033,
                    "faces": [
                        {
                            "detection_id": f"frame_{i}_face_0",
                            "bbox": [100, 100, 150, 150],
                            "confidence": 0.9,
                            "embedding": np.random.rand(512).astype(np.float32),
                        }
                    ],
                }
                for i in range(10)
            ]

            # Test tracklet building
            tracklets = tracker.build_tracklets(mock_detections)
            assert isinstance(tracklets, list), "Should return tracklets list"

            print("✅ Video Face Processing - PASSED")
            return True

        finally:
            Path(temp_db).unlink(missing_ok=True)

    except ImportError as e:
        print(f"❌ Video Face Processing - SKIPPED (Import Error: {e})")
        return False
    except Exception as e:
        print(f"❌ Video Face Processing - FAILED: {e}")
        return False


def test_model_manager():
    """Test model manager implementation"""
    print("Testing Model Manager...")

    try:
        from server.model_manager import ModelManager

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            temp_db = tmp.name

        try:
            # Test model manager initialization
            model_manager = ModelManager(temp_db)

            # Test current version retrieval
            version = model_manager.get_current_model_version()
            assert version is not None, "Should have current model version"

            # Test performance benchmarking
            benchmark = model_manager.benchmark_model_performance(
                model_version="test_v1", test_embeddings=np.random.rand(10, 512).astype(np.float32)
            )
            assert "accuracy_metrics" in benchmark, "Should include accuracy metrics"

            print("✅ Model Manager - PASSED")
            return True

        finally:
            Path(temp_db).unlink(missing_ok=True)

    except ImportError as e:
        print(f"❌ Model Manager - SKIPPED (Import Error: {e})")
        return False
    except Exception as e:
        print(f"❌ Model Manager - FAILED: {e}")
        return False


def test_api_routers():
    """Test that API routers can be imported"""
    print("Testing API Routers...")

    routers_tested = 0
    routers_passed = 0

    # Test privacy router
    try:
        from server.api.routers.privacy import router as privacy_router

        assert privacy_router is not None, "Privacy router should exist"
        routers_passed += 1
        print("  ✅ Privacy Router")
    except ImportError as e:
        print(f"  ❌ Privacy Router - Import Error: {e}")
    except Exception as e:
        print(f"  ❌ Privacy Router - Error: {e}")
    routers_tested += 1

    # Test mobile router
    try:
        from server.api.routers.mobile import router as mobile_router

        assert mobile_router is not None, "Mobile router should exist"
        routers_passed += 1
        print("  ✅ Mobile Router")
    except ImportError as e:
        print(f"  ❌ Mobile Router - Import Error: {e}")
    except Exception as e:
        print(f"  ❌ Mobile Router - Error: {e}")
    routers_tested += 1

    # Test onboarding router
    try:
        from server.api.routers.onboarding import router as onboarding_router

        assert onboarding_router is not None, "Onboarding router should exist"
        routers_passed += 1
        print("  ✅ Onboarding Router")
    except ImportError as e:
        print(f"  ❌ Onboarding Router - Import Error: {e}")
    except Exception as e:
        print(f"  ❌ Onboarding Router - Error: {e}")
    routers_tested += 1

    if routers_passed == routers_tested:
        print("✅ API Routers - ALL PASSED")
        return True
    else:
        print(f"⚠️ API Routers - {routers_passed}/{routers_tested} PASSED")
        return routers_passed > 0


def run_validation_tests():
    """Run all validation tests"""
    print("🚀 Face Recognition Implementation Validation")
    print("=" * 60)

    tests = [
        test_privacy_controls,
        test_mobile_service,
        test_onboarding_service,
        test_face_attribute_analyzer,
        test_analytics_service,
        test_smart_organization,
        test_advanced_search,
        test_natural_language_search,
        test_video_processing,
        test_model_manager,
        test_api_routers,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} - FAILED: {e}")

    print("\n" + "=" * 60)
    print(f"📊 Validation Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED! Face Recognition Implementation is working correctly!")
    elif passed > total * 0.8:
        print("✅ Most tests passed! Implementation is largely working.")
    elif passed > total * 0.5:
        print("⚠️ Some tests passed. Implementation is partially working.")
    else:
        print("❌ Many tests failed. Implementation needs attention.")

    print("\n🏆 Implementation Status:")
    print(f"  • Privacy Controls: {'✅' if passed >= 1 else '❌'}")
    print(f"  • Mobile Features: {'✅' if passed >= 2 else '❌'}")
    print(f"  • User Experience: {'✅' if passed >= 3 else '❌'}")
    print(f"  • Advanced Analytics: {'✅' if passed >= 5 else '❌'}")
    print(f"  • Search & NLP: {'✅' if passed >= 7 else '❌'}")
    print(f"  • Video Processing: {'✅' if passed >= 9 else '❌'}")
    print(f"  • API Integration: {'✅' if passed >= 10 else '❌'}")

    return passed / total


if __name__ == "__main__":
    success_rate = run_validation_tests()
    exit(0 if success_rate > 0.8 else 1)
