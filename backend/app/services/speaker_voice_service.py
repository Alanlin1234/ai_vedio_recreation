"""
说话人识别和声纹管理服务
支持从视频切片中提取说话人信息，并为每个人物分配和管理voice seed
支持多说话人分离和跨切片说话人匹配
"""
import os
import sys
import json
import hashlib
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import subprocess
import tempfile
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config


class SpeakerEmbeddingExtractor:
    """声纹特征提取器 - 支持多种后端"""
    
    def __init__(self, backend: str = 'auto'):
        self.backend = backend
        self.embedding_model = None
        self.embedding_dim = 192
        
        if backend in ['auto', 'speechbrain']:
            self._init_speechbrain()
        
        if self.embedding_model is None and backend in ['auto', 'pyannote']:
            self._init_pyannote_embedding()
    
    def _init_speechbrain(self):
        """初始化SpeechBrain声纹模型"""
        try:
            from speechbrain.inference.speaker import SpeakerRecognition
            self.embedding_model = SpeakerRecognition(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir="pretrained_models/spkrec-ecapa-voxceleb"
            )
            self.backend = 'speechbrain'
            self.embedding_dim = 192
            print("[声纹提取] SpeechBrain ECAPA-TDNN 模型加载成功")
        except Exception as e:
            print(f"[声纹提取] SpeechBrain加载失败: {e}")
            self.embedding_model = None
    
    def _init_pyannote_embedding(self):
        """初始化pyannote声纹模型"""
        try:
            from pyannote.audio import Model
            self.embedding_model = Model.from_pretrained(
                "pyannote/embedding",
                use_auth_token=os.environ.get("HUGGINGFACE_TOKEN", None)
            )
            self.backend = 'pyannote'
            self.embedding_dim = 512
            print("[声纹提取] pyannote/embedding 模型加载成功")
        except Exception as e:
            print(f"[声纹提取] pyannote embedding加载失败: {e}")
            self.embedding_model = None
    
    def extract_embedding(self, audio_path: str) -> Optional[np.ndarray]:
        """从音频文件提取声纹embedding"""
        if self.embedding_model is None:
            return self._extract_mfcc_embedding(audio_path)
        
        try:
            if self.backend == 'speechbrain':
                return self._extract_speechbrain_embedding(audio_path)
            elif self.backend == 'pyannote':
                return self._extract_pyannote_embedding(audio_path)
        except Exception as e:
            print(f"[声纹提取] {self.backend}提取失败: {e}")
            return self._extract_mfcc_embedding(audio_path)
        
        return self._extract_mfcc_embedding(audio_path)
    
    def _extract_speechbrain_embedding(self, audio_path: str) -> Optional[np.ndarray]:
        """使用SpeechBrain提取embedding"""
        try:
            embedding = self.embedding_model.encode_batch(audio_path)
            return embedding.squeeze().cpu().numpy()
        except Exception as e:
            print(f"[声纹提取] SpeechBrain提取失败: {e}")
            return None
    
    def _extract_pyannote_embedding(self, audio_path: str) -> Optional[np.ndarray]:
        """使用pyannote提取embedding"""
        try:
            import torch
            from pyannote.audio import Inference
            inference = Inference(self.embedding_model, window="whole")
            embedding = inference(audio_path)
            return embedding.cpu().numpy()
        except Exception as e:
            print(f"[声纹提取] pyannote提取失败: {e}")
            return None
    
    def _extract_mfcc_embedding(self, audio_path: str) -> Optional[np.ndarray]:
        """使用MFCC作为备选方案提取特征"""
        try:
            import wave
            import struct
            
            temp_wav = None
            if not audio_path.endswith('.wav'):
                temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_path = temp_wav.name
                temp_wav.close()
                
                cmd = [
                    'ffmpeg', '-y', '-i', audio_path,
                    '-ac', '1', '-ar', '16000',
                    '-f', 'wav', temp_path
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                if result.returncode != 0:
                    return None
                audio_path = temp_path
            
            with wave.open(audio_path, 'rb') as wf:
                n_frames = wf.getnframes()
                framerate = wf.getframerate()
                sample_width = wf.getsampwidth()
                
                frames = wf.readframes(min(n_frames, framerate * 10))
                
                if sample_width == 2:
                    samples = np.array(struct.unpack(f'{len(frames)//2}h', frames), dtype=np.float32)
                else:
                    samples = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
                
                samples = samples / (2 ** (8 * sample_width - 1))
            
            if temp_wav and os.path.exists(temp_path):
                os.remove(temp_path)
            
            mfcc = self._compute_mfcc(samples, framerate, n_mfcc=20)
            return mfcc.astype(np.float32)
            
        except Exception as e:
            print(f"[声纹提取] MFCC提取失败: {e}")
            return None
    
    def _compute_mfcc(self, signal: np.ndarray, sr: int, n_mfcc: int = 20) -> np.ndarray:
        """计算MFCC特征"""
        n_fft = 512
        hop_length = 256
        
        if len(signal) < n_fft:
            signal = np.pad(signal, (0, n_fft - len(signal)))
        
        frames_list = []
        for i in range(0, len(signal) - n_fft + 1, hop_length):
            frame = signal[i:i+n_fft]
            windowed = frame * np.hamming(n_fft)
            fft_result = np.abs(np.fft.rfft(windowed))
            frames_list.append(fft_result)
        
        if not frames_list:
            return np.zeros(n_mfcc)
        
        spectrogram = np.array(frames_list).T
        
        low_freq = 0
        high_freq = sr // 2
        n_mels = 26
        
        mel_points = np.linspace(
            2595 * np.log10(1 + low_freq / 700),
            2595 * np.log10(1 + high_freq / 700),
            n_mels + 2
        )
        hz_points = 700 * (10 ** (mel_points / 2595) - 1)
        bin_points = np.floor((n_fft + 1) * hz_points / sr).astype(int)
        
        filterbank = np.zeros((n_mels, spectrogram.shape[0]))
        for m in range(n_mels):
            f_left = bin_points[m]
            f_center = bin_points[m + 1]
            f_right = bin_points[m + 2]
            
            for k in range(f_left, f_center):
                if k < filterbank.shape[1]:
                    filterbank[m, k] = (k - f_left) / (f_center - f_left + 1e-10)
            for k in range(f_center, f_right):
                if k < filterbank.shape[1]:
                    filterbank[m, k] = (f_right - k) / (f_right - f_center + 1e-10)
        
        mel_spectrum = np.dot(filterbank, spectrogram)
        mel_spectrum = np.where(mel_spectrum == 0, np.finfo(float).eps, mel_spectrum)
        log_mel_spectrum = np.log(mel_spectrum)
        
        dct_matrix = np.zeros((n_mfcc, n_mels))
        for i in range(n_mfcc):
            for j in range(n_mels):
                dct_matrix[i, j] = np.cos(np.pi * i * (j + 0.5) / n_mels)
        
        mfcc = np.dot(dct_matrix, log_mel_spectrum)
        return np.mean(mfcc, axis=1)


class SpeakerDiarizationService:
    """说话人分离服务 - 支持多种后端"""
    
    def __init__(self, hf_token: Optional[str] = None):
        self.hf_token = hf_token or os.environ.get("HUGGINGFACE_TOKEN", None)
        self.diarization_pipeline = None
        self.use_pyannote = False
        
        self._init_pyannote()
    
    def _init_pyannote(self):
        """初始化pyannote说话人分离"""
        try:
            from pyannote.audio import Pipeline
            
            if self.hf_token:
                self.diarization_pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=self.hf_token
                )
            else:
                self.diarization_pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1"
                )
            
            self.use_pyannote = True
            print("[说话人分离] pyannote/speaker-diarization-3.1 加载成功")
        except Exception as e:
            print(f"[说话人分离] pyannote加载失败: {e}")
            print("[说话人分离] 将使用简化方法（假设单说话人）")
            self.use_pyannote = False
    
    def diarize(self, audio_path: str) -> Dict[str, Any]:
        """
        执行说话人分离
        
        Returns:
            {
                'success': bool,
                'speakers': [{'speaker_id': str, 'segments': [...], 'total_duration': float}],
                'speaker_segments': [{'speaker_id': str, 'start': float, 'end': float}]
            }
        """
        if self.use_pyannote and self.diarization_pipeline:
            return self._diarize_with_pyannote(audio_path)
        else:
            return self._diarize_simple(audio_path)
    
    def _diarize_with_pyannote(self, audio_path: str) -> Dict[str, Any]:
        """使用pyannote进行说话人分离"""
        try:
            diarization = self.diarization_pipeline(audio_path)
            
            speakers = {}
            speaker_segments = []
            
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
            
            return {
                'success': True,
                'speakers': list(speakers.values()),
                'speaker_segments': speaker_segments,
                'total_speakers': len(speakers),
                'method': 'pyannote'
            }
            
        except Exception as e:
            print(f"[说话人分离] pyannote分离失败: {e}")
            return self._diarize_simple(audio_path)
    
    def _diarize_simple(self, audio_path: str) -> Dict[str, Any]:
        """简化方法：假设整个音频是一个说话人"""
        duration = self._get_audio_duration(audio_path)
        speaker_id = f"speaker_0"
        
        return {
            'success': True,
            'speakers': [{
                'speaker_id': speaker_id,
                'segments': [{'start': 0.0, 'end': duration, 'duration': duration}],
                'total_duration': duration
            }],
            'speaker_segments': [{'speaker_id': speaker_id, 'start': 0.0, 'end': duration}],
            'total_speakers': 1,
            'method': 'simple'
        }
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长"""
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 
                 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
                capture_output=True,
                text=True
            )
            return float(result.stdout.strip())
        except:
            return 0.0


class SpeakerVoiceService:
    """说话人识别和声纹管理服务"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        hf_token: Optional[str] = None,
        embedding_backend: str = 'auto'
    ):
        self.api_key = api_key or Config.SILICONFLOW_API_KEY
        self.base_url = Config.SILICONFLOW_BASE_URL
        self.hf_token = hf_token or os.environ.get("HUGGINGFACE_TOKEN", None)
        
        self.embedding_extractor = SpeakerEmbeddingExtractor(backend=embedding_backend)
        self.diarization_service = SpeakerDiarizationService(hf_token=self.hf_token)
        
        self.speaker_registry: Dict[str, Dict[str, Any]] = {}
        self._load_speaker_registry()
    
    def _load_speaker_registry(self):
        """加载说话人注册表"""
        registry_path = self._get_registry_path()
        if os.path.exists(registry_path):
            try:
                with open(registry_path, 'r', encoding='utf-8') as f:
                    self.speaker_registry = json.load(f)
                print(f"[说话人注册表] 加载了 {len(self.speaker_registry)} 个已注册说话人")
            except Exception as e:
                print(f"[说话人注册表] 加载失败: {e}")
                self.speaker_registry = {}
    
    def _save_speaker_registry(self):
        """保存说话人注册表"""
        registry_path = self._get_registry_path()
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(self.speaker_registry, f, ensure_ascii=False, indent=2, default=self._json_serializer)
    
    def _json_serializer(self, obj):
        """JSON序列化器"""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def _get_registry_path(self) -> str:
        """获取注册表文件路径"""
        return os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'speaker_registry.json'
        )
    
    def extract_speakers_from_audio(
        self, 
        audio_path: str, 
        video_slice_id: Optional[str] = None,
        enable_matching: bool = True
    ) -> Dict[str, Any]:
        """
        从音频文件中提取说话人信息
        
        Args:
            audio_path: 音频文件路径
            video_slice_id: 视频切片ID（可选）
            enable_matching: 是否启用跨切片说话人匹配
            
        Returns:
            包含说话人信息和声纹特征的结果
        """
        try:
            if not os.path.exists(audio_path):
                return {
                    'success': False,
                    'error': f'音频文件不存在: {audio_path}'
                }
            
            print(f"[说话人识别] 处理音频: {audio_path}")
            
            diarization_result = self.diarization_service.diarize(audio_path)
            
            if not diarization_result.get('success'):
                return diarization_result
            
            speakers = diarization_result['speakers']
            speaker_segments = diarization_result['speaker_segments']
            
            for speaker in speakers:
                speaker_id = speaker['speaker_id']
                
                embedding = self._extract_speaker_embedding_from_segments(
                    audio_path, speaker['segments']
                )
                
                if embedding is not None:
                    speaker['embedding'] = embedding
                    speaker['embedding_dim'] = len(embedding)
                
                if enable_matching and embedding is not None:
                    matched_speaker = self._match_speaker_by_embedding(embedding)
                    if matched_speaker:
                        speaker['matched_to'] = matched_speaker['speaker_id']
                        speaker['voice_seed'] = matched_speaker['voice_seed']
                        speaker['is_new'] = False
                    else:
                        new_speaker_id = self._register_speaker(
                            embedding=embedding,
                            audio_path=audio_path,
                            slice_id=video_slice_id
                        )
                        speaker['speaker_id'] = new_speaker_id
                        speaker['voice_seed'] = self._generate_voice_seed_from_embedding(embedding)
                        speaker['is_new'] = True
                else:
                    speaker['voice_seed'] = self._generate_voice_seed_from_audio(audio_path)
                    speaker['is_new'] = True
            
            return {
                'success': True,
                'speakers': speakers,
                'speaker_segments': speaker_segments,
                'total_speakers': len(speakers),
                'video_slice_id': video_slice_id,
                'audio_path': audio_path,
                'diarization_method': diarization_result.get('method', 'unknown')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'说话人提取失败: {str(e)}'
            }
    
    def _extract_speaker_embedding_from_segments(
        self, 
        audio_path: str, 
        segments: List[Dict[str, float]]
    ) -> Optional[np.ndarray]:
        """从音频片段中提取说话人embedding"""
        embeddings = []
        
        for segment in segments[:3]:
            start_time = segment.get('start', 0)
            end_time = segment.get('end', 5)
            duration = end_time - start_time
            
            if duration <= 0:
                continue
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                cmd = [
                    'ffmpeg', '-y', '-i', audio_path,
                    '-ss', str(start_time), '-t', str(min(duration, 10)),
                    '-ac', '1', '-ar', '16000',
                    '-f', 'wav', temp_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                
                if result.returncode != 0:
                    continue
                
                if not os.path.exists(temp_path) or os.path.getsize(temp_path) < 1000:
                    continue
                
                embedding = self.embedding_extractor.extract_embedding(temp_path)
                if embedding is not None:
                    embeddings.append(embedding)
                    
            except Exception as e:
                print(f"[声纹提取] 片段处理失败: {e}")
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
        
        if embeddings:
            return np.mean(embeddings, axis=0).astype(np.float32)
        
        return None
    
    def _match_speaker_by_embedding(
        self, 
        embedding: np.ndarray, 
        threshold: float = 0.75
    ) -> Optional[Dict[str, Any]]:
        """
        通过embedding匹配已注册的说话人
        
        Args:
            embedding: 声纹embedding
            threshold: 匹配阈值（余弦相似度）
            
        Returns:
            匹配到的说话人信息，如果未匹配到则返回None
        """
        best_match = None
        best_similarity = 0.0
        
        for speaker_id, speaker_info in self.speaker_registry.items():
            saved_embedding = speaker_info.get('embedding')
            if saved_embedding is None:
                continue
            
            saved_embedding = np.array(saved_embedding)
            
            similarity = self._cosine_similarity(embedding, saved_embedding)
            
            if similarity > best_similarity and similarity >= threshold:
                best_similarity = similarity
                best_match = {
                    'speaker_id': speaker_id,
                    'voice_seed': speaker_info.get('voice_seed'),
                    'similarity': similarity,
                    'first_seen_in': speaker_info.get('first_seen_in')
                }
        
        return best_match
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        if len(a) != len(b):
            min_len = min(len(a), len(b))
            a = a[:min_len]
            b = b[:min_len]
        
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def _register_speaker(
        self, 
        embedding: np.ndarray,
        audio_path: str,
        slice_id: Optional[str] = None
    ) -> str:
        """注册新说话人"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        speaker_id = f"speaker_{timestamp}_{len(self.speaker_registry)}"
        
        voice_seed = self._generate_voice_seed_from_embedding(embedding)
        
        self.speaker_registry[speaker_id] = {
            'speaker_id': speaker_id,
            'embedding': embedding.tolist(),
            'voice_seed': voice_seed,
            'first_seen_in': slice_id,
            'audio_sample_path': audio_path,
            'created_at': datetime.now().isoformat()
        }
        
        self._save_speaker_registry()
        print(f"[说话人注册] 新说话人: {speaker_id}")
        
        return speaker_id
    
    def _generate_voice_seed_from_embedding(self, embedding: np.ndarray) -> str:
        """从声纹embedding生成voice seed"""
        if embedding is None:
            return "0"
        embedding_str = ''.join([f"{x:.6f}" for x in embedding.flatten()[:10]])
        seed_int = abs(hash(embedding_str)) % (2**31)
        return str(seed_int)
    
    def _generate_voice_seed_from_audio(self, audio_path: str) -> str:
        """从音频文件生成voice seed（备选方案）"""
        file_hash = self._calculate_file_hash(audio_path)
        seed_int = int(file_hash[:8], 16) % (2**31)
        return str(seed_int)
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件的MD5哈希"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def process_video_slices_with_speakers(
        self, 
        video_slices: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量处理视频切片，提取每个切片的说话人信息并进行跨切片匹配
        
        Args:
            video_slices: 视频切片列表，每个切片包含output_file和audio_file
            
        Returns:
            包含所有切片说话人信息和跨切片匹配结果
        """
        results = {
            'success': True,
            'slices': [],
            'all_speakers': {},
            'speaker_mapping': {},
            'cross_slice_matches': []
        }
        
        for slice_info in video_slices:
            slice_id = slice_info.get('slice_id', f"slice_{slice_info.get('index', 0)}")
            audio_path = slice_info.get('audio_file') or slice_info.get('output_file')
            
            if not audio_path or not os.path.exists(audio_path):
                print(f"[说话人识别] 警告: 切片 {slice_id} 没有音频文件，跳过")
                continue
            
            speaker_result = self.extract_speakers_from_audio(
                audio_path, 
                video_slice_id=slice_id,
                enable_matching=True
            )
            
            if speaker_result.get('success'):
                for speaker in speaker_result.get('speakers', []):
                    speaker_id = speaker['speaker_id']
                    voice_seed = speaker.get('voice_seed', '0')
                    
                    if speaker_id not in results['all_speakers']:
                        results['all_speakers'][speaker_id] = {
                            'speaker_id': speaker_id,
                            'voice_seed': voice_seed,
                            'first_seen_in': slice_id,
                            'is_new': speaker.get('is_new', True)
                        }
                        results['speaker_mapping'][speaker_id] = voice_seed
                    
                    if speaker.get('matched_to'):
                        results['cross_slice_matches'].append({
                            'slice_id': slice_id,
                            'original_speaker': speaker.get('matched_to'),
                            'current_speaker': speaker_id,
                            'similarity': speaker.get('similarity', 0)
                        })
                
                results['slices'].append({
                    'slice_id': slice_id,
                    'speakers': speaker_result.get('speakers', []),
                    'total_speakers': speaker_result.get('total_speakers', 0)
                })
        
        results['total_unique_speakers'] = len(results['all_speakers'])
        results['total_cross_slice_matches'] = len(results['cross_slice_matches'])
        
        return results
    
    def get_speaker_consistency_score(
        self, 
        video_slices: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        计算视频切片间的说话人一致性得分
        
        Args:
            video_slices: 视频切片列表
            
        Returns:
            一致性评估结果
        """
        process_result = self.process_video_slices_with_speakers(video_slices)
        
        if not process_result.get('success'):
            return {
                'success': False,
                'error': process_result.get('error', '处理失败')
            }
        
        total_slices = len(process_result['slices'])
        total_speakers = process_result['total_unique_speakers']
        cross_matches = process_result['total_cross_slice_matches']
        
        if total_slices <= 1:
            consistency_score = 1.0
        else:
            consistency_score = max(0, 1.0 - (total_speakers - 1) / (total_slices))
        
        return {
            'success': True,
            'consistency_score': consistency_score,
            'total_slices': total_slices,
            'total_unique_speakers': total_speakers,
            'cross_slice_matches': cross_matches,
            'speaker_details': process_result['all_speakers'],
            'match_details': process_result['cross_slice_matches']
        }
    
    def save_speaker_voice_seed(
        self, 
        speaker_id: str, 
        voice_seed: str, 
        audio_sample_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """保存说话人的voice seed"""
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
    
    def get_speaker_voice_seed(self, speaker_id: str) -> Optional[str]:
        """获取说话人的voice seed"""
        if speaker_id in self.speaker_registry:
            return self.speaker_registry[speaker_id].get('voice_seed')
        
        voice_seeds_dir = os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'voice_seeds'
        )
        voice_seed_file = os.path.join(voice_seeds_dir, f"{speaker_id}.json")
        
        if os.path.exists(voice_seed_file):
            with open(voice_seed_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('voice_seed')
        
        return None
    
    def list_registered_speakers(self) -> List[Dict[str, Any]]:
        """列出所有已注册的说话人"""
        speakers = []
        for speaker_id, info in self.speaker_registry.items():
            speakers.append({
                'speaker_id': speaker_id,
                'voice_seed': info.get('voice_seed'),
                'first_seen_in': info.get('first_seen_in'),
                'created_at': info.get('created_at')
            })
        return speakers
    
    def clear_registry(self):
        """清空说话人注册表"""
        self.speaker_registry = {}
        self._save_speaker_registry()
        print("[说话人注册表] 已清空")


if __name__ == "__main__":
    service = SpeakerVoiceService()
    
    test_audio = "path/to/audio.wav"
    if os.path.exists(test_audio):
        result = service.extract_speakers_from_audio(test_audio)
        print(f"说话人识别结果: {json.dumps(result, indent=2, ensure_ascii=False, default=str)}")
