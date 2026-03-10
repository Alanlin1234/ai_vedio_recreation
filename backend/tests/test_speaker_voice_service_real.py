"""
说话人识别服务完整功能测试脚本
支持真实人声测试和TTS生成测试音频
"""
import os
import sys
import json
import tempfile
import subprocess
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.speaker_voice_service import (
    SpeakerVoiceService, 
    SpeakerEmbeddingExtractor,
    SpeakerDiarizationService
)


def find_available_audio_files(base_dir: str = None, max_files: int = 10) -> List[str]:
    """查找项目中可用的音频文件"""
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    audio_files = []
    search_dirs = [
        os.path.join(base_dir, 'downloads'),
        os.path.join(base_dir, 'video'),
    ]
    
    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue
        for root, dirs, files in os.walk(search_dir):
            for file in files:
                if file.endswith(('.mp3', '.wav', '.m4a', '.aac')):
                    audio_files.append(os.path.join(root, file))
                    if len(audio_files) >= max_files:
                        return audio_files
    return audio_files


def get_audio_info(audio_path: str) -> Dict[str, Any]:
    """获取音频文件信息"""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', 
             '-show_format', '-show_streams', audio_path],
            capture_output=True, text=True, timeout=30
        )
        info = json.loads(result.stdout)
        format_info = info.get('format', {})
        stream_info = info.get('streams', [{}])[0]
        return {
            'duration': float(format_info.get('duration', 0)),
            'sample_rate': int(stream_info.get('sample_rate', 0)),
            'channels': int(stream_info.get('channels', 0)),
            'format': format_info.get('format_name', 'unknown'),
            'size': int(format_info.get('size', 0))
        }
    except Exception as e:
        return {'error': str(e)}


class TTSAudioGenerator:
    """TTS音频生成器"""
    
    def __init__(self):
        self.tts_service = None
        self._init_tts()
    
    def _init_tts(self):
        try:
            from app.services.text_to_speech_service import TextToSpeechService
            self.tts_service = TextToSpeechService()
        except Exception as e:
            print(f"[TTS] 初始化失败: {e}")
            self.tts_service = None
    
    def generate_audio(self, text: str, output_path: str, voice_seed: str = None) -> Optional[str]:
        if self.tts_service is None:
            return self._generate_with_edge_tts(text, output_path)
        try:
            result = self.tts_service.text_to_speech(
                text=text, output_path=output_path, voice_seed=voice_seed
            )
            if result.get('success'):
                return output_path
        except Exception as e:
            print(f"[TTS] 生成失败: {e}")
        return self._generate_with_edge_tts(text, output_path)
    
    def _generate_with_edge_tts(self, text: str, output_path: str) -> Optional[str]:
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
            import asyncio
            asyncio.run(communicate.save(output_path))
            if os.path.exists(output_path):
                return output_path
        except Exception as e:
            print(f"[edge-tts] 生成失败: {e}")
        return None


def test_with_real_audio():
    """使用真实音频测试说话人提取"""
    print("\n" + "="*60)
    print("测试: 真实音频说话人提取")
    print("="*60)
    
    audio_files = find_available_audio_files(max_files=3)
    
    if not audio_files:
        print("❌ 未找到可用的音频文件")
        return False
    
    print(f"找到 {len(audio_files)} 个音频文件")
    
    test_audio = audio_files[0]
    audio_info = get_audio_info(test_audio)
    
    print(f"\n测试音频: {os.path.basename(test_audio)}")
    print(f"  - 时长: {audio_info.get('duration', 0):.2f}s")
    print(f"  - 采样率: {audio_info.get('sample_rate', 0)}Hz")
    print(f"  - 声道数: {audio_info.get('channels', 0)}")
    
    service = SpeakerVoiceService(embedding_backend='auto')
    service.clear_registry()
    
    result = service.extract_speakers_from_audio(test_audio, "test_slice_1", enable_matching=True)
    
    if result.get('success'):
        print(f"\n✅ 真实音频说话人提取成功")
        print(f"   - 分离方法: {result.get('diarization_method')}")
        print(f"   - 说话人数量: {result.get('total_speakers')}")
        
        for speaker in result.get('speakers', []):
            print(f"   - 说话人ID: {speaker['speaker_id']}")
            print(f"     - 是否新说话人: {speaker.get('is_new', True)}")
            print(f"     - Voice Seed: {speaker.get('voice_seed', 'N/A')}")
            if 'embedding_dim' in speaker:
                print(f"     - Embedding维度: {speaker['embedding_dim']}")
        return True
    else:
        print(f"❌ 真实音频说话人提取失败: {result.get('error')}")
        return False


def test_cross_slice_with_real_audio():
    """使用真实音频测试跨切片说话人匹配"""
    print("\n" + "="*60)
    print("测试: 真实音频跨切片说话人匹配")
    print("="*60)
    
    audio_files = find_available_audio_files(max_files=5)
    
    if len(audio_files) < 2:
        print(f"❌ 找到的音频文件不足2个，当前: {len(audio_files)}")
        return False
    
    print(f"找到 {len(audio_files)} 个音频文件")
    
    service = SpeakerVoiceService(embedding_backend='auto')
    service.clear_registry()
    
    test_slices = []
    for i, audio in enumerate(audio_files[:3]):
        audio_info = get_audio_info(audio)
        if audio_info.get('duration', 0) > 0:
            test_slices.append({
                'slice_id': f'slice_{i}',
                'audio_file': audio
            })
            print(f"  切片 {i}: {os.path.basename(audio)} ({audio_info.get('duration', 0):.2f}s)")
    
    if len(test_slices) < 2:
        print("❌ 有效音频切片不足2个")
        return False
    
    result = service.process_video_slices_with_speakers(test_slices)
    
    if result.get('success'):
        print(f"\n✅ 跨切片处理成功")
        print(f"   - 总切片数: {len(result['slices'])}")
        print(f"   - 唯一说话人数: {result['total_unique_speakers']}")
        print(f"   - 跨切片匹配数: {result['total_cross_slice_matches']}")
        
        print("\n   已注册说话人:")
        for speaker_id, info in result['all_speakers'].items():
            print(f"   - {speaker_id}: 首次出现在 {info['first_seen_in']}")
        
        if result['cross_slice_matches']:
            print("\n   跨切片匹配详情:")
            for match in result['cross_slice_matches']:
                print(f"   - 切片 {match['slice_id']}: 匹配到 {match['original_speaker']} (相似度: {match.get('similarity', 0):.4f})")
        
        return True
    else:
        print(f"❌ 跨切片处理失败")
        return False


def test_tts_generated_audio():
    """测试TTS生成音频的说话人识别"""
    print("\n" + "="*60)
    print("测试: TTS生成音频说话人识别")
    print("="*60)
    
    tts = TTSAudioGenerator()
    
    test_texts = [
        "这是第一个测试文本，用于测试说话人识别功能。",
        "这是第二个测试文本，应该被识别为同一个说话人。",
        "这是第三个测试文本，继续验证说话人一致性。"
    ]
    
    temp_dir = tempfile.mkdtemp()
    audio_files = []
    
    print("生成TTS测试音频...")
    for i, text in enumerate(test_texts):
        output_path = os.path.join(temp_dir, f"tts_test_{i}.mp3")
        result = tts.generate_audio(text, output_path)
        if result and os.path.exists(result):
            audio_files.append(result)
            print(f"  ✅ 生成音频 {i}: {text[:20]}...")
        else:
            print(f"  ❌ 生成音频 {i} 失败")
    
    if len(audio_files) < 2:
        print("❌ TTS音频生成失败，无法继续测试")
        return False
    
    service = SpeakerVoiceService(embedding_backend='auto')
    service.clear_registry()
    
    test_slices = [
        {'slice_id': f'tts_slice_{i}', 'audio_file': audio}
        for i, audio in enumerate(audio_files)
    ]
    
    result = service.process_video_slices_with_speakers(test_slices)
    
    if result.get('success'):
        print(f"\n✅ TTS音频说话人识别成功")
        print(f"   - 总切片数: {len(result['slices'])}")
        print(f"   - 唯一说话人数: {result['total_unique_speakers']}")
        print(f"   - 跨切片匹配数: {result['total_cross_slice_matches']}")
        
        consistency = result['total_cross_slice_matches'] / max(len(result['slices']) - 1, 1)
        print(f"   - 一致性比例: {consistency:.2%}")
        
        return True
    else:
        print(f"❌ TTS音频说话人识别失败")
        return False


def test_speaker_consistency_with_real_audio():
    """测试说话人一致性得分计算"""
    print("\n" + "="*60)
    print("测试: 真实音频说话人一致性得分")
    print("="*60)
    
    audio_files = find_available_audio_files(max_files=5)
    
    if len(audio_files) < 2:
        print(f"❌ 找到的音频文件不足2个")
        return False
    
    service = SpeakerVoiceService(embedding_backend='auto')
    service.clear_registry()
    
    test_slices = []
    for i, audio in enumerate(audio_files[:3]):
        audio_info = get_audio_info(audio)
        if audio_info.get('duration', 0) > 0:
            test_slices.append({
                'slice_id': f'slice_{i}',
                'audio_file': audio
            })
    
    if len(test_slices) < 2:
        print("❌ 有效音频切片不足2个")
        return False
    
    result = service.get_speaker_consistency_score(test_slices)
    
    if result.get('success'):
        print(f"✅ 一致性得分计算成功")
        print(f"   - 一致性得分: {result['consistency_score']:.4f}")
        print(f"   - 总切片数: {result['total_slices']}")
        print(f"   - 唯一说话人数: {result['total_unique_speakers']}")
        print(f"   - 跨切片匹配数: {result['cross_slice_matches']}")
        
        print("\n   说话人详情:")
        for speaker_id, info in result['speaker_details'].items():
            print(f"   - {speaker_id}: 首次出现 {info['first_seen_in']}")
        
        return True
    else:
        print(f"❌ 一致性得分计算失败: {result.get('error')}")
        return False


def test_embedding_similarity_with_real_audio():
    """测试真实音频声纹相似度计算"""
    print("\n" + "="*60)
    print("测试: 真实音频声纹相似度计算")
    print("="*60)
    
    audio_files = find_available_audio_files(max_files=3)
    
    if len(audio_files) < 2:
        print(f"❌ 找到的音频文件不足2个")
        return False
    
    extractor = SpeakerEmbeddingExtractor(backend='auto')
    
    embeddings = []
    for i, audio in enumerate(audio_files[:2]):
        print(f"提取音频 {i+1} 的声纹特征: {os.path.basename(audio)}")
        embedding = extractor.extract_embedding(audio)
        if embedding is not None:
            embeddings.append(embedding)
            print(f"  ✅ 特征维度: {len(embedding)}")
        else:
            print(f"  ❌ 提取失败")
    
    if len(embeddings) < 2:
        print("❌ 声纹提取失败")
        return False
    
    service = SpeakerVoiceService(embedding_backend='auto')
    similarity = service._cosine_similarity(embeddings[0], embeddings[1])
    
    print(f"\n✅ 声纹相似度计算成功")
    print(f"   - 音频1 vs 音频2 相似度: {similarity:.4f}")
    print(f"   - 判断: {'同一说话人' if similarity > 0.75 else '不同说话人'} (阈值: 0.75)")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("说话人识别服务完整功能测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    tests = [
        ("真实音频说话人提取", test_with_real_audio),
        ("真实音频跨切片匹配", test_cross_slice_with_real_audio),
        ("TTS生成音频测试", test_tts_generated_audio),
        ("真实音频一致性得分", test_speaker_consistency_with_real_audio),
        ("真实音频声纹相似度", test_embedding_similarity_with_real_audio),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append((name, False))
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed_count = 0
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
        if passed:
            passed_count += 1
    
    print(f"\n总计: {passed_count}/{len(results)} 通过")
    
    return passed_count == len(results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
