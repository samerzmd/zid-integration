"""
Example usage of the Zid Integration API
Run this script to test the API endpoints
"""

import asyncio
import httpx
import json


class ZidIntegrationTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def test_health_check(self):
        """Test health check endpoint"""
        print("🏥 Testing health check...")
        response = await self.client.get(f"{self.base_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    
    async def test_root_endpoint(self):
        """Test root endpoint"""
        print("🏠 Testing root endpoint...")
        response = await self.client.get(f"{self.base_url}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    
    async def test_oauth_authorization(self):
        """Test OAuth authorization endpoint"""
        print("🔐 Testing OAuth authorization...")
        response = await self.client.get(f"{self.base_url}/auth/authorize")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    
    async def test_products_endpoint(self):
        """Test products endpoint (will fail without auth)"""
        print("📦 Testing products endpoint...")
        params = {"merchant_id": "test_merchant"}
        response = await self.client.get(f"{self.base_url}/products", params=params)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    
    async def test_orders_endpoint(self):
        """Test orders endpoint (will fail without auth)"""
        print("📋 Testing orders endpoint...")
        params = {"merchant_id": "test_merchant"}
        response = await self.client.get(f"{self.base_url}/orders", params=params)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    
    async def test_webhook_endpoint(self):
        """Test webhook endpoint"""
        print("🔗 Testing webhook endpoint...")
        webhook_payload = {
            "event": "order.created",
            "id": "test_event_123",
            "merchant_id": "test_merchant",
            "data": {
                "order_id": 12345,
                "status": "pending",
                "total": 99.99,
                "customer": {
                    "name": "Test Customer",
                    "email": "test@example.com"
                }
            }
        }
        
        response = await self.client.post(
            f"{self.base_url}/webhooks/zid",
            json=webhook_payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    
    async def test_webhook_events_list(self):
        """Test webhook events listing"""
        print("📋 Testing webhook events list...")
        response = await self.client.get(f"{self.base_url}/webhooks/events")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    
    async def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Zid Integration API Tests\n")
        
        try:
            await self.test_health_check()
            await self.test_root_endpoint()
            await self.test_oauth_authorization()
            await self.test_products_endpoint()
            await self.test_orders_endpoint()
            await self.test_webhook_endpoint()
            await self.test_webhook_events_list()
            
            print("✅ All tests completed!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
        
        finally:
            await self.client.aclose()


async def main():
    """Main function"""
    tester = ZidIntegrationTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())