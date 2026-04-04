"""
Admin API Endpoint Tests
Tests for: /api/admin/dashboard, /api/admin/users, /api/admin/payments, /api/admin/premium
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAdminDashboard:
    """Tests for /api/admin/dashboard endpoint"""
    
    def test_dashboard_returns_200(self):
        """Dashboard endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/admin/dashboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✅ Dashboard returns 200")
    
    def test_dashboard_contains_required_fields(self):
        """Dashboard should contain all required stats fields"""
        response = requests.get(f"{BASE_URL}/api/admin/dashboard")
        data = response.json()
        
        required_fields = [
            "total_users", "premium_users", "total_coupons", "today_coupons",
            "weekly_coupons", "pending_payments", "approved_payments",
            "won", "lost", "win_rate", "revenue"
        ]
        
        for field in required_fields:
            assert field in data, f"Dashboard should contain '{field}'"
        
        print(f"✅ Dashboard contains all required fields: {list(data.keys())}")
    
    def test_dashboard_field_types(self):
        """Dashboard fields should have correct types"""
        response = requests.get(f"{BASE_URL}/api/admin/dashboard")
        data = response.json()
        
        # All should be integers
        int_fields = ["total_users", "premium_users", "total_coupons", "today_coupons",
                      "weekly_coupons", "pending_payments", "approved_payments",
                      "won", "lost", "win_rate", "revenue"]
        
        for field in int_fields:
            assert isinstance(data[field], int), f"{field} should be int, got {type(data[field])}"
        
        # win_rate should be 0-100
        assert 0 <= data["win_rate"] <= 100, f"win_rate should be 0-100, got {data['win_rate']}"
        
        print(f"✅ Dashboard field types are correct")


class TestAdminUsers:
    """Tests for /api/admin/users endpoint"""
    
    def test_users_returns_200(self):
        """Users endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/admin/users")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✅ Admin users returns 200")
    
    def test_users_returns_list_with_count(self):
        """Users endpoint should return users list and count"""
        response = requests.get(f"{BASE_URL}/api/admin/users")
        data = response.json()
        
        assert "users" in data, "Response should contain 'users'"
        assert "count" in data, "Response should contain 'count'"
        assert isinstance(data["users"], list), "users should be a list"
        assert isinstance(data["count"], int), "count should be int"
        assert data["count"] == len(data["users"]), "count should match users length"
        
        print(f"✅ Admin users returns list with count={data['count']}")
    
    def test_users_no_mongodb_id(self):
        """Users should not contain MongoDB _id"""
        response = requests.get(f"{BASE_URL}/api/admin/users")
        data = response.json()
        
        for user in data["users"]:
            assert "_id" not in user, "MongoDB _id should be excluded"
        
        print(f"✅ Admin users excludes MongoDB _id")
    
    def test_users_contain_required_fields(self):
        """Each user should contain required fields"""
        response = requests.get(f"{BASE_URL}/api/admin/users")
        data = response.json()
        
        if len(data["users"]) > 0:
            user = data["users"][0]
            required_fields = ["telegram_id", "created_at", "last_interaction"]
            
            for field in required_fields:
                assert field in user, f"User should contain '{field}'"
            
            print(f"✅ Users contain required fields")
        else:
            print(f"⚠️ No users to verify fields")


class TestAdminPayments:
    """Tests for /api/admin/payments endpoint"""
    
    def test_payments_returns_200(self):
        """Payments endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/admin/payments")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✅ Admin payments returns 200")
    
    def test_payments_returns_list_with_count(self):
        """Payments endpoint should return payments list and count"""
        response = requests.get(f"{BASE_URL}/api/admin/payments")
        data = response.json()
        
        assert "payments" in data, "Response should contain 'payments'"
        assert "count" in data, "Response should contain 'count'"
        assert isinstance(data["payments"], list), "payments should be a list"
        assert isinstance(data["count"], int), "count should be int"
        
        print(f"✅ Admin payments returns list with count={data['count']}")
    
    def test_payments_no_mongodb_id(self):
        """Payments should not contain MongoDB _id"""
        response = requests.get(f"{BASE_URL}/api/admin/payments")
        data = response.json()
        
        for payment in data["payments"]:
            assert "_id" not in payment, "MongoDB _id should be excluded"
        
        print(f"✅ Admin payments excludes MongoDB _id")


class TestAdminPremiumAction:
    """Tests for /api/admin/premium endpoint"""
    
    def test_premium_activate_nonexistent_user_returns_404(self):
        """Activating premium for non-existent user should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/admin/premium",
            json={"telegram_id": "NONEXISTENT_USER_999999", "action": "activate"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✅ Premium activate for non-existent user returns 404")
    
    def test_premium_deactivate_nonexistent_user_returns_404(self):
        """Deactivating premium for non-existent user should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/admin/premium",
            json={"telegram_id": "NONEXISTENT_USER_999999", "action": "deactivate"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✅ Premium deactivate for non-existent user returns 404")
    
    def test_premium_action_requires_telegram_id(self):
        """Premium action should require telegram_id"""
        response = requests.post(
            f"{BASE_URL}/api/admin/premium",
            json={"action": "activate"}
        )
        # Should return 422 (validation error) for missing field
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"✅ Premium action requires telegram_id")
    
    def test_premium_action_requires_action_field(self):
        """Premium action should require action field"""
        response = requests.post(
            f"{BASE_URL}/api/admin/premium",
            json={"telegram_id": "123"}
        )
        # Should return 422 (validation error) for missing field
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"✅ Premium action requires action field")


class TestAdminPremiumActivateDeactivate:
    """Tests for premium activate/deactivate with existing user"""
    
    @pytest.fixture(autouse=True)
    def get_existing_user(self):
        """Get an existing user for testing"""
        response = requests.get(f"{BASE_URL}/api/admin/users")
        data = response.json()
        if data["users"]:
            self.test_user = data["users"][0]
        else:
            pytest.skip("No users available for premium testing")
    
    def test_premium_activate_existing_user(self):
        """Activating premium for existing user should succeed"""
        response = requests.post(
            f"{BASE_URL}/api/admin/premium",
            json={"telegram_id": self.test_user["telegram_id"], "action": "activate"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["status"] == "success", "Status should be success"
        assert data["action"] == "activate", "Action should be activate"
        assert data["telegram_id"] == self.test_user["telegram_id"], "telegram_id should match"
        
        print(f"✅ Premium activate for existing user succeeds")
    
    def test_premium_deactivate_existing_user(self):
        """Deactivating premium for existing user should succeed"""
        response = requests.post(
            f"{BASE_URL}/api/admin/premium",
            json={"telegram_id": self.test_user["telegram_id"], "action": "deactivate"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["status"] == "success", "Status should be success"
        assert data["action"] == "deactivate", "Action should be deactivate"
        
        print(f"✅ Premium deactivate for existing user succeeds")
    
    def test_premium_activate_verify_persistence(self):
        """After activating premium, user should show as premium"""
        # Activate premium
        requests.post(
            f"{BASE_URL}/api/admin/premium",
            json={"telegram_id": self.test_user["telegram_id"], "action": "activate"}
        )
        
        # Verify in users list
        response = requests.get(f"{BASE_URL}/api/admin/users")
        data = response.json()
        
        user = next((u for u in data["users"] if u["telegram_id"] == self.test_user["telegram_id"]), None)
        assert user is not None, "User should exist"
        assert user.get("is_premium") is True, "User should be premium after activation"
        assert "premium_until" in user, "User should have premium_until field"
        
        print(f"✅ Premium activation persisted correctly")
        
        # Cleanup: deactivate
        requests.post(
            f"{BASE_URL}/api/admin/premium",
            json={"telegram_id": self.test_user["telegram_id"], "action": "deactivate"}
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
