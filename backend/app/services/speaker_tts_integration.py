"""
说话人TTS集成服务
整合说话人识别和TTS，实现基于voice seed的声音一致性生成
"""
import os
import sys
from typing import Dict, List, Any, Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.services.speaker_voice_service import SpeakerVoiceService
from app.services.text_to_speech_service import TextToSpeechService
from app.services.ffmpeg_service import FFmpegService


class SpeakerTTSIntegration:
    """说话人TTS集成服务"""
    
    def __init__(self):
        self.speaker_service = SpeakerVoiceService()
        self.tts_service = TextToSpeechService()
        self.ffmpeg_service = FFmpegService()
    
    async def process_video_slices_with_voice_consistency(
        self,
        video_slices: List[Dict[str, Any]],
        output_dir: str
    ) -> Dict[str, Any]:
        """
        处理视频切片，提取说话人信息并生成一致的语音
        
        Args:
            video_slices: 视频切片列表
            output_dir: 输出目录
            
        Returns:
            处理结果，包含说话人信息和生成的音频
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 步骤1: 提取所有切片的说话人信息
        print("[说话人TTS] 步骤1: 提取说话人信息...")
        speaker_result = self.speaker_service.process_video_slices_with_speakers(video_slices)
        
        if not speaker_result.get('success'):
            return {
                'success': False,
                'error': '提取说话人信息失败'
            }
        
        print(f"[说话人TTS] 识别到 {speaker_result['total_unique_speakers']} 个唯一说话人")
        
        # 步骤2: 为每个切片生成对应的语音
        # 这里假设每个切片有对应的文本内容
        print("[说话人TTS] 步骤2: 为每个切片生成语音...")
        generated_audios = []
        speaker_mapping = speaker_result['speaker_mapping']
        
        for slice_info in speaker_result['slices']:
            slice_id = slice_info['slice_id']
            speakers = slice_info['speakers']
            
            # 找到原始切片信息
            original_slice = next(
                (s for s in video_slices if s.get('slice_id') == slice_id),
                None
            )
            
            if not original_slice:
                continue
            
            # 假设从某个地方获取文本内容（例如从scene_prompts）
            text = original_slice.get('text', '') or original_slice.get('script', '')
            
            if not text:
                print(f"[说话人TTS] 警告: 切片 {slice_id} 没有文本内容，跳过")
                continue
            
            # 为每个说话人生成对应的语音
            for speaker in speakers:
                speaker_id = speaker['speaker_id']
                voice_seed = speaker_mapping.get(speaker_id)
                
                # 生成输出路径
                audio_output_path = os.path.join(
                    output_dir,
                    f"{slice_id}_speaker_{speaker_id}.mp3"
                )
                
                # 使用voice seed生成语音
                tts_result = self.tts_service.text_to_speech(
                    text=text,
                    output_path=audio_output_path,
                    voice_seed=voice_seed,
                    speaker_id=speaker_id
                )
                
                if tts_result.get('success'):
                    generated_audios.append({
                        'slice_id': slice_id,
                        'speaker_id': speaker_id,
                        'voice_seed': voice_seed,
                        'audio_path': tts_result['audio_path'],
                        'text': text
                    })
                    print(f"[说话人TTS] 为切片 {slice_id} 的说话人 {speaker_id} 生成语音成功")
                else:
                    print(f"[说话人TTS] 为切片 {slice_id} 的说话人 {speaker_id} 生成语音失败: {tts_result.get('error')}")
        
        return {
            'success': True,
            'speaker_info': speaker_result,
            'generated_audios': generated_audios,
            'total_audios': len(generated_audios)
        }
    
    def generate_audio_with_speaker(
        self,
        text: str,
        speaker_id: Optional[str] = None,
        audio_sample_path: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        为指定说话人生成语音
        
        Args:
            text: 要生成的文本
            speaker_id: 说话人ID（如果提供，将使用已保存的voice seed）
            audio_sample_path: 音频样本路径（如果speaker_id不存在，将从此音频提取）
            output_path: 输出音频路径
            
        Returns:
            TTS生成结果
        """
        voice_seed = None
        
        # 如果提供了speaker_id，尝试获取对应的voice_seed
        if speaker_id:
            voice_seed = self.speaker_service.get_speaker_voice_seed(speaker_id)
            if voice_seed:
                print(f"[说话人TTS] 使用已保存的说话人 {speaker_id} 的voice seed: {voice_seed}")
        
        # 如果speaker_id不存在但提供了音频样本，提取并保存
        if not voice_seed and audio_sample_path and os.path.exists(audio_sample_path):
            print(f"[说话人TTS] 从音频样本提取说话人信息...")
            speaker_result = self.speaker_service.extract_speakers_from_audio(audio_sample_path)
            
            if speaker_result.get('success') and speaker_result.get('speakers'):
                speaker = speaker_result['speakers'][0]
                extracted_speaker_id = speaker.get('speaker_id')
                voice_seed = speaker.get('voice_seed')
                
                # 保存voice seed
                if not speaker_id:
                    speaker_id = extracted_speaker_id
                
                save_result = self.speaker_service.save_speaker_voice_seed(
                    speaker_id=speaker_id,
                    voice_seed=voice_seed,
                    audio_sample_path=audio_sample_path
                )
                
                if save_result.get('success'):
                    print(f"[说话人TTS] 成功保存说话人 {speaker_id} 的voice seed")
        
        # 如果仍然没有voice_seed，使用默认值
        if not voice_seed:
            print(f"[说话人TTS] 警告: 未找到voice seed，将使用默认voice")
        
        # 生成语音
        return self.tts_service.text_to_speech(
            text=text,
            output_path=output_path,
            voice_seed=voice_seed,
            speaker_id=speaker_id
        )


# 使用示例
if __name__ == "__main__":
    import asyncio
    
    integration = SpeakerTTSIntegration()
    
    # 示例1: 处理视频切片
    async def example_process_slices():
        video_slices = [
            {
                'slice_id': 'slice_0',
                'output_file': 'path/to/slice_0.mp4',
                'audio_file': 'path/to/slice_0_audio.wav',
                'text': '这是第一个场景的文本内容'
            },
            {
                'slice_id': 'slice_1',
                'output_file': 'path/to/slice_1.mp4',
                'audio_file': 'path/to/slice_1_audio.wav',
                'text': '这是第二个场景的文本内容'
            }
        ]
        
        result = await integration.process_video_slices_with_voice_consistency(
            video_slices=video_slices,
            output_dir='./output/audio'
        )
        
        print(f"处理结果: {result}")
    
    # 示例2: 为特定说话人生成语音
    def example_generate_with_speaker():
        # 方式1: 使用已保存的speaker_id
        result1 = integration.generate_audio_with_speaker(
            text="这是要生成的文本内容",
            speaker_id="speaker_abc123",
            output_path="./output/audio/speaker_abc123.mp3"
        )
        print(f"结果1: {result1}")
        
        # 方式2: 从音频样本提取说话人信息
        result2 = integration.generate_audio_with_speaker(
            text="这是要生成的文本内容",
            audio_sample_path="./samples/speaker_sample.wav",
            output_path="./output/audio/new_speaker.mp3"
        )
        print(f"结果2: {result2}")
    
    # 运行示例
    # asyncio.run(example_process_slices())
    # example_generate_with_speaker()

