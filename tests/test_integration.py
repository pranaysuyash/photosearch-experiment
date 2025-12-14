"""
Integration Tests for PhotoSearch

This module provides comprehensive integration tests that verify all
components work together correctly.

Features:
- End-to-end workflow testing
- Component interaction verification
- Performance benchmarking
- Error handling validation
- Data consistency checks

Usage:
    python -m pytest tests/test_integration.py
    
    # Or run specific tests
    python -m pytest tests/test_integration.py::test_hybrid_search_workflow
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import all components
from intent_recognition import IntentDetector
from saved_searches import SavedSearchManager
from job_queue import JobQueue
from face_clustering import FaceClusterer
from ocr_search import OCRSearch
from modal_system import DialogManager
from persistent_job_store import PersistentJobStore
from code_splitting import get_code_splitting_config, LazyLoadMonitor
from tauri_integration import TauriCommandManager

class TestIntegration:
    """Integration tests for PhotoSearch components."""
    
    def setup_method(self):
        """Setup test environment."""
        self.test_dir = tempfile.mkdtemp()
        print(f"Test directory: {self.test_dir}")
        
        # Initialize all components with test databases
        self.intent_detector = IntentDetector()
        self.saved_searches = SavedSearchManager(os.path.join(self.test_dir, 'saved_searches.db'))
        self.job_queue = JobQueue(os.path.join(self.test_dir, 'job_queue.db'))
        self.face_clusterer = FaceClusterer(os.path.join(self.test_dir, 'face_clusters.db'))
        self.ocr_search = OCRSearch(os.path.join(self.test_dir, 'ocr_search.db'))
        self.dialog_manager = DialogManager(os.path.join(self.test_dir, 'dialogs.db'))
        self.persistent_jobs = PersistentJobStore(os.path.join(self.test_dir, 'persistent_jobs.db'))
        self.lazy_monitor = LazyLoadMonitor(os.path.join(self.test_dir, 'lazy_load.json'))
        self.tauri_manager = TauriCommandManager()
    
    def teardown_method(self):
        """Cleanup test environment."""
        # Close all database connections
        self.saved_searches.close()
        self.job_queue.close()
        self.face_clusterer.close()
        self.ocr_search.close()
        self.dialog_manager.close()
        self.persistent_jobs.close()
        
        # Remove test directory
        shutil.rmtree(self.test_dir)
        print(f"Cleaned up test directory: {self.test_dir}")
    
    def test_hybrid_search_workflow(self):
        """Test complete hybrid search workflow with intent detection."""
        print("\n=== Testing Hybrid Search Workflow ===")
        
        # Test intent detection
        query = "Canon camera beach vacation 2023"
        intent_result = self.intent_detector.detect_intent(query)
        
        assert intent_result['primary_intent'] == 'camera'
        assert 'location' in intent_result['secondary_intents']
        assert intent_result['confidence'] > 0.5
        
        print(f"✅ Intent detection: {intent_result['primary_intent']}")
        
        # Test search saving
        search_id = self.saved_searches.save_search(
            query=query,
            mode='hybrid',
            results_count=42,
            intent=intent_result['primary_intent']
        )
        
        assert search_id is not None
        assert isinstance(search_id, int)
        
        print(f"✅ Saved search: {search_id}")
        
        # Test search retrieval
        saved_search = self.saved_searches.get_saved_search_by_id(search_id)
        assert saved_search is not None
        assert saved_search['query'] == query
        assert saved_search['intent'] == 'camera'
        
        print(f"✅ Retrieved search: {saved_search['query']}")
        
        # Test analytics
        analytics = self.saved_searches.get_overall_analytics()
        assert analytics['total_saved_searches'] >= 1
        assert analytics['total_executions'] >= 0
        
        print(f"✅ Analytics: {analytics['total_saved_searches']} searches")
        
        print("✅ Hybrid search workflow completed successfully")
    
    def test_job_queue_workflow(self):
        """Test complete job queue workflow."""
        print("\n=== Testing Job Queue Workflow ===")
        
        # Register a test handler
        def test_handler(job, update_callback):
            update_callback(status='processing', progress=25, message='Starting test job')
            
            # Simulate work
            import time
            time.sleep(0.1)
            
            update_callback(progress=75, message='Processing data')
            time.sleep(0.1)
            
            update_callback(status='completed', progress=100, message='Job completed', 
                          result={'processed': 10, 'success': True})
            
            return {'status': 'success', 'data': 'test result'}
        
        self.job_queue.register_handler('test', test_handler)
        
        # Create a job
        job_id = self.job_queue.add_job(
            job_type='test',
            payload={'test_id': 1, 'data': 'test'},
            priority='high'
        )
        
        assert job_id is not None
        print(f"✅ Created job: {job_id}")
        
        # Start workers
        self.job_queue.start_workers()
        print("✅ Started job workers")
        
        # Wait for job to complete
        import time
        max_wait = 5
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            job = self.job_queue.get_job(job_id)
            if job and job['status'] == 'completed':
                break
            time.sleep(0.5)
        
        # Verify job completion
        job = self.job_queue.get_job(job_id)
        assert job is not None
        assert job['status'] == 'completed'
        assert job['progress'] == 100
        
        print(f"✅ Job completed: {job['status']}")
        
        # Get statistics
        stats = self.job_queue.get_queue_stats()
        assert stats['total_jobs'] >= 1
        assert stats['status_counts']['completed'] >= 1
        
        print(f"✅ Queue stats: {stats['total_jobs']} jobs")
        
        # Stop workers
        self.job_queue.stop_workers()
        print("✅ Stopped job workers")
        
        print("✅ Job queue workflow completed successfully")
    
    def test_face_clustering_workflow(self):
        """Test face clustering workflow (if libraries available)."""
        print("\n=== Testing Face Clustering Workflow ===")
        
        # Check if face libraries are available
        from face_clustering import FACE_LIBRARIES_AVAILABLE
        
        if not FACE_LIBRARIES_AVAILABLE:
            print("⚠️  Face libraries not available, skipping face clustering test")
            print("   Install with: pip install mtcnn facenet-pytorch torch")
            return
        
        # Create test images directory
        test_images_dir = os.path.join(self.test_dir, 'test_images')
        os.makedirs(test_images_dir, exist_ok=True)
        
        # Create a simple test image (we'll use a placeholder since we can't generate real images)
        # In a real test, you would use actual image files
        test_image_path = os.path.join(test_images_dir, 'test.jpg')
        
        # For this test, we'll just verify the clustering methods exist and work
        # without actually processing images
        
        # Test cluster statistics (should be empty initially)
        stats = self.face_clusterer.get_cluster_statistics()
        assert stats['total_faces'] == 0
        assert stats['total_clusters'] == 0
        
        print("✅ Initial cluster statistics verified")
        
        # Test that methods exist and don't crash
        try:
            clusters = self.face_clusterer.get_all_clusters()
            assert clusters['total'] == 0
            print("✅ Get all clusters method works")
            
            clustered_images = self.face_clusterer.get_clustered_images()
            assert clustered_images['total_images'] == 0
            print("✅ Get clustered images method works")
            
        except Exception as e:
            print(f"❌ Face clustering error: {e}")
            raise
        
        print("✅ Face clustering workflow completed successfully")
    
    def test_ocr_workflow(self):
        """Test OCR workflow (if libraries available)."""
        print("\n=== Testing OCR Workflow ===")
        
        # Check if OCR libraries are available
        from ocr_search import OCR_LIBRARIES_AVAILABLE
        
        if not OCR_LIBRARIES_AVAILABLE:
            print("⚠️  OCR libraries not available, skipping OCR test")
            print("   Install with: pip install pytesseract opencv-python pillow numpy")
            print("   And install Tesseract OCR on your system")
            return
        
        # Test OCR statistics (should be empty initially)
        stats = self.ocr_search.get_ocr_summary()
        assert stats['total_images_processed'] == 0
        assert stats['images_with_text'] == 0
        
        print("✅ Initial OCR statistics verified")
        
        # Test that methods exist and don't crash
        try:
            # Test search (should return empty results)
            search_result = self.ocr_search.search_text('test')
            assert search_result['total'] == 0
            print("✅ OCR search method works")
            
        except Exception as e:
            print(f"❌ OCR error: {e}")
            raise
        
        print("✅ OCR workflow completed successfully")
    
    def test_dialog_system_workflow(self):
        """Test complete dialog system workflow."""
        print("\n=== Testing Dialog System Workflow ===")
        
        # Create different types of dialogs
        confirmation_id = self.dialog_manager.create_confirmation_dialog(
            title="Delete Image",
            message="Are you sure you want to delete this image?"
        )
        
        error_id = self.dialog_manager.create_error_dialog(
            title="Operation Failed",
            message="Failed to save changes",
            details="Database connection error"
        )
        
        progress_id = self.dialog_manager.create_progress_dialog(
            title="Processing Images",
            message="Scanning and indexing photos...",
            total_steps=5
        )
        
        input_id = self.dialog_manager.create_input_dialog(
            title="Enter Tag",
            message="Add a tag to this image:",
            input_label="Tag Name"
        )
        
        print(f"✅ Created dialogs: {confirmation_id}, {error_id}, {progress_id}, {input_id}")
        
        # Test dialog retrieval
        confirmation_dialog = self.dialog_manager.get_dialog(confirmation_id)
        assert confirmation_dialog is not None
        assert confirmation_dialog['dialog_type'] == 'confirmation'
        assert confirmation_dialog['title'] == 'Delete Image'
        
        print("✅ Dialog retrieval works")
        
        # Test active dialogs
        active_dialogs = self.dialog_manager.get_active_dialogs()
        assert len(active_dialogs) >= 4
        
        print(f"✅ Active dialogs: {len(active_dialogs)}")
        
        # Test dialog actions
        self.dialog_manager.record_dialog_action(confirmation_id, 'confirm', {'image_id': '123'})
        self.dialog_manager.close_dialog(confirmation_id, 'confirm')
        
        closed_dialog = self.dialog_manager.get_dialog(confirmation_id)
        assert closed_dialog is not None
        assert closed_dialog['is_open'] == False
        
        print("✅ Dialog actions work")
        
        # Test progress dialog updates
        self.dialog_manager.update_progress_dialog(
            progress_id,
            progress=50,
            status='processing',
            message='Halfway through scanning...'
        )
        
        updated_progress = self.dialog_manager.get_dialog(progress_id)
        assert updated_progress['state_data']['progress'] == 50
        
        print("✅ Progress updates work")
        
        # Test statistics
        stats = self.dialog_manager.get_dialog_statistics()
        assert stats['total_dialogs'] >= 4
        assert stats['active_dialogs'] >= 3  # One was closed
        
        print(f"✅ Dialog statistics: {stats['total_dialogs']} dialogs")
        
        print("✅ Dialog system workflow completed successfully")
    
    def test_persistent_job_store_workflow(self):
        """Test persistent job store workflow."""
        print("\n=== Testing Persistent Job Store Workflow ===")
        
        # Create jobs with different types and priorities
        scan_job = self.persistent_jobs.create_job(
            job_type='scan',
            payload={'path': '/photos', 'force': False},
            priority='high'
        )
        
        index_job = self.persistent_jobs.create_job(
            job_type='index',
            payload={'files': ['file1.jpg', 'file2.jpg']},
            priority='medium'
        )
        
        export_job = self.persistent_jobs.create_job(
            job_type='export',
            payload={'format': 'zip'},
            priority='low'
        )
        
        print(f"✅ Created jobs: {scan_job}, {index_job}, {export_job}")
        
        # Test job retrieval
        retrieved_job = self.persistent_jobs.get_job(scan_job)
        assert retrieved_job is not None
        assert retrieved_job['job_type'] == 'scan'
        assert retrieved_job['priority'] == 'high'
        
        print("✅ Job retrieval works")
        
        # Test job updates
        self.persistent_jobs.update_job(
            scan_job,
            status='processing',
            progress=50,
            message='Scanning files...'
        )
        
        updated_job = self.persistent_jobs.get_job(scan_job)
        assert updated_job['status'] == 'processing'
        assert updated_job['progress'] == 50
        
        print("✅ Job updates work")
        
        # Test job completion
        self.persistent_jobs.update_job(
            scan_job,
            status='completed',
            progress=100,
            message='Scan completed',
            result={'files_found': 42, 'files_indexed': 42}
        )
        
        completed_job = self.persistent_jobs.get_job(scan_job)
        assert completed_job['status'] == 'completed'
        assert completed_job['progress'] == 100
        
        print("✅ Job completion works")
        
        # Test job statistics
        stats = self.persistent_jobs.get_job_statistics()
        assert stats['total_jobs'] >= 3
        assert stats['status_distribution']['completed'] >= 1
        assert stats['status_distribution']['pending'] >= 2
        
        print(f"✅ Job statistics: {stats['total_jobs']} jobs")
        
        # Test job history
        history = self.persistent_jobs.get_job_history(scan_job)
        assert len(history) >= 2  # Created and completed
        
        print(f"✅ Job history: {len(history)} entries")
        
        print("✅ Persistent job store workflow completed successfully")
    
    def test_code_splitting_configuration(self):
        """Test code splitting configuration."""
        print("\n=== Testing Code Splitting Configuration ===")
        
        # Get configuration
        config = get_code_splitting_config()
        
        assert config['enabled'] == True
        assert 'chunks' in config
        assert len(config['chunks']) > 0
        
        print(f"✅ Code splitting enabled: {config['enabled']}")
        print(f"✅ Configured chunks: {len(config['chunks'])}")
        
        # Test chunk configuration
        main_chunk = config['chunks']['main']
        assert main_chunk['priority'] == 'high'
        assert main_chunk['preload'] == True
        
        search_chunk = config['chunks']['search']
        assert search_chunk['priority'] == 'medium'
        assert search_chunk['lazy'] == True
        
        print("✅ Chunk configurations verified")
        
        # Test performance monitoring
        monitor = self.lazy_monitor
        
        # Record some test loads
        monitor.record_lazy_load('SearchComponent', 150, 'search', True)
        monitor.record_lazy_load('GalleryComponent', 250, 'gallery', True)
        monitor.record_lazy_load('SearchComponent', 120, 'search', True)
        
        # Get performance stats
        stats = monitor.get_performance_stats()
        assert stats['total_components'] >= 2
        assert stats['total_loads'] >= 3
        
        print(f"✅ Performance stats: {stats['total_loads']} loads")
        
        # Get chunk performance
        chunk_stats = monitor.get_chunk_performance()
        assert 'search' in chunk_stats
        assert 'gallery' in chunk_stats
        
        print(f"✅ Chunk performance: {len(chunk_stats)} chunks")
        
        print("✅ Code splitting configuration completed successfully")
    
    def test_tauri_integration(self):
        """Test Tauri integration components."""
        print("\n=== Testing Tauri Integration ===")
        
        # Test command definitions
        commands = self.tauri_manager.get_all_commands()
        assert len(commands) >= 8
        
        print(f"✅ Tauri commands defined: {len(commands)}")
        
        # Test specific command
        scan_command = self.tauri_manager.get_command('scan_directory')
        assert scan_command is not None
        assert 'path' in scan_command['parameters']
        
        print("✅ Scan command verified")
        
        # Test Rust code generation
        rust_code = self.tauri_manager.generate_rust_skeleton()
        assert 'fn scan_directory' in rust_code
        assert 'fn search_photos' in rust_code
        assert 'Builder::default()' in rust_code
        
        print("✅ Rust skeleton code generated")
        
        # Test React hooks generation
        react_code = self.tauri_manager.generate_frontend_hooks()
        assert 'useTauriCommands' in react_code
        assert 'invoke' in react_code
        assert 'scanDirectory' in react_code
        
        print("✅ React hooks generated")
        
        # Test configuration generation
        tauri_config = self.tauri_manager.generate_tauri_config()
        assert '"productName": "PhotoSearch"' in tauri_config
        assert '"devPath": "http://localhost:5173"' in tauri_config
        
        print("✅ Tauri config generated")
        
        # Test integration checklist
        checklist = self.tauri_manager.get_integration_checklist()
        assert len(checklist) >= 10
        
        print(f"✅ Integration checklist: {len(checklist)} steps")
        
        print("✅ Tauri integration completed successfully")
    
    def test_component_interactions(self):
        """Test interactions between different components."""
        print("\n=== Testing Component Interactions ===")
        
        # Test: Intent detection → Saved search
        query = "family vacation beach 2023"
        intent = self.intent_detector.detect_intent(query)
        
        search_id = self.saved_searches.save_search(
            query=query,
            mode='hybrid',
            intent=intent['primary_intent']
        )
        
        # Verify the search was saved with correct intent
        saved_search = self.saved_searches.get_saved_search_by_id(search_id)
        assert saved_search['intent'] == intent['primary_intent']
        
        print("✅ Intent detection → Saved search integration works")
        
        # Test: Job creation → Dialog notification
        job_id = self.job_queue.add_job(
            job_type='scan',
            payload={'path': '/photos'}
        )
        
        # Create a progress dialog for the job
        dialog_id = self.dialog_manager.create_progress_dialog(
            title="Scanning Photos",
            message="Processing your photo library...",
            total_steps=5
        )
        
        # Verify both were created
        job = self.job_queue.get_job(job_id)
        dialog = self.dialog_manager.get_dialog(dialog_id)
        
        assert job is not None
        assert dialog is not None
        
        print("✅ Job creation → Dialog notification integration works")
        
        # Test: OCR extraction → Search enhancement (if OCR available)
        from ocr_search import OCR_LIBRARIES_AVAILABLE
        if OCR_LIBRARIES_AVAILABLE:
            # This would normally extract text and enhance search
            # For test purposes, we'll just verify the components can interact
            ocr_stats = self.ocr_search.get_ocr_summary()
            assert 'total_images_processed' in ocr_stats
            print("✅ OCR → Search enhancement integration verified")
        else:
            print("⚠️  OCR libraries not available, skipping OCR interaction test")
        
        print("✅ Component interactions completed successfully")
    
    def test_error_handling(self):
        """Test error handling across components."""
        print("\n=== Testing Error Handling ===")
        
        # Test invalid intent detection
        try:
            result = self.intent_detector.detect_intent("")
            assert result['primary_intent'] == 'generic'
            print("✅ Empty query handled gracefully")
        except Exception as e:
            print(f"❌ Intent detection error: {e}")
            raise
        
        # Test invalid job retrieval
        try:
            job = self.job_queue.get_job("invalid_job_id")
            assert job is None
            print("✅ Invalid job ID handled gracefully")
        except Exception as e:
            print(f"❌ Job retrieval error: {e}")
            raise
        
        # Test invalid dialog retrieval
        try:
            dialog = self.dialog_manager.get_dialog("invalid_dialog_id")
            assert dialog is None
            print("✅ Invalid dialog ID handled gracefully")
        except Exception as e:
            print(f"❌ Dialog retrieval error: {e}")
            raise
        
        print("✅ Error handling completed successfully")
    
    def test_performance_benchmarks(self):
        """Test performance of key operations."""
        print("\n=== Testing Performance Benchmarks ===")
        
        import time
        
        # Benchmark intent detection
        start_time = time.time()
        for i in range(100):
            self.intent_detector.detect_intent(f"test query {i}")
        intent_time = time.time() - start_time
        
        print(f"✅ Intent detection: {intent_time:.3f}s for 100 queries ({intent_time/100:.3f}s avg)")
        
        # Benchmark job creation
        start_time = time.time()
        for i in range(50):
            self.job_queue.add_job(job_type='test', payload={'test': i})
        job_time = time.time() - start_time
        
        print(f"✅ Job creation: {job_time:.3f}s for 50 jobs ({job_time/50:.3f}s avg)")
        
        # Benchmark dialog creation
        start_time = time.time()
        for i in range(50):
            self.dialog_manager.create_confirmation_dialog(
                title=f"Test {i}",
                message=f"Test message {i}"
            )
        dialog_time = time.time() - start_time
        
        print(f"✅ Dialog creation: {dialog_time:.3f}s for 50 dialogs ({dialog_time/50:.3f}s avg)")
        
        # Benchmark search operations
        start_time = time.time()
        for i in range(20):
            self.saved_searches.get_saved_searches(limit=10)
        search_time = time.time() - start_time
        
        print(f"✅ Search operations: {search_time:.3f}s for 20 queries ({search_time/20:.3f}s avg)")
        
        print("✅ Performance benchmarks completed successfully")


if __name__ == "main__":
    # Run all tests
    test_suite = TestIntegration()
    
    try:
        test_suite.test_hybrid_search_workflow()
        test_suite.test_job_queue_workflow()
        test_suite.test_face_clustering_workflow()
        test_suite.test_ocr_workflow()
        test_suite.test_dialog_system_workflow()
        test_suite.test_persistent_job_store_workflow()
        test_suite.test_code_splitting_configuration()
        test_suite.test_tauri_integration()
        test_suite.test_component_interactions()
        test_suite.test_error_handling()
        test_suite.test_performance_benchmarks()
        
        print("\n" + "="*60)
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        test_suite.teardown_method()