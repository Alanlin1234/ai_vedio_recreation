"""
说话人识别和声纹管理服务
支持从视频切片中提取说话人信息，并为每个人物分配和管理voice seed
"""
import os
import sys
import json
import hashlib
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import requests

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config
# from app.models import db  # 暂时注释，如果需要数据库存储可以启用


class SpeakerVoiceService:
    """说话人识别和声纹管理服务"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.SILICONFLOW_API_KEY
        self.base_url = Config.SILICONFLOW_BASE_URL
        
        # 使用pyannote.audio进行说话人识别（可选，需要安装）
        self.use_pyannote = False
        try:
            from pyannote.audio import Pipeline
            # 需要先获取token: https://huggingface.co/pyannote/speaker-diarization
            # self.diarization_pipeline = Pipeline.from_pretrained(
            #     "pyannote/speaker-diarization-3.1",
            #     use_auth_token="YOUR_HF_TOKEN"
            # )
            # self.use_pyannote = True
        except ImportError:
            print("[说话人识别] pyannote.audio未安装，将使用基于ASR的简化方法")
            self.use_pyannote = False
    
    def extract_speakers_from_audio(
        self, 
        audio_path: str, 
        video_slice_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从音频文件中提取说话人信息
        
        Args:
            audio_path: 音频文件路径
            video_slice_id: 视频切片ID（可选）
            
        Returns:
            包含说话人信息和声纹特征的结果
        """
        try:
            if not os.path.exists(audio_path):
                return {
                    'success': False,
                    'error': f'音频文件不存在: {audio_path}'
                }
            
            # 方法1: 使用pyannote.audio进行说话人分离
            if self.use_pyannote:
                return self._extract_speakers_with_pyannote(audio_path, video_slice_id)
            
            # 方法2: 使用简化方法（基于ASR的时间戳和声纹特征）
            return self._extract_speakers_simplified(audio_path, video_slice_id)
            
        except Exception as e:
            return {
                'success': False,
                'error': f'说话人提取失败: {str(e)}'
            }
    
    def _extract_speakers_with_pyannote(
        self, 
        audio_path: str, 
        video_slice_id: Optional[str]
    ) -> Dict[str, Any]:
        """使用pyannote.audio提取说话人"""
        # 运行说话人分离
        diarization = self.diarization_pipeline(audio_path)
        
        speakers = {}
        speaker_segments = []
        
        # 处理每个说话人片段
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker_id = speaker
            if speaker_id not in speakers:
                speakers[speaker_id] = {
                    'speaker_id': speaker_id,
                    'segments': [],
                    'total_duration': 0.0
                }
            
            segment = {
                'start': turn.start,
                'end': turn.end,
                'duration': turn.end - turn.start
            }
            speakers[speaker_id]['segments'].append(segment)
            speakers[speaker_id]['total_duration'] += segment['duration']
            speaker_segments.append({
                'speaker_id': speaker_id,
                'start': turn.start,
                'end': turn.end
            })
        
        # 计算每个说话人的声纹特征（使用音频片段）
        speaker_embeddings = {}
        for speaker_id, speaker_info in speakers.items():
            # 提取该说话人的音频片段并计算embedding
            embedding = self._extract_speaker_embedding(audio_path, speaker_info['segments'])
            speaker_embeddings[speaker_id] = embedding
            
            # 生成voice seed（使用embedding的哈希）
            voice_seed = self._generate_voice_seed_from_embedding(embedding)
            speakers[speaker_id]['voice_seed'] = voice_seed
            speakers[speaker_id]['embedding'] = embedding.tolist() if embedding is not None else None
        
        return {
            'success': True,
            'speakers': list(speakers.values()),
            'speaker_segments': speaker_segments,
            'total_speakers': len(speakers),
            'video_slice_id': video_slice_id,
            'audio_path': audio_path
        }
    
    def _extract_speakers_simplified(
        self, 
        audio_path: str, 
        video_slice_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        简化的说话人识别方法
        使用ASR API获取带时间戳的转录，然后为每个时间片段分配说话人
        """
        from app.services.speech_recognition_service import SimpleSpeechRecognizer
        
        try:
            # 调用ASR获取带时间戳的转录（如果API支持）
            recognizer = SimpleSpeechRecognizer()
            asr_result = recognizer.transcribe(audio_path)
            
            if not asr_result.get('success'):
                # 如果ASR失败，假设只有一个说话人
                return self._create_single_speaker_result(audio_path, video_slice_id)
            
            # 如果ASR支持说话人分离，使用ASR结果
            # 否则，假设整个音频片段是一个说话人
            text = asr_result.get('text', '')
            
            # 生成一个默认的说话人ID
            speaker_id = self._generate_speaker_id(audio_path)
            
            # 计算音频的简单特征作为voice seed
            voice_seed = self._generate_voice_seed_from_audio(audio_path)
            
            speaker_info = {
                'speaker_id': speaker_id,
                'text': text,
                'voice_seed': voice_seed,
                'start': 0.0,
                'end': self._get_audio_duration(audio_path),
                'duration': self._get_audio_duration(audio_path)
            }
            
            return {
                'success': True,
                'speakers': [speaker_info],
                'speaker_segments': [{
                    'speaker_id': speaker_id,
                    'start': 0.0,
                    'end': speaker_info['end']
                }],
                'total_speakers': 1,
                'video_slice_id': video_slice_id,
                'audio_path': audio_path,
                'asr_text': text
            }
            
        except Exception as e:
            print(f"[说话人识别] 简化方法失败: {e}")
            return self._create_single_speaker_result(audio_path, video_slice_id)
    
    def _create_single_speaker_result(
        self, 
        audio_path: str, 
        video_slice_id: Optional[str]
    ) -> Dict[str, Any]:
        """创建单个说话人的结果"""
        speaker_id = self._generate_speaker_id(audio_path)
        duration = self._get_audio_duration(audio_path)
        voice_seed = self._generate_voice_seed_from_audio(audio_path)
        
        return {
            'success': True,
            'speakers': [{
                'speaker_id': speaker_id,
                'voice_seed': voice_seed,
                'start': 0.0,
                'end': duration,
                'duration': duration
            }],
            'speaker_segments': [{
                'speaker_id': speaker_id,
                'start': 0.0,
                'end': duration
            }],
            'total_speakers': 1,
            'video_slice_id': video_slice_id,
            'audio_path': audio_path
        }
    
    def _generate_speaker_id(self, audio_path: str) -> str:
        """生成说话人ID"""
        # 使用音频文件的哈希和时间戳生成唯一ID
        file_hash = self._calculate_file_hash(audio_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"speaker_{file_hash[:8]}_{timestamp}"
    
    def _generate_voice_seed_from_audio(self, audio_path: str) -> str:
        """
        从音频文件生成voice seed
        这里使用文件哈希作为seed，实际应用中可以使用声纹特征
        """
        file_hash = self._calculate_file_hash(audio_path)
        # 将哈希转换为整数seed（用于TTS系统）
        seed_int = int(file_hash[:8], 16) % (2**31)  # 限制在32位整数范围内
        return str(seed_int)
    
    def _generate_voice_seed_from_embedding(self, embedding: np.ndarray) -> str:
        """从声纹embedding生成voice seed"""
        if embedding is None:
            return "0"
        # 使用embedding的哈希作为seed
        embedding_str = ''.join([str(x) for x in embedding.flatten()[:10]])  # 取前10个值
        seed_int = hash(embedding_str) % (2**31)
        return str(abs(seed_int))
    
    def _extract_speaker_embedding(
        self, 
        audio_path: str, 
        segments: List[Dict[str, float]]
    ) -> Optional[np.ndarray]:
        """
        提取说话人的声纹embedding
        这里使用简化方法，实际应用中可以使用专业的声纹识别模型
        """
        # TODO: 实现真正的声纹特征提取
        # 可以使用wav2vec2或其他声纹识别模型
        return None
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件的MD5哈希"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长"""
        try:
            import subprocess
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 
                 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
                capture_output=True,
                text=True
            )
            return float(result.stdout.strip())
        except:
            return 0.0
    
    def save_speaker_voice_seed(
        self, 
        speaker_id: str, 
        voice_seed: str, 
        audio_sample_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        保存说话人的voice seed到数据库或文件
        
        Args:
            speaker_id: 说话人ID
            voice_seed: voice seed值
            audio_sample_path: 音频样本路径（可选）
            metadata: 额外的元数据（可选）
            
        Returns:
            保存结果
        """
        try:
            # 这里可以保存到数据库
            # 为了简化，我们先保存到JSON文件
            voice_seeds_dir = os.path.join(
                os.path.dirname(__file__), '..', '..', 'data', 'voice_seeds'
            )
            os.makedirs(voice_seeds_dir, exist_ok=True)
            
            voice_seed_file = os.path.join(voice_seeds_dir, f"{speaker_id}.json")
            
            voice_seed_data = {
                'speaker_id': speaker_id,
                'voice_seed': voice_seed,
                'audio_sample_path': audio_sample_path,
                'metadata': metadata or {},
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            with open(voice_seed_file, 'w', encoding='utf-8') as f:
                json.dump(voice_seed_data, f, ensure_ascii=False, indent=2)
            
            return {
                'success': True,
                'speaker_id': speaker_id,
                'voice_seed': voice_seed,
                'file_path': voice_seed_file
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'保存voice seed失败: {str(e)}'
            }
    
    def get_speaker_voice_seed(self, speaker_id: str) -> Optional[str]:
        """
        获取说话人的voice seed
        
        Args:
            speaker_id: 说话人ID
            
        Returns:
            voice seed值，如果不存在则返回None
        """
        try:
            voice_seeds_dir = os.path.join(
                os.path.dirname(__file__), '..', '..', 'data', 'voice_seeds'
            )
            voice_seed_file = os.path.join(voice_seeds_dir, f"{speaker_id}.json")
            
            if os.path.exists(voice_seed_file):
                with open(voice_seed_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('voice_seed')
            
            return None
            
        except Exception as e:
            print(f"[说话人识别] 获取voice seed失败: {e}")
            return None
    
    def match_speaker_by_audio(
        self, 
        audio_path: str, 
        threshold: float = 0.8
    ) -> Optional[Dict[str, Any]]:
        """
        通过音频匹配已有的说话人
        
        Args:
            audio_path: 待匹配的音频文件路径
            threshold: 匹配阈值（0-1之间）
            
        Returns:
            匹配到的说话人信息，如果未匹配到则返回None
        """
        try:
            # 生成当前音频的voice seed
            current_voice_seed = self._generate_voice_seed_from_audio(audio_path)
            current_speaker_id = self._generate_speaker_id(audio_path)
            
            # 查找所有已保存的voice seed
            voice_seeds_dir = os.path.join(
                os.path.dirname(__file__), '..', '..', 'data', 'voice_seeds'
            )
            
            if not os.path.exists(voice_seeds_dir):
                return None
            
            # 遍历所有voice seed文件，查找匹配的
            best_match = None
            best_similarity = 0.0
            
            for filename in os.listdir(voice_seeds_dir):
                if not filename.endswith('.json'):
                    continue
                
                voice_seed_file = os.path.join(voice_seeds_dir, filename)
                with open(voice_seed_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                    saved_voice_seed = saved_data.get('voice_seed')
                    
                    # 简单的相似度计算（实际应用中应该使用更复杂的声纹匹配）
                    similarity = self._calculate_seed_similarity(
                        current_voice_seed, 
                        saved_voice_seed
                    )
                    
                    if similarity > best_similarity and similarity >= threshold:
                        best_similarity = similarity
                        best_match = saved_data
            
            return best_match if best_match else None
            
        except Exception as e:
            print(f"[说话人识别] 匹配说话人失败: {e}")
            return None
    
    def _calculate_seed_similarity(self, seed1: str, seed2: str) -> float:
        """
        计算两个voice seed的相似度
        这里使用简化方法，实际应用中应该使用声纹特征进行匹配
        """
        try:
            # 如果seed完全相同，相似度为1.0
            if seed1 == seed2:
                return 1.0
            
            # 计算数值差异（假设seed是数字字符串）
            try:
                val1 = int(seed1)
                val2 = int(seed2)
                # 使用绝对差异的倒数作为相似度（简化方法）
                diff = abs(val1 - val2)
                max_val = max(abs(val1), abs(val2), 1)
                similarity = 1.0 - min(diff / max_val, 1.0)
                return similarity
            except ValueError:
                # 如果不是数字，使用字符串相似度
                # 使用简单的编辑距离
                return 0.5  # 默认相似度
        except:
            return 0.0
    
    def process_video_slices_with_speakers(
        self, 
        video_slices: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量处理视频切片，提取每个切片的说话人信息
        
        Args:
            video_slices: 视频切片列表，每个切片包含output_file和audio_file
            
        Returns:
            包含所有切片说话人信息的结果
        """
        results = {
            'success': True,
            'slices': [],
            'all_speakers': {},  # 所有唯一的说话人
            'speaker_mapping': {}  # speaker_id -> voice_seed映射
        }
        
        for slice_info in video_slices:
            slice_id = slice_info.get('slice_id', f"slice_{slice_info.get('index', 0)}")
            audio_path = slice_info.get('audio_file') or slice_info.get('output_file')
            
            if not audio_path or not os.path.exists(audio_path):
                # 如果音频文件不存在，尝试从视频中提取
                video_path = slice_info.get('output_file')
                if video_path and os.path.exists(video_path):
                    # 这里应该调用音频提取服务
                    print(f"[说话人识别] 警告: 切片 {slice_id} 没有音频文件，跳过")
                    continue
                else:
                    continue
            
            # 提取说话人信息
            speaker_result = self.extract_speakers_from_audio(audio_path, slice_id)
            
            if speaker_result.get('success'):
                # 保存每个说话人的voice seed
                for speaker in speaker_result.get('speakers', []):
                    speaker_id = speaker['speaker_id']
                    voice_seed = speaker['voice_seed']
                    
                    # 检查是否已经存在该说话人
                    existing_speaker = results['all_speakers'].get(speaker_id)
                    if not existing_speaker:
                        # 保存voice seed
                        save_result = self.save_speaker_voice_seed(
                            speaker_id=speaker_id,
                            voice_seed=voice_seed,
                            audio_sample_path=audio_path,
                            metadata={
                                'slice_id': slice_id,
                                'video_path': slice_info.get('output_file')
                            }
                        )
                        
                        results['all_speakers'][speaker_id] = {
                            'speaker_id': speaker_id,
                            'voice_seed': voice_seed,
                            'first_seen_in': slice_id
                        }
                        results['speaker_mapping'][speaker_id] = voice_seed
                
                results['slices'].append({
                    'slice_id': slice_id,
                    'speakers': speaker_result.get('speakers', []),
                    'total_speakers': speaker_result.get('total_speakers', 0)
                })
        
        results['total_unique_speakers'] = len(results['all_speakers'])
        
        return results


# 使用示例
if __name__ == "__main__":
    service = SpeakerVoiceService()
    
    # 测试单个音频文件
    test_audio = "path/to/audio.wav"
    result = service.extract_speakers_from_audio(test_audio)
    print(f"说话人识别结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # 保存voice seed
    if result.get('success') and result.get('speakers'):
        speaker = result['speakers'][0]
        save_result = service.save_speaker_voice_seed(
            speaker_id=speaker['speaker_id'],
            voice_seed=speaker['voice_seed'],
            audio_sample_path=test_audio
        )
        print(f"保存结果: {save_result}")
        
        # 获取voice seed
        voice_seed = service.get_speaker_voice_seed(speaker['speaker_id'])
        print(f"获取到的voice seed: {voice_seed}")

