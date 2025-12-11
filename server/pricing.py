"""
Pricing Module - Handle pricing tiers, usage tracking, and billing logic

This module provides:
- Pricing tier definitions
- Usage tracking and enforcement
- Billing cycle management
- API endpoints for pricing information
"""

from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime
import os


class PricingTier(BaseModel):
    """Represents a pricing tier with limits and features."""
    name: str
    image_limit: int
    price_monthly: float
    price_yearly: Optional[float] = None
    features: List[str]
    stripe_price_id: Optional[str] = None
    is_popular: bool = False


class UsageStats(BaseModel):
    """Represents current usage statistics for a user."""
    current_tier: str
    image_count: int
    image_limit: int
    usage_percentage: float
    billing_cycle_start: datetime
    billing_cycle_end: Optional[datetime] = None
    days_remaining: int


class PricingManager:
    """Manage pricing tiers and usage tracking."""
    
    def __init__(self):
        """Initialize pricing manager with default tiers."""
        self.tiers = self._load_default_tiers()
        self.usage_cache = {}  # Simple in-memory cache for demo
    
    def _load_default_tiers(self) -> Dict[str, PricingTier]:
        """Load default pricing tiers."""
        return {
            "free": PricingTier(
                name="Free",
                image_limit=5000,
                price_monthly=0.0,
                price_yearly=None,
                features=[
                    "Basic search functionality",
                    "Metadata extraction",
                    "Up to 5,000 images",
                    "Community support"
                ],
                stripe_price_id=None,
                is_popular=False
            ),
            "basic": PricingTier(
                name="Basic",
                image_limit=25000,
                price_monthly=9.99,
                price_yearly=99.99,
                features=[
                    "All Free features",
                    "Advanced search",
                    "Up to 25,000 images",
                    "Priority support",
                    "Usage analytics"
                ],
                stripe_price_id="price_basic_monthly",
                is_popular=True
            ),
            "pro": PricingTier(
                name="Pro",
                image_limit=100000,
                price_monthly=29.99,
                price_yearly=299.99,
                features=[
                    "All Basic features",
                    "Up to 100,000 images",
                    "API access",
                    "Team collaboration",
                    "Advanced analytics",
                    "Dedicated support"
                ],
                stripe_price_id="price_pro_monthly",
                is_popular=False
            ),
            "enterprise": PricingTier(
                name="Enterprise",
                image_limit=-1,  # -1 means unlimited
                price_monthly=0.0,  # Custom pricing
                price_yearly=None,
                features=[
                    "Custom image limits",
                    "Custom features",
                    "Dedicated account manager",
                    "SLA guarantees",
                    "On-premise options"
                ],
                stripe_price_id=None,
                is_popular=False
            )
        }
    
    def get_all_tiers(self) -> List[PricingTier]:
        """Get all available pricing tiers."""
        return list(self.tiers.values())
    
    def get_tier(self, tier_name: str) -> Optional[PricingTier]:
        """Get a specific pricing tier by name."""
        return self.tiers.get(tier_name.lower())
    
    def get_tier_by_image_count(self, image_count: int) -> PricingTier:
        """Get the appropriate tier based on image count."""
        # Find the smallest tier that can accommodate the image count
        suitable_tiers = []
        
        for tier_name, tier in self.tiers.items():
            if tier_name == "enterprise":
                continue  # Skip enterprise for auto-selection
            
            if tier.image_limit == -1 or image_count <= tier.image_limit:
                suitable_tiers.append(tier)
        
        # Return the smallest suitable tier (cheapest that fits)
        if suitable_tiers:
            return min(suitable_tiers, key=lambda x: x.image_limit)
        
        # If no suitable tier found, return enterprise
        return self.tiers["enterprise"]
    
    def track_usage(self, user_id: str, image_count: int) -> UsageStats:
        """Track usage for a user and return current stats."""
        # In a real implementation, this would query the database
        # For now, we'll use a simple cache
        
        if user_id not in self.usage_cache:
            # New user - start with free tier
            self.usage_cache[user_id] = {
                "tier": "free",
                "image_count": 0,
                "billing_cycle_start": datetime.now()
            }
        
        # Update image count
        self.usage_cache[user_id]["image_count"] = image_count
        
        # Get current tier
        current_tier = self.usage_cache[user_id]["tier"]
        tier_info = self.tiers[current_tier]
        
        # Calculate usage stats
        usage_percentage = (image_count / tier_info.image_limit) * 100 if tier_info.image_limit > 0 else 0
        
        return UsageStats(
            current_tier=current_tier,
            image_count=image_count,
            image_limit=tier_info.image_limit,
            usage_percentage=min(usage_percentage, 100),  # Cap at 100%
            billing_cycle_start=self.usage_cache[user_id]["billing_cycle_start"],
            billing_cycle_end=None,  # Would be calculated in real implementation
            days_remaining=30  # Placeholder
        )
    
    def check_limit(self, user_id: str, additional_images: int = 0) -> bool:
        """Check if user can add more images without exceeding limit."""
        if user_id not in self.usage_cache:
            return True  # New users can always add images
        
        current_count = self.usage_cache[user_id]["image_count"]
        current_tier = self.usage_cache[user_id]["tier"]
        tier_info = self.tiers[current_tier]
        
        if tier_info.image_limit == -1:  # Unlimited
            return True
        
        return (current_count + additional_images) <= tier_info.image_limit
    
    def upgrade_tier(self, user_id: str, new_tier: str) -> bool:
        """Upgrade a user to a new tier."""
        if new_tier not in self.tiers:
            return False
        
        if user_id not in self.usage_cache:
            self.usage_cache[user_id] = {
                "tier": new_tier,
                "image_count": 0,
                "billing_cycle_start": datetime.now()
            }
        else:
            self.usage_cache[user_id]["tier"] = new_tier
            self.usage_cache[user_id]["billing_cycle_start"] = datetime.now()
        
        return True


# Global pricing manager instance
pricing_manager = PricingManager()