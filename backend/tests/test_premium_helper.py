"""
Premium Helper Unit Tests
Tests for: FREE_TOTAL_LIMIT (3 TOTAL coupons), can_create_coupon, can_use_risk_level, is_premium_active, activate_premium
Updated: Now tests TOTAL limit (not daily) - users get 3 TOTAL coupons then must upgrade
"""
import pytest
import sys
import os
from datetime import datetime, timedelta

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from premium_helper import PremiumHelper


class TestPremiumHelperConstants:
    """Test premium helper constants - FREE_TOTAL_LIMIT should be 3 (TOTAL not daily)"""
    
    def test_free_total_limit_is_3(self):
        """FREE_TOTAL_LIMIT should be 3 (TOTAL coupons, not daily)"""
        assert PremiumHelper.FREE_TOTAL_LIMIT == 3, f"Expected FREE_TOTAL_LIMIT=3, got {PremiumHelper.FREE_TOTAL_LIMIT}"
        print(f"✅ FREE_TOTAL_LIMIT = {PremiumHelper.FREE_TOTAL_LIMIT}")
    
    def test_prices_exist(self):
        """Prices should be defined"""
        assert "monthly" in PremiumHelper.PRICES, "Monthly price should exist"
        assert "yearly" in PremiumHelper.PRICES, "Yearly price should exist"
        assert PremiumHelper.PRICES["monthly"] == 99, "Monthly price should be 99"
        print(f"✅ Prices: monthly={PremiumHelper.PRICES['monthly']}, yearly={PremiumHelper.PRICES['yearly']}")


class TestCanCreateCoupon:
    """Test can_create_coupon function - checks TOTAL coupons (not daily)"""
    
    def test_can_create_coupon_new_user(self):
        """New user with no coupons should be able to create"""
        user = {"telegram_id": "123", "total_coupons": 0}
        can_create, msg = PremiumHelper.can_create_coupon(user)
        
        assert can_create is True, f"New user should be able to create coupon: {msg}"
        print(f"✅ New user can create coupon")
    
    def test_can_create_coupon_under_limit(self):
        """User with 2 total coupons should be able to create"""
        user = {"telegram_id": "123", "total_coupons": 2}
        can_create, msg = PremiumHelper.can_create_coupon(user)
        
        assert can_create is True, f"User under limit should be able to create: {msg}"
        print(f"✅ User with 2 total coupons can create more")
    
    def test_can_create_coupon_blocks_after_3_total_free(self):
        """User with 3 TOTAL coupons should be blocked (free user)"""
        user = {
            "telegram_id": "123", 
            "total_coupons": 3,
            "is_premium": False
        }
        can_create, msg = PremiumHelper.can_create_coupon(user)
        
        assert can_create is False, "Free user at TOTAL limit should be blocked"
        assert "3/3" in msg or "bitti" in msg.lower(), f"Message should mention limit reached: {msg}"
        print(f"✅ Free user blocked after 3 TOTAL coupons: {msg[:60]}...")
    
    def test_can_create_coupon_blocks_after_exceeding_limit(self):
        """User with more than 3 TOTAL coupons should be blocked"""
        user = {
            "telegram_id": "123", 
            "total_coupons": 5,
            "is_premium": False
        }
        can_create, msg = PremiumHelper.can_create_coupon(user)
        
        assert can_create is False, "Free user exceeding TOTAL limit should be blocked"
        print(f"✅ Free user blocked with 5 total coupons")
    
    def test_can_create_coupon_admin_unlimited(self):
        """Admin user should have unlimited coupons regardless of count"""
        user = {
            "telegram_id": "123", 
            "total_coupons": 100,
            "is_admin": True
        }
        can_create, msg = PremiumHelper.can_create_coupon(user)
        
        assert can_create is True, f"Admin should have unlimited: {msg}"
        print(f"✅ Admin user can create unlimited coupons")
    
    def test_can_create_coupon_premium_unlimited(self):
        """Premium user should have unlimited coupons"""
        future = (datetime.utcnow() + timedelta(days=30)).isoformat()
        user = {
            "telegram_id": "123", 
            "total_coupons": 100,
            "is_premium": True,
            "premium_until": future
        }
        can_create, msg = PremiumHelper.can_create_coupon(user)
        
        assert can_create is True, f"Premium user should have unlimited: {msg}"
        print(f"✅ Premium user can create unlimited coupons")


class TestCanUseRiskLevel:
    """Test can_use_risk_level function"""
    
    def test_can_use_banko_free_user(self):
        """Free user should be able to use banko"""
        user = {"telegram_id": "123", "is_premium": False}
        can_use, msg = PremiumHelper.can_use_risk_level(user, "banko")
        
        assert can_use is True, f"Free user should use banko: {msg}"
        print(f"✅ Free user can use banko")
    
    def test_can_use_orta_free_user(self):
        """Free user should be able to use orta"""
        user = {"telegram_id": "123", "is_premium": False}
        can_use, msg = PremiumHelper.can_use_risk_level(user, "orta")
        
        assert can_use is True, f"Free user should use orta: {msg}"
        print(f"✅ Free user can use orta")
    
    def test_cannot_use_zor_free_user(self):
        """Free user should NOT be able to use zor"""
        user = {"telegram_id": "123", "is_premium": False}
        can_use, msg = PremiumHelper.can_use_risk_level(user, "zor")
        
        assert can_use is False, "Free user should NOT use zor"
        assert "premium" in msg.lower(), "Message should mention premium"
        print(f"✅ Free user blocked from zor: {msg[:50]}...")
    
    def test_can_use_zor_premium_user(self):
        """Premium user should be able to use zor"""
        future = (datetime.utcnow() + timedelta(days=30)).isoformat()
        user = {
            "telegram_id": "123", 
            "is_premium": True,
            "premium_until": future
        }
        can_use, msg = PremiumHelper.can_use_risk_level(user, "zor")
        
        assert can_use is True, f"Premium user should use zor: {msg}"
        print(f"✅ Premium user can use zor")


class TestIsPremiumActive:
    """Test is_premium_active function"""
    
    def test_is_premium_active_false_for_non_premium(self):
        """Non-premium user should return False"""
        user = {"telegram_id": "123", "is_premium": False}
        result = PremiumHelper.is_premium_active(user)
        
        assert result is False, "Non-premium user should return False"
        print(f"✅ Non-premium user returns False")
    
    def test_is_premium_active_false_for_missing_fields(self):
        """User without premium fields should return False"""
        user = {"telegram_id": "123"}
        result = PremiumHelper.is_premium_active(user)
        
        assert result is False, "User without premium fields should return False"
        print(f"✅ User without premium fields returns False")
    
    def test_is_premium_active_true_for_active_premium(self):
        """Active premium user should return True"""
        future = (datetime.utcnow() + timedelta(days=30)).isoformat()
        user = {
            "telegram_id": "123", 
            "is_premium": True,
            "premium_until": future
        }
        result = PremiumHelper.is_premium_active(user)
        
        assert result is True, "Active premium user should return True"
        print(f"✅ Active premium user returns True")
    
    def test_is_premium_active_false_for_expired_premium(self):
        """Expired premium user should return False"""
        past = (datetime.utcnow() - timedelta(days=1)).isoformat()
        user = {
            "telegram_id": "123", 
            "is_premium": True,
            "premium_until": past
        }
        result = PremiumHelper.is_premium_active(user)
        
        assert result is False, "Expired premium user should return False"
        print(f"✅ Expired premium user returns False")


class TestActivatePremium:
    """Test activate_premium function"""
    
    def test_activate_premium_monthly_returns_correct_fields(self):
        """activate_premium should return correct fields for monthly"""
        result = PremiumHelper.activate_premium("123", "monthly")
        
        assert "is_premium" in result, "Should contain is_premium"
        assert "premium_since" in result, "Should contain premium_since"
        assert "premium_until" in result, "Should contain premium_until"
        assert "premium_type" in result, "Should contain premium_type"
        assert "expiry_reminder_sent" in result, "Should contain expiry_reminder_sent"
        
        assert result["is_premium"] is True, "is_premium should be True"
        assert result["premium_type"] == "monthly", "premium_type should be monthly"
        assert result["expiry_reminder_sent"] is False, "expiry_reminder_sent should be False"
        
        # Verify premium_until is ~30 days from now
        until = datetime.fromisoformat(result["premium_until"])
        now = datetime.utcnow()
        diff = (until - now).days
        assert 29 <= diff <= 31, f"Monthly premium should be ~30 days, got {diff}"
        
        print(f"✅ activate_premium monthly: {result}")
    
    def test_activate_premium_yearly_returns_correct_fields(self):
        """activate_premium should return correct fields for yearly"""
        result = PremiumHelper.activate_premium("123", "yearly")
        
        assert result["is_premium"] is True, "is_premium should be True"
        assert result["premium_type"] == "yearly", "premium_type should be yearly"
        assert result["expiry_reminder_sent"] is False, "expiry_reminder_sent should be False"
        
        # Verify premium_until is ~365 days from now
        until = datetime.fromisoformat(result["premium_until"])
        now = datetime.utcnow()
        diff = (until - now).days
        assert 364 <= diff <= 366, f"Yearly premium should be ~365 days, got {diff}"
        
        print(f"✅ activate_premium yearly: {result}")
    
    def test_activate_premium_30_day_duration(self):
        """Monthly premium should be exactly 30 days"""
        result = PremiumHelper.activate_premium("123", "monthly")
        
        since = datetime.fromisoformat(result["premium_since"])
        until = datetime.fromisoformat(result["premium_until"])
        diff = (until - since).days
        
        assert diff == 30, f"Monthly premium should be 30 days, got {diff}"
        print(f"✅ Monthly premium is 30 days")


class TestGetRemainingDays:
    """Test get_remaining_days function"""
    
    def test_get_remaining_days_non_premium(self):
        """Non-premium user should return 0"""
        user = {"telegram_id": "123", "is_premium": False}
        days = PremiumHelper.get_remaining_days(user)
        
        assert days == 0, f"Non-premium should return 0, got {days}"
        print(f"✅ Non-premium remaining days: {days}")
    
    def test_get_remaining_days_active_premium(self):
        """Active premium should return positive days"""
        future = (datetime.utcnow() + timedelta(days=15)).isoformat()
        user = {
            "telegram_id": "123", 
            "is_premium": True,
            "premium_until": future
        }
        days = PremiumHelper.get_remaining_days(user)
        
        assert 14 <= days <= 16, f"Expected ~15 days, got {days}"
        print(f"✅ Active premium remaining days: {days}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
