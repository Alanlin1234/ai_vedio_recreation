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
    
    async def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """获取视频信息（公共方法）"""
        return await self._get_video_info(video_path)
    
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
        temp_dir = None
        try:
            logger.info(f"开始合成最终视频，使用 {len(video_segments)} 个片段")
            
            if not video_segments:
                logger.error("没有视频片段可以合成")
                return None
            
            temp_dir = os.path.join(os.path.dirname(video_segments[0]['output_file']), f"temp_{uuid.uuid4().hex[:8]}")
            os.makedirs(temp_dir, exist_ok=True)
            
            segment_list_path = os.path.join(temp_dir, "segments.txt")
            with open(segment_list_path, 'w') as f:
                for segment in video_segments:
                    f.write(f"file '{segment['output_file']}'\n")
            
            output_video_path = os.path.join(
                os.path.dirname(video_segments[0]['output_file']),
                f"final_{uuid.uuid4().hex[:8]}.mp4"
            )
            
            cmd = [
                self.ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', segment_list_path,
                '-c', 'copy',
                '-y',
                output_video_path
            ]
            
            await self._run_ffmpeg_command(cmd)
            
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
                
                if os.path.exists(final_with_audio_path) and os.path.getsize(final_with_audio_path) > 0:
                    try:
                        if os.path.exists(output_video_path):
                            os.remove(output_video_path)
                        os.rename(final_with_audio_path, output_video_path)
                        logger.info(f"音频合并成功: {output_video_path}")
                    except Exception as e:
                        logger.warning(f"重命名音频视频文件失败: {e}")
                        output_video_path = final_with_audio_path
            
            if os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
                logger.info(f"最终视频合成成功: {output_video_path}")
                return output_video_path
            else:
                logger.error(f"最终视频合成失败: {output_video_path}")
                return None
        except Exception as e:
            logger.error(f"最终视频合成失败: {str(e)}")
            return None
        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.debug(f"已清理临时目录: {temp_dir}")
                except Exception as e:
                    logger.warning(f"清理临时目录失败: {e}")
    
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
            # 检查ffprobe是否可用
            if not self.ffprobe_path:
                logger.warning("ffprobe未找到，返回默认视频信息")
                return {
                    'duration': 10,  # 假设默认时长10秒
                    'width': 1920,
                    'height': 1080,
                    'bitrate': 0,
                    'format_name': 'mp4'
                }
            
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
    
    async def download_video(self, video_url: str, output_path: str) -> str:
        """下载视频文件"""
        try:
            logger.info(f"开始下载视频: {video_url} -> {output_path}")
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 使用requests库下载视频
            import requests
            
            # 发送GET请求下载视频
            response = requests.get(video_url, stream=True, timeout=60)
            response.raise_for_status()  # 检查请求是否成功
            
            # 写入文件
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"视频下载成功: {output_path}")
                return output_path
            else:
                logger.error(f"视频下载失败: {output_path}")
                return None
        except Exception as e:
            logger.error(f"视频下载失败: {str(e)}")
            return None
    
    async def extract_last_frame(self, video_path: str, output_path: str) -> Dict[str, Any]:
        """
        从视频中提取最后一帧
        
        Args:
            video_path: 视频文件路径
            output_path: 输出路径
            
        Returns:
            包含成功状态和最后一帧路径的字典
        """
        try:
            logger.info(f"开始从视频中提取最后一帧: {video_path} -> {output_path}")
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 清理可能存在的旧文件
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                    logger.info(f"已清理旧的最后一帧文件: {output_path}")
                except Exception as e:
                    logger.warning(f"清理旧文件失败: {str(e)}")
            
            # 方法1：使用ffprobe获取视频时长
            duration = None
            if self.ffprobe_path:
                try:
                    # 获取视频时长
                    duration_cmd = [
                        self.ffprobe_path, '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'default=noprint_wrappers=1:nokey=1', video_path
                    ]
                    
                    # 执行ffprobe命令获取视频时长
                    result = await asyncio.create_subprocess_exec(
                        *duration_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await result.communicate()
                    
                    if result.returncode == 0:
                        try:
                            duration = float(stdout.decode().strip())
                            logger.info(f"视频时长: {duration}秒")
                        except ValueError:
                            logger.warning(f"无法解析视频时长: {stdout.decode()}")
                    else:
                        logger.warning(f"ffprobe获取视频时长失败: {stderr.decode()}")
                except Exception as e:
                    logger.warning(f"使用ffprobe获取视频时长时发生异常: {str(e)}")
            else:
                logger.warning("ffprobe未找到，使用备选方法")
            
            # 方法列表，按优先级尝试
            extract_methods = []
            
            # 只有当duration有效时，才添加基于时长提取的方法
            if duration is not None and isinstance(duration, (int, float)):
                extract_methods.append(
                    {
                        "name": "基于时长提取",
                        "cmd": [
                            self.ffmpeg_path, '-i', video_path,
                            '-ss', str(max(0, duration - 0.1)),  # 使用0.1秒的偏移，更安全
                            '-vframes', '1',
                            '-q:v', '2',
                            '-y',
                            output_path
                        ],
                        "condition": True
                    }
                )
            
            # 添加其他提取方法
            extract_methods.extend([
                # 方法2：使用tail滤镜提取最后一个关键帧
                {
                    "name": "使用tail滤镜提取最后一个关键帧",
                    "cmd": [
                        self.ffmpeg_path, '-i', video_path,
                        '-vf', 'select=eq(pict_type,PICT_TYPE_I),tail=1',
                        '-vframes', '1',
                        '-q:v', '2',
                        '-y',
                        output_path
                    ],
                    "condition": True
                },
                # 方法3：使用reverse滤镜提取第一帧（即原视频的最后一帧）
                {
                    "name": "使用reverse滤镜提取第一帧",
                    "cmd": [
                        self.ffmpeg_path, '-i', video_path,
                        '-vf', 'reverse',
                        '-vframes', '1',
                        '-q:v', '2',
                        '-y',
                        output_path
                    ],
                    "condition": True
                },
                # 方法4：使用更简单的命令，直接提取最后一帧
                {
                    "name": "使用简单命令提取最后一帧",
                    "cmd": [
                        self.ffmpeg_path, '-i', video_path,
                        '-vframes', '1',
                        '-q:v', '2',
                        '-y',
                        output_path
                    ],
                    "condition": True
                },
                # 方法5：使用seek到视频末尾的方式
                {
                    "name": "使用seek到视频末尾的方式",
                    "cmd": [
                        self.ffmpeg_path, '-sseof', '-1', '-i', video_path,
                        '-vframes', '1',
                        '-q:v', '2',
                        '-y',
                        output_path
                    ],
                    "condition": True
                }
            ])
            
            # 尝试所有可用的方法
            for method in extract_methods:
                if method["condition"]:
                    logger.info(f"尝试方法: {method['name']}")
                    logger.debug(f"执行命令: {' '.join(method['cmd'])}")
                    
                    try:
                        # 执行ffmpeg命令
                        result = await asyncio.create_subprocess_exec(
                            *method['cmd'],
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await result.communicate()
                        
                        # 检查命令执行结果
                        if result.returncode == 0:
                            # 检查输出文件是否有效
                            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                                logger.info(f"成功提取最后一帧: {output_path} (使用方法: {method['name']})")
                                return {
                                    'success': True,
                                    'frame_path': output_path,
                                    'method_used': method['name']
                                }
                            else:
                                logger.warning(f"方法 {method['name']} 执行成功，但输出文件无效")
                        else:
                            error_msg = stderr.decode('utf-8', errors='ignore')
                            logger.warning(f"方法 {method['name']} 执行失败: {error_msg}")
                    except Exception as e:
                        logger.warning(f"方法 {method['name']} 执行异常: {str(e)}")
            
            # 如果所有方法都失败，尝试使用更基础的方法
            logger.info("尝试使用最基础的方法提取最后一帧")
            try:
                # 使用最基础的命令，不使用复杂的滤镜
                basic_cmd = [
                    self.ffmpeg_path,
                    '-i', video_path,
                    '-vf', 'select=v:eq(n\,N-1)',
                    '-vframes', '1',
                    '-q:v', '2',
                    '-y',
                    output_path
                ]
                
                logger.debug(f"执行基础命令: {' '.join(basic_cmd)}")
                
                result = await asyncio.create_subprocess_exec(
                    *basic_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info(f"成功提取最后一帧: {output_path} (使用基础方法)")
                    return {
                        'success': True,
                        'frame_path': output_path,
                        'method_used': '基础方法'
                    }
            except Exception as e:
                logger.warning(f"基础方法执行失败: {str(e)}")
            
            # 所有方法都失败
            logger.error(f"所有提取最后一帧的方法都失败了: {video_path}")
            return {'success': False, 'error': '所有提取方法都失败了'}
        except Exception as e:
            logger.error(f"提取最后一帧失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    async def remove_audio(self, video_path: str) -> str:
        """
        移除视频中的音频轨道
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            移除音频后的视频路径
        """
        try:
            logger.info(f"开始移除视频中的音频: {video_path}")
            
            # 生成输出路径
            output_dir = os.path.dirname(video_path)
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(output_dir, f"{base_name}_no_audio.mp4")
            
            # 构建FFmpeg命令
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-c:v', 'copy',  # 复制视频轨道
                '-an',  # 移除音频轨道
                '-y',  # 覆盖输出文件
                output_path
            ]
            
            # 执行FFmpeg命令
            await self._run_ffmpeg_command(cmd)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"音频移除成功: {output_path}")
                return output_path
            else:
                logger.error(f"音频移除失败: {output_path}")
                return video_path  # 如果失败，返回原始视频路径
        except Exception as e:
            logger.error(f"音频移除失败: {str(e)}")
            return video_path  # 如果异常，返回原始视频路径
    
    def normalize_frame_path(self, frame_path: str) -> str:
        """
        标准化帧路径为file://格式的绝对路径
        
        Args:
            frame_path: 本地文件路径或URL
            
        Returns:
            file://格式的绝对路径或原URL
        """
        try:
            # 如果已经是URL格式，直接返回
            if frame_path.startswith('file://') or \
               frame_path.startswith('http://') or \
               frame_path.startswith('https://'):
                return frame_path
            
            # 转换为绝对路径
            abs_path = os.path.abspath(frame_path)
            
            # 转换为file://格式
            # 在Windows上，需要处理盘符（例如：C:\path -> file:///C:/path）
            if os.name == 'nt':  # Windows
                # 将反斜杠转换为正斜杠
                abs_path = abs_path.replace('\\', '/')
                # 添加file://前缀
                return f"file:///{abs_path}"
            else:  # Linux/Mac
                return f"file://{abs_path}"
        except Exception as e:
            logger.error(f"路径标准化失败: {str(e)}")
            return frame_path  # 失败时返回原路径
    
    async def sync_audio_video(self, video_path: str, audio_path: str, output_path: str) -> Dict[str, Any]:
        """
        同步音频和视频
        
        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出文件路径
            
        Returns:
            包含成功状态和输出路径的字典
        """
        try:
            logger.info(f"开始同步音频和视频: {video_path} + {audio_path} -> {output_path}")
            
            # 1. 验证输入文件
            if not os.path.exists(video_path):
                error_msg = f'视频文件不存在: {video_path}'
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            if not os.path.exists(audio_path):
                error_msg = f'音频文件不存在: {audio_path}'
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # 2. 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # 3. 构建FFmpeg命令（使用更兼容的参数）
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',  # 复制视频流
                '-c:a', 'aac',   # 重新编码音频为AAC
                '-b:a', '192k',  # 设置音频比特率
                '-strict', 'experimental',
                '-shortest',     # 使用最短的时长
                '-y',            # 覆盖输出文件
                output_path
            ]
            
            # 4. 执行命令并捕获详细错误
            logger.info(f"执行音视频同步命令: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            # 5. 检查执行结果
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"FFmpeg执行失败: {error_msg}")
                return {
                    'success': False,
                    'error': f'FFmpeg执行失败: {error_msg}',
                    'returncode': process.returncode
                }
            
            # 6. 验证输出文件
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"音视频同步成功: {output_path}, 文件大小: {os.path.getsize(output_path)} 字节")
                return {
                    'success': True,
                    'output_path': output_path
                }
            else:
                error_msg = '输出文件不存在或为空'
                logger.error(f"音视频同步失败: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
        except Exception as e:
            error_msg = f"音视频同步异常: {str(e)}"
            logger.error(error_msg)
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': error_msg
            }
    
    async def compose_videos(self, video_paths: List[str], output_path: str) -> Dict[str, Any]:
        """
        合成多个视频片段
        
        Args:
            video_paths: 视频片段路径列表
            output_path: 输出文件路径
            
        Returns:
            包含成功状态和输出路径的字典
        """
        try:
            logger.info(f"开始合成视频片段: {len(video_paths)}个片段 -> {output_path}")
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 过滤掉不存在的视频文件
            valid_video_paths = []
            for video_path in video_paths:
                if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                    valid_video_paths.append(video_path)
                    logger.info(f"添加有效视频片段: {video_path}")
                else:
                    logger.warning(f"跳过无效视频片段: {video_path}")
            
            if not valid_video_paths:
                logger.error("没有有效的视频片段可以合成")
                return {
                    'success': False,
                    'error': '没有有效的视频片段可以合成'
                }
            
            # 创建临时文件列表
            temp_dir = os.path.join(os.path.dirname(output_path), f"temp_{uuid.uuid4().hex[:8]}")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 生成视频片段列表文件
            segment_list_path = os.path.join(temp_dir, "segments.txt")
            with open(segment_list_path, 'w', encoding='utf-8') as f:
                for video_path in valid_video_paths:
                    # 使用绝对路径，确保FFmpeg能正确找到文件
                    abs_path = os.path.abspath(video_path)
                    # 转义路径中的特殊字符
                    abs_path = abs_path.replace('\\', '/')
                    f.write(f"file '{abs_path}'\n")
            
            # 打印生成的segments.txt文件内容
            with open(segment_list_path, 'r', encoding='utf-8') as f:
                logger.info(f"生成的segments.txt内容: {f.read()}")
            
            # 构建FFmpeg命令
            cmd = [
                self.ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', segment_list_path,
                '-c', 'copy',
                '-y',
                output_path
            ]
            
            logger.info(f"执行FFmpeg命令: {' '.join(cmd)}")
            
            # 执行FFmpeg命令
            result = await self._run_ffmpeg_command(cmd)
            logger.info(f"FFmpeg命令执行结果: {result}")
            
            # 检查输出文件
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"视频合成成功: {output_path}")
                # 清理临时文件
                if os.path.exists(segment_list_path):
                    os.remove(segment_list_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
                return {
                    'success': True,
                    'output_path': output_path
                }
            else:
                logger.error(f"视频合成失败: {output_path}")
                # 保留临时文件以便调试
                logger.info(f"保留临时文件用于调试: {segment_list_path}")
                return {
                    'success': False,
                    'error': '输出文件不存在或为空'
                }
        except Exception as e:
            logger.error(f"视频合成失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
