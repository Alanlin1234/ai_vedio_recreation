#!/usr/bin/env python3
"""
抖音爬虫服务启动脚本
用于启动Douyin_TikTok_Download_API爬虫服务
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def check_crawler_service():
    """检查爬虫服务是否正常运行"""
    try:
        response = requests.get("http://localhost:8081/api/douyin/web/fetch_hot_search_result", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_crawler_service():
    """启动爬虫服务"""
    crawler_path = Path("d:/ai-agent-comfy/backend/crawler/Douyin_TikTok_Download_API-main")
    
    if not crawler_path.exists():
        print("❌ 爬虫项目目录不存在，请先解压爬虫压缩包")
        return False
    
    # 检查requirements.txt是否存在
    requirements_file = crawler_path / "requirements.txt"
    if not requirements_file.exists():
        print("❌ requirements.txt文件不存在")
        return False
    
    # 检查start.py是否存在
    start_file = crawler_path / "start.py"
    if not start_file.exists():
        print("❌ start.py文件不存在")
        return False
    
    print("🚀 正在启动抖音爬虫服务...")
    
    try:
        # 切换到爬虫目录
        os.chdir(str(crawler_path))
        
        # 安装依赖（如果尚未安装）
        print("📦 检查依赖包...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True, text=True)
        
        # 启动爬虫服务
        print("🔥 启动爬虫服务...")
        process = subprocess.Popen([sys.executable, "start.py"], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE,
                                 text=True)
        
        # 等待服务启动
        print("⏳ 等待服务启动...")
        for i in range(30):  # 最多等待30秒
            if check_crawler_service():
                print("✅ 爬虫服务启动成功！")
                print(f"📊 服务地址: http://localhost:80")
                print(f"📚 API文档: http://localhost:80/docs")
                return True
            time.sleep(1)
        
        print("❌ 爬虫服务启动超时")
        return False
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        if e.stderr:
            print(f"错误信息: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ 启动爬虫服务失败: {e}")
        return False

def stop_crawler_service():
    """停止爬虫服务"""
    print("🛑 正在停止爬虫服务...")
    
    # 查找并终止相关进程
    try:
        # Windows系统使用taskkill命令
        subprocess.run(["taskkill", "/F", "/IM", "python.exe"], 
                      capture_output=True, text=True)
        print("✅ 爬虫服务已停止")
    except Exception as e:
        print(f"❌ 停止爬虫服务失败: {e}")

def main():
    """主函数"""
    print("=" * 50)
    print("🎯 抖音爬虫服务管理工具")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action == "start":
            start_crawler_service()
        elif action == "stop":
            stop_crawler_service()
        elif action == "status":
            if check_crawler_service():
                print("✅ 爬虫服务正在运行")
            else:
                print("❌ 爬虫服务未运行")
        else:
            print("用法: python start_crawler.py [start|stop|status]")
    else:
        # 交互式模式
        print("请选择操作:")
        print("1. 启动爬虫服务")
        print("2. 停止爬虫服务")
        print("3. 检查服务状态")
        print("4. 退出")
        
        choice = input("请输入选择 (1-4): ").strip()
        
        if choice == "1":
            start_crawler_service()
        elif choice == "2":
            stop_crawler_service()
        elif choice == "3":
            if check_crawler_service():
                print("✅ 爬虫服务正在运行")
            else:
                print("❌ 爬虫服务未运行")
        elif choice == "4":
            print("👋 再见！")
        else:
            print("❌ 无效选择")

if __name__ == "__main__":
    main()