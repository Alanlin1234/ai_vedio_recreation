# 首尾帧连接方式使用指南

## 概述

本系统实现了首尾帧连接方式，确保场景间的视觉连贯性。核心思想是：**下一个场景的第一个关键帧必须是上一个场景的最后一个关键帧**，从而保证场景间的无缝衔接。

## 核心特性

1. **首尾帧强制连接**: 下一个场景的首帧 = 上一个场景的尾帧
2. **上下文增强的Prompt**: Prompt中包含上一个场景的详细信息，确保视觉连贯性
3. **自动帧提取**: 自动从生成的视频中提取最后一帧，供下一个场景使用

## 工作流程

```
场景1生成
  ↓
提取场景1的最后一个关键帧
  ↓
场景2生成时：
  - 第一个关键帧 = 场景1的最后一个关键帧（强制）
  - Prompt中包含场景1的上下文信息
  - 生成剩余的关键帧
  ↓
提取场景2的最后一个关键帧
  ↓
场景3生成时：重复上述过程...
```

## 代码实现

### 1. 帧连续性服务

**文件**: `backend/app/services/frame_continuity_service.py`

核心类：`FrameContinuityService`

```python
from app.services.frame_continuity_service import FrameContinuityService

service = FrameContinuityService()

# 设置上一个场景的最后一帧
service.set_previous_scene_frame(
    last_frame="path/to/last_frame.jpg",
    context={
        'video_prompt': '上一个场景的描述',
        'style_elements': {...}
    }
)

# 构建包含上下文的prompt
enhanced_prompt = service.build_contextual_prompt(
    current_prompt="当前场景的描述",
    previous_scene_info={...},
    use_first_frame_constraint=True
)
```

### 2. 关键帧生成（已修改）

**文件**: `backend/app/services/qwen_video_service.py`

方法：`generate_keyframes_with_qwen_image_edit()`

新增参数：
- `previous_last_frame`: 上一个场景的最后一帧（可选）

```python
keyframe_result = qwen_video_service.generate_keyframes_with_qwen_image_edit(
    prompt=keyframe_prompt,
    reference_images=reference_images,
    num_keyframes=3,
    previous_last_frame=previous_scene_last_frame  # 新增参数
)
```

**工作原理**：
1. 如果提供了 `previous_last_frame`，直接将其作为第一个关键帧
2. 生成剩余的关键帧（num_keyframes - 1）
3. Prompt中包含上下文信息，确保视觉连贯性

### 3. 视频生成流程（已修改）

**文件**: `backend/app/services/video_recreation_service.py`

在 `generate_videos_with_qwen()` 方法中：

```python
# 获取上一个场景的最后一帧
previous_last_frame = None
if i > 0 and previous_scene_keyframes:
    previous_last_frame = previous_scene_keyframes[-1]
    
# 生成关键帧时传入previous_last_frame
keyframe_result = self.qwen_video_service.generate_keyframes_with_qwen_image_edit(
    keyframe_prompt,
    reference_images=reference_images,
    num_keyframes=3,
    previous_last_frame=previous_last_frame  # 关键：传入上一场景的最后一帧
)

# 验证首尾帧连接
if previous_last_frame and keyframes:
    if keyframes[0] != previous_last_frame:
        # 强制使用previous_last_frame作为第一个关键帧
        keyframes[0] = previous_last_frame
```

### 4. Prompt增强（已修改）

**文件**: `backend/app/services/scene_segmentation_service.py`

方法：`generate_video_prompt_for_scene()`

现在会在prompt中包含：
- 上一个场景的详细描述
- 上一个场景的风格元素（人物、环境、视觉风格）
- **强制约束**：第一个关键帧必须与上一场景的最后一帧完全相同
- 场景连贯性要求

## 使用示例

### 基本使用

```python
from app.services.video_recreation_service import VideoRecreationService

service = VideoRecreationService()

# 生成视频时，自动使用首尾帧连接
result = await service.generate_videos_with_qwen(
    scene_analysis=scene_analysis,
    video_path=video_path,
    recreation_id=recreation_id,
    task_dir=task_dir,
    video_understanding=video_understanding
)
```

### 手动控制

```python
from app.services.qwen_video_service import QwenVideoService
from app.services.frame_continuity_service import FrameContinuityService

qwen_service = QwenVideoService()
continuity_service = FrameContinuityService()

# 场景1：生成关键帧
scene1_keyframes = qwen_service.generate_keyframes_with_qwen_image_edit(
    prompt=scene1_prompt,
    reference_images=reference_images,
    num_keyframes=3
)

# 获取场景1的最后一个关键帧
scene1_last_frame = scene1_keyframes['keyframes'][-1]

# 场景2：使用首尾帧连接
scene2_prompt_enhanced = continuity_service.build_contextual_prompt(
    current_prompt=scene2_prompt,
    previous_scene_info=scene1_info,
    use_first_frame_constraint=True
)

scene2_keyframes = qwen_service.generate_keyframes_with_qwen_image_edit(
    prompt={'video_prompt': scene2_prompt_enhanced, ...},
    reference_images=reference_images,
    num_keyframes=3,
    previous_last_frame=scene1_last_frame  # 关键：传入上一场景的最后一帧
)
```

## 验证首尾帧连接

系统会自动验证首尾帧连接：

```python
# 在video_recreation_service.py中
if previous_last_frame and keyframes:
    if keyframes[0] == previous_last_frame:
        print("首尾帧连接验证成功")
    else:
        print("警告：首尾帧连接可能有问题，强制修正")
        keyframes[0] = previous_last_frame  # 强制使用正确的帧
```

## 优势

1. **视觉连贯性**: 场景间无缝衔接，没有突兀的跳跃
2. **风格一致性**: Prompt中包含上下文信息，确保风格保持一致
3. **自动化**: 自动提取和传递最后一帧，无需手动干预
4. **可验证**: 自动验证首尾帧连接，确保正确性

## 注意事项

1. **第一个场景**: 第一个场景没有上一个场景，所以不使用首尾帧连接
2. **关键帧数量**: 使用首尾帧连接时，实际生成的关键帧数量 = num_keyframes - 1（第一个直接使用上一场景的最后一帧）
3. **Prompt长度**: 增强的prompt包含更多上下文信息，可能会更长，需要确保API支持

## 故障排查

### 问题1: 首尾帧连接失败

**症状**: 第一个关键帧与上一场景的最后一帧不一致

**解决方案**:
- 检查 `previous_last_frame` 是否正确传递
- 查看日志确认是否使用了强制修正
- 检查prompt中是否包含正确的约束信息

### 问题2: 关键帧数量不足

**症状**: 生成的关键帧数量少于预期

**原因**: 使用首尾帧连接时，第一个关键帧直接使用上一场景的最后一帧，如果后续生成失败，可能导致数量不足

**解决方案**:
- 检查API调用是否成功
- 查看日志中的警告信息
- 考虑增加重试机制

### 问题3: Prompt过长

**症状**: API返回错误，提示prompt过长

**解决方案**:
- 减少上下文信息的长度
- 只包含关键的风格元素
- 使用更简洁的描述

## 未来改进

1. **视频帧提取**: 不仅使用关键帧，还可以从生成的视频中提取最后一帧，更精确
2. **智能选择**: 根据场景内容智能选择最佳连接帧
3. **过渡效果**: 在首尾帧之间添加平滑的过渡效果
4. **质量检查**: 自动检查首尾帧连接的质量，如果质量不佳则重新生成

