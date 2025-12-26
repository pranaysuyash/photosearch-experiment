#!/usr/bin/env python3
"""
Test script for pricing functionality
"""

import sys
import os

# Add the server directory to the path so we can import the pricing module
sys.path.append(os.path.join(os.path.dirname(__file__), "server"))

from pricing import pricing_manager


def test_pricing_tiers():
    """Test that pricing tiers are loaded correctly."""
    print("Testing pricing tiers...")

    tiers = pricing_manager.get_all_tiers()
    print(f"✓ Found {len(tiers)} pricing tiers")

    for tier in tiers:
        print(f"  - {tier.name}: ${tier.price_monthly}/month, {tier.image_limit} images")

    # Test specific tier retrieval
    free_tier = pricing_manager.get_tier("free")
    assert free_tier is not None, "Free tier should exist"
    assert free_tier.image_limit == 5000, "Free tier should have 5000 image limit"
    print("✓ Free tier retrieval works")

    pro_tier = pricing_manager.get_tier("pro")
    assert pro_tier is not None, "Pro tier should exist"
    assert pro_tier.image_limit == 100000, "Pro tier should have 100000 image limit"
    print("✓ Pro tier retrieval works")

    # Test non-existent tier
    none_tier = pricing_manager.get_tier("nonexistent")
    assert none_tier is None, "Non-existent tier should return None"
    print("✓ Non-existent tier handling works")


def test_tier_recommendation():
    """Test tier recommendation based on image count."""
    print("\nTesting tier recommendations...")

    # Test small collection - should recommend free tier
    small_tier = pricing_manager.get_tier_by_image_count(1000)
    assert small_tier.name == "Free", "1000 images should recommend Free tier"
    print("✓ 1000 images → Free tier")

    # Test medium collection - should recommend basic tier
    medium_tier = pricing_manager.get_tier_by_image_count(10000)
    assert medium_tier.name == "Basic", "10000 images should recommend Basic tier"
    print("✓ 10000 images → Basic tier")

    # Test large collection - should recommend pro tier
    large_tier = pricing_manager.get_tier_by_image_count(50000)
    assert large_tier.name == "Pro", "50000 images should recommend Pro tier"
    print("✓ 50000 images → Pro tier")

    # Test very large collection - should recommend enterprise tier
    huge_tier = pricing_manager.get_tier_by_image_count(200000)
    assert huge_tier.name == "Enterprise", "200000 images should recommend Enterprise tier"
    print("✓ 200000 images → Enterprise tier")


def test_usage_tracking():
    """Test usage tracking functionality."""
    print("\nTesting usage tracking...")

    user_id = "test_user_1"

    # Test initial usage tracking
    stats = pricing_manager.track_usage(user_id, 1000)
    assert stats.current_tier == "free", "New user should start with free tier"
    assert stats.image_count == 1000, "Image count should be tracked correctly"
    assert stats.image_limit == 5000, "Free tier limit should be 5000"
    print("✓ Initial usage tracking works")

    # Test usage percentage calculation
    usage_pct = stats.usage_percentage
    expected_pct = (1000 / 5000) * 100
    assert abs(usage_pct - expected_pct) < 0.01, f"Usage percentage should be {expected_pct}%, got {usage_pct}%"
    print(f"✓ Usage percentage calculation works: {usage_pct:.1f}%")

    # Test limit checking
    can_add = pricing_manager.check_limit(user_id, 3000)
    assert can_add, "Should be able to add 3000 more images (total 4000 < 5000 limit)"
    print("✓ Limit checking works for allowed addition")

    can_add_too_much = pricing_manager.check_limit(user_id, 5000)
    assert not can_add_too_much, "Should not be able to add 5000 more images (total 6000 > 5000 limit)"
    print("✓ Limit checking works for denied addition")


def test_tier_upgrades():
    """Test tier upgrade functionality."""
    print("\nTesting tier upgrades...")

    user_id = "test_user_2"

    # Start with free tier
    pricing_manager.track_usage(user_id, 1000)

    # Upgrade to basic tier
    success = pricing_manager.upgrade_tier(user_id, "basic")
    assert success, "Upgrade to basic tier should succeed"
    print("✓ Upgrade to Basic tier works")

    # Verify the upgrade took effect
    stats = pricing_manager.track_usage(user_id, 1000)
    assert stats.current_tier == "basic", "User should now be on basic tier"
    assert stats.image_limit == 25000, "Basic tier limit should be 25000"
    print("✓ Tier upgrade reflected in usage stats")

    # Test invalid tier upgrade
    invalid_success = pricing_manager.upgrade_tier(user_id, "invalid_tier")
    assert not invalid_success, "Upgrade to invalid tier should fail"
    print("✓ Invalid tier upgrade handling works")


def main():
    """Run all pricing tests."""
    print("=" * 60)
    print("PRICING FUNCTIONALITY TESTS")
    print("=" * 60)

    try:
        test_pricing_tiers()
        test_tier_recommendation()
        test_usage_tracking()
        test_tier_upgrades()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
