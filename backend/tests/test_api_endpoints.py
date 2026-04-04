"""
Backend API Endpoint Tests
Tests for: /api/, /api/stats, /api/users, /api/coupons/recent, /api/success-rates
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAPIEndpoints:
    """API endpoint tests for betting bot dashboard"""
    
    def test_root_endpoint_returns_running_status(self):
        """Test /api/ returns running status"""
        response = requests.get(f"{BASE_URL}/api/")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Response should contain 'status' field"
        assert data["status"] == "running", f"Expected status 'running', got '{data['status']}'"
        assert "message" in data, "Response should contain 'message' field"
        print(f"✅ Root endpoint: {data}")
    
    def test_stats_endpoint_returns_statistics(self):
        """Test /api/stats returns statistics"""
        response = requests.get(f"{BASE_URL}/api/stats")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify required fields exist
        assert "total_users" in data, "Response should contain 'total_users'"
        assert "total_coupons" in data, "Response should contain 'total_coupons'"
        assert "total_matches" in data, "Response should contain 'total_matches'"
        assert "total_predictions" in data, "Response should contain 'total_predictions'"
        assert "recent_activities" in data, "Response should contain 'recent_activities'"
        
        # Verify data types
        assert isinstance(data["total_users"], int), "total_users should be int"
        assert isinstance(data["total_coupons"], int), "total_coupons should be int"
        assert isinstance(data["recent_activities"], list), "recent_activities should be list"
        
        print(f"✅ Stats endpoint: users={data['total_users']}, coupons={data['total_coupons']}")
    
    def test_users_endpoint_returns_user_list(self):
        """Test /api/users returns user list"""
        response = requests.get(f"{BASE_URL}/api/users")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "users" in data, "Response should contain 'users' field"
        assert "count" in data, "Response should contain 'count' field"
        assert isinstance(data["users"], list), "users should be a list"
        assert isinstance(data["count"], int), "count should be int"
        
        # Verify no _id in response (MongoDB ObjectId should be excluded)
        for user in data["users"]:
            assert "_id" not in user, "MongoDB _id should be excluded from response"
        
        print(f"✅ Users endpoint: count={data['count']}")
    
    def test_coupons_recent_endpoint_returns_coupon_list(self):
        """Test /api/coupons/recent returns coupon list"""
        response = requests.get(f"{BASE_URL}/api/coupons/recent")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "coupons" in data, "Response should contain 'coupons' field"
        assert "count" in data, "Response should contain 'count' field"
        assert isinstance(data["coupons"], list), "coupons should be a list"
        assert isinstance(data["count"], int), "count should be int"
        
        # Verify no _id in response
        for coupon in data["coupons"]:
            assert "_id" not in coupon, "MongoDB _id should be excluded from response"
        
        print(f"✅ Coupons recent endpoint: count={data['count']}")
    
    def test_success_rates_endpoint_returns_rate_data(self):
        """Test /api/success-rates returns success rate data"""
        response = requests.get(f"{BASE_URL}/api/success-rates")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify required fields for each risk level
        assert "banko" in data, "Response should contain 'banko' rate"
        assert "orta" in data, "Response should contain 'orta' rate"
        assert "zor" in data, "Response should contain 'zor' rate"
        assert "total_coupons" in data, "Response should contain 'total_coupons'"
        assert "won_coupons" in data, "Response should contain 'won_coupons'"
        
        # Verify data types (rates should be numbers 0-100)
        assert isinstance(data["banko"], (int, float)), "banko should be numeric"
        assert isinstance(data["orta"], (int, float)), "orta should be numeric"
        assert isinstance(data["zor"], (int, float)), "zor should be numeric"
        assert 0 <= data["banko"] <= 100, "banko rate should be 0-100"
        assert 0 <= data["orta"] <= 100, "orta rate should be 0-100"
        assert 0 <= data["zor"] <= 100, "zor rate should be 0-100"
        
        print(f"✅ Success rates: banko={data['banko']}%, orta={data['orta']}%, zor={data['zor']}%")
    
    def test_matches_today_endpoint(self):
        """Test /api/matches/today returns matches"""
        response = requests.get(f"{BASE_URL}/api/matches/today")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "matches" in data, "Response should contain 'matches' field"
        assert "count" in data, "Response should contain 'count' field"
        assert isinstance(data["matches"], list), "matches should be a list"
        
        print(f"✅ Matches today endpoint: count={data['count']}")
    
    def test_predictions_recent_endpoint(self):
        """Test /api/predictions/recent returns predictions"""
        response = requests.get(f"{BASE_URL}/api/predictions/recent")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "predictions" in data, "Response should contain 'predictions' field"
        assert "count" in data, "Response should contain 'count' field"
        assert isinstance(data["predictions"], list), "predictions should be a list"
        
        print(f"✅ Predictions recent endpoint: count={data['count']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
