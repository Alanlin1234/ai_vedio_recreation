## 导出图像识别代码和Prompt结果计划

### 1. 执行导出脚本

* 运行已创建的 `export_image_recognition_and_prompts.py` 脚本

* 脚本将在当前目录下创建一个以时间戳命名的导出目录

* 导出目录将包含：

  * 核心图像识别代码文件

  * 生成的Prompt结果（真实或示例）

  * 工作流程图说明

### 2. 导出内容说明

#### 图像识别代码

* `qwen_video_service.py_analyze_keyframes_with_qwen3vl_plus.py`：使用qwen3-vl-plus分析关键帧的代码

* `qwen_video_service.py_generate_keyframes_with_qwen_image_edit.py`：使用qwen-image-edit生成关键帧的代码

* `qwen_vl_service.py__generate_slice_prompt.py`：为单个切片生成prompt的代码

* `qwen_vl_service.py_analyze_video_content.py`：分析视频内容的代码

* `scene_segmentation_service.py_generate_video_prompt_for_scene.py`：生成视频提示词的代码

#### Prompt结果

* `generated_prompts.json`（如果提供了视频）：基于真实视频生成的Prompt结果

* `sample_generated_prompts.json`：示例Prompt结果，包含场景描述和风格元素

#### 工作流程说明

* `workflow_diagram.md`：详细的图像识别和Prompt生成工作流程说明

### 3. 运行方式

```bash
python export_image_recognition_and_prompts.py [视频文件路径]
```

* 不提供视频路径时，生成示例Prompt结果

* 提供视频路径时，使用真实视频生成Prompt结果

### 4. 预期结果

* 成功创建导出目录

* 导出目录中包含所有指定的文件

* 文件内容完整，格式正确

* 可以直接查看和使用导出的代码和Prompt结果

