"""
FFmpeg 拼接与信息读取（pipeline combine-video 使用）
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _find_exe(name: str) -> Optional[str]:
    try:
        if os.name == 'nt':
            r = subprocess.run(['where', name], capture_output=True, text=True)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip().split('\n')[0]
        else:
            r = subprocess.run(['which', name], capture_output=True, text=True)
            if r.returncode == 0:
                return r.stdout.strip()
    except Exception:
        pass
    return None


class FFmpegService:
    def __init__(self, config: Dict[str, Any] | None = None):
        self.ffmpeg_path = (config or {}).get('ffmpeg_path') or _find_exe('ffmpeg')
        self.ffprobe_path = (config or {}).get('ffprobe_path') or _find_exe('ffprobe')
        if not self.ffmpeg_path:
            raise RuntimeError('未找到 ffmpeg，请安装并加入 PATH')

    async def _run(self, cmd: List[str]) -> subprocess.CompletedProcess:
        def _sync():
            return subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        return await asyncio.to_thread(_sync)

    async def concatenate_videos(self, video_paths: List[str], output_path: str) -> Optional[str]:
        """将多个视频文件无损拼接为单个文件（codec copy）。"""
        valid = [p for p in video_paths if p and os.path.isfile(p)]
        if not valid:
            logger.error('concatenate_videos: 无有效输入文件')
            return None

        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        tmp_dir = tempfile.mkdtemp(prefix='ffmpeg_concat_')
        list_file = os.path.join(tmp_dir, 'list.txt')
        try:
            with open(list_file, 'w', encoding='utf-8') as f:
                for p in valid:
                    ap = os.path.abspath(p).replace('\\', '/')
                    f.write(f"file '{ap}'\n")

            cmd = [
                self.ffmpeg_path,
                '-y',
                '-f',
                'concat',
                '-safe',
                '0',
                '-i',
                list_file,
                '-c',
                'copy',
                output_path,
            ]
            proc = await self._run(cmd)
            if proc.returncode != 0:
                logger.error('ffmpeg concat failed: %s', proc.stderr)
                return None
            if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
                return output_path
        finally:
            try:
                os.remove(list_file)
                os.rmdir(tmp_dir)
            except OSError:
                pass
        return None

    async def compose_videos(self, video_paths: List[str], output_path: str) -> Dict[str, Any]:
        """供 storyboard_to_video_service 等调用，与 concatenate_videos 等价，返回 success 字典。"""
        out = await self.concatenate_videos(video_paths, output_path)
        if out:
            return {'success': True, 'path': out}
        return {'success': False, 'error': 'FFmpeg 拼接失败'}

    async def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """返回 duration、resolution、fps 等简单信息。"""
        if not self.ffprobe_path:
            return {'duration': 0, 'resolution': '', 'fps': 0}
        cmd = [
            self.ffprobe_path,
            '-v',
            'quiet',
            '-print_format',
            'json',
            '-show_format',
            '-show_streams',
            video_path,
        ]
        proc = await self._run(cmd)
        if proc.returncode != 0:
            return {'duration': 0, 'resolution': '', 'fps': 0}
        try:
            data = json.loads(proc.stdout or '{}')
        except json.JSONDecodeError:
            return {'duration': 0, 'resolution': '', 'fps': 0}

        fmt = data.get('format') or {}
        duration = float(fmt.get('duration') or 0)
        width = height = 0
        fps = 0.0
        for s in data.get('streams') or []:
            if s.get('codec_type') == 'video':
                width = int(s.get('width') or 0)
                height = int(s.get('height') or 0)
                fr = s.get('r_frame_rate') or '0/1'
                if '/' in fr:
                    a, b = fr.split('/')
                    try:
                        fps = float(a) / float(b) if float(b) else 0
                    except ValueError:
                        fps = 0
                break

        resolution = f'{width}x{height}' if width and height else ''
        return {
            'duration': duration,
            'resolution': resolution,
            'fps': fps,
        }
