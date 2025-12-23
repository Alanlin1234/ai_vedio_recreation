from typing import Dict, Any
from ..utils.video_utils import VideoUtils

class TemporalChecker:
    def __init__(self, config: Dict[str, Any]):
# 初始化时序一致性检查器
        self.config = config
        self.video_utils = VideoUtils()
        self.threshold = config.get('temporal_threshold', 0.8)
    
    async def check_temporal_consistency(self, current_scene: Dict[str, Any], previous_scene: Dict[str, Any]) -> Dict[str, Any]:
# 检查时序一致性
        # 检查参数
        if not current_scene or not previous_scene:
            return {
                'success': False,
                'error': '场景信息不完整'
            }
        
        current_info = current_scene.get('video_info')
        previous_info = previous_scene.get('video_info')
        
        if not current_info or not previous_info:
            return {
                'success': False,
                'error': '视频信息不完整'
            }
        
        try:
            # 1. 检查时间线连续性
            timeline_consistency = self.check_timeline_consistency(current_info, previous_info)
            
            # 2. 检查动作流畅度
            action_smoothness = await self.check_action_smoothness(current_scene, previous_scene)
            
            # 3. 检查事件发展逻辑
            event_logic = await self.check_event_logic(current_scene, previous_scene)
            
            # 4. 计算整体时序一致性分数
            overall_score = self.calculate_overall_temporal_score(
                timeline_consistency,
                action_smoothness,
                event_logic
            )
            
            # 5. 生成检查结果
            result = {
                'score': overall_score,
                'passed': overall_score >= self.threshold,
                'issues': [] if overall_score >= self.threshold else ['时序一致性未达标'],
                'success': True,
                'timeline_consistency': timeline_consistency,
                'action_smoothness': action_smoothness,
                'event_logic': event_logic
            }
            
            # 如果不一致，添加改进建议
            if not result['passed']:
                result['suggestions'] = self.generate_suggestions(result)
            
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'score': 0.0,
                'passed': False,
                'issues': [str(e)]
            }
    
    def check_timeline_consistency(self, curr_video_info: Dict[str, Any], prev_video_info: Dict[str, Any]) -> float:
# 检查时间线连续性
        # 检查帧率一致性
        curr_fps = curr_video_info.get('fps', 0)
        prev_fps = prev_video_info.get('fps', 0)
        
        if curr_fps == 0 or prev_fps == 0:
            return 0.0
        
        # 帧率差异越小，分数越高
        fps_diff = abs(curr_fps - prev_fps) / max(curr_fps, prev_fps)
        fps_score = 1.0 - fps_diff
        
        # 检查时长合理性
        curr_duration = curr_video_info.get('duration', 0)
        prev_duration = prev_video_info.get('duration', 0)
        
        # 时长差异不应过大
        duration_diff = abs(curr_duration - prev_duration) / max(curr_duration, prev_duration)
        duration_score = 1.0 - min(duration_diff, 0.5) * 2  # 差异超过50%时，分数降为0
        
        # 综合分数
        return (fps_score * 0.6 + duration_score * 0.4)
    
    async def check_action_smoothness(self, current_scene: Dict[str, Any], previous_scene: Dict[str, Any]) -> float:
# 检查动作流畅度
        # 这里可以添加更复杂的动作分析
        # 由于是示例实现，这里返回一个默认值
        return 0.85
    
    async def check_event_logic(self, current_scene: Dict[str, Any], previous_scene: Dict[str, Any]) -> float:
# 检查事件发展逻辑
        # 这里可以添加更复杂的事件逻辑分析
        # 由于是示例实现，这里返回一个默认值
        return 0.9
    
    def calculate_overall_temporal_score(self, timeline_consistency: float, action_smoothness: float, event_logic: float) -> float:
# 计算整体时序一致性分数
        # 加权平均
        weights = {
            'timeline_consistency': 0.4,
            'action_smoothness': 0.3,
            'event_logic': 0.3
        }
        
        overall_score = (
            timeline_consistency * weights['timeline_consistency'] +
            action_smoothness * weights['action_smoothness'] +
            event_logic * weights['event_logic']
        )
        
        return overall_score
    
    def generate_suggestions(self, check_result: Dict[str, Any]) -> list:
# 根据检查结果生成改进建议
        suggestions = []
        
        if check_result['timeline_consistency'] < self.threshold:
            suggestions.append("保持场景间的帧率一致，确保时间线流畅")
        
        if check_result['action_smoothness'] < self.threshold:
            suggestions.append("优化动作过渡，确保场景间的动作连贯自然")
        
        if check_result['event_logic'] < self.threshold:
            suggestions.append("确保场景间的事件发展符合逻辑，避免突兀的情节跳转")
        
        return suggestions

