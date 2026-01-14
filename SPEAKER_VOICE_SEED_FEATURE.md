# 说话人识别和Voice Seed功能说明

## 功能概述

基于您的需求，我已经实现了说话人识别和Voice Seed管理系统。该系统可以从视频切片音频中提取说话人信息，为每个人物分配voice seed，并在生成新视频时使用相同的seed保持声音一致性。

## 实现的功能

### 1. 说话人识别服务 (`SpeakerVoiceService`)

**位置**: `backend/app/services/speaker_voice_service.py`

**核心功能**:
- ✅ 从音频文件中提取说话人信息
- ✅ 生成每个说话人的voice seed
- ✅ 保存和检索voice seed
- ✅ 说话人匹配（通过音频匹配已有说话人）
- ✅ 批量处理视频切片

**主要方法**:
- `extract_speakers_from_audio()`: 从音频提取说话人
- `save_speaker_voice_seed()`: 保存voice seed
- `get_speaker_voice_seed()`: 获取voice seed
- `process_video_slices_with_speakers()`: 批量处理视频切片

### 2. TTS集成服务 (`SpeakerTTSIntegration`)

**位置**: `backend/app/services/speaker_tts_integration.py`

**核心功能**:
- ✅ 整合说话人识别和TTS生成
- ✅ 使用voice seed生成一致的声音
- ✅ 支持从音频样本自动提取说话人信息

**主要方法**:
- `generate_audio_with_speaker()`: 为指定说话人生成语音
- `process_video_slices_with_voice_consistency()`: 批量处理并生成语音

### 3. TTS服务增强

**位置**: `backend/app/services/text_to_speech_service.py`

**新增功能**:
- ✅ 支持 `voice_seed` 参数
- ✅ 支持 `speaker_id` 参数（自动查找对应的voice_seed）
- ✅ 在TTS请求中包含seed参数

## 使用流程

### 基本使用示例

```python
from app.services.speaker_voice_service import SpeakerVoiceService
from app.services.speaker_tts_integration import SpeakerTTSIntegration

# 1. 初始化服务
speaker_service = SpeakerVoiceService()
integration = SpeakerTTSIntegration()

# 2. 从视频切片音频中提取说话人信息
result = speaker_service.extract_speakers_from_audio("path/to/audio.wav")

# 3. 保存voice seed
for speaker in result['speakers']:
    speaker_service.save_speaker_voice_seed(
        speaker_id=speaker['speaker_id'],
        voice_seed=speaker['voice_seed'],
        audio_sample_path="path/to/audio.wav"
    )

# 4. 使用voice seed生成语音
tts_result = integration.generate_audio_with_speaker(
    text="这是要生成的文本",
    speaker_id="speaker_abc123",  # 使用已保存的speaker_id
    output_path="./output/audio.mp3"
)
```

### 完整工作流

```
1. 视频切片 → 2. 提取音频 → 3. 识别说话人 → 4. 生成voice_seed
                                                      ↓
8. 使用voice_seed生成TTS ← 7. 查找voice_seed ← 6. 匹配说话人 ← 5. 保存voice_seed
```

## 集成到现有代码

### 在 `test_simple_video_process.py` 中集成

您可以按照以下方式集成到现有的测试流程中：

```python
from app.services.speaker_tts_integration import SpeakerTTSIntegration

class VideoProcessingTest:
    def __init__(self, video_path: str, slice_count: int = 5):
        # ... 现有代码 ...
        self.speaker_tts = SpeakerTTSIntegration()
    
    async def extract_speakers_from_slices(self):
        """从视频切片中提取说话人信息"""
        from app.services.speaker_voice_service import SpeakerVoiceService
        speaker_service = SpeakerVoiceService()
        
        result = speaker_service.process_video_slices_with_speakers(self.video_slices)
        
        if result.get('success'):
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

## 文件结构

```
backend/
├── app/
│   └── services/
│       ├── speaker_voice_service.py          # 说话人识别服务
│       ├── speaker_tts_integration.py        # TTS集成服务
│       └── text_to_speech_service.py         # TTS服务（已增强）
├── examples/
│   └── test_speaker_voice_integration.py     # 测试示例
└── docs/
    └── SPEAKER_VOICE_SEED_GUIDE.md           # 详细使用指南

data/
└── voice_seeds/                              # Voice seed存储目录
    ├── speaker_xxx.json
    └── speaker_yyy.json
```

## 技术实现

### Voice Seed生成

当前实现使用音频文件的哈希值生成voice seed。对于更准确的结果，可以：

1. **使用声纹特征**: 提取音频的声纹embedding，然后生成seed
2. **使用pyannote.audio**: 专业的说话人分离工具（代码中已预留接口）

### 说话人匹配

当前使用简化的相似度计算。可以改进为：

1. **声纹匹配**: 使用专业的声纹识别模型
2. **特征向量比较**: 计算embedding之间的余弦相似度

### 存储方式

当前使用JSON文件存储，可以：

1. **迁移到数据库**: 使用MySQL/PostgreSQL存储
2. **添加版本管理**: 支持voice seed的版本控制
3. **实现缓存**: 使用Redis缓存常用的voice seed

## 配置说明

### 环境要求

```bash
# 基础依赖（已包含在requirements.txt中）
- requests
- numpy

# 可选：专业说话人识别（需要单独安装）
pip install pyannote.audio
# 需要HuggingFace token: https://huggingface.co/pyannote/speaker-diarization
```

### API配置

Voice seed功能依赖于TTS API支持seed参数。当前实现针对SiliconFlow API，其他API可能需要调整参数名称。

## 测试

运行测试示例：

```bash
cd backend
python examples/test_speaker_voice_integration.py
```

或参考 `backend/docs/SPEAKER_VOICE_SEED_GUIDE.md` 获取详细的使用说明和示例。

## 注意事项

1. **Voice Seed格式**: 当前实现使用整数作为seed。不同TTS API可能有不同要求。

2. **说话人识别精度**: 
   - 当前使用简化方法，精度有限
   - 建议安装pyannote.audio提高识别精度
   - 或在生产环境使用专业的声纹识别服务

3. **性能考虑**:
   - 说话人识别是计算密集型操作
   - 建议使用异步处理
   - 可以考虑缓存已识别的结果

4. **数据存储**:
   - Voice seed默认保存在本地文件系统
   - 建议迁移到数据库以便管理和查询

## 未来改进方向

1. ✅ **数据库集成**: 将voice seed存储迁移到数据库
2. ✅ **高级说话人识别**: 集成pyannote.audio
3. ✅ **声纹匹配优化**: 使用机器学习模型
4. ✅ **Voice Clone支持**: 集成voice cloning技术
5. ✅ **批量管理界面**: 提供说话人管理UI

## 相关文档

- [详细使用指南](./backend/docs/SPEAKER_VOICE_SEED_GUIDE.md)
- [测试示例代码](./backend/examples/test_speaker_voice_integration.py)

## 支持

如有问题或建议，请查看代码注释或提交Issue。

