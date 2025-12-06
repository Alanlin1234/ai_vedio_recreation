#!/usr/bin/env python3
"""
测试抖音爬虫API是否正常工作
"""

import requests

def test_crawler_api():
    """测试爬虫API"""
    print("=== 测试抖音爬虫API ===")
    
    # 爬虫API地址
    url = "http://127.0.0.1:80/api/douyin/web/fetch_hot_search_result"
    
    try:
        # 发送GET请求
        response = requests.get(url, timeout=5)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("✅ 爬虫API正常响应")
        else:
            print(f"❌ 爬虫API返回错误状态码: {response.status_code}")
    
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到爬虫服务，请确保服务已启动")
    except requests.exceptions.Timeout:
        print("❌ 爬虫服务响应超时")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print()

def test_large_model_api():
    """检查大模型API配置"""
    print("=== 检查大模型API配置 ===")
    
    # 检查大模型配置
    import configparser
    import os
    
    config_path = os.path.join("backend", "config.py")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        if "LLM_API_KEY" in config_content:
            print("✅ 大模型API配置已存在")
        else:
            print("❌ 大模型API配置不存在或未配置")
            print("请在backend/config.py中配置LLM_API_KEY")
    
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
    
    print()

if __name__ == "__main__":
    test_crawler_api()
    test_large_model_api()
