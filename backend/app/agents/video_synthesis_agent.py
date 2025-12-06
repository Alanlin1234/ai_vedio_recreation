"""
视频合成Agent
"""
from typing import Dict, Any, List
from .base_agent import BaseAgent
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip
import os


class VideoSynthesisAgent(BaseAgent):
    """负责将所有素材合成最终视频"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("VideoSynthesisAgent", config)
        self.output_dir = config.get('output_dir', 'output/videos') if config else 'output/videos'
        
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        合成最终视频
        
        Args:
            input_data: {
                'passed_images': List[Dict] - 通过检验的图像
                'narration_audio': Optional[str] - 旁白音频路径
                'background_music': Optional[str] - 背景音乐路径
                'output_filename': Optional[str] - 输出文件名
            }
            
        Returns:
            {
                'video_path': str - 生成的视频路径
                'duration': float - 视频时长
            }
        """
        try:
            if not self.validate_input(input_data, ['passed_images']):
                return self.create_result(False, error="缺少图像数据")
            
            self.log_execution("start", "开始视频合成")
            
            images = input_data['passed_images']
            narration_audio = input_data.get('narration_audio')
            background_music = input_data.get('background_music')
            output_filename = input_data.get('output_filename', 'output_video.mp4')
            
            # 创建输出目录
            os.makedirs(self.output_dir, exist_ok=True)
            output_path = os.path.join(self.output_dir, output_filename)
            
            # 合成视频
            video_path, duration = await self._synthesize_video(
                images, 
                narration_audio, 
                background_music, 
                output_path
            )
            
            self.log_execution("complete", f"视频生成完成: {video_path}")
            
            return self.create_result(True, {
                'video_path': video_path,
                'duration': duration,
                'resolution': '1920x1080',
                'fps': 30
            })
            
        except Exception as e:
            self.logger.error(f"视频合成失败: {str(e)}")
            return self.create_result(False, error=str(e))
    
    async def _synthesize_video(
        self, 
        images: List[Dict], 
        narration_audio: str, 
        background_music: str,
        output_path: str
    ) -> tuple:
        """合成视频"""
        try:
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            # MoviePy 是同步的，在线程池中运行
            with ThreadPoolExecutor() as executor:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    executor,
                    self._synthesize_video_sync,
                    images,
                    narration_audio,
                    background_music,
                    output_path
                )
            
            return result
            
        except Exception as e:
            self.logger.error(f"视频合成过程出错: {str(e)}")
            raise
    
    def _synthesize_video_sync(
        self,
        images: List[Dict],
        narration_audio: str,
        background_music: str,
        output_path: str
    ) -> tuple:
        """同步方式合成视频（在线程池中运行）"""
        try:
            import os
            
            # 检查是否启用mock模式
            use_mock = os.environ.get('USE_MOCK_IMAGE_GENERATION', 'false').lower() == 'true'
            
            if use_mock:
                self.logger.info("[Mock模式] 跳过实际视频合成，返回模拟结果")
                # 不创建实际视频，仅返回模拟路径
                self.logger.info(f"[Mock模式] 模拟生成视频: {output_path}")
                # 创建输出目录
                os.makedirs(self.output_dir, exist_ok=True)
                # 返回模拟的视频路径和时长
                return output_path, 60.0  # 模拟60秒视频
            
            # 实际视频合成逻辑（保留原有代码）
            from moviepy.editor import (
                ImageClip, concatenate_videoclips, AudioFileClip,
                CompositeAudioClip, CompositeVideoClip
            )
            import requests
            from PIL import Image
            import io
            
            self.logger.info("开始视频合成...")
            
            # 1. 下载并创建图像片段
            clips = []
            temp_images = []
            
            for idx, img_data in enumerate(images):
                try:
                    image_url = img_data.get('image_url', '')
                    duration = img_data.get('duration', 3.0)
                    shot_id = img_data.get('shot_id', idx)
                    
                    self.logger.info(f"处理镜头 {shot_id}: {image_url}")
                    
                    # 下载图像
                    img_path = self._download_image(image_url, shot_id)
                    temp_images.append(img_path)
                    
                    # 创建图像片段
                    clip = ImageClip(img_path).set_duration(duration)
                    
                    # 添加转场效果
                    if idx > 0:
                        clip = self._add_transition(clip, 'fade')
                    
                    clips.append(clip)
                    
                except Exception as e:
                    self.logger.error(f"处理镜头 {idx} 失败: {str(e)}")
                    continue
            
            if not clips:
                raise Exception("没有可用的图像片段")
            
            self.logger.info(f"成功创建 {len(clips)} 个图像片段")
            
            # 2. 拼接所有片段
            final_clip = concatenate_videoclips(clips, method="compose")
            total_duration = final_clip.duration
            
            self.logger.info(f"视频总时长: {total_duration:.2f}秒")
            
            # 3. 处理音频
            audio_clips = []
            
            # 添加旁白音频
            if narration_audio and os.path.exists(narration_audio):
                self.logger.info(f"添加旁白音频: {narration_audio}")
                narration = AudioFileClip(narration_audio)
                audio_clips.append(narration)
            
            # 添加背景音乐
            if background_music and os.path.exists(background_music):
                self.logger.info(f"添加背景音乐: {background_music}")
                music = AudioFileClip(background_music)
                
                # 调整音乐长度以匹配视频
                if music.duration < total_duration:
                    # 循环播放
                    music = music.audio_loop(duration=total_duration)
                else:
                    # 裁剪
                    music = music.subclip(0, total_duration)
                
                # 降低背景音乐音量
                music = music.volumex(0.3)
                audio_clips.append(music)
            
            # 合成音频
            if audio_clips:
                if len(audio_clips) == 1:
                    final_audio = audio_clips[0]
                else:
                    final_audio = CompositeAudioClip(audio_clips)
                
                final_clip = final_clip.set_audio(final_audio)
            
            # 4. 导出视频
            self.logger.info(f"导出视频到: {output_path}")
            
            final_clip.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                threads=4,
                preset='medium'
            )
            
            # 5. 清理临时文件
            for temp_img in temp_images:
                try:
                    if os.path.exists(temp_img):
                        os.remove(temp_img)
                except:
                    pass
            
            # 关闭所有片段
            for clip in clips:
                clip.close()
            final_clip.close()
            
            self.logger.info("视频合成完成！")
            
            return output_path, total_duration
            
        except Exception as e:
            self.logger.error(f"视频合成失败: {str(e)}")
            raise
    
    def _download_image(self, image_url: str, shot_id: int) -> str:
        """下载图像到本地"""
        import requests
        import os
        from urllib.parse import urlparse
        
        # 创建临时目录
        temp_dir = os.path.join(self.output_dir, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # 如果是本地文件
        if image_url.startswith('file://'):
            return image_url.replace('file://', '')
        
        # 如果是HTTP URL
        if image_url.startswith('http'):
            temp_path = os.path.join(temp_dir, f'shot_{shot_id}.png')
            
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            
            return temp_path
        
        # 如果是相对路径
        return image_url
    
    def _add_transition(self, clip, transition_type: str = 'fade', duration: float = 0.5):
        """
        添加转场效果
        
        支持的转场类型:
        - fade: 淡入淡出
        - crossfade: 交叉淡化
        - slide: 滑动
        """
        from moviepy.editor import vfx
        
        if transition_type == 'fade':
            # 淡入效果
            clip = clip.fadein(duration)
        elif transition_type == 'crossfade':
            # 交叉淡化（需要在拼接时处理）
            clip = clip.crossfadein(duration)
        
        return clip
    
    def _add_effects(self, clip, effects: List[str]):
        """
        添加视频效果
        
        支持的效果:
        - speed: 速度调整
        - mirror: 镜像
        - blackwhite: 黑白
        - invert: 反色
        """
        from moviepy.editor import vfx
        
        for effect in effects:
            if effect == 'speed_2x':
                clip = clip.fx(vfx.speedx, 2)
            elif effect == 'speed_0.5x':
                clip = clip.fx(vfx.speedx, 0.5)
            elif effect == 'mirror_x':
                clip = clip.fx(vfx.mirror_x)
            elif effect == 'mirror_y':
                clip = clip.fx(vfx.mirror_y)
            elif effect == 'blackwhite':
                clip = clip.fx(vfx.blackwhite)
            elif effect == 'invert':
                clip = clip.fx(vfx.invert_colors)
        
        return clip
    
    def _add_text_overlay(self, clip, text: str, position: str = 'bottom', duration: float = None):
        """
        添加文字叠加
        
        Args:
            clip: 视频片段
            text: 文字内容
            position: 位置 ('top', 'center', 'bottom')
            duration: 显示时长（None表示整个片段）
        """
        from moviepy.editor import TextClip, CompositeVideoClip
        
        # 创建文字片段
        txt_clip = TextClip(
            text,
            fontsize=50,
            color='white',
            font='Arial',
            stroke_color='black',
            stroke_width=2
        )
        
        # 设置位置
        if position == 'top':
            txt_clip = txt_clip.set_position(('center', 50))
        elif position == 'center':
            txt_clip = txt_clip.set_position('center')
        else:  # bottom
            txt_clip = txt_clip.set_position(('center', clip.h - 100))
        
        # 设置时长
        if duration:
            txt_clip = txt_clip.set_duration(duration)
        else:
            txt_clip = txt_clip.set_duration(clip.duration)
        
        # 合成
        return CompositeVideoClip([clip, txt_clip])
    
    def _mix_audio(self, audio_clips: List, volumes: List[float] = None):
        """
        混合多个音频轨道
        
        Args:
            audio_clips: 音频片段列表
            volumes: 每个音频的音量（0.0-1.0）
        """
        from moviepy.editor import CompositeAudioClip
        
        if not audio_clips:
            return None
        
        # 调整音量
        if volumes:
            adjusted_clips = []
            for clip, volume in zip(audio_clips, volumes):
                adjusted_clips.append(clip.volumex(volume))
            audio_clips = adjusted_clips
        
        # 合成音频
        return CompositeAudioClip(audio_clips)
