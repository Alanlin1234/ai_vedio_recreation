#!/usr/bin/env python3
"""
测试爬虫服务的搜索功能
"""

import requests
import json

# 爬虫服务的基础URL
BASE_URL = "http://localhost:80"

# 测试获取抖音热点搜索结果
def test_douyin_hot_search():
    """测试获取抖音热点搜索结果"""
    print("测试抖音热点搜索功能...")
    
    # 构建请求URL和参数
    hot_search_url = f"{BASE_URL}/api/douyin/web/fetch_hot_search_result"
    
    try:
        # 发送请求
        response = requests.get(hot_search_url, timeout=30)
        
        # 打印响应状态码
        print(f"响应状态码: {response.status_code}")
        
        # 解析响应内容
        data = response.json()
        print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        # 检查响应结果
        if response.status_code == 200:
            if data.get("code") == 200 and data.get("data"):
                print(f"获取热点成功，返回了 {len(data['data'])} 个结果")
                return True
            else:
                print(f"获取热点失败，错误信息: {data.get('message', '未知错误')}")
                return False
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"测试失败，发生异常: {str(e)}")
        return False

# 测试获取单个视频信息
def test_fetch_one_video():
    """测试获取单个视频信息功能"""
    print("\n测试获取单个视频信息功能...")
    
    # 使用一个示例视频ID
    video_id = "7372484719365098803"
    
    # 构建请求URL和参数
    fetch_url = f"{BASE_URL}/api/douyin/web/fetch_one_video"
    params = {
        "aweme_id": video_id
    }
    
    try:
        # 发送请求
        response = requests.get(fetch_url, params=params, timeout=30)
        
        # 打印响应状态码
        print(f"响应状态码: {response.status_code}")
        
        # 解析响应内容
        data = response.json()
        print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        # 检查响应结果
        if response.status_code == 200:
            if data.get("code") == 200 and data.get("data"):
                print("获取视频信息成功")
                return True
            else:
                print(f"获取视频信息失败，错误信息: {data.get('message', '未知错误')}")
                return False
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"测试失败，发生异常: {str(e)}")
        return False

if __name__ == "__main__":
    # 运行测试
    test_douyin_hot_search()
    test_fetch_one_video()
