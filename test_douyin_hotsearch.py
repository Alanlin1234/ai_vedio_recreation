import requests

def test_douyin_hotsearch():
    """Test Douyin hot search API endpoint"""
    # Crawler is running on port 80 with correct API path
    url = "http://127.0.0.1/api/douyin/web/fetch_hot_search_result"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print("✅ Douyin hot search API is working!")
            print(f"   Status: {response.status_code}")
            print(f"   Data: {result.get('data', {})}")
            print(f"   Message: {result.get('message', '')}")
            return True
        else:
            print(f"❌ Douyin hot search API returned error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except requests.ConnectionError:
        print("❌ Douyin crawler API is not running or port 8000 is not accessible")
        return False
    except Exception as e:
        print(f"❌ Error testing Douyin hot search API: {e}")
        return False

if __name__ == "__main__":
    print("Testing Douyin hot search API...")
    test_douyin_hotsearch()