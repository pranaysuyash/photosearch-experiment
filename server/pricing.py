"""
Pricing Module - Handle pricing tiers, usage tracking, and billing logic

This module provides:
- Pricing tier definitions
- Usage tracking and enforcement
- Billing cycle management
- API endpoints for pricing information
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime, timedelta


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
        self.usage_cache: Dict[str, Dict[str, Any]] = {}  # Simple in-memory cache for demo
        # Minimal in-memory time series. In production this should live in a DB.
        self.usage_history: Dict[str, List[Dict[str, Any]]] = {}

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
                    "Community support",
                ],
                stripe_price_id=None,
                is_popular=False,
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
                    "Usage analytics",
                ],
                stripe_price_id="price_basic_monthly",
                is_popular=True,
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
                    "Dedicated support",
                ],
                stripe_price_id="price_pro_monthly",
                is_popular=False,
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
                    "On-premise options",
                ],
                stripe_price_id=None,
                is_popular=False,
            ),
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
                "billing_cycle_start": datetime.now(),
            }

        # Update image count
        self.usage_cache[user_id]["image_count"] = image_count

        # Record history snapshot
        hist = self.usage_history.setdefault(user_id, [])
        hist.append(
            {
                "timestamp": datetime.now().isoformat(),
                "tier": self.usage_cache[user_id]["tier"],
                "image_count": int(image_count),
            }
        )
        # Keep history bounded to avoid unbounded growth in long-running processes.
        if len(hist) > 5000:
            del hist[:-1000]

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
            days_remaining=30,  # Placeholder
        )

    def get_usage_history(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Return recent usage history snapshots for a user."""
        if days <= 0:
            days = 1
        cutoff = datetime.now() - timedelta(days=int(days))
        history = self.usage_history.get(user_id, [])
        out: List[Dict[str, Any]] = []
        for item in history:
            ts = item.get("timestamp")
            try:
                dt = datetime.fromisoformat(str(ts))
            except Exception:
                continue
            if dt >= cutoff:
                out.append(item)
        return out

    def get_user_growth_rate(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Compute a simple growth rate for a user's image count over time."""
        history = self.get_usage_history(user_id, days=days)
        if not history:
            return {
                "user_id": user_id,
                "days": int(days),
                "start": None,
                "end": None,
                "delta_images": 0,
                "avg_images_per_day": 0.0,
            }

        # Use first/last snapshot in window.
        start = history[0]
        end = history[-1]
        start_count = int(start.get("image_count", 0) or 0)
        end_count = int(end.get("image_count", 0) or 0)
        delta = end_count - start_count
        days_f = float(max(int(days), 1))
        return {
            "user_id": user_id,
            "days": int(days),
            "start": start,
            "end": end,
            "delta_images": delta,
            "avg_images_per_day": delta / days_f,
        }

    def get_tier_averages(self) -> Dict[str, Dict[str, Any]]:
        """Return average image counts per tier for currently tracked users."""
        by_tier: Dict[str, List[int]] = {}
        for uid, rec in self.usage_cache.items():
            tier = str(rec.get("tier", "free"))
            cnt = int(rec.get("image_count", 0) or 0)
            by_tier.setdefault(tier, []).append(cnt)

        out: Dict[str, Dict[str, Any]] = {}
        for tier, counts in by_tier.items():
            if counts:
                out[tier] = {
                    "users": len(counts),
                    "avg_image_count": sum(counts) / float(len(counts)),
                    "min_image_count": min(counts),
                    "max_image_count": max(counts),
                }
            else:
                out[tier] = {
                    "users": 0,
                    "avg_image_count": 0.0,
                    "min_image_count": 0,
                    "max_image_count": 0,
                }
        return out

    def get_company_usage_analytics(self) -> Dict[str, Any]:
        """Return a lightweight company-wide snapshot across all tracked users."""
        total_users = len(self.usage_cache)
        total_images = 0
        tier_distribution: Dict[str, int] = {}
        top_users: List[Dict[str, Any]] = []

        for uid, rec in self.usage_cache.items():
            tier = str(rec.get("tier", "free"))
            cnt = int(rec.get("image_count", 0) or 0)
            total_images += cnt
            tier_distribution[tier] = tier_distribution.get(tier, 0) + 1
            top_users.append({"user_id": uid, "tier": tier, "image_count": cnt})

        top_users.sort(key=lambda r: int(r.get("image_count", 0) or 0), reverse=True)
        top_users = top_users[:10]

        return {
            "total_users": total_users,
            "total_images": total_images,
            "tier_distribution": tier_distribution,
            "tier_averages": self.get_tier_averages(),
            "top_users": top_users,
            "generated_at": datetime.now().isoformat(),
        }

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
                "billing_cycle_start": datetime.now(),
            }
        else:
            self.usage_cache[user_id]["tier"] = new_tier
            self.usage_cache[user_id]["billing_cycle_start"] = datetime.now()

        return True


# Global pricing manager instance
pricing_manager = PricingManager()
