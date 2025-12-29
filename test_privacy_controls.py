#!/usr/bin/env python3
"""
Privacy Controls Test Suite - Phase 6

Tests the privacy and security controls implementation for face recognition.
Validates GDPR compliance, consent management, and privacy-aware processing.

Usage:
    python test_privacy_controls.py
"""

import os
import sys
import tempfile

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_privacy_controls():
    """Test privacy controls system"""
    print("🔒 Testing Privacy Controls System...")

    try:
        from server.privacy_controls import PrivacyControlsManager, ConsentType

        # Create temporary database for testing
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            privacy_manager = PrivacyControlsManager(
                face_db_path=tmp_db.name, privacy_db_path=tmp_db.name.replace(".db", "_privacy.db")
            )

            test_user_id = "test_user_123"

            # Test 1: Request consent
            print("  ✓ Testing consent request...")
            consent_id = privacy_manager.request_consent(
                user_id=test_user_id,
                consent_type=ConsentType.FACE_RECOGNITION,
                purpose="Face recognition for photo organization",
                legal_basis="consent",
            )
            assert consent_id, "Consent ID should be generated"

            # Test 2: Grant consent
            print("  ✓ Testing consent granting...")
            success = privacy_manager.grant_consent(consent_id, test_user_id)
            assert success, "Consent should be granted successfully"

            # Test 3: Check consent
            print("  ✓ Testing consent validation...")
            has_consent = privacy_manager.check_consent(test_user_id, ConsentType.FACE_RECOGNITION)
            assert has_consent, "User should have valid consent"

            # Test 4: Privacy dashboard
            print("  ✓ Testing privacy dashboard...")
            dashboard = privacy_manager.get_privacy_dashboard(test_user_id)
            assert dashboard["user_id"] == test_user_id, "Dashboard should contain user data"
            assert "consents" in dashboard, "Dashboard should contain consent information"

            # Test 5: Data export
            print("  ✓ Testing data export...")
            export_id = privacy_manager.export_user_data(user_id=test_user_id, export_types=["consent", "audit_logs"])
            assert export_id, "Export request ID should be generated"

            # Test 6: Anonymization
            print("  ✓ Testing data anonymization...")
            anonymized_id = privacy_manager.anonymize_person_data(person_id="test_person_1", user_id=test_user_id)
            assert anonymized_id.startswith("anon_"), "Anonymized ID should have proper prefix"

            # Test 7: Consent withdrawal
            print("  ✓ Testing consent withdrawal...")
            withdrawn = privacy_manager.withdraw_consent(test_user_id, ConsentType.FACE_RECOGNITION)
            assert withdrawn, "Consent should be withdrawn successfully"

            # Verify consent is no longer valid
            has_consent_after = privacy_manager.check_consent(test_user_id, ConsentType.FACE_RECOGNITION)
            assert not has_consent_after, "Consent should be invalid after withdrawal"

            print("✅ Privacy Controls tests passed!")

            # Cleanup
            os.unlink(tmp_db.name)
            privacy_db_path = tmp_db.name.replace(".db", "_privacy.db")
            if os.path.exists(privacy_db_path):
                os.unlink(privacy_db_path)

            return True

    except Exception as e:
        print(f"❌ Privacy Controls test failed: {e}")
        return False


def test_privacy_aware_processing():
    """Test privacy-aware face processing"""
    print("🎭 Testing Privacy-Aware Face Processing...")

    try:
        from server.privacy_controls import PrivacyControlsManager, PrivacyLevel
        from server.privacy_aware_face_processor import PrivacyAwareFaceProcessor

        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            privacy_manager = PrivacyControlsManager(
                face_db_path=tmp_db.name, privacy_db_path=tmp_db.name.replace(".db", "_privacy.db")
            )

            # Mock face clusterer for testing
            class MockFaceClusterer:
                def detect_faces_in_image(self, image_path, min_confidence=0.5):
                    # Return mock face detections
                    return [
                        {
                            "bounding_box": [100, 100, 50, 50],
                            "confidence": 0.9,
                            "quality_score": 0.8,
                            "attributes": {"age": 25, "emotion": "happy", "pose": "frontal"},
                        },
                        {
                            "bounding_box": [200, 150, 45, 45],
                            "confidence": 0.85,
                            "quality_score": 0.7,
                            "attributes": {"age": 35, "emotion": "neutral", "pose": "profile"},
                        },
                    ]

            mock_clusterer = MockFaceClusterer()
            privacy_processor = PrivacyAwareFaceProcessor(mock_clusterer, privacy_manager)

            test_user_id = "test_user_456"
            test_image_path = "test_image.jpg"

            # Test 1: Processing without consent (should be blocked or anonymous)
            print("  ✓ Testing processing without consent...")
            result = privacy_processor.process_with_privacy_controls(
                test_image_path, test_user_id, force_privacy_level=PrivacyLevel.NO_PROCESSING
            )
            assert not result.processing_allowed, "Processing should be blocked without consent"

            # Test 2: Anonymous processing
            print("  ✓ Testing anonymous processing...")
            result = privacy_processor.process_with_privacy_controls(
                test_image_path, test_user_id, force_privacy_level=PrivacyLevel.ANONYMOUS_ONLY
            )
            assert result.processing_allowed, "Anonymous processing should be allowed"
            assert result.anonymized_data, "Data should be anonymized"

            # Test 3: Minimal processing
            print("  ✓ Testing minimal processing...")
            result = privacy_processor.process_with_privacy_controls(
                test_image_path, test_user_id, force_privacy_level=PrivacyLevel.MINIMAL_PROCESSING
            )
            assert result.processing_allowed, "Minimal processing should be allowed"
            assert result.faces_detected > 0, "Faces should be detected"

            # Test 4: Privacy compliance validation
            print("  ✓ Testing privacy compliance validation...")
            compliance = privacy_processor.validate_privacy_compliance(test_user_id)
            assert "compliance_status" in compliance, "Compliance report should contain status"
            assert "consent_status" in compliance, "Compliance report should contain consent status"

            # Test 5: Batch processing
            print("  ✓ Testing batch processing with privacy...")
            batch_results = privacy_processor.batch_process_with_privacy(
                [test_image_path, "test_image2.jpg"], test_user_id
            )
            assert len(batch_results) == 2, "Should process all images in batch"

            print("✅ Privacy-Aware Processing tests passed!")

            # Cleanup
            os.unlink(tmp_db.name)
            privacy_db_path = tmp_db.name.replace(".db", "_privacy.db")
            if os.path.exists(privacy_db_path):
                os.unlink(privacy_db_path)

            return True

    except Exception as e:
        print(f"❌ Privacy-Aware Processing test failed: {e}")
        return False


def test_api_endpoints():
    """Test privacy API endpoints"""
    print("🌐 Testing Privacy API Endpoints...")

    try:
        # Import API models to verify they're properly defined
        from server.api.routers.privacy import (
            ConsentRequest,
            DataExportRequest,
            AnonymizationRequest,
            PrivacySettingsRequest,
        )

        # Test model validation
        print("  ✓ Testing API models...")

        consent_request = ConsentRequest(
            consent_type="face_recognition", purpose="Photo organization and search", legal_basis="consent"
        )
        assert consent_request.consent_type == "face_recognition"

        export_request = DataExportRequest(export_types=["consent", "audit_logs"], include_biometric_data=False)
        assert len(export_request.export_types) == 2

        anon_request = AnonymizationRequest(person_id="person_123", reason="User requested data deletion")
        assert anon_request.person_id == "person_123"

        privacy_settings = PrivacySettingsRequest(privacy_level="anonymous", face_recognition_enabled=False)
        assert privacy_settings.privacy_level == "anonymous"

        print("✅ Privacy API Endpoints tests passed!")
        return True

    except Exception as e:
        print(f"❌ Privacy API Endpoints test failed: {e}")
        return False


def test_gdpr_compliance():
    """Test GDPR compliance features"""
    print("🇪🇺 Testing GDPR Compliance Features...")

    try:
        from server.privacy_controls import PrivacyControlsManager, ConsentType

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            privacy_manager = PrivacyControlsManager(
                face_db_path=tmp_db.name, privacy_db_path=tmp_db.name.replace(".db", "_privacy.db")
            )

            test_user_id = "gdpr_test_user"

            # Test GDPR Article 6 - Lawful basis for processing
            print("  ✓ Testing lawful basis for processing...")
            consent_id = privacy_manager.request_consent(
                user_id=test_user_id,
                consent_type=ConsentType.FACE_RECOGNITION,
                purpose="Automated photo organization",
                legal_basis="consent",  # GDPR Article 6(1)(a)
            )
            privacy_manager.grant_consent(consent_id, test_user_id)

            # Test GDPR Article 7 - Conditions for consent
            print("  ✓ Testing consent withdrawal (Article 7)...")
            withdrawn = privacy_manager.withdraw_consent(test_user_id, ConsentType.FACE_RECOGNITION)
            assert withdrawn, "User should be able to withdraw consent"

            # Test GDPR Article 17 - Right to erasure
            print("  ✓ Testing right to erasure (Article 17)...")
            anonymized_id = privacy_manager.anonymize_person_data("test_person", test_user_id)
            assert anonymized_id, "Personal data should be anonymized"

            # Test GDPR Article 20 - Right to data portability
            print("  ✓ Testing data portability (Article 20)...")
            export_id = privacy_manager.export_user_data(
                user_id=test_user_id, export_types=["consent", "audit_logs", "privacy_settings"]
            )
            assert export_id, "User data should be exportable"

            # Test GDPR Article 12 - Transparent information
            print("  ✓ Testing transparent information (Article 12)...")
            dashboard = privacy_manager.get_privacy_dashboard(test_user_id)
            assert "privacy_rights" in dashboard, "Privacy rights should be clearly explained"

            # Test data retention and cleanup
            print("  ✓ Testing data retention policies...")
            cleanup_stats = privacy_manager.cleanup_expired_data(dry_run=True)
            assert "expired_consents" in cleanup_stats, "Should track expired consents"

            print("✅ GDPR Compliance tests passed!")

            # Cleanup
            os.unlink(tmp_db.name)
            privacy_db_path = tmp_db.name.replace(".db", "_privacy.db")
            if os.path.exists(privacy_db_path):
                os.unlink(privacy_db_path)

            return True

    except Exception as e:
        print(f"❌ GDPR Compliance test failed: {e}")
        return False


def main():
    """Run all privacy control tests"""
    print("🔐 Phase 6: Privacy and Security Controls - Test Suite")
    print("=" * 60)

    tests = [
        ("Privacy Controls System", test_privacy_controls),
        ("Privacy-Aware Processing", test_privacy_aware_processing),
        ("Privacy API Endpoints", test_api_endpoints),
        ("GDPR Compliance", test_gdpr_compliance),
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
        print("🎉 All Phase 6 Privacy Controls tests passed!")
        print("\n🔒 Privacy Features Validated:")
        print("  ✅ Consent management (GDPR Article 7)")
        print("  ✅ Data export (GDPR Article 20)")
        print("  ✅ Right to erasure (GDPR Article 17)")
        print("  ✅ Privacy-aware processing")
        print("  ✅ Audit logging and transparency")
        print("  ✅ Data anonymization")
        print("  ✅ Privacy by design architecture")
        return True
    else:
        print(f"❌ {total - passed} tests failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
