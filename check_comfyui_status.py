#!/usr/bin/env python3
"""
检查ComfyUI系统状态，特别是GPU使用情况
"""

import requests
import json

def check_comfyui_status():
    """检查ComfyUI系统状态"""
    try:
        response = requests.get('http://127.0.0.1:8188/system_stats', timeout=5)
        if response.status_code == 200:
            data = json.loads(response.text)
            print('=== 系统状态 ===')
            print(f'操作系统: {data["system"]["os"]}')
            print(f'总内存: {data["system"]["ram_total"]/(1024*1024*1024):.2f} GB')
            print(f'可用内存: {data["system"]["ram_free"]/(1024*1024*1024):.2f} GB')
            print(f'ComfyUI版本: {data["system"]["comfyui_version"]}')
            
            print('\n=== GPU信息 ===')
            if 'gpu' in data:
                gpu_data = data['gpu']
                print(f'GPU设备: {gpu_data.get("name", "未知")}')
                print(f'VRAM总容量: {gpu_data.get("vram_total", 0)/(1024*1024*1024):.2f} GB')
                print(f'VRAM可用容量: {gpu_data.get("vram_free", 0)/(1024*1024*1024):.2f} GB')
                print(f'GPU利用率: {gpu_data.get("utilization", 0)}%')
                print('✅ 当前使用GPU进行生成')
            else:
                print('❌ 未检测到GPU，使用CPU进行生成')
        else:
            print(f'❌ ComfyUI服务返回错误状态: {response.status_code}')
    except requests.exceptions.ConnectionError:
        print('❌ 无法连接到ComfyUI服务')
    except Exception as e:
        print(f'❌ 检查ComfyUI状态时出错: {e}')

if __name__ == '__main__':
    check_comfyui_status()
