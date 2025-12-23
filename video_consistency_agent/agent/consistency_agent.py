from typing import Dict, Any, List
import yaml
import os

from .perception import PerceptionModule
from .analysis import AnalysisModule
from .decision import DecisionModule
from .feedback import FeedbackModule

class ConsistencyAgent:
    def __init__(self, config_path: str):
# 初始化一致性检查Agent
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 初始化各模块
        self.perception = PerceptionModule(self.config)
        self.analysis = AnalysisModule(self.config)
        self.decision = DecisionModule(self.config)
        self.feedback = FeedbackModule(self.config)
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
# 加载配置文件
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config
    
    async def check_consistency(self, current_scene: Dict[str, Any], previous_scene: Dict[str, Any], prompt_data: Dict[str, Any]) -> Dict[str, Any]:
# 检查场景一致性
        try:
            # 1. 感知阶段：获取场景信息
            # 1.1 获取当前场景的多源关键帧信息
            current_scene_with_keyframes = self.perception.extract_multi_source_keyframes(current_scene)
            current_scene_info = self.perception.get_scene_info(current_scene_with_keyframes)
            
            # 1.2 获取上一场景信息
            prev_scene_info = self.perception.get_prev_scene_info(previous_scene)
            
            # 1.3 解析提示词信息
            parsed_prompt = self.perception.parse_prompt_info(prompt_data)
            
            # 2. 分析阶段：评估一致性
            consistency_results = await self.analysis.evaluate_consistency(current_scene_info, prev_scene_info)
            
            # 3. 决策阶段：生成优化策略
            optimization_strategy = self.decision.generate_optimization_strategy(consistency_results)
            
            # 4. 反馈阶段：生成优化建议
            optimization_feedback = self.feedback.generate_optimization_feedback(
                consistency_results, 
                parsed_prompt['original_prompt'], 
                parsed_prompt['generation_params']
            )
            
            # 5. 整合结果
            final_result = {
                'consistency_results': consistency_results,
                'optimization_strategy': optimization_strategy,
                'optimization_feedback': optimization_feedback,
                'passed': consistency_results['passed']
            }
            
            return final_result
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'passed': False
            }
    
    async def run_check_loop(self, video_generation_pipeline, scene_data: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
# 运行一致性检查循环
        retry_count = 0
        current_scene = scene_data.copy()
        
        while retry_count <= max_retries:
            # 获取前一场景
            previous_scene = video_generation_pipeline.get_previous_scene(current_scene['order'] - 1)
            
            # 检查一致性
            check_result = await self.check_consistency(
                current_scene,
                previous_scene,
                current_scene.get('prompt_data', {})
            )
            
            if check_result['passed']:
                # 一致性检查通过
                return {
                    'status': 'success',
                    'message': '一致性检查通过',
                    'scene': current_scene,
                    'retry_count': retry_count
                }
            
            # 检查是否达到最大重试次数
            if retry_count >= max_retries:
                return {
                    'status': 'failure',
                    'message': f'已达到最大重试次数: {max_retries}',
                    'scene': current_scene,
                    'retry_count': retry_count,
                    'check_result': check_result
                }
            
            # 获取优化建议
            optimized_prompt = check_result['optimization_feedback']['optimized_prompt']
            adjusted_params = check_result['optimization_feedback']['adjusted_params']
            
            # 更新场景数据
            current_scene['prompt_data']['optimized_prompt'] = optimized_prompt
            current_scene['prompt_data']['generation_params'] = adjusted_params
            
            # 重新生成视频
            regenerated_scene = await video_generation_pipeline.regenerate_scene(
                current_scene['order'],
                optimized_prompt,
                adjusted_params
            )
            
            # 更新当前场景
            current_scene = regenerated_scene
            retry_count += 1
        
        return {
            'status': 'failure',
            'message': '一致性检查失败',
            'scene': current_scene,
            'retry_count': retry_count,
            'check_result': check_result
        }

