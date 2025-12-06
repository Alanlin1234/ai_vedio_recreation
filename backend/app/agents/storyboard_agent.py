#视频分镜Agent

from typing import Dict, Any, List
from .base_agent import BaseAgent


class StoryboardAgent(BaseAgent):
    #负责分镜和镜头规划
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("StoryboardAgent", config)
        
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        
        
        try:
            if not self.validate_input(input_data, ['scenes']):
                return self.create_result(False, error="缺少场景数据")
            
            self.log_execution("start", "开始分镜规划")
            
            scenes = input_data['scenes']
            style = input_data.get('style', 'cinematic')
            
            # 为每个场景规划镜头
            storyboard = []
            shots = []
            shot_id = 1
            
            for scene in scenes:
                scene_shots = self._plan_scene_shots(scene, style, shot_id)
                shots.extend(scene_shots)
                
                storyboard.append({
                    'scene_id': scene['scene_id'],
                    'scene_name': scene['name'],
                    'shots': scene_shots,
                    'shot_count': len(scene_shots)
                })
                
                shot_id += len(scene_shots)
            
            self.log_execution("complete", f"规划了{len(shots)}个镜头")
            
            return self.create_result(True, {
                'storyboard': storyboard,
                'shots': shots,
                'total_shots': len(shots)
            })
            
        except Exception as e:
            self.logger.error(f"分镜规划失败: {str(e)}")
            return self.create_result(False, error=str(e))
    
    def _plan_scene_shots(self, scene: Dict, style: str, start_id: int) -> List[Dict[str, Any]]:
        #为每个场景规划镜头
        duration = scene['duration']
        visual_desc = scene['visual_description']
        
        # 根据场景时长决定镜头数量
        shot_count = max(1, duration // 5)  # 暂时每5秒一个镜头
        shot_duration = duration / shot_count
        
        shots = []
        for i in range(shot_count):
            shots.append({
                'shot_id': start_id + i,
                'scene_id': scene['scene_id'],
                'shot_type': self._determine_shot_type(i, shot_count),
                'camera_angle': self._determine_camera_angle(i, shot_count),
                'movement': self._determine_camera_movement(i, shot_count),
                'duration': shot_duration,
                'visual_description': visual_desc,
                'style': style,
                'prompt': self._generate_shot_prompt(visual_desc, style, i, shot_count)
            })
        
        return shots
    
    def _determine_shot_type(self, index: int, total: int) -> str:
        #镜头类型
        types = ['wide_shot', 'medium_shot', 'close_up', 'extreme_close_up']
        if index == 0:
            return 'wide_shot'  # 开场用全景
        elif index == total - 1:
            return 'close_up'  # 结尾用特写
        return types[index % len(types)]
    
    def _determine_camera_angle(self, index: int, total: int) -> str:
        #机位角度
        angles = ['eye_level', 'high_angle', 'low_angle', 'dutch_angle']
        return angles[index % len(angles)]
    
    def _determine_camera_movement(self, index: int, total: int) -> str:
        #确定镜头运动
        movements = ['static', 'pan', 'tilt', 'zoom', 'dolly']
        return movements[index % len(movements)]
    
    def _generate_shot_prompt(self, visual_desc: str, style: str, index: int, total: int) -> str:
        #生成镜头提示词
        shot_type = self._determine_shot_type(index, total)
        angle = self._determine_camera_angle(index, total)
        
        return f"{style} style, {shot_type}, {angle}, {visual_desc}, high quality, cinematic lighting"
