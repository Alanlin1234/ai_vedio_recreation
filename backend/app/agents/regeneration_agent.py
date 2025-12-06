#重新生成Agent - 处理一致性检查失败的场景

from typing import Dict, Any, List
from .base_agent import BaseAgent
import asyncio


class RegenerationAgent(BaseAgent):
    #负责重新生成一致性不足的场景
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("RegenerationAgent", config)
        self.max_retries = config.get('max_retries', 3) if config else 3
        self.consistency_threshold = config.get('consistency_threshold', 0.85) if config else 0.85
        
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        
        try:
            if not self.validate_input(input_data, ['failed_images']):
                return self.create_result(False, error="缺少失败图像数据")
            
            self.log_execution("start", "开始重新生成流程")
            
            failed_images = input_data['failed_images']
            scene_groups = input_data.get('scene_groups', {})
            original_shots = input_data.get('original_shots', [])
            workflow_config = input_data.get('workflow_config', {})
            
            # 获取代理实例
            image_gen_agent = input_data.get('image_generation_agent')
            consistency_agent = input_data.get('consistency_agent')
            
            if not image_gen_agent or not consistency_agent:
                return self.create_result(False, error="缺少必要的代理实例")
            
            # 按场景分组失败的图像
            failed_by_scene = self._group_by_scene(failed_images)
            
            # 重新生成每个失败的场景
            regenerated_images = []
            final_passed_images = []
            failed_scenes = []
            retry_stats = {
                'total_scenes': len(failed_by_scene),
                'total_retries': 0,
                'successful_regenerations': 0,
                'failed_regenerations': 0,
                'retry_details': []
            }
            
            for scene_id, scene_images in failed_by_scene.items():
                self.logger.info(f"处理场景 {scene_id}，包含 {len(scene_images)} 个失败镜头")
                
                # 重新生成场景
                result = await self._regenerate_scene(
                    scene_id=scene_id,
                    failed_images=scene_images,
                    original_shots=original_shots,
                    workflow_config=workflow_config,
                    image_gen_agent=image_gen_agent,
                    consistency_agent=consistency_agent
                )
                
                regenerated_images.extend(result['regenerated'])
                final_passed_images.extend(result['passed'])
                
                if result['failed']:
                    failed_scenes.append({
                        'scene_id': scene_id,
                        'failed_images': result['failed'],
                        'retry_count': result['retry_count']
                    })
                
                # 更新统计
                retry_stats['total_retries'] += result['retry_count']
                if result['passed']:
                    retry_stats['successful_regenerations'] += 1
                else:
                    retry_stats['failed_regenerations'] += 1
                
                retry_stats['retry_details'].append({
                    'scene_id': scene_id,
                    'retry_count': result['retry_count'],
                    'success': len(result['passed']) > 0,
                    'passed_count': len(result['passed']),
                    'failed_count': len(result['failed'])
                })
            
            self.log_execution(
                "complete",
                f"重新生成完成: {retry_stats['successful_regenerations']}/{retry_stats['total_scenes']} 场景成功"
            )
            
            return self.create_result(True, {
                'regenerated_images': regenerated_images,
                'final_passed_images': final_passed_images,
                'failed_scenes': failed_scenes,
                'retry_stats': retry_stats
            })
            
        except Exception as e:
            self.logger.error(f"重新生成失败: {str(e)}")
            return self.create_result(False, error=str(e))
    
    def _group_by_scene(self, images: List[Dict]) -> Dict[int, List[Dict]]:
        """按场景分组图像"""
        grouped = {}
        for img in images:
            scene_id = img.get('scene_id', 0)
            if scene_id not in grouped:
                grouped[scene_id] = []
            grouped[scene_id].append(img)
        return grouped
    
    async def _regenerate_scene(
        self,
        scene_id: int,
        failed_images: List[Dict],
        original_shots: List[Dict],
        workflow_config: Dict,
        image_gen_agent,
        consistency_agent
    ) -> Dict[str, Any]:
        """
        重新生成单个场景，直到一致性达标或达到最大重试次数
        
        Returns:
            {
                'regenerated': List[Dict] - 所有重新生成的图像
                'passed': List[Dict] - 通过一致性检查的图像
                'failed': List[Dict] - 仍然失败的图像
                'retry_count': int - 重试次数
            }
        """
        regenerated = []
        passed = []
        current_failed = failed_images
        retry_count = 0
        
        for attempt in range(self.max_retries):
            retry_count += 1
            self.logger.info(f"场景 {scene_id} 第 {attempt + 1}/{self.max_retries} 次重新生成")
            
            # 准备重新生成的镜头数据
            shots_to_regenerate = self._prepare_shots_for_regeneration(
                current_failed,
                original_shots,
                attempt,
                workflow_config
            )
            
            # 调用图像生成代理
            gen_result = await image_gen_agent.execute({
                'shots_with_references': shots_to_regenerate,
                'workflow': workflow_config,
                'batch_size': 1
            })
            
            if not gen_result['success']:
                self.logger.error(f"场景 {scene_id} 重新生成失败: {gen_result.get('error')}")
                continue
            
            new_images = gen_result['data']['generated_images']
            regenerated.extend(new_images)
            
            # 检查场景内一致性
            consistency_result = await self._check_scene_consistency(
                scene_id,
                new_images,
                consistency_agent
            )
            
            if not consistency_result['success']:
                self.logger.error(f"场景 {scene_id} 一致性检查失败")
                current_failed = new_images
                continue
            
            # 分离通过和失败的图像
            scene_passed = consistency_result['data']['passed_images']
            scene_failed = consistency_result['data']['failed_images']
            
            passed.extend(scene_passed)
            current_failed = scene_failed
            
            # 如果所有图像都通过，退出循环
            if not current_failed:
                self.logger.info(f"场景 {scene_id} 在第 {attempt + 1} 次尝试后全部通过")
                break
            
            # 如果还有失败的，继续下一次尝试
            self.logger.warning(
                f"场景 {scene_id} 仍有 {len(current_failed)} 个镜头未通过，"
                f"继续重试..."
            )
        
        # 达到最大重试次数
        if current_failed:
            self.logger.warning(
                f"场景 {scene_id} 在 {self.max_retries} 次尝试后仍有 "
                f"{len(current_failed)} 个镜头未通过一致性检查"
            )
        
        return {
            'regenerated': regenerated,
            'passed': passed,
            'failed': current_failed,
            'retry_count': retry_count
        }
    
    def _prepare_shots_for_regeneration(
        self,
        failed_images: List[Dict],
        original_shots: List[Dict],
        attempt: int,
        workflow_config: Dict
    ) -> List[Dict]:
        """
        准备重新生成的镜头数据
        
        在每次重试时，调整参数以提高一致性
        """
        shots = []
        
        for img in failed_images:
            shot_id = img.get('shot_id')
            
            # 找到原始镜头信息
            original_shot = next(
                (s for s in original_shots if s.get('shot_id') == shot_id),
                None
            )
            
            if not original_shot:
                self.logger.warning(f"未找到镜头 {shot_id} 的原始信息")
                continue
            
            # 优化提示词以提高一致性
            optimized_prompt = self._optimize_prompt_for_consistency(
                original_shot.get('prompt', ''),
                img.get('consistency_score', 0),
                attempt,
                workflow_config
            )
            
            # 调整生成参数
            adjusted_params = self._adjust_generation_params(
                workflow_config,
                attempt
            )
            
            shot_data = {
                'shot_id': shot_id,
                'scene_id': img.get('scene_id'),
                'prompt': optimized_prompt,
                'original_prompt': original_shot.get('prompt'),
                'references': original_shot.get('references', []),
                'shot_type': original_shot.get('shot_type'),
                'duration': original_shot.get('duration', 3.0),
                'retry_attempt': attempt + 1,
                **adjusted_params
            }
            
            shots.append(shot_data)
        
        return shots
    
    def _optimize_prompt_for_consistency(
        self,
        original_prompt: str,
        consistency_score: float,
        attempt: int,
        workflow_config: Dict
    ) -> str:
        """
        优化提示词以提高一致性
        
        策略：
        1. 添加更强的风格约束
        2. 增加细节描述
        3. 强调一致性关键词
        """
        # 获取风格前缀
        style_prefix = workflow_config.get('style_prefix', '')
        
        # 根据尝试次数增加约束强度
        if attempt == 0:
            # 第一次重试：添加基础风格约束
            consistency_keywords = "consistent style, uniform lighting"
        elif attempt == 1:
            # 第二次重试：增强约束
            consistency_keywords = "highly consistent style, matching color palette, uniform lighting, coherent composition"
        else:
            # 第三次及以后：最强约束
            consistency_keywords = "extremely consistent style, identical color grading, perfectly matching lighting, coherent visual language, unified aesthetic"
        
        # 组合提示词
        if style_prefix:
            optimized = f"{style_prefix}, {consistency_keywords}, {original_prompt}"
        else:
            optimized = f"{consistency_keywords}, {original_prompt}"
        
        return optimized
    
    def _adjust_generation_params(
        self,
        workflow_config: Dict,
        attempt: int
    ) -> Dict[str, Any]:
        """
        调整生成参数以提高一致性
        
        策略：
        1. 降低 CFG Scale（减少创造性，提高一致性）
        2. 增加采样步数（提高质量）
        3. 使用固定种子（如果需要）
        """
        params = workflow_config.copy()
        
        # 基础 CFG Scale
        base_cfg = params.get('cfg_scale', 3.5)
        
        # 根据尝试次数调整
        if attempt == 0:
            # 第一次：略微降低 CFG
            params['cfg_scale'] = max(2.0, base_cfg - 0.5)
        elif attempt == 1:
            # 第二次：进一步降低 CFG
            params['cfg_scale'] = max(1.5, base_cfg - 1.0)
        else:
            # 第三次及以后：最低 CFG
            params['cfg_scale'] = max(1.0, base_cfg - 1.5)
        
        # 增加采样步数
        base_steps = params.get('steps', 25)
        params['steps'] = base_steps + (attempt * 5)
        
        # 添加更强的负面提示词
        base_negative = params.get('negative_prompt', '')
        consistency_negative = "inconsistent style, varying lighting, different color palette, mismatched aesthetic"
        params['negative_prompt'] = f"{base_negative}, {consistency_negative}"
        
        return params
    
    async def _check_scene_consistency(
        self,
        scene_id: int,
        images: List[Dict],
        consistency_agent
    ) -> Dict[str, Any]:
        """
        检查场景内的一致性
        
        重点检查：
        1. 场景内镜头的风格一致性
        2. 与场景阈值（0.85）的比较
        """
        try:
            # 调用一致性检查代理
            result = await consistency_agent.execute({
                'generated_images': images,
                'storyboard': []  # 场景内检查不需要完整分镜
            })
            
            if not result['success']:
                return result
            
            # 应用场景一致性阈值（0.85）
            passed_images = []
            failed_images = []
            
            for img in images:
                consistency_score = img.get('consistency_score', 0)
                
                if consistency_score >= self.consistency_threshold:
                    passed_images.append(img)
                    self.logger.info(
                        f"镜头 {img.get('shot_id')} 通过一致性检查 "
                        f"(得分: {consistency_score:.3f})"
                    )
                else:
                    failed_images.append(img)
                    self.logger.warning(
                        f"镜头 {img.get('shot_id')} 未通过一致性检查 "
                        f"(得分: {consistency_score:.3f}, 阈值: {self.consistency_threshold})"
                    )
            
            return self.create_result(True, {
                'passed_images': passed_images,
                'failed_images': failed_images,
                'scene_consistency_score': result['data'].get('overall_score', 0)
            })
            
        except Exception as e:
            self.logger.error(f"场景一致性检查失败: {str(e)}")
            return self.create_result(False, error=str(e))
    
    def _analyze_failure_reasons(self, failed_images: List[Dict]) -> Dict[str, Any]:
        """分析失败原因"""
        reasons = {
            'low_style_consistency': 0,
            'low_character_consistency': 0,
            'low_scene_consistency': 0,
            'low_quality': 0,
            'generation_error': 0
        }
        
        for img in failed_images:
            if not img.get('success'):
                reasons['generation_error'] += 1
                continue
            
            score = img.get('consistency_score', 0)
            
            # 简单分类（实际应该根据详细的一致性报告）
            if score < 0.7:
                reasons['low_quality'] += 1
            elif score < 0.8:
                reasons['low_scene_consistency'] += 1
            else:
                reasons['low_style_consistency'] += 1
        
        return reasons
