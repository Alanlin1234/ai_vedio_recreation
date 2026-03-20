#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
内容生成服务
提供新故事生成、亮点扩展、教育意义扩展等功能
"""

import os
import sys
from typing import Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config import config
from app.services.video_analysis_agent import DashScopeChatModel

class ContentGenerationService:
    
    def __init__(self, api_key: str = None, model_name: str = "qwen-max-latest"):
        self.llm = DashScopeChatModel(
            api_key=api_key or config.DASHSCOPE_API_KEY,
            model_name=model_name
        )
    
    def generate_new_script(
        self, 
        video_understanding: str, 
        original_script: str
    ) -> Dict[str, Any]:
        try:
            messages = [
                SystemMessage(content="""你是一个专业的故事创作者，擅长基于现有视频内容创作新的故事。
要求：
1. 保持原故事的核心主题和价值观
2. 可以适当扩展情节，增加趣味性
3. 语言要生动有趣，适合视频讲述
4. 保持故事的连贯性和逻辑性
5. 字数控制在500-1000字左右"""),
                HumanMessage(content=f"""请基于以下视频理解内容，创作一个新的故事：

视频理解内容：
{video_understanding}

原始文案（参考）：
{original_script}

请创作一个新的、更加生动有趣的故事版本。""")
            ]
            
            result = self.llm.generate([messages])
            new_script = result.generations[0][0].message.content
            
            return {
                'success': True,
                'new_script': new_script
            }
        except Exception as e:
            print(f"生成新故事失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'new_script': original_script or video_understanding
            }
    
    def _expand_highlights(
        self, 
        original_highlights: str, 
        new_story: str
    ) -> Dict[str, str]:
        try:
            messages = [
                SystemMessage(content="""你是一个专业的故事分析专家，擅长提炼和扩展故事亮点。
要求：
1. 结合新故事内容，扩展或重写故事亮点
2. 每个亮点用一句话描述
3. 突出故事的精彩之处和创新点
4. 保持语言的生动性和吸引力"""),
                HumanMessage(content=f"""请基于以下内容，扩展故事亮点：

原始亮点（参考）：
{original_highlights}

新故事内容：
{new_story}

请生成新的、更加精彩的故事亮点。""")
            ]
            
            result = self.llm.generate([messages])
            expanded_highlights = result.generations[0][0].message.content
            
            return {
                'success': True,
                'expanded_highlights': expanded_highlights
            }
        except Exception as e:
            print(f"扩展故事亮点失败: {e}")
            return {
                'success': False,
                'expanded_highlights': original_highlights or '这个新故事在原有基础上进行了创新和扩展，情节更加生动有趣，给人全新的感受。',
                'error': str(e)
            }
    
    def _expand_educational_meaning(
        self, 
        original_educational: str, 
        new_story: str
    ) -> Dict[str, str]:
        try:
            messages = [
                SystemMessage(content="""你是一个专业的教育专家，擅长挖掘和扩展故事的教育意义。
要求：
1. 结合新故事内容，扩展或重写教育意义
2. 从品德、知识、生活智慧等多角度分析
3. 每个教育意义用一段话描述
4. 保持教育意义的深度和启发性"""),
                HumanMessage(content=f"""请基于以下内容，扩展教育意义：

原始教育意义（参考）：
{original_educational}

新故事内容：
{new_story}

请生成新的、更加深刻的教育意义。""")
            ]
            
            result = self.llm.generate([messages])
            expanded_educational = result.generations[0][0].message.content
            
            return {
                'success': True,
                'expanded_educational': expanded_educational
            }
        except Exception as e:
            print(f"扩展教育意义失败: {e}")
            return {
                'success': False,
                'expanded_educational': original_educational or '这个新故事教会我们更多的道理，鼓励我们在生活中保持善良、勇敢和智慧，用积极的心态面对挑战。',
                'error': str(e)
            }

# 保持向后兼容性
__all__ = ['ContentGenerationService']
