#!/usr/bin/env python3
"""
检查ComfyUI服务是否正常运行的脚本
"""

import requests
import sys

def check_comfyui():
    """检查ComfyUI服务状态"""
    try:
        # 检查ComfyUI API是否响应
        response = requests.get("http://127.0.0.1:8188/system_stats", timeout=5)
        if response.status_code == 200:
            print("✅ ComfyUI服务正常响应")
            return True
        else:
            print(f"❌ ComfyUI服务返回错误状态码: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ ComfyUI服务未运行或无法连接")
        return False
    except Exception as e:
        print(f"❌ 检查ComfyUI服务时发生错误: {e}")
        return False

if __name__ == "__main__":
    if check_comfyui():
        sys.exit(0)
    else:
        sys.exit(1)
