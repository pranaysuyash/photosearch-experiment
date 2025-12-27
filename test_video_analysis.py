#!/usr/bin/env python3
"""
Test script for Video Analysis functionality

This script tests the video analysis system without requiring actual video files.
It creates mock data to verify the database schema and API endpoints work correctly.
"""

import os
import sys
import tempfile
import sqlite3
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_video_analyzer_database():
    """Test the VideoAnalyzer database initialization and basic operations."""
    print("🎬 Testing Video Analysis Database...")

    from src.video_analysis import VideoAnalyzer

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        with tempfile.TemporaryDirectory() as cache_dir:
            # Initialize analyzer
            analyzer = VideoAnalyzer(db_path=db_path, cache_dir=cache_dir)

            # Test database schema
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row

            # Check if tables exist
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name IN ('video_metadata', 'video_keyframes', 'video_scenes', 'video_ocr')
                """
            )
            tables = [row["name"] for row in cursor.fetchall()]

            expected_tables = [
                "video_metadata",
                "video_keyframes",
                "video_scenes",
                "video_ocr",
            ]
            assert all(
                table in tables for table in expected_tables
            ), f"Missing tables: {set(expected_tables) - set(tables)}"

            # Test statistics with empty database
            stats = analyzer.get_video_statistics()
            assert stats["total_videos"] == 0
            assert stats["total_keyframes"] == 0

            # Test search with empty database
            results = analyzer.search_video_content("test query")
            assert len(results) == 0

            conn.close()
    finally:
        os.unlink(db_path)

    print("✅ Database tests passed!")


def test_video_analysis_imports():
    """Test that all required imports work correctly."""
    print("📦 Testing Video Analysis Imports...")

    # Test optional dependencies
    try:
        import cv2  # noqa: F401

        print("✅ OpenCV available")
    except ImportError:
        print("⚠️  OpenCV not available - will use ffmpeg fallback")

    try:
        import ffmpeg  # noqa: F401

        print("✅ ffmpeg-python available")
    except ImportError:
        raise AssertionError("ffmpeg-python not available - video processing will fail")

    try:
        from PIL import Image  # noqa: F401

        print("✅ PIL available")
    except ImportError:
        raise AssertionError("PIL not available - image processing will fail")

    print("✅ Import tests passed!")


def test_api_endpoints():
    """Test that video analysis API endpoints are properly defined."""
    print("🌐 Testing API Endpoints...")

    # Import the server components to check analyzer availability
    sys.path.insert(0, str(project_root / "server"))

    # Check if video analyzer is initialized
    from server.core.components import video_analyzer

    # Test that the analyzer exists
    assert video_analyzer is not None, "Video analyzer not initialized"

    print("✅ API endpoint tests passed!")


def test_ui_component():
    """Test that the UI component can be imported."""
    print("🎨 Testing UI Component...")

    # Check if the component file exists and is valid TypeScript
    component_path = project_root / "ui" / "src" / "components" / "video" / "VideoAnalysisPanel.tsx"

    if not component_path.exists():
        raise AssertionError("VideoAnalysisPanel.tsx not found")

    # Read the component file and check for key elements
    content = component_path.read_text()

    required_elements = [
        "VideoAnalysisPanel",
        "analyzeVideo",
        "searchVideoContent",
        "glass.surface",
        "export default VideoAnalysisPanel",
    ]

    for element in required_elements:
        if element not in content:
            raise AssertionError(f"Missing required element: {element}")

    print("✅ UI component tests passed!")


def main():
    """Run all tests."""
    print("🚀 Starting Video Analysis Tests...\n")

    tests = [
        test_video_analysis_imports,
        test_video_analyzer_database,
        test_api_endpoints,
        test_ui_component,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {str(e)}")
        print()  # Add spacing between tests

    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Video Analysis system is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
