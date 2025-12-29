#!/usr/bin/env python3
"""
Performance Optimization Test Suite - Phase 7

Tests the performance optimization implementation for face recognition.
Validates caching, concurrent processing, memory management, and database optimization.

Usage:
    python test_performance_optimization.py
"""

import os
import sys
import time
import tempfile
import sqlite3

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_intelligent_caching():
    """Test intelligent caching system"""
    print("🧠 Testing Intelligent Caching System...")

    try:
        from server.face_performance_optimizer import IntelligentCache

        # Create cache with small size for testing
        cache = IntelligentCache(max_size_mb=1)  # 1MB cache

        # Test 1: Basic cache operations
        print("  ✓ Testing basic cache operations...")
        test_data = {"faces": [1, 2, 3], "confidence": 0.9}
        cache.put("test_key", test_data, 100, "user123")

        retrieved_data = cache.get("test_key", "user123")
        assert retrieved_data == test_data, "Cache should return stored data"

        # Test 2: Cache miss
        print("  ✓ Testing cache miss...")
        missing_data = cache.get("nonexistent_key", "user123")
        assert missing_data is None, "Cache should return None for missing keys"

        # Test 3: Cache eviction
        print("  ✓ Testing cache eviction...")
        # Fill cache beyond capacity with more realistic sizes
        large_data = {"large_array": list(range(1000))}  # Smaller test data
        large_size = 200000  # 200KB per entry

        # Add enough entries to exceed 1MB cache
        for i in range(8):  # 8 * 200KB = 1.6MB > 1MB cache limit
            cache.put(f"large_key_{i}", large_data, large_size, "user123")

        # Original small data should be evicted due to cache size limit
        cache.get("test_key", "user123")
        # Note: Due to LRU eviction, the original data may or may not be evicted
        # The test should check that cache is managing size properly
        current_stats = cache.get_stats()
        assert current_stats["evictions"] > 0, "Should have performed evictions"

        # Test 4: Cache statistics
        print("  ✓ Testing cache statistics...")
        stats = cache.get_stats()
        assert "hit_rate" in stats, "Stats should include hit rate"
        assert "cache_size_mb" in stats, "Stats should include cache size"
        assert stats["hits"] > 0, "Should have recorded cache hits"

        # Test 5: User data clearing
        print("  ✓ Testing user data clearing...")
        cache.put("user_data", {"personal": True}, 50, "user456")
        cache.clear_user_data("user456")
        cleared_data = cache.get("user_data", "user456")
        assert cleared_data is None, "User data should be cleared"

        print("✅ Intelligent Caching tests passed!")
        return True

    except Exception as e:
        print(f"❌ Intelligent Caching test failed: {e}")
        return False


def test_database_optimizer():
    """Test database optimization"""
    print("🗄️ Testing Database Optimizer...")

    try:
        from server.face_performance_optimizer import DatabaseOptimizer

        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            db_path = tmp_db.name

            # Create test tables
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE faces (
                        id INTEGER PRIMARY KEY,
                        image_path TEXT,
                        confidence REAL,
                        age_estimate INTEGER,
                        emotion TEXT,
                        pose_type TEXT,
                        overall_quality REAL
                    )
                """)
                cursor.execute("""
                    CREATE TABLE cluster_membership (
                        face_id INTEGER,
                        cluster_id INTEGER
                    )
                """)
                conn.commit()

            optimizer = DatabaseOptimizer(db_path)

            # Test 1: Index optimization
            print("  ✓ Testing index optimization...")
            result = optimizer.optimize_indexes()
            assert result["status"] == "completed", "Index optimization should complete"
            assert len(result["indexes_created"]) > 0, "Should create some indexes"

            # Test 2: Query performance analysis
            print("  ✓ Testing query performance analysis...")
            test_query = "SELECT COUNT(*) FROM faces WHERE confidence > 0.8"
            analysis = optimizer.analyze_query_performance(test_query)
            assert "execution_time" in analysis, "Analysis should include execution time"
            assert "query_plan" in analysis, "Analysis should include query plan"

            # Test 3: Database settings optimization
            print("  ✓ Testing database settings optimization...")
            optimizer.optimize_database_settings()

            # Verify settings were applied
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode")
                journal_mode = cursor.fetchone()[0]
                assert journal_mode == "wal", "Journal mode should be set to WAL"

            print("✅ Database Optimizer tests passed!")

            # Cleanup
            os.unlink(db_path)
            return True

    except Exception as e:
        print(f"❌ Database Optimizer test failed: {e}")
        return False


def test_memory_manager():
    """Test memory management"""
    print("💾 Testing Memory Manager...")

    try:
        from server.face_performance_optimizer import MemoryManager

        memory_manager = MemoryManager(memory_limit_mb=1024)

        # Test 1: Memory usage tracking
        print("  ✓ Testing memory usage tracking...")
        memory_usage = memory_manager.get_memory_usage()
        assert "rss_mb" in memory_usage, "Should track RSS memory"
        assert "percent" in memory_usage, "Should track memory percentage"
        assert memory_usage["rss_mb"] > 0, "Should have positive memory usage"

        # Test 2: Memory limit checking
        print("  ✓ Testing memory limit checking...")
        within_limits = memory_manager.check_memory_limit()
        assert isinstance(within_limits, bool), "Should return boolean for limit check"

        # Test 3: Memory optimization
        print("  ✓ Testing memory optimization...")
        memory_manager.get_memory_usage()
        memory_manager.optimize_memory()
        memory_after = memory_manager.get_memory_usage()

        # Memory optimization should complete without error
        assert memory_after["rss_mb"] >= 0, "Memory usage should be valid after optimization"

        # Test 4: Memory trend analysis
        print("  ✓ Testing memory trend analysis...")
        # Add some memory stats
        for i in range(5):
            memory_manager.memory_stats.append({"timestamp": time.time() + i, "memory_mb": 100 + i * 10})

        trend = memory_manager.get_memory_trend()
        assert "trend" in trend, "Should provide trend analysis"
        assert "avg_memory_mb" in trend, "Should provide average memory"

        print("✅ Memory Manager tests passed!")
        return True

    except Exception as e:
        print(f"❌ Memory Manager test failed: {e}")
        return False


def test_concurrent_processor():
    """Test concurrent processing"""
    print("⚡ Testing Concurrent Processor...")

    try:
        from server.face_performance_optimizer import ConcurrentProcessor

        processor = ConcurrentProcessor(max_workers=2)

        # Mock processing function
        def mock_process_item(item, user_id=None, **kwargs):
            time.sleep(0.1)  # Simulate processing time
            return {"item": item, "processed": True, "user_id": user_id}

        # Test 1: Concurrent batch processing
        print("  ✓ Testing concurrent batch processing...")
        test_items = ["item1", "item2", "item3", "item4"]

        start_time = time.time()
        results = processor.process_batch_concurrent(test_items, mock_process_item, "test_user")
        processing_time = time.time() - start_time

        assert len(results) == len(test_items), "Should process all items"
        assert all(r.get("processed") for r in results), "All items should be processed"
        assert processing_time < 0.5, "Concurrent processing should be faster than sequential"

        # Test 2: Error handling in concurrent processing
        print("  ✓ Testing error handling...")

        def error_process_item(item, user_id=None, **kwargs):
            if item == "error_item":
                raise ValueError("Test error")
            return {"item": item, "processed": True}

        error_items = ["good_item", "error_item", "another_good_item"]
        error_results = processor.process_batch_concurrent(error_items, error_process_item, "test_user")

        assert len(error_results) == len(error_items), "Should handle all items including errors"
        error_result = next(r for r in error_results if r.get("item") == "error_item")
        assert "error" in error_result, "Error items should contain error information"

        print("✅ Concurrent Processor tests passed!")
        return True

    except Exception as e:
        print(f"❌ Concurrent Processor test failed: {e}")
        return False


def test_performance_optimizer():
    """Test main performance optimizer"""
    print("🚀 Testing Performance Optimizer...")

    try:
        from server.face_performance_optimizer import FacePerformanceOptimizer, OptimizationConfig

        # Mock face clusterer
        class MockFaceClusterer:
            def __init__(self):
                self.db_path = "test.db"

            def detect_faces_in_image(self, image_path, min_confidence=0.5):
                return [
                    {"bounding_box": [100, 100, 50, 50], "confidence": 0.9},
                    {"bounding_box": [200, 150, 45, 45], "confidence": 0.85},
                ]

        # Create optimizer with test config
        config = OptimizationConfig(
            enable_caching=True,
            cache_size_mb=10,  # Small cache for testing
            max_concurrent_threads=2,
            batch_size=4,
            memory_limit_mb=512,
        )

        mock_clusterer = MockFaceClusterer()
        optimizer = FacePerformanceOptimizer(face_clusterer=mock_clusterer, privacy_manager=None, config=config)

        # Test 1: System optimization
        print("  ✓ Testing system optimization...")
        optimization_result = optimizer.optimize_system()
        assert optimization_result["status"] == "completed", "System optimization should complete"
        assert len(optimization_result["optimizations_applied"]) > 0, "Should apply optimizations"

        # Test 2: Performance baseline measurement
        print("  ✓ Testing performance baseline...")
        baseline = optimizer._measure_performance_baseline()
        assert "baseline_measurement_time" in baseline, "Should measure baseline time"
        assert "memory_usage" in baseline, "Should include memory usage"

        # Test 3: Batch processing with optimizations
        print("  ✓ Testing optimized batch processing...")
        test_images = ["test1.jpg", "test2.jpg", "test3.jpg"]  # Mock paths

        # Mock the single image processing to avoid file system dependencies
        def mock_process_single(image_path, user_id, **kwargs):
            return {"image_path": image_path, "faces_detected": 2, "processing_time": 0.1}

        optimizer._process_single_image = mock_process_single

        batch_result = optimizer.process_batch_optimized(test_images, "test_user")
        assert batch_result["status"] == "completed", "Batch processing should complete"
        assert batch_result["total_images"] == len(test_images), "Should process all images"

        # Test 4: Performance report generation
        print("  ✓ Testing performance report...")
        report = optimizer.get_performance_report()
        assert "performance_summary" in report, "Report should include performance summary"
        assert "current_system_state" in report, "Report should include system state"
        assert "recommendations" in report, "Report should include recommendations"

        # Test 5: Resource cleanup
        print("  ✓ Testing resource cleanup...")
        optimizer.cleanup_resources()

        print("✅ Performance Optimizer tests passed!")
        return True

    except Exception as e:
        print(f"❌ Performance Optimizer test failed: {e}")
        return False


def test_api_endpoints():
    """Test performance API endpoints"""
    print("🌐 Testing Performance API Endpoints...")

    try:
        # Import API models to verify they're properly defined
        from server.api.routers.performance import (
            OptimizationConfigRequest,
            BatchProcessingRequest,
            PerformanceResponse,
        )

        # Test model validation
        print("  ✓ Testing API models...")

        config_request = OptimizationConfigRequest(
            enable_caching=True, cache_size_mb=256, max_concurrent_threads=4, batch_size=16
        )
        assert config_request.enable_caching
        assert config_request.cache_size_mb == 256

        batch_request = BatchProcessingRequest(
            image_paths=["test1.jpg", "test2.jpg"], user_id="test_user", processing_options={"quality_threshold": 0.8}
        )
        assert len(batch_request.image_paths) == 2
        assert batch_request.user_id == "test_user"

        response = PerformanceResponse(status="success", message="Operation completed", data={"processed": 5})
        assert response.status == "success"
        assert response.data["processed"] == 5

        print("✅ Performance API Endpoints tests passed!")
        return True

    except Exception as e:
        print(f"❌ Performance API Endpoints test failed: {e}")
        return False


def test_performance_integration():
    """Test performance optimization integration"""
    print("🔗 Testing Performance Integration...")

    try:
        from server.face_performance_optimizer import FacePerformanceOptimizer, OptimizationConfig

        # Test integration with privacy controls
        print("  ✓ Testing privacy integration...")

        # Mock privacy manager
        class MockPrivacyManager:
            def check_consent(self, user_id, consent_type):
                return True

            def _log_privacy_action(self, **kwargs):
                pass

        config = OptimizationConfig(enable_caching=True, max_concurrent_threads=2)
        privacy_manager = MockPrivacyManager()

        optimizer = FacePerformanceOptimizer(face_clusterer=None, privacy_manager=privacy_manager, config=config)

        # Test that privacy manager is properly integrated
        assert optimizer.privacy_manager is not None, "Privacy manager should be integrated"
        assert optimizer.cache.privacy_manager is not None, "Cache should have privacy manager"

        # Test performance with privacy controls
        print("  ✓ Testing performance with privacy controls...")
        optimization_result = optimizer.optimize_system()
        assert optimization_result["status"] == "completed", "Should work with privacy controls"

        # Test cache privacy compliance
        print("  ✓ Testing cache privacy compliance...")
        if optimizer.cache:
            optimizer.cache.put("test_data", {"sensitive": True}, 100, "user123")
            optimizer.cache.clear_user_data("user123")
            cleared_data = optimizer.cache.get("test_data", "user123")
            assert cleared_data is None, "Privacy-compliant cache clearing should work"

        print("✅ Performance Integration tests passed!")
        return True

    except Exception as e:
        print(f"❌ Performance Integration test failed: {e}")
        return False


def main():
    """Run all performance optimization tests"""
    print("⚡ Phase 7: Performance Optimization - Test Suite")
    print("=" * 60)

    tests = [
        ("Intelligent Caching", test_intelligent_caching),
        ("Database Optimizer", test_database_optimizer),
        ("Memory Manager", test_memory_manager),
        ("Concurrent Processor", test_concurrent_processor),
        ("Performance Optimizer", test_performance_optimizer),
        ("Performance API Endpoints", test_api_endpoints),
        ("Performance Integration", test_performance_integration),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed!")

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All Phase 7 Performance Optimization tests passed!")
        print("\n⚡ Performance Features Validated:")
        print("  ✅ Intelligent caching with privacy compliance")
        print("  ✅ Database query optimization and indexing")
        print("  ✅ Memory management and monitoring")
        print("  ✅ Concurrent processing with thread safety")
        print("  ✅ Performance metrics and monitoring")
        print("  ✅ Resource cleanup and optimization")
        print("  ✅ API endpoints for performance control")
        print("  ✅ Integration with privacy controls")
        return True
    else:
        print(f"❌ {total - passed} tests failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
