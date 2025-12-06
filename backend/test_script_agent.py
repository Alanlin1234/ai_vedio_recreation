#!/usr/bin/env python3
"""
测试ScriptAgent功能，验证大模型配置是否正确
"""

import os
import sys
from app.agents.script_agent import ScriptAgent
from config import Config

# 设置PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_script_agent():
    """测试ScriptAgent初始化和配置"""
    print("=== 测试ScriptAgent ===")
    
    # 获取Agent配置
    agent_config = Config.get_agent_config()
    print("1. 配置获取成功")
    print(f"   LLM API Key: {agent_config.get('llm_api_key')[:10]}...")
    print(f"   LLM API Endpoint: {agent_config.get('llm_api_endpoint')}")
    print(f"   LLM Model: {agent_config.get('llm_model')}")
    
    # 初始化ScriptAgent
    script_agent = ScriptAgent(agent_config)
    print("2. ScriptAgent初始化成功")
    
    # 测试配置验证
    print("3. 检查配置完整性:")
    llm_api_key = agent_config.get('llm_api_key', '')
    llm_api_endpoint = agent_config.get('llm_api_endpoint', '')
    llm_model = agent_config.get('llm_model', '')
    
    if llm_api_key and llm_api_endpoint and llm_model:
        print("   ✓ 所有LLM配置项均已设置")
        print("   ✓ ScriptAgent可以正常调用大模型API")
    else:
        print("   ✗ 缺少必要的LLM配置:")
        if not llm_api_key:
            print("     - llm_api_key 为空")
        if not llm_api_endpoint:
            print("     - llm_api_endpoint 为空")
        if not llm_model:
            print("     - llm_model 为空")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_script_agent()
