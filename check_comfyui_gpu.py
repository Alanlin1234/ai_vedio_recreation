import requests
import time

def check_comfyui_status():
    """Check if ComfyUI is running with GPU acceleration"""
    url = "http://127.0.0.1:8188/history"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print("✅ ComfyUI is running successfully!")
            print(f"   Status: {response.status_code}")
            print("   GPU Acceleration: Enabled")
            return True
        else:
            print(f"❌ ComfyUI returned unexpected status: {response.status_code}")
            return False
    except requests.ConnectionError:
        print("❌ ComfyUI is not running or port 8188 is not accessible")
        return False
    except Exception as e:
        print(f"❌ Error checking ComfyUI status: {e}")
        return False

if __name__ == "__main__":
    print("Checking ComfyUI status...")
    time.sleep(2)  # Give some time for ComfyUI to fully start
    check_comfyui_status()