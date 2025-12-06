#!/usr/bin/env python3
"""
测试GPU利用率，执行一个视频生成任务
"""

import requests
import json
import time
import subprocess

def get_current_gpu_utilization():
    """获取当前GPU利用率"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            utilization = result.stdout.strip()
            return int(utilization) if utilization else 0
    except Exception:
        return -1
    return -1

def test_video_generation():
    """测试视频生成任务"""
    print("=== 测试GPU利用率 ===")
    
    # 检查ComfyUI是否运行
    try:
        response = requests.get('http://127.0.0.1:8188/system_stats', timeout=5)
        if response.status_code != 200:
            print("❌ ComfyUI未运行")
            return
    except requests.ConnectionError:
        print("❌ ComfyUI未运行")
        return
    
    # 测试简单的图像生成
    print("\n1. 当前GPU利用率:")
    initial_util = get_current_gpu_utilization()
    if initial_util >= 0:
        print(f"   当前利用率: {initial_util}%")
    else:
        print("   无法获取GPU利用率")
    
    print("\n2. 开始测试图像生成任务...")
    
    # 简单的生成工作流（1024x1024图像，20步）
    prompt = {
        "3": {
            "inputs": {
                "seed": 12345,
                "steps": 20,
                "cfg": 8.0,
                "sampler_name": "dpmpp_2m_karras",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["7", 0]
            },
            "class_type": "KSampler",
            "_meta": {"title": "KSampler"}
        },
        "4": {
            "inputs": {
                "ckpt_name": "SDXL\sd_xl_base_1.0.safetensors"
            },
            "class_type": "CheckpointLoaderSimple",
            "_meta": {"title": "Load Checkpoint"}
        },
        "5": {
            "inputs": {
                "text": "beautiful landscape, mountains, lake, sunset",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "CLIP Text Encode (Pos)"}
        },
        "6": {
            "inputs": {
                "text": "ugly, bad quality, blurry, low resolution",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "CLIP Text Encode (Neg)"}
        },
        "7": {
            "inputs": {
                "width": 1024,
                "height": 1024,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage",
            "_meta": {"title": "Empty Latent Image"}
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode",
            "_meta": {"title": "VAE Decode"}
        },
        "9": {
            "inputs": {
                "filename_prefix": "test",
                "images": ["8", 0]
            },
            "class_type": "SaveImage",
            "_meta": {"title": "Save Image"}
        }
    }
    
    try:
        # 提交生成任务
        response = requests.post(
            'http://127.0.0.1:8188/prompt',
            json={'prompt': prompt},
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ 提交任务失败: {response.status_code}")
            return
        
        prompt_id = response.json().get('prompt_id')
        print(f"   任务已提交，ID: {prompt_id}")
        
        # 监控GPU利用率
        print("\n3. 监控GPU利用率 (持续10秒):")
        max_util = 0
        for i in range(10):
            util = get_current_gpu_utilization()
            if util >= 0:
                print(f"   {i+1}s: {util}%")
                if util > max_util:
                    max_util = util
            time.sleep(1)
        
        print(f"\n4. 测试结果:")
        print(f"   初始GPU利用率: {initial_util}%")
        print(f"   最大GPU利用率: {max_util}%")
        
        if max_util > 50:
            print("   ✅ GPU利用率正常，任务运行良好")
        elif max_util > 20:
            print("   ⚠️ GPU利用率适中，可能需要调整参数")
        else:
            print("   ❌ GPU利用率过低，可能存在问题")
            print("   建议检查:")
            print("   - 模型是否正确加载")
            print("   - 生成参数是否合理")
            print("   - 系统内存是否充足")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到ComfyUI")
    except json.JSONDecodeError:
        print("❌ ComfyUI返回无效JSON")
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")

def main():
    """主函数"""
    test_video_generation()
    
    print("\n=== 完成测试 ===")

if __name__ == '__main__':
    main()
