"""
帧连续性服务
实现首尾帧连接方式，确保场景间的视觉连贯性
下一个场景的首帧必须是上一个场景的最后一帧
"""
import os
import sys
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class FrameContinuityService:
    """帧连续性服务，负责管理场景间的首尾帧连接"""
    
    def __init__(self):
        """初始化帧连续性服务"""
        self.previous_scene_last_frame = None
        self.previous_scene_context = None
    
    def set_previous_scene_frame(self, last_frame: str, context: Optional[Dict[str, Any]] = None):
        """
        设置上一个场景的最后一帧
        
        Args:
            last_frame: 上一个场景的最后一帧路径或URL
            context: 上一个场景的上下文信息（可选）
        """
        self.previous_scene_last_frame = last_frame
        self.previous_scene_context = context
        logger.info(f"设置上一个场景的最后一帧: {last_frame}")
    
    def get_previous_scene_last_frame(self) -> Optional[str]:
        """获取上一个场景的最后一帧"""
        return self.previous_scene_last_frame
    
    def build_contextual_prompt(
        self, 
        current_prompt: str,
        previous_scene_info: Optional[Dict[str, Any]] = None,
        use_first_frame_constraint: bool = True
    ) -> str:
        """
        构建包含上下文的prompt
        
        Args:
            current_prompt: 当前场景的原始prompt
            previous_scene_info: 上一个场景的信息
            use_first_frame_constraint: 是否使用首帧约束
            
        Returns:
            增强后的prompt，包含上下文信息
        """
        contextual_parts = []
        
        if previous_scene_info:
            # 添加上一个场景的详细上下文
            previous_prompt = previous_scene_info.get('video_prompt', '')
            previous_style = previous_scene_info.get('style_elements', {})
            
            context_text = "\n\n【上一场景上下文信息】\n"
            context_text += f"上一场景内容描述: {previous_prompt[:200]}\n"
            
            if previous_style:
                context_text += f"- 人物风格: {previous_style.get('characters', '')}\n"
                context_text += f"- 环境风格: {previous_style.get('environment', '')}\n"
                context_text += f"- 视觉风格: {previous_style.get('visual_style', '')}\n"
            
            contextual_parts.append(context_text)
        
        # 添加强制首帧连接的约束
        if use_first_frame_constraint and self.previous_scene_last_frame:
            constraint_text = (
                "\n\n【关键约束】\n"
                "当前场景的第一个关键帧必须与上一个场景的最后一个关键帧完全相同！\n"
                "这意味着当前场景的起始画面必须无缝衔接上一个场景的结束画面。\n"
                "请在生成第一个关键帧时，确保视觉元素、构图、色彩、光线等都与上一场景的最后一帧保持一致。\n"
                "后续关键帧可以逐渐过渡到当前场景的主要内容。"
            )
            contextual_parts.append(constraint_text)
        
        # 添加场景连贯性要求
        if previous_scene_info:
            continuity_text = (
                "\n\n【场景连贯性要求】\n"
                "1. 保持视觉风格的一致性（色彩、光线、画质）\n"
                "2. 保持人物外观的一致性（服装、发型、表情特征）\n"
                "3. 保持环境元素的一致性（背景、道具、氛围）\n"
                "4. 确保场景过渡自然流畅，没有突兀的跳跃\n"
                "5. 第一个关键帧必须完美衔接上一场景的最后一帧"
            )
            contextual_parts.append(continuity_text)
        
        # 组合所有上下文信息
        enhanced_prompt = current_prompt + "".join(contextual_parts)
        
        return enhanced_prompt
    
    def generate_keyframes_with_first_frame_constraint(
        self,
        base_keyframes: List[str],
        previous_last_frame: Optional[str] = None,
        num_keyframes: int = 3
    ) -> List[str]:
        """
        生成关键帧，确保第一个关键帧是上一个场景的最后一帧
        
        Args:
            base_keyframes: 基础生成的关键帧列表
            previous_last_frame: 上一个场景的最后一帧（如果提供，将作为第一个关键帧）
            num_keyframes: 需要的总关键帧数量
            
        Returns:
            调整后的关键帧列表，第一个是关键帧是previous_last_frame（如果提供）
        """
        result_keyframes = []
        
        # 如果提供了上一个场景的最后一帧，将其作为第一个关键帧
        if previous_last_frame:
            result_keyframes.append(previous_last_frame)
            logger.info(f"使用上一个场景的最后一帧作为当前场景的第一个关键帧")
            
            # 从base_keyframes中选择剩余的帧
            # 如果base_keyframes已经包含了previous_last_frame，需要避免重复
            remaining_frames = [f for f in base_keyframes if f != previous_last_frame]
            
            # 如果还需要更多关键帧，使用剩余的base_keyframes
            needed_count = num_keyframes - 1
            result_keyframes.extend(remaining_frames[:needed_count])
            
            # 如果还不够，可以重复最后一个（虽然不理想，但至少保证数量）
            while len(result_keyframes) < num_keyframes and remaining_frames:
                result_keyframes.append(remaining_frames[-1])
        else:
            # 如果没有提供上一个场景的最后一帧，使用原始的关键帧
            result_keyframes = base_keyframes[:num_keyframes]
        
        logger.info(f"生成的关键帧数量: {len(result_keyframes)} (需要: {num_keyframes})")
        return result_keyframes
    
    def extract_last_frame_from_video(self, video_path: str) -> Optional[str]:
        """
        从视频中提取最后一帧
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            最后一帧的路径，如果失败则返回None
        """
        try:
            import subprocess
            import tempfile
            
            # 创建临时目录保存帧
            temp_dir = tempfile.mkdtemp()
            frame_path = os.path.join(temp_dir, "last_frame.jpg")
            
            # 使用ffmpeg提取最后一帧
            # 首先获取视频时长
            duration_cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', video_path
            ]
            
            result = subprocess.run(duration_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"获取视频时长失败: {result.stderr}")
                return None
            
            try:
                duration = float(result.stdout.strip())
            except ValueError:
                logger.error(f"无法解析视频时长: {result.stdout}")
                return None
            
            # 提取最后一帧（使用稍微提前一点的时间，避免最后一帧可能不存在）
            extract_time = max(0, duration - 0.1)
            
            extract_cmd = [
                'ffmpeg', '-i', video_path,
                '-ss', str(extract_time),
                '-vframes', '1',
                '-q:v', '2',
                '-y',
                frame_path
            ]
            
            result = subprocess.run(extract_cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(frame_path):
                logger.info(f"成功提取最后一帧: {frame_path}")
                return frame_path
            else:
                logger.error(f"提取最后一帧失败: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"提取最后一帧时发生异常: {str(e)}")
            return None
    
    def extract_last_keyframe(self, keyframes: List[str]) -> Optional[str]:
        """
        从关键帧列表中获取最后一个关键帧
        
        Args:
            keyframes: 关键帧列表
            
        Returns:
            最后一个关键帧，如果列表为空则返回None
        """
        if keyframes:
            return keyframes[-1]
        return None
    
    def reset(self):
        """重置状态，清除上一个场景的信息"""
        self.previous_scene_last_frame = None
        self.previous_scene_context = None
        logger.info("已重置帧连续性服务状态")


# 使用示例
if __name__ == "__main__":
    service = FrameContinuityService()
    
    # 设置上一个场景的最后一帧
    service.set_previous_scene_frame(
        last_frame="path/to/previous_scene_last_frame.jpg",
        context={
            'video_prompt': '上一个场景的描述',
            'style_elements': {
                'characters': '人物描述',
                'environment': '环境描述',
                'visual_style': '视觉风格'
            }
        }
    )
    
    # 构建包含上下文的prompt
    current_prompt = "当前场景的描述"
    enhanced_prompt = service.build_contextual_prompt(
        current_prompt=current_prompt,
        previous_scene_info={
            'video_prompt': '上一个场景的描述',
            'style_elements': {
                'characters': '人物描述',
                'environment': '环境描述',
                'visual_style': '视觉风格'
            }
        }
    )
    
    print(enhanced_prompt)

