# FFmpeg视频处理服务

import os
import subprocess
import asyncio
from typing import Dict, List, Any
import logging
import uuid

logger = logging.getLogger(__name__)


class FFmpegService:
    
    
    def __init__(self, config: Dict[str, Any] = None):
        from app.config.video_reconstruction_config import get_config
        
        # 获取配置
        self.system_config = get_config()
        ffmpeg_config = self.system_config.get_ffmpeg_config()
        
        # 合并传入的配置
        if config:
            ffmpeg_config.update(config)
        
        # 设置FFmpeg路径
        self.ffmpeg_path = ffmpeg_config.get("ffmpeg_path", "")
        if not self.ffmpeg_path:
            self.ffmpeg_path = self._find_ffmpeg()
        
        # 设置FFprobe路径
        self.ffprobe_path = ffmpeg_config.get("ffprobe_path", "")
        if not self.ffprobe_path:
            self.ffprobe_path = self._find_ffprobe()
        
        if not self.ffmpeg_path:
            logger.error("FFmpeg未找到，请确保已安装FFmpeg并添加到系统路径")
            raise RuntimeError("FFmpeg未找到")
        
        self.default_slice_duration = ffmpeg_config.get("default_slice_duration", 3)
        self.video_quality = ffmpeg_config.get("video_quality", "high")
        self.audio_quality = ffmpeg_config.get("audio_quality", "high")
        self.timeout = ffmpeg_config.get("timeout", 600)
        
        logger.info(f"FFmpeg路径: {self.ffmpeg_path}")
        logger.info(f"FFprobe路径: {self.ffprobe_path}")
        logger.info(f"FFmpeg配置: slice_duration={self.default_slice_duration}s, quality={self.video_quality}")
    
    def _find_ffmpeg(self) -> str:
        
        try:
            # 在Windows上查找ffmpeg.exe
            if os.name == 'nt':
                # 检查系统路径
                result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout.strip().split('\n')[0]
                
                # 检查常见安装位置
                common_paths = [
                    r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
                    r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',
                    r'D:\ffmpeg\bin\ffmpeg.exe',
                    r'E:\ffmpeg\bin\ffmpeg.exe'
                ]
                
                for path in common_paths:
                    if os.path.exists(path):
                        return path
            else:
                # 在Linux/Mac上查找ffmpeg
                result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout.strip()
            
            return None
        except Exception as e:
            logger.error(f"查找FFmpeg失败: {str(e)}")
            return None
    
    def _find_ffprobe(self) -> str:
        
        try:
            # 在Windows上查找ffprobe.exe
            if os.name == 'nt':
                # 检查系统路径
                result = subprocess.run(['where', 'ffprobe'], capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout.strip().split('\n')[0]
                
                # 检查常见安装位置
                common_paths = [
                    r'C:\Program Files\ffmpeg\bin\ffprobe.exe',
                    r'C:\Program Files (x86)\ffmpeg\bin\ffprobe.exe',
                    r'D:\ffmpeg\bin\ffprobe.exe',
                    r'E:\ffmpeg\bin\ffprobe.exe'
                ]
                
                for path in common_paths:
                    if os.path.exists(path):
                        return path
            else:
                # 在Linux/Mac上查找ffprobe
                result = subprocess.run(['which', 'ffprobe'], capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout.strip()
            
            # 如果找不到ffprobe，尝试使用ffmpeg路径替换名称
            if hasattr(self, 'ffmpeg_path') and self.ffmpeg_path:
                ffprobe_path = self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
                if os.path.exists(ffprobe_path):
                    return ffprobe_path
            
            return None
        except Exception as e:
            logger.error(f"查找FFprobe失败: {str(e)}")
            return None
    
    async def slice_video(self, video_path: str, slice_duration: int = None, slice_limit: int = 0) -> Dict[str, Any]:
        #将视频切片为指定时长的片段
        
        
        try:
            # 如果未指定切片时长，使用配置中的默认值
            if slice_duration is None:
                slice_duration = self.default_slice_duration
            logger.info(f"开始切片视频: {video_path}, 切片时长: {slice_duration}秒, 切片限制: {slice_limit}")
            
            # 获取视频信息
            video_info = await self._get_video_info(video_path)
            if not video_info:
                logger.error("获取视频信息失败")
                return None
            
            total_duration = video_info.get('duration', 0)
            if total_duration <= 0:
                logger.error("视频时长无效")
                return None
            
            # 创建输出目录
            output_dir = os.path.join(os.path.dirname(video_path), f"slices_{uuid.uuid4().hex[:8]}")
            os.makedirs(output_dir, exist_ok=True)
            
            # 计算切片数量
            slice_count = max(1, int(total_duration / slice_duration) + 1)
            
            # 应用切片限制
            if slice_limit > 0:
                slice_count = min(slice_count, slice_limit)
                logger.info(f"应用切片限制，只生成 {slice_count} 个切片")
            
            slices = []
            
            for i in range(slice_count):
                start_time = i * slice_duration
                if start_time >= total_duration:
                    break
                
                # 生成切片文件名
                slice_filename = f"slice_{i:03d}.mp4"
                slice_path = os.path.join(output_dir, slice_filename)
                
                # 构建优化的FFmpeg命令，使用更兼容的CPU编码
                cmd = [
                    self.ffmpeg_path,
                    '-i', video_path,
                    '-ss', str(start_time),
                    '-t', str(slice_duration),
                    '-c:v', 'libx264',  # 使用CPU编码，提高兼容性
                    '-preset', 'fast',  # 更快的编码速度
                    '-crf', '28',  # 更低的视频质量，加快生成速度
                    '-g', '60',  # 减少关键帧数量
                    '-c:a', 'aac',
                    '-b:a', '64k',  # 降低音频比特率
                    '-y',
                    slice_path
                ]
                
                # 执行FFmpeg命令
                await self._run_ffmpeg_command(cmd)
                
                # 检查切片是否生成成功
                if os.path.exists(slice_path) and os.path.getsize(slice_path) > 0:
                    # 提取切片的关键帧
                    preview_path = await self._extract_keyframe(slice_path)
                    keyframes = await self._extract_keyframes(slice_path, num_keyframes=3)
                    
                    slice_info = {
                        "slice_id": f"slice_{i}",
                        "input_file": video_path,
                        "output_file": slice_path,
                        "preview_file": preview_path,
                        "keyframes": keyframes,
                        "start_time": start_time,
                        "duration": slice_duration,
                        "index": i
                    }
                    slices.append(slice_info)
                    logger.info(f"切片成功: {slice_path}，提取了 {len(keyframes)} 个关键帧")
                else:
                    logger.warning(f"切片失败: {slice_path}")
            
            if not slices:
                logger.error("所有切片都失败了")
                return None
            
            return {
                "slices": slices,
                "slice_info": {
                    "total_slices": len(slices),
                    "slice_duration": slice_duration,
                    "input_video": video_path,
                    "output_dir": output_dir
                }
            }
        except Exception as e:
            logger.error(f"视频切片失败: {str(e)}")
            return None
    
    async def extract_audio(self, video_path: str) -> Dict[str, Any]:
        """从视频中提取音频"""
        try:
            logger.info(f"开始从视频中提取音频: {video_path}")
            
            # 生成音频输出路径
            audio_path = os.path.splitext(video_path)[0] + '.mp3'
            
            # 构建FFmpeg命令
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-q:a', '0',
                '-map', 'a',
                '-y',
                audio_path
            ]
            
            # 执行FFmpeg命令
            await self._run_ffmpeg_command(cmd)
            
            # 检查音频是否生成成功
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                logger.info(f"音频提取成功: {audio_path}")
                return {
                    "audio_path": audio_path,
                    "input_video": video_path
                }
            else:
                logger.error(f"音频提取失败: {audio_path}")
                return None
        except Exception as e:
            logger.error(f"音频提取失败: {str(e)}")
            return None
    
    async def synthesize_final_video(self, video_segments: List[Dict[str, Any]], audio_path: str = None, story_data: Dict[str, Any] = None) -> str:
# 合成最终视频
        try:
            logger.info(f"开始合成最终视频，使用 {len(video_segments)} 个片段")
            
            if not video_segments:
                logger.error("没有视频片段可以合成")
                return None
            
            # 创建临时目录
            temp_dir = os.path.join(os.path.dirname(video_segments[0]['output_file']), f"temp_{uuid.uuid4().hex[:8]}")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 1. 生成视频片段列表文件
            segment_list_path = os.path.join(temp_dir, "segments.txt")
            with open(segment_list_path, 'w') as f:
                for segment in video_segments:
                    f.write(f"file '{segment['output_file']}'\n")
            
            # 2. 生成最终视频文件名
            output_video_path = os.path.join(
                os.path.dirname(video_segments[0]['output_file']),
                f"final_{uuid.uuid4().hex[:8]}.mp4"
            )
            
            # 3. 构建FFmpeg命令
            cmd = [
                self.ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', segment_list_path,
                '-c', 'copy',
                '-y',
                output_video_path
            ]
            
            # 执行FFmpeg命令合并视频片段
            await self._run_ffmpeg_command(cmd)
            
            # 4. 如果有音频，合并音频到视频
            if audio_path and os.path.exists(audio_path):
                final_with_audio_path = os.path.join(
                    os.path.dirname(video_segments[0]['output_file']),
                    f"final_with_audio_{uuid.uuid4().hex[:8]}.mp4"
                )
                
                cmd = [
                    self.ffmpeg_path,
                    '-i', output_video_path,
                    '-i', audio_path,
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-strict', 'experimental',
                    '-shortest',
                    '-y',
                    final_with_audio_path
                ]
                
                await self._run_ffmpeg_command(cmd)
                
                # 替换原视频文件
                os.replace(final_with_audio_path, output_video_path)
                logger.info(f"音频合并成功: {output_video_path}")
            
            # 5. 清理临时文件
            os.remove(segment_list_path)
            os.rmdir(temp_dir)
            
            if os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
                logger.info(f"最终视频合成成功: {output_video_path}")
                return output_video_path
            else:
                logger.error(f"最终视频合成失败: {output_video_path}")
                return None
        except Exception as e:
            logger.error(f"最终视频合成失败: {str(e)}")
            return None
    
    async def _extract_keyframes(self, video_path: str, num_keyframes: int = 3) -> List[str]:
        """从视频中提取多个关键帧，优化版"""
        try:
            keyframes = []
            video_info = await self._get_video_info(video_path)
            duration = video_info.get('duration', 10)
            
            # 生成关键帧保存目录
            video_dir = os.path.dirname(video_path)
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            keyframes_dir = os.path.join(video_dir, f"keyframes_{base_name}")
            os.makedirs(keyframes_dir, exist_ok=True)
            
            # 优化1：使用更高效的方式提取关键帧
            # 生成临时文件列表
            temp_keyframes = []
            for i in range(num_keyframes):
                keyframe_path = os.path.join(keyframes_dir, f"keyframe_{i+1}.jpg")
                temp_keyframes.append(keyframe_path)
            
            # 优化2：使用单条FFmpeg命令提取所有关键帧，减少进程创建开销
            # 计算关键帧提取时间点，均匀分布
            timestamps = []
            for i in range(num_keyframes):
                # 避免在视频开始和结束处提取，选择中间点
                timestamp = (i + 1) * duration / (num_keyframes + 1)
                timestamps.append(str(timestamp))
            
            # 构建批量提取命令
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-q:v', '1',  # 更高质量
                '-vf', f"select='eq(pict_type,PICT_TYPE_I)',fps=1,trim=start=0:end={duration},select='between(n,0,{num_keyframes-1})'",
                '-y',
                os.path.join(keyframes_dir, f"keyframe_%d.jpg")
            ]
            
            # 执行批量提取命令
            await self._run_ffmpeg_command(cmd)
            
            # 检查生成的关键帧
            for i in range(num_keyframes):
                keyframe_path = os.path.join(keyframes_dir, f"keyframe_{i+1}.jpg")
                if os.path.exists(keyframe_path) and os.path.getsize(keyframe_path) > 0:
                    keyframes.append(keyframe_path)
                else:
                    logger.warning(f"关键帧提取失败: {keyframe_path}")
                    
                    # 备选方案：如果批量提取失败，尝试单帧提取
                    timestamp = timestamps[i]
                    cmd_single = [
                        self.ffmpeg_path,
                        '-i', video_path,
                        '-ss', timestamp,
                        '-vframes', '1',
                        '-q:v', '1',
                        '-y',
                        keyframe_path
                    ]
                    await self._run_ffmpeg_command(cmd_single)
                    
                    if os.path.exists(keyframe_path) and os.path.getsize(keyframe_path) > 0:
                        keyframes.append(keyframe_path)
                        logger.info(f"备选方案成功提取关键帧: {keyframe_path}")
            
            return keyframes
        except Exception as e:
            logger.error(f"关键帧提取失败: {str(e)}")
            return []
    
    async def _extract_keyframe(self, video_path: str) -> str:
        """从视频中提取单个关键帧作为预览图（兼容旧代码）"""
        keyframes = await self._extract_keyframes(video_path, num_keyframes=1)
        return keyframes[0] if keyframes else None
    
    async def _get_video_info(self, video_path: str) -> Dict[str, Any]:
        """获取视频信息"""
        try:
            # 使用ffprobe获取视频信息
            ffprobe_cmd = [
                self.ffprobe_path,
                '-i', video_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams'
            ]
            
            # 执行ffprobe命令
            result = await self._run_ffmpeg_command(ffprobe_cmd, capture_output=True)
            
            if result:
                import json
                info = json.loads(result)
                
                # 提取基本信息
                duration = float(info['format']['duration'])
                width = height = 0
                
                for stream in info['streams']:
                    if stream['codec_type'] == 'video':
                        width = int(stream['width'])
                        height = int(stream['height'])
                        break
                
                return {
                    'duration': duration,
                    'width': width,
                    'height': height,
                    'bitrate': info['format'].get('bit_rate', 0),
                    'format_name': info['format']['format_name']
                }
            # 如果ffprobe失败，尝试使用ffmpeg命令获取基本信息
            logger.warning("ffprobe获取视频信息失败，尝试使用ffmpeg命令获取基本信息")
            return {
                'duration': 10,  # 假设默认时长10秒
                'width': 1920,
                'height': 1080,
                'bitrate': 0,
                'format_name': 'mp4'
            }
        except Exception as e:
            logger.error(f"获取视频信息失败: {str(e)}")
            # 返回默认信息，避免整个流程失败
            return {
                'duration': 10,  # 假设默认时长10秒
                'width': 1920,
                'height': 1080,
                'bitrate': 0,
                'format_name': 'mp4'
            }
    
    async def _run_ffmpeg_command(self, cmd: List[str], capture_output: bool = False) -> str:
        """执行FFmpeg命令"""
        try:
            logger.debug(f"执行FFmpeg命令: {' '.join(cmd)}")
            
            if capture_output:
                # 捕获输出
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=False
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"FFmpeg命令失败: {' '.join(cmd)}")
                    logger.error(f"错误输出: {stderr.decode('utf-8', errors='ignore')}")
                    return None
                
                return stdout.decode('utf-8', errors='ignore')
            else:
                # 不捕获输出，直接执行
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                    shell=False
                )
                
                await process.wait()
                
                if process.returncode != 0:
                    logger.error(f"FFmpeg命令失败: {' '.join(cmd)}")
                    return None
                
                return "success"
        except Exception as e:
            logger.error(f"执行FFmpeg命令失败: {str(e)}")
            return None
    
    async def resize_video(self, video_path: str, width: int, height: int) -> str:
        """调整视频大小"""
        try:
            logger.info(f"开始调整视频大小: {video_path} -> {width}x{height}")
            
            # 生成输出路径
            output_path = os.path.join(
                os.path.dirname(video_path),
                f"resized_{width}x{height}_{os.path.basename(video_path)}"
            )
            
            # 构建FFmpeg命令
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-vf', f"scale={width}:{height}",
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-strict', 'experimental',
                '-y',
                output_path
            ]
            
            # 执行FFmpeg命令
            await self._run_ffmpeg_command(cmd)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"视频大小调整成功: {output_path}")
                return output_path
            else:
                logger.error(f"视频大小调整失败: {output_path}")
                return None
        except Exception as e:
            logger.error(f"视频大小调整失败: {str(e)}")
            return None
    
    async def generate_thumbnail(self, video_path: str, timestamp: float = 0.0) -> str:
        """生成视频缩略图"""
        try:
            logger.info(f"开始生成视频缩略图: {video_path}, 时间点: {timestamp}")
            
            # 生成输出路径
            thumbnail_path = os.path.splitext(video_path)[0] + '_thumbnail.jpg'
            
            # 构建FFmpeg命令
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-ss', str(timestamp),
                '-vframes', '1',
                '-q:v', '2',
                '-y',
                thumbnail_path
            ]
            
            # 执行FFmpeg命令
            await self._run_ffmpeg_command(cmd)
            
            if os.path.exists(thumbnail_path) and os.path.getsize(thumbnail_path) > 0:
                logger.info(f"视频缩略图生成成功: {thumbnail_path}")
                return thumbnail_path
            else:
                logger.error(f"视频缩略图生成失败: {thumbnail_path}")
                return None
        except Exception as e:
            logger.error(f"视频缩略图生成失败: {str(e)}")
            return None
