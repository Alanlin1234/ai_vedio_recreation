# 说话人识别和Voice Seed使用指南

## 概述

本系统实现了基于说话人识别的voice seed管理功能，可以从视频切片中提取说话人信息，并为每个人物分配voice seed，确保在生成新视频时使用相同的声音特征。

## 核心功能

1. **说话人识别**: 从视频切片音频中提取说话人信息
2. **Voice Seed管理**: 为每个说话人保存和管理voice seed
3. **一致性TTS生成**: 使用保存的voice seed生成具有一致声音特征的语音

## 快速开始

### 1. 基本使用

```python
from app.services.speaker_voice_service import SpeakerVoiceService
from app.services.speaker_tts_integration import SpeakerTTSIntegration

# 初始化服务
speaker_service = SpeakerVoiceService()
integration = SpeakerTTSIntegration()

# 从音频文件中提取说话人信息
result = speaker_service.extract_speakers_from_audio("path/to/audio.wav")

if result.get('success'):
    for speaker in result['speakers']:
        speaker_id = speaker['speaker_id']
        voice_seed = speaker['voice_seed']
        
        # 保存voice seed
        speaker_service.save_speaker_voice_seed(
            speaker_id=speaker_id,
            voice_seed=voice_seed,
            audio_sample_path="path/to/audio.wav"
        )
```

### 2. 使用Voice Seed生成语音

```python
# 方式1: 使用speaker_id（自动获取对应的voice_seed）
result = integration.generate_audio_with_speaker(
    text="这是要生成的文本",
    speaker_id="speaker_abc123",
    output_path="./output/audio.mp3"
)

# 方式2: 从音频样本提取说话人信息并生成
result = integration.generate_audio_with_speaker(
    text="这是要生成的文本",
    audio_sample_path="./samples/speaker_sample.wav",
    output_path="./output/audio.mp3"
)
```

### 3. 批量处理视频切片

```python
import asyncio
from app.services.ffmpeg_service import FFmpegService

async def process_video_slices():
    ffmpeg_service = FFmpegService()
    integration = SpeakerTTSIntegration()
    
    # 切片视频
    slice_result = await ffmpeg_service.slice_video(
        "path/to/video.mp4",
        slice_duration=5
    )
    
    video_slices = slice_result['slices']
    
    # 为每个切片添加文本内容
    for slice_info in video_slices:
        slice_info['text'] = "该切片的文本内容"
    
    # 处理切片：提取说话人 + 生成语音
    result = await integration.process_video_slices_with_voice_consistency(
        video_slices=video_slices,
        output_dir="./output/audio"
    )
    
    return result

# 运行
result = asyncio.run(process_video_slices())
```

## 工作流程

### 完整流程示例

```
1. 视频切片
   ↓
2. 提取每个切片的音频
   ↓
3. 从音频中识别说话人
   ↓
4. 为每个说话人生成voice_seed
   ↓
5. 保存voice_seed到数据库/文件
   ↓
6. 生成新视频时，根据说话人ID查找对应的voice_seed
   ↓
7. 使用voice_seed生成具有一致声音特征的TTS音频
```

## API参考

### SpeakerVoiceService

#### `extract_speakers_from_audio(audio_path, video_slice_id=None)`

从音频文件中提取说话人信息。

**参数**:
- `audio_path`: 音频文件路径
- `video_slice_id`: 视频切片ID（可选）

**返回**:
```python
{
    'success': True,
    'speakers': [
        {
            'speaker_id': 'speaker_abc123',
            'voice_seed': '12345',
            'start': 0.0,
            'end': 5.0,
            'duration': 5.0
        }
    ],
    'total_speakers': 1
}
```

#### `save_speaker_voice_seed(speaker_id, voice_seed, audio_sample_path=None, metadata=None)`

保存说话人的voice seed。

**参数**:
- `speaker_id`: 说话人ID
- `voice_seed`: voice seed值
- `audio_sample_path`: 音频样本路径（可选）
- `metadata`: 额外元数据（可选）

#### `get_speaker_voice_seed(speaker_id)`

获取说话人的voice seed。

**返回**: voice seed字符串，如果不存在则返回None

#### `process_video_slices_with_speakers(video_slices)`

批量处理视频切片，提取每个切片的说话人信息。

**参数**:
- `video_slices`: 视频切片列表，每个切片应包含 `output_file` 和 `audio_file`

**返回**:
```python
{
    'success': True,
    'slices': [...],
    'all_speakers': {...},
    'speaker_mapping': {'speaker_id': 'voice_seed'},
    'total_unique_speakers': 2
}
```

### SpeakerTTSIntegration

#### `generate_audio_with_speaker(text, speaker_id=None, audio_sample_path=None, output_path=None)`

为指定说话人生成语音。

**参数**:
- `text`: 要生成的文本
- `speaker_id`: 说话人ID（如果提供，将使用已保存的voice_seed）
- `audio_sample_path`: 音频样本路径（如果speaker_id不存在，将从此音频提取）
- `output_path`: 输出音频路径

**返回**: TTS生成结果

#### `process_video_slices_with_voice_consistency(video_slices, output_dir)`

处理视频切片，提取说话人信息并生成一致的语音。

**参数**:
- `video_slices`: 视频切片列表（每个切片应包含 `text` 或 `script` 字段）
- `output_dir`: 输出目录

## 集成到现有流程

### 在视频二创流程中集成

```python
from app.services.speaker_tts_integration import SpeakerTTSIntegration

class VideoRecreationService:
    def __init__(self):
        # ... 其他初始化 ...
        self.speaker_tts = SpeakerTTSIntegration()
    
    async def process_video_for_recreation(self, video_path, recreation_id):
        # ... 前面的处理步骤 ...
        
        # 在生成TTS音频时，使用说话人识别
        if scene_prompts:
            for scene in scene_prompts:
                scene_id = scene.get('scene_id')
                text = scene.get('text', '')
                
                # 检查是否有对应的说话人
                speaker_id = scene.get('speaker_id')
                audio_sample = scene.get('audio_sample_path')
                
                # 生成音频
                tts_result = self.speaker_tts.generate_audio_with_speaker(
                    text=text,
                    speaker_id=speaker_id,
                    audio_sample_path=audio_sample,
                    output_path=f"./output/scene_{scene_id}_audio.mp3"
                )
```

### 在test_simple_video_process.py中集成

```python
# 在VideoProcessingTest类中添加
from app.services.speaker_tts_integration import SpeakerTTSIntegration

class VideoProcessingTest:
    def __init__(self, video_path: str, slice_count: int = 5):
        # ... 其他初始化 ...
        self.speaker_tts = SpeakerTTSIntegration()
    
    async def extract_speakers_from_slices(self):
        """从视频切片中提取说话人信息"""
        speaker_service = SpeakerVoiceService()
        
        # 处理所有切片
        result = speaker_service.process_video_slices_with_speakers(self.video_slices)
        
        if result.get('success'):
            # 保存说话人映射
            self.speaker_mapping = result['speaker_mapping']
            return True
        return False
    
    async def synthesize_audio(self):
        """使用voice seed生成音频"""
        for i, video in enumerate(self.generated_videos):
            if video['success']:
                scene_prompt = self.scene_prompts[i]
                text = scene_prompt.get('parsed_prompt', '')
                
                # 获取对应的说话人ID（如果有）
                speaker_id = scene_prompt.get('speaker_id')
                
                # 使用voice seed生成音频
                audio_result = self.speaker_tts.generate_audio_with_speaker(
                    text=text,
                    speaker_id=speaker_id,
                    output_path=os.path.join(self.output_dir, f"scene_{i+1}_audio.mp3")
                )
                
                if audio_result.get('success'):
                    video['audio_path'] = audio_result['audio_path']
```

## 注意事项

1. **Voice Seed格式**: 当前实现使用整数作为voice seed。不同TTS API可能支持不同的seed格式，需要根据实际情况调整。

2. **说话人识别精度**: 当前实现使用简化方法。要提高识别精度，建议：
   - 安装并使用 `pyannote.audio` 进行专业的说话人分离
   - 使用专业的声纹识别模型提取embedding
   - 实现更复杂的声纹匹配算法

3. **存储位置**: Voice seed默认保存在 `backend/data/voice_seeds/` 目录下。建议：
   - 迁移到数据库存储（如MySQL）
   - 实现voice seed的版本管理
   - 支持voice seed的导入/导出

4. **性能优化**: 
   - 说话人识别是计算密集型操作，建议使用异步处理
   - 考虑缓存已识别的说话人信息
   - 批量处理时可以并行化

## 测试

运行测试脚本：

```bash
cd backend
python examples/test_speaker_voice_integration.py
```

或参考 `backend/examples/test_speaker_voice_integration.py` 中的示例代码。

## 故障排查

### 问题1: 说话人识别失败

**可能原因**:
- 音频文件不存在或格式不支持
- pyannote.audio未安装（如果使用）

**解决方案**:
- 检查音频文件路径和格式
- 确保已安装必要的依赖
- 查看日志获取详细错误信息

### 问题2: Voice Seed未生效

**可能原因**:
- TTS API不支持seed参数
- Voice seed格式不正确

**解决方案**:
- 检查TTS API文档，确认是否支持seed参数
- 根据API要求调整voice seed格式
- 查看TTS服务的日志输出

### 问题3: 说话人匹配不准确

**可能原因**:
- 使用简化的相似度计算
- 音频质量差或噪音大

**解决方案**:
- 使用更专业的声纹识别模型
- 提高音频质量
- 调整匹配阈值

## 未来改进

1. **数据库集成**: 将voice seed存储迁移到数据库
2. **高级说话人识别**: 集成pyannote.audio或类似工具
3. **声纹匹配优化**: 使用机器学习模型进行更准确的声纹匹配
4. **Voice Clone支持**: 集成voice cloning技术，实现更自然的声音复制
5. **批量管理**: 提供说话人和voice seed的批量管理界面

