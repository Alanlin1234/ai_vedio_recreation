"""
说话人识别服务独立功能测试脚本
测试声纹提取、说话人分离、跨切片匹配等功能
"""
import os
import sys
import json
import tempfile
import subprocess
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.speaker_voice_service import (
    SpeakerVoiceService, 
    SpeakerEmbeddingExtractor,
    SpeakerDiarizationService
)


def create_test_audio(duration: float = 3.0, output_path: str = None) -> str:
    """
    创建测试音频文件（使用ffmpeg生成静音音频）
    实际测试时应该使用真实音频
    """
    if output_path is None:
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        output_path = temp_file.name
        temp_file.close()
    
    cmd = [
        'ffmpeg', '-y', '-f', 'lavfi', 
        '-i', f'anullsrc=r=16000:cl=mono',
        '-t', str(duration),
        '-ac', '1', '-ar', '16000',
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    if result.returncode != 0:
        print(f"创建测试音频失败: {result.stderr.decode()}")
        return None
    
    return output_path


def create_test_audio_with_tone(duration: float = 3.0, frequency: int = 440, output_path: str = None) -> str:
    """
    创建带音调的测试音频
    """
    if output_path is None:
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        output_path = temp_file.name
        temp_file.close()
    
    cmd = [
        'ffmpeg', '-y', '-f', 'lavfi',
        '-i', f'sine=frequency={frequency}:duration={duration}',
        '-ac', '1', '-ar', '16000',
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    if result.returncode != 0:
        print(f"创建测试音频失败: {result.stderr.decode()}")
        return None
    
    return output_path


def test_embedding_extractor():
    """测试声纹特征提取器"""
    print("\n" + "="*60)
    print("测试1: 声纹特征提取器")
    print("="*60)
    
    extractor = SpeakerEmbeddingExtractor(backend='auto')
    
    test_audio = create_test_audio_with_tone(duration=2.0, frequency=440)
    if not test_audio or not os.path.exists(test_audio):
        print("❌ 无法创建测试音频文件")
        return False
    
    try:
        print(f"测试音频: {test_audio}")
        
        embedding = extractor.extract_embedding(test_audio)
        
        if embedding is not None:
            print(f"✅ 声纹提取成功")
            print(f"   - 特征维度: {len(embedding)}")
            print(f"   - 特征范围: [{embedding.min():.4f}, {embedding.max():.4f}]")
            print(f"   - 特征均值: {embedding.mean():.4f}")
            return True
        else:
            print("❌ 声纹提取失败")
            return False
    finally:
        if test_audio and os.path.exists(test_audio):
            os.remove(test_audio)


def test_diarization_service():
    """测试说话人分离服务"""
    print("\n" + "="*60)
    print("测试2: 说话人分离服务")
    print("="*60)
    
    diarization = SpeakerDiarizationService()
    
    test_audio = create_test_audio(duration=5.0)
    if not test_audio or not os.path.exists(test_audio):
        print("❌ 无法创建测试音频文件")
        return False
    
    try:
        print(f"测试音频: {test_audio}")
        
        result = diarization.diarize(test_audio)
        
        if result.get('success'):
            print(f"✅ 说话人分离成功")
            print(f"   - 方法: {result.get('method', 'unknown')}")
            print(f"   - 说话人数量: {result.get('total_speakers', 0)}")
            for speaker in result.get('speakers', []):
                print(f"   - 说话人 {speaker['speaker_id']}: 时长 {speaker['total_duration']:.2f}s")
            return True
        else:
            print(f"❌ 说话人分离失败: {result.get('error')}")
            return False
    finally:
        if test_audio and os.path.exists(test_audio):
            os.remove(test_audio)


def test_single_audio_extraction():
    """测试单个音频的说话人提取"""
    print("\n" + "="*60)
    print("测试3: 单个音频说话人提取")
    print("="*60)
    
    service = SpeakerVoiceService(embedding_backend='auto')
    service.clear_registry()
    
    test_audio = create_test_audio_with_tone(duration=3.0, frequency=440)
    if not test_audio or not os.path.exists(test_audio):
        print("❌ 无法创建测试音频文件")
        return False
    
    try:
        print(f"测试音频: {test_audio}")
        
        result = service.extract_speakers_from_audio(
            test_audio, 
            video_slice_id="test_slice_1",
            enable_matching=True
        )
        
        if result.get('success'):
            print(f"✅ 说话人提取成功")
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
            print(f"❌ 说话人提取失败: {result.get('error')}")
            return False
    finally:
        if test_audio and os.path.exists(test_audio):
            os.remove(test_audio)


def test_cross_slice_matching():
    """测试跨切片说话人匹配"""
    print("\n" + "="*60)
    print("测试4: 跨切片说话人匹配")
    print("="*60)
    
    service = SpeakerVoiceService(embedding_backend='auto')
    service.clear_registry()
    
    test_audio_1 = create_test_audio_with_tone(duration=3.0, frequency=440)
    test_audio_2 = create_test_audio_with_tone(duration=3.0, frequency=440)
    test_audio_3 = create_test_audio_with_tone(duration=3.0, frequency=880)
    
    if not all([test_audio_1, test_audio_2, test_audio_3]):
        print("❌ 无法创建测试音频文件")
        return False
    
    try:
        print("测试场景: 3个切片，前2个相同说话人，第3个不同说话人")
        
        result = service.process_video_slices_with_speakers([
            {'slice_id': 'slice_1', 'audio_file': test_audio_1},
            {'slice_id': 'slice_2', 'audio_file': test_audio_2},
            {'slice_id': 'slice_3', 'audio_file': test_audio_3}
        ])
        
        if result.get('success'):
            print(f"✅ 跨切片处理成功")
            print(f"   - 总切片数: {len(result['slices'])}")
            print(f"   - 唯一说话人数: {result['total_unique_speakers']}")
            print(f"   - 跨切片匹配数: {result['total_cross_slice_matches']}")
            
            print("\n   已注册说话人:")
            for speaker_id, info in result['all_speakers'].items():
                print(f"   - {speaker_id}: 首次出现在 {info['first_seen_in']}")
            
            if result['cross_slice_matches']:
                print("\n   跨切片匹配:")
                for match in result['cross_slice_matches']:
                    print(f"   - 切片 {match['slice_id']}: 匹配到 {match['original_speaker']}")
            
            return True
        else:
            print(f"❌ 跨切片处理失败: {result.get('error')}")
            return False
    finally:
        for audio in [test_audio_1, test_audio_2, test_audio_3]:
            if audio and os.path.exists(audio):
                os.remove(audio)


def test_speaker_consistency_score():
    """测试说话人一致性得分计算"""
    print("\n" + "="*60)
    print("测试5: 说话人一致性得分")
    print("="*60)
    
    service = SpeakerVoiceService(embedding_backend='auto')
    service.clear_registry()
    
    test_audio_1 = create_test_audio_with_tone(duration=3.0, frequency=440)
    test_audio_2 = create_test_audio_with_tone(duration=3.0, frequency=440)
    test_audio_3 = create_test_audio_with_tone(duration=3.0, frequency=880)
    
    if not all([test_audio_1, test_audio_2, test_audio_3]):
        print("❌ 无法创建测试音频文件")
        return False
    
    try:
        print("测试场景: 计算多切片视频的说话人一致性")
        
        result = service.get_speaker_consistency_score([
            {'slice_id': 'slice_1', 'audio_file': test_audio_1},
            {'slice_id': 'slice_2', 'audio_file': test_audio_2},
            {'slice_id': 'slice_3', 'audio_file': test_audio_3}
        ])
        
        if result.get('success'):
            print(f"✅ 一致性得分计算成功")
            print(f"   - 一致性得分: {result['consistency_score']:.4f}")
            print(f"   - 总切片数: {result['total_slices']}")
            print(f"   - 唯一说话人数: {result['total_unique_speakers']}")
            print(f"   - 跨切片匹配数: {result['cross_slice_matches']}")
            
            return True
        else:
            print(f"❌ 一致性得分计算失败: {result.get('error')}")
            return False
    finally:
        for audio in [test_audio_1, test_audio_2, test_audio_3]:
            if audio and os.path.exists(audio):
                os.remove(audio)


def test_speaker_registry():
    """测试说话人注册表管理"""
    print("\n" + "="*60)
    print("测试6: 说话人注册表管理")
    print("="*60)
    
    service = SpeakerVoiceService(embedding_backend='auto')
    service.clear_registry()
    
    test_audio = create_test_audio_with_tone(duration=2.0, frequency=440)
    if not test_audio or not os.path.exists(test_audio):
        print("❌ 无法创建测试音频文件")
        return False
    
    try:
        result = service.extract_speakers_from_audio(test_audio, "test_slice")
        
        if not result.get('success'):
            print(f"❌ 说话人提取失败")
            return False
        
        speakers = service.list_registered_speakers()
        print(f"✅ 注册说话人数量: {len(speakers)}")
        
        if speakers:
            speaker = speakers[0]
            voice_seed = service.get_speaker_voice_seed(speaker['speaker_id'])
            print(f"   - 说话人ID: {speaker['speaker_id']}")
            print(f"   - Voice Seed: {voice_seed}")
            print(f"   - 首次出现: {speaker['first_seen_in']}")
        
        service.clear_registry()
        speakers_after_clear = service.list_registered_speakers()
        print(f"✅ 清空后说话人数量: {len(speakers_after_clear)}")
        
        return True
    finally:
        if test_audio and os.path.exists(test_audio):
            os.remove(test_audio)


def test_cosine_similarity():
    """测试余弦相似度计算"""
    print("\n" + "="*60)
    print("测试7: 余弦相似度计算")
    print("="*60)
    
    service = SpeakerVoiceService(embedding_backend='auto')
    
    vec1 = np.array([1.0, 0.0, 0.0])
    vec2 = np.array([1.0, 0.0, 0.0])
    vec3 = np.array([0.0, 1.0, 0.0])
    vec4 = np.array([0.707, 0.707, 0.0])
    
    sim_same = service._cosine_similarity(vec1, vec2)
    sim_ortho = service._cosine_similarity(vec1, vec3)
    sim_angle = service._cosine_similarity(vec1, vec4)
    
    print(f"✅ 相同向量相似度: {sim_same:.4f} (期望: 1.0)")
    print(f"✅ 正交向量相似度: {sim_ortho:.4f} (期望: 0.0)")
    print(f"✅ 45度角向量相似度: {sim_angle:.4f} (期望: ~0.707)")
    
    if abs(sim_same - 1.0) < 0.001 and abs(sim_ortho - 0.0) < 0.001:
        return True
    else:
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("说话人识别服务功能测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    tests = [
        ("声纹特征提取器", test_embedding_extractor),
        ("说话人分离服务", test_diarization_service),
        ("单个音频说话人提取", test_single_audio_extraction),
        ("跨切片说话人匹配", test_cross_slice_matching),
        ("说话人一致性得分", test_speaker_consistency_score),
        ("说话人注册表管理", test_speaker_registry),
        ("余弦相似度计算", test_cosine_similarity),
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
