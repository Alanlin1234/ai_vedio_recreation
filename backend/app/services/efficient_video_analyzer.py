"""
高效视频分析服务
采用采样 + 语音转写策略，大幅降低延迟和成本
"""

import os
import sys
import time
import base64
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import Field

import dashscope
from dashscope import Generation

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config import config


class EfficientVideoAnalyzer:
    """
    高效视频分析器

    流程：
    1. 智能抽帧（场景切换检测 + 均匀采样，最多16帧）
    2. 音频提取 + 语音转写（SiliconFlow/SenseVoice）
    3. Qwen-VL 分析关键帧 + 文本 → 故事理解
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.DASHSCOPE_API_KEY
        self.speech_api_key = config.SILICONFLOW_API_KEY
        dashscope.api_key = self.api_key

    async def analyze_video(self, video_path: str) -> Dict[str, Any]:
        """
        完整的高效视频分析流程

        Args:
            video_path: 视频文件路径

        Returns:
            包含分析结果的字典
        """
        start_time = time.time()

        try:
            if not os.path.exists(video_path):
                return {
                    "success": False,
                    "error": f"视频文件不存在: {video_path}"
                }

            from app.services.ffmpeg_service import FFmpegService
            ffmpeg_service = FFmpegService()

            audio_result = await ffmpeg_service.extract_audio(video_path)
            audio_path = audio_result.get('audio_path') if audio_result else None

            transcription = None
            if audio_path and os.path.exists(audio_path):
                transcription = await self._transcribe_audio(audio_path)

            keyframes_result = await ffmpeg_service.extract_smart_keyframes(
                video_path,
                max_frames=16,
                min_interval=2.0
            )
            keyframes = keyframes_result.get('keyframes', [])

            if not keyframes:
                return {
                    "success": False,
                    "error": "关键帧提取失败"
                }

            frame_descriptions = await self._analyze_keyframes_with_qwenvl(keyframes)

            story_content = await self._generate_story_from_frames_and_text(
                frame_descriptions,
                transcription,
                keyframes_result.get('duration', 0)
            )

            time_cost = time.time() - start_time

            return {
                "success": True,
                "video_path": os.path.abspath(video_path),
                "analysis_type": "efficient_video_analysis",
                "time_cost": round(time_cost, 2),
                "content": story_content,
                "timestamp": datetime.now().isoformat(),
                "keyframes_count": len(keyframes),
                "keyframes": keyframes,
                "transcription": transcription,
                "frame_descriptions": frame_descriptions
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"高效视频分析失败: {str(e)}"
            }

    async def _transcribe_audio(self, audio_path: str) -> Optional[str]:
        """
        语音转写：使用 SiliconFlow SenseVoice
        """
        try:
            from app.services.speech_recognition_service import SiliconFlowSpeechRecognizer

            recognizer = SiliconFlowSpeechRecognizer(api_key=self.speech_api_key)
            result = recognizer.transcribe_audio(audio_path, model="FunAudioLLM/SenseVoiceSmall")

            if result.get('success'):
                text = result.get('text', '')
                print(f"[语音转写] 成功，转写长度: {len(text)}")
                return text
            else:
                print(f"[语音转写] 失败: {result.get('error')}")
                return None

        except Exception as e:
            print(f"[语音转写] 异常: {str(e)}")
            return None

    async def _analyze_keyframes_with_qwenvl(
        self,
        keyframes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        使用 Qwen-VL 分析关键帧
        每批5张图，控制token消耗
        """
        descriptions = []

        batch_size = 5
        for i in range(0, len(keyframes), batch_size):
            batch = keyframes[i:i+batch_size]

            image_contents = []
            for kf in batch:
                if os.path.exists(kf['path']):
                    with open(kf['path'], 'rb') as f:
                        img_data = f.read()
                    img_b64 = base64.b64encode(img_data).decode('utf-8')
                    image_contents.append({
                        'url': f"data:image/jpeg;base64,{img_b64}"
                    })

            if not image_contents:
                continue

            prompt = f"""请分析这些图片序列，描述每个画面的：
1. 场景（时间、地点、环境）
2. 人物/主体（动作、表情、外观）
3. 重要物体
4. 氛围/情绪

图片时间点：{[f"{kf['timestamp']:.1f}s" for kf in batch]}

请按顺序描述每个画面。"""

            try:
                response = Generation.call(
                    model="qwen-vl-flash",
                    messages=[
                        {"role": "user", "content": [
                            {"image": img['url']} for img in image_contents
                        ] + [{"text": prompt}]}
                    ],
                    result_format='message',
                    temperature=0.7,
                    max_tokens=1500
                )

                if response.status_code == 200:
                    content = response.output.choices[0].message.content
                    for j, kf in enumerate(batch):
                        descriptions.append({
                            'timestamp': kf['timestamp'],
                            'scene_change': kf.get('scene_change', False),
                            'description': content
                        })
                    print(f"[帧分析] 第 {i//batch_size + 1} 批完成")
                else:
                    print(f"[帧分析] API失败: {response.message}")

            except Exception as e:
                print(f"[帧分析] 异常: {str(e)}")

        return descriptions

    async def _generate_story_from_frames_and_text(
        self,
        frame_descriptions: List[Dict[str, Any]],
        transcription: Optional[str],
        duration: float
    ) -> str:
        """
        整合关键帧描述和语音转写，生成视频故事理解
        """
        frames_text = "\n".join([
            f"[{fd['timestamp']:.1f}s] {fd['description']}"
            for fd in frame_descriptions
        ])

        transcription_text = f"\n\n语音转写内容：\n{transcription}" if transcription else "\n\n（无语音内容）"

        prompt = f"""请简洁描述这个视频的故事（100字以内）：

视频时长：{duration:.0f}秒

关键帧描述：
{frames_text}
{transcription_text}

要求：用简洁流畅的语言概括故事主线，不要罗列细节。"""

        try:
            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你是一个专业的故事分析师，擅长深度理解视频叙事内容。"},
                    {"role": "user", "content": prompt}
                ],
                result_format='message',
                temperature=0.7,
                max_tokens=400
            )

            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                return f"视频分析完成（{len(frame_descriptions)}个关键帧）"

        except Exception as e:
            print(f"[故事生成] 异常: {str(e)}")
            return f"视频分析完成（{len(frame_descriptions)}个关键帧）"


class EfficientVideoAnalyzerWithHighlights:
    """
    带亮点提取的高效视频分析器
    在 EfficientVideoAnalyzer 基础上，增加亮点和教育意义提取
    """

    def __init__(self, api_key: str = None):
        self.analyzer = EfficientVideoAnalyzer(api_key)

    async def analyze_video_complete(self, video_path: str) -> Dict[str, Any]:
        """
        完整的视频分析：内容 + 亮点 + 教育意义
        """
        base_result = await self.analyzer.analyze_video(video_path)

        if not base_result.get('success'):
            return base_result

        story_content = base_result.get('content', '')

        highlights = await self._extract_highlights(story_content)
        educational = await self._extract_educational(story_content)

        return {
            **base_result,
            'highlights': highlights,
            'educational_meaning': educational
        }

    async def _extract_highlights(self, story_content: str) -> str:
        """提炼故事亮点"""
        if not story_content or len(story_content) < 50:
            return "暂无亮点描述"

        try:
            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你是一个简洁的影视评论家。"},
                    {"role": "user", "content": f"用3句话概括这个故事的精彩之处，每个亮点不超过20字：\n\n{story_content[:1000]}"}
                ],
                result_format='message',
                temperature=0.8,
                max_tokens=300
            )

            print(f"[亮点提取] 响应状态码: {response.status_code}")

            if response.status_code == 200:
                content = response.output.choices[0].message.content
                print(f"[亮点提取] 成功: {content[:50]}...")
                return content
            else:
                print(f"[亮点提取] 失败: {getattr(response, 'message', 'unknown')}")
                return "精彩的故事"

        except Exception as e:
            print(f"[亮点提取] 异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return "精彩的故事"

    async def _extract_educational(self, story_content: str) -> str:
        """提取教育意义"""
        if not story_content or len(story_content) < 50:
            return "暂无教育意义描述"

        try:
            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你是一个简洁的教育专家。"},
                    {"role": "user", "content": f"用2句话概括这个故事的教育意义，每句不超过25字：\n\n{story_content[:1000]}"}
                ],
                result_format='message',
                temperature=0.7,
                max_tokens=200
            )

            print(f"[教育意义] 响应状态码: {response.status_code}")

            if response.status_code == 200:
                content = response.output.choices[0].message.content
                print(f"[教育意义] 成功: {content[:50]}...")
                return content
            else:
                print(f"[教育意义] 失败: {getattr(response, 'message', 'unknown')}")
                return "富有教育意义"

        except Exception as e:
            print(f"[教育意义] 异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return "富有教育意义"
