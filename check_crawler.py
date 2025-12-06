import requests
import time

def check_crawler_service():
    """检查爬虫服务是否正常运行"""
    try:
        response = requests.get("http://localhost:88/api/hybrid/video_data", timeout=5)
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    print("检查爬虫服务状态...")
    if check_crawler_service():
        print("✅ 爬虫服务正在运行")
    else:
        print("⚠️  爬虫服务未响应，可能正在启动中或出现问题")
        print("继续启动后端服务...")
