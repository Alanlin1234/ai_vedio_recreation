#!/usr/bin/env python3
"""
诊断GPU利用率低的原因
"""

import requests
import json
import subprocess
import psutil

def check_comfyui_status():
    """检查ComfyUI状态"""
    print("=== 1. 检查ComfyUI状态 ===")
    try:
        response = requests.get('http://127.0.0.1:8188/system_stats', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ ComfyUI服务正常运行")
            print(f"   版本: {data['system']['comfyui_version']}")
            print(f"   PyTorch: {data['system']['pytorch_version']}")
            print(f"   运行参数: {data['system']['argv']}")
            
            # 检查GPU设备
            if 'devices' in data:
                for i, device in enumerate(data['devices']):
                    print(f"\n   GPU设备 {i}:")
                    print(f"      名称: {device.get('name', '未知')}")
                    print(f"      类型: {device.get('type', '未知')}")
                    print(f"      VRAM总容量: {device.get('vram_total', 0)/1024/1024/1024:.1f} GB")
                    print(f"      VRAM可用: {device.get('vram_free', 0)/1024/1024/1024:.1f} GB")
            else:
                print("❌ 未检测到GPU设备")
        else:
            print(f"❌ ComfyUI返回错误状态: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到ComfyUI服务")
    except Exception as e:
        print(f"❌ 检查ComfyUI时出错: {e}")

def check_system_resources():
    """检查系统资源使用情况"""
    print("\n=== 2. 系统资源使用情况 ===")
    
    # CPU使用率
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"CPU使用率: {cpu_percent}%")
    if cpu_percent > 80:
        print("   ⚠️ CPU使用率过高，可能导致GPU瓶颈")
    
    # 内存使用情况
    mem = psutil.virtual_memory()
    print(f"内存使用率: {mem.percent}%")
    print(f"可用内存: {mem.available/1024/1024/1024:.1f} GB")
    if mem.percent > 80:
        print("   ⚠️ 内存使用率过高")
    
    # 磁盘IO
    disk = psutil.disk_io_counters()
    print(f"磁盘读取: {disk.read_bytes/1024/1024:.1f} MB")
    print(f"磁盘写入: {disk.write_bytes/1024/1024:.1f} MB")

def check_nvidia_smi():
    """检查NVIDIA GPU状态"""
    print("\n=== 3. NVIDIA GPU状态 (nvidia-smi) ===")
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ NVIDIA GPU驱动正常")
            # 提取关键信息
            lines = result.stdout.split('\n')
            for line in lines:
                if 'CUDA Version' in line:
                    print(f"   {line.strip()}")
                if 'NVIDIA GeForce' in line:
                    print(f"   {line.strip()}")
                if 'Memory-Usage' in line:
                    print(f"   {line.strip()}")
                if 'GPU-Util' in line:
                    print(f"   {line.strip()}")
        else:
            print("❌ 执行nvidia-smi失败")
    except FileNotFoundError:
        print("❌ 未安装nvidia-smi")
    except Exception as e:
        print(f"❌ 检查NVIDIA GPU时出错: {e}")

def check_running_processes():
    """检查占用GPU的进程"""
    print("\n=== 4. 检查占用GPU的进程 ===")
    try:
        result = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory', '--format=csv,noheader'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if lines and len(lines[0]) > 0:
                print("占用GPU的进程:")
                for line in lines:
                    pid, name, memory = line.strip().split(', ')
                    print(f"   PID {pid}: {name} - 已用内存: {memory}")
            else:
                print("   目前没有占用GPU计算的进程")
        else:
            print("❌ 执行nvidia-smi进程查询失败")
    except Exception as e:
        print(f"❌ 检查GPU进程时出错: {e}")

def check_generation_params():
    """检查生成参数建议"""
    print("\n=== 5. 生成参数优化建议 ===")
    print("建议的优化参数：")
    print("   - 分辨率: 1920x1080")
    print("   - 采样步骤: 30-40步")
    print("   - 采样器: DPM++ 2M Karras")
    print("   - 批量大小: 1-2")
    print("   - 启用xformers或flash attention")
    print("   - 减少CPU密集型预处理")

def main():
    """主函数"""
    print("开始诊断GPU利用率低的原因...\n")
    
    check_comfyui_status()
    check_system_resources()
    check_nvidia_smi()
    check_running_processes()
    check_generation_params()
    
    print("\n=== 6. 综合分析 ===")
    print("GPU利用率低的可能原因：")
    print("1. 生成参数设置不合理（分辨率过低、采样步骤少）")
    print("2. 存在CPU瓶颈（CPU利用率接近100%）")
    print("3. 未启用GPU优化选项（如xformers）")
    print("4. 生成处于非GPU密集阶段")
    print("5. 系统资源不足（内存或磁盘瓶颈）")
    print("6. 工作流设计问题（包含太多CPU节点）")
    
    print("\n优化建议：")
    print("1. 调整生成参数，增加GPU工作量")
    print("2. 关闭其他占用资源的程序")
    print("3. 在ComfyUI中启用xformers")
    print("4. 优化工作流，减少CPU密集型操作")
    print("5. 确保足够的系统内存")
    print("6. 监控生成过程，确认是否处于GPU密集阶段")

if __name__ == '__main__':
    main()
