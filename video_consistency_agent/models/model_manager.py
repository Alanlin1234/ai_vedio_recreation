from typing import Dict, Any, Union
from .vlm_client import VLMClient
from .llm_client import LLMClient

class ModelManager:
    def __init__(self, config: Dict[str, Any]):
# 初始化模型管理器
        self.config = config
        self.vlm_client = VLMClient(config)
        self.llm_client = LLMClient(config)
    
    async def analyze_video_content(self, video_path: str, prompt: str) -> Dict[str, Any]:
# 调用VLM分析视频内容
        return await self.vlm_client.analyze_video_content(video_path, prompt)
    
    async def compare_scene_styles(self, scene1_path: str, scene2_path: str) -> Dict[str, Any]:
# 比较两个场景的风格一致性
        return await self.vlm_client.compare_scene_styles(scene1_path, scene2_path)
    
    async def describe_scene_content(self, video_path: str) -> Dict[str, Any]:
# 描述场景内容
        return await self.vlm_client.describe_scene_content(video_path)
    
    async def analyze_keyframe_content(self, keyframe_path: str) -> Dict[str, Any]:
# 分析关键帧内容
        return await self.vlm_client.analyze_keyframe_content(keyframe_path)
    
    async def analyze_content_coherence(self, scene1_desc: str, scene2_desc: str) -> Dict[str, Any]:
# 分析场景间的内容连贯性
        return await self.llm_client.analyze_content_coherence(scene1_desc, scene2_desc)
    
    async def generate_optimized_prompt(self, original_prompt: str, issues: list) -> Dict[str, Any]:
# 生成优化后的prompt
        return await self.llm_client.generate_optimized_prompt(original_prompt, issues)
    
    async def evaluate_scene_logic(self, scene_sequence: list) -> Dict[str, Any]:
# 评估场景序列的逻辑一致性
        return await self.llm_client.evaluate_scene_logic(scene_sequence)
    
    async def generate_consistency_report(self, consistency_results: Dict[str, Any]) -> Dict[str, Any]:
# 生成一致性检查报告
        return await self.llm_client.generate_consistency_report(consistency_results)

