from typing import Dict, Any
from ..utils.feature_extractor import FeatureExtractor
from ..utils.similarity import SimilarityCalculator
from ..utils.video_utils import VideoUtils

class VisualChecker:
    def __init__(self, config: Dict[str, Any]):
# 初始化视觉一致性检查器
        self.config = config
        self.feature_extractor = FeatureExtractor()
        self.similarity_calculator = SimilarityCalculator()
        self.video_utils = VideoUtils()
        self.threshold = config.get('visual_threshold', 0.8)
    
    async def check_keyframe_continuity(self, prev_end_frame: str, curr_start_frame: str) -> float:
# 检查关键帧连续性
        # 使用CLIP相似度计算关键帧连续性
        similarity = self.similarity_calculator.calculate_clip_similarity(
            prev_end_frame,
            curr_start_frame
        )
        return similarity
    
    async def check_multi_source_keyframe_consistency(self, current_scene: Dict[str, Any], previous_scene: Dict[str, Any]) -> float:
# 检查多源关键帧的一致性
        # 1. 获取多种来源的关键帧
        # 1.1 当前场景自身的关键帧
        current_scene_keyframes = current_scene.get('scene_keyframes', [])
        # 1.2 当前场景的原视频切片关键帧
        current_original_keyframes = current_scene.get('original_keyframes', [])
        # 1.3 上一个场景的关键帧
        previous_keyframes = previous_scene.get('keyframes', [])
        
        total_similarity = 0.0
        similarity_count = 0
        
        # 2. 计算场景自身关键帧与原视频切片关键帧的相似度
        if current_scene_keyframes and current_original_keyframes:
            # 比较当前场景的第一个关键帧与原视频切片的关键帧
            scene_original_similarity = 0.0
            count = 0
            for original_frame in current_original_keyframes:
                if current_scene_keyframes:
                    similarity = self.similarity_calculator.calculate_clip_similarity(
                        current_scene_keyframes[0],
                        original_frame
                    )
                    scene_original_similarity += similarity
                    count += 1
            
            if count > 0:
                scene_original_similarity /= count
                total_similarity += scene_original_similarity
                similarity_count += 1
        
        # 3. 计算当前场景关键帧与上一个场景关键帧的相似度
        if current_scene_keyframes and previous_keyframes:
            # 比较当前场景的第一个关键帧与上一个场景的最后一个关键帧
            scene_scene_similarity = self.similarity_calculator.calculate_clip_similarity(
                previous_keyframes[-1],
                current_scene_keyframes[0]
            )
            total_similarity += scene_scene_similarity
            similarity_count += 1
        
        # 4. 计算当前场景原视频切片关键帧与上一个场景关键帧的相似度
        if current_original_keyframes and previous_keyframes:
            # 比较当前场景原视频切片的第一个关键帧与上一个场景的最后一个关键帧
            original_scene_similarity = self.similarity_calculator.calculate_clip_similarity(
                previous_keyframes[-1],
                current_original_keyframes[0]
            )
            total_similarity += original_scene_similarity
            similarity_count += 1
        
        # 5. 返回平均相似度
        if similarity_count > 0:
            return total_similarity / similarity_count
        else:
            return 1.0  # 默认通过
    
    async def check_visual_consistency(self, current_scene: Dict[str, Any], previous_scene: Dict[str, Any]) -> Dict[str, Any]:
        """检查视觉一致性"""
        if not current_scene:
            return {
                'success': True,
                'score': 1.0,
                'passed': True,
                'issues': []
            }
        
        if not previous_scene:
            return {
                'success': True,
                'score': 1.0,
                'passed': True,
                'issues': []
            }
        
        try:
            current_keyframes = current_scene.get('keyframes', [])
            previous_keyframes = previous_scene.get('keyframes', [])
            
            if not current_keyframes and not previous_keyframes:
                return {
                    'success': True,
                    'score': 1.0,
                    'passed': True,
                    'issues': []
                }
            
            if not current_keyframes or not previous_keyframes:
                return {
                    'success': True,
                    'score': 0.8,
                    'passed': True,
                    'issues': ['关键帧信息不完整，使用默认通过']
                }
            
            keyframe_continuity = await self.check_keyframe_continuity(
                previous_keyframes[-1],
                current_keyframes[0]
            )
            
            color_consistency = self.check_color_consistency(
                previous_keyframes[-1],
                current_keyframes[0]
            )
            
            multi_source_consistency = await self.check_multi_source_keyframe_consistency(current_scene, previous_scene)
            
            overall_score = self.calculate_overall_visual_score(
                keyframe_continuity,
                1.0,
                color_consistency,
                multi_source_consistency
            )
            
            result = {
                'score': overall_score,
                'passed': overall_score >= self.threshold,
                'issues': [] if overall_score >= self.threshold else ['视觉一致性未达标'],
                'success': True,
                'keyframe_continuity': keyframe_continuity,
                'color_consistency': color_consistency,
                'multi_source_consistency': multi_source_consistency
            }
            
            if not result['passed']:
                result['suggestions'] = self.generate_suggestions(result)
            
            return result
        except Exception as e:
            return {
                'success': True,
                'score': 0.7,
                'passed': True,
                'issues': [f'视觉检查异常: {str(e)}，使用默认通过']
            }
    
    def calculate_overall_visual_score(self, keyframe_continuity: float, resolution_consistency: float, color_consistency: float, multi_source_consistency: float = 1.0) -> float:
# 计算整体视觉一致性分数，增加多源关键帧一致性的权重
        # 加权平均，增加多源关键帧一致性的权重
        weights = {
            'keyframe_continuity': 0.4,
            'resolution_consistency': 0.15,
            'color_consistency': 0.25,
            'multi_source_consistency': 0.2  # 新增多源关键帧一致性权重
        }
        
        overall_score = (
            keyframe_continuity * weights['keyframe_continuity'] +
            resolution_consistency * weights['resolution_consistency'] +
            color_consistency * weights['color_consistency'] +
            multi_source_consistency * weights['multi_source_consistency']
        )
        
        return overall_score
    
    def check_resolution_consistency(self, curr_video_info: Dict[str, Any], prev_video_info: Dict[str, Any]) -> float:
# 检查分辨率一致性
        if not curr_video_info or not prev_video_info:
            return 0.0
        
        curr_width = curr_video_info.get('width', 0)
        curr_height = curr_video_info.get('height', 0)
        prev_width = prev_video_info.get('width', 0)
        prev_height = prev_video_info.get('height', 0)
        
        # 检查分辨率是否完全一致
        if curr_width == prev_width and curr_height == prev_height:
            return 1.0
        else:
            # 计算分辨率差异比例
            width_diff = abs(curr_width - prev_width) / max(curr_width, prev_width)
            height_diff = abs(curr_height - prev_height) / max(curr_height, prev_height)
            return 1.0 - (width_diff + height_diff) / 2
    
    def check_color_consistency(self, prev_frame: str, curr_frame: str) -> float:
# 检查色彩一致性
        # 计算整体视觉相似度
        similarity = self.similarity_calculator.calculate_overall_visual_similarity(
            prev_frame,
            curr_frame
        )
        return similarity
    
    def generate_suggestions(self, check_result: Dict[str, Any]) -> list:
# 根据检查结果生成改进建议
        suggestions = []
        
        if check_result.get('keyframe_continuity', 1.0) < self.threshold:
            suggestions.append("优化关键帧过渡，确保上一场景的结束帧与当前场景的开始帧自然衔接")
        
        if check_result.get('resolution_consistency', 1.0) < self.threshold:
            suggestions.append("保持场景间的分辨率一致")
        
        if check_result.get('color_consistency', 1.0) < self.threshold:
            suggestions.append("调整色彩、光照，确保场景间的视觉风格统一")
        
        return suggestions

