#!/usr/bin/env python3
"""
详细检查ComfyUI系统状态，查看完整的API返回数据
"""

import requests
import json

def check_comfyui_detailed():
    """详细检查ComfyUI系统状态"""
    try:
        response = requests.get('http://127.0.0.1:8188/system_stats', timeout=5)
        if response.status_code == 200:
            data = json.loads(response.text)
            print('=== 完整系统状态 ===')
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            print('\n=== GPU信息检查 ===')
            if 'gpu' in data:
                print(f'✅ GPU信息存在: {data["gpu"]}')
            else:
                print('❌ GPU信息不存在于系统状态中')
                # 检查pipeline状态，看看是否有GPU相关信息
                if 'pipeline' in data:
                    print(f'Pipeline信息: {data["pipeline"]}')
        else:
            print(f'❌ ComfyUI服务返回错误状态: {response.status_code}')
    except requests.exceptions.ConnectionError:
        print('❌ 无法连接到ComfyUI服务')
    except Exception as e:
        print(f'❌ 检查ComfyUI状态时出错: {e}')

if __name__ == '__main__':
    check_comfyui_detailed()
