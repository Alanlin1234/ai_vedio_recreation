#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
图像识别代码和Prompt结果导出脚本

该脚本用于导出项目中的图像识别代码和生成的prompt结果，包括：
1. 关键图像识别方法的代码提取
2. 生成的prompt结果的保存和展示
3. 支持独立运行的功能演示
"""

import sys
import os
import time
import asyncio
import json
import logging
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImageRecognitionAndPromptExporter:
    """图像识别和Prompt结果导出器"""
    
    def __init__(self):
        self.export_dir = f"exported_results_{int(time.time())}"
        os.makedirs(self.export_dir, exist_ok=True)
        logger.info(f"导出目录: {self.export_dir}")
    
    def export_image_recognition_code(self):
        """导出图像识别相关的核心代码"""
        logger.info("开始导出图像识别代码...")
        
        # 定义要导出的文件和方法
        export_config = [
            {
                "file_path": "backend/app/services/qwen_video_service.py",
                "methods": ["analyze_keyframes_with_qwen3vl_plus", "generate_keyframes_with_qwen_image_edit"]
            },
            {
                "file_path": "backend/app/services/qwen_vl_service.py",
                "methods": ["_generate_slice_prompt", "analyze_video_content"]
            },
            {
                "file_path": "backend/app/services/scene_segmentation_service.py",
                "methods": ["generate_video_prompt_for_scene"]
            }
        ]
        
        # 提取并保存代码
        for config in export_config:
            try:
                file_path = os.path.join(os.path.dirname(__file__), config["file_path"])
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 提取指定方法
                for method in config["methods"]:
                    # 查找方法定义
                    method_start = content.find(f"def {method}")
                    if method_start == -1:
                        logger.warning(f"方法 {method} 未在 {config['file_path']} 中找到")
                        continue
                    
                    # 查找方法结束（基于缩进）
                    lines = content[method_start:].split('\n')
                    method_end = 0
                    indent_level = 0
                    
                    for i, line in enumerate(lines):
                        stripped = line.lstrip()
                        if i == 0:
                            # 第一行是方法定义，确定缩进级别
                            indent_level = len(line) - len(stripped)
                        elif stripped and len(line) - len(stripped) < indent_level:
                            # 找到了缩进级别更小的行，说明方法结束
                            method_end = i
                            break
                    
                    if method_end == 0:
                        method_end = len(lines)
                    
                    method_code = '\n'.join(lines[:method_end])
                    
                    # 保存到文件
                    output_file = os.path.join(
                        self.export_dir,
                        f"{os.path.basename(config['file_path'])}_{method}.py"
                    )
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(f"# 从 {config['file_path']} 导出的 {method} 方法\n\n")
                        f.write(method_code)
                    
                    logger.info(f"已导出方法 {method} 到 {output_file}")
                    
            except Exception as e:
                logger.error(f"导出 {config['file_path']} 时出错: {str(e)}")
    
    async def generate_and_export_prompt_results(self, video_path: str = None):
        """生成并导出Prompt结果"""
        logger.info("开始生成和导出Prompt结果...")
        
        try:
            # 导入必要的服务
            from app import create_app
            from app.services.ffmpeg_service import FFmpegService
            from app.services.qwen_vl_service import QwenVLService
            from app.services.qwen_video_service import QwenVideoService
            from app.services.content_generation_service import ContentGenerationService
            from app.services.scene_segmentation_service import SceneSegmentationService
            from app.services.json_prompt_parser import JSONPromptParser
            
            # 创建应用实例
            app = create_app()
            
            with app.app_context():
                # 初始化服务
                ffmpeg_service = FFmpegService()
                qwen_vl_service = QwenVLService()
                qwen_video_service = QwenVideoService()
                content_generator = ContentGenerationService()
                scene_segmenter = SceneSegmentationService()
                json_parser = JSONPromptParser()
                
                # 如果提供了视频路径，执行完整流程
                if video_path and os.path.exists(video_path):
                    logger.info(f"使用视频 {video_path} 生成Prompt结果...")
                    
                    # 视频切片
                    video_info = await ffmpeg_service.get_video_info(video_path)
                    total_duration = video_info.get('duration', 20)
                    slice_duration = total_duration / 3  # 只生成3个切片
                    
                    slice_result = await ffmpeg_service.slice_video(
                        video_path,
                        slice_duration=slice_duration,
                        separate_audio=True
                    )
                    
                    if slice_result and 'slices' in slice_result:
                        video_slices = slice_result['slices'][:3]  # 只处理前3个切片
                        
                        # 分析视频切片
                        await qwen_vl_service.analyze_video_content(video_slices)
                        
                        # 提取关键帧
                        for i, slice_info in enumerate(video_slices):
                            keyframe_result = await ffmpeg_service.extract_keyframes(
                                slice_info['output_file'],
                                num_keyframes=3,
                                output_dir=os.path.join(self.export_dir, f"keyframes_{i}")
                            )
                            if keyframe_result and 'keyframes' in keyframe_result:
                                video_slices[i]['keyframes'] = keyframe_result['keyframes']
                        
                        # 分析关键帧并生成Prompt
                        prompt_results = []
                        for i, slice_info in enumerate(video_slices):
                            if 'keyframes' in slice_info and slice_info['keyframes']:
                                # 使用qwen3-vl-plus分析关键帧
                                vl_result = qwen_video_service.analyze_keyframes_with_qwen3vl_plus(
                                    slice_info['keyframes'],
                                    {"video_prompt": f"分析第{i+1}个场景的关键帧，生成详细的视频描述"}
                                )
                                
                                if vl_result.get('success'):
                                    # 生成视频提示词
                                    prompt_result = scene_segmenter.generate_video_prompt_for_scene(
                                        scene={
                                            "description": vl_result.get('prompt', ''),
                                            "setting": "视频场景"
                                        },
                                        video_understanding="视频分析结果",
                                        audio_text="音频转录内容",
                                        scene_index=i
                                    )
                                    
                                    prompt_results.append({
                                        "scene_id": i+1,
                                        "original_analysis": vl_result,
                                        "generated_prompt": prompt_result,
                                        "timestamp": time.time()
                                    })
                        
                        # 保存Prompt结果
                        prompts_output_file = os.path.join(self.export_dir, "generated_prompts.json")
                        with open(prompts_output_file, 'w', encoding='utf-8') as f:
                            json.dump(prompt_results, f, ensure_ascii=False, indent=2)
                        
                        logger.info(f"已生成并保存 {len(prompt_results)} 个Prompt结果到 {prompts_output_file}")
                        return prompt_results
                else:
                    # 生成示例Prompt结果
                    logger.info("生成示例Prompt结果...")
                    
                    # 模拟生成一些示例Prompt
                    sample_prompts = [
                        {
                            "scene_id": 1,
                            "original_analysis": {
                                "success": True,
                                "prompt": "一个阳光明媚的早晨，城市街道上车辆川流不息，行人们匆忙赶路",
                                "style": "写实风格，清晰细节"
                            },
                            "generated_prompt": {
                                "success": True,
                                "video_prompt": "阳光明媚的早晨，现代化城市街道，车辆川流不息，行人们匆忙赶路，写实风格，清晰细节，4K分辨率",
                                "style_elements": {"type": "realistic"}
                            },
                            "timestamp": time.time()
                        },
                        {
                            "scene_id": 2,
                            "original_analysis": {
                                "success": True,
                                "prompt": "夜晚的咖啡馆，温暖的灯光，人们在交谈，背景音乐柔和",
                                "style": "温馨风格，暖色调"
                            },
                            "generated_prompt": {
                                "success": True,
                                "video_prompt": "夜晚的咖啡馆，温暖的灯光，人们在愉快交谈，背景音乐柔和，温馨风格，暖色调，4K分辨率",
                                "style_elements": {"type": "warm", "lighting": "soft"}
                            },
                            "timestamp": time.time()
                        }
                    ]
                    
                    # 保存示例Prompt结果
                    prompts_output_file = os.path.join(self.export_dir, "sample_generated_prompts.json")
                    with open(prompts_output_file, 'w', encoding='utf-8') as f:
                        json.dump(sample_prompts, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"已生成并保存示例Prompt结果到 {prompts_output_file}")
                    return sample_prompts
                    
        except Exception as e:
            logger.error(f"生成Prompt结果时出错: {str(e)}")
            return []
    
    def export_workflow_diagram(self):
        """导出工作流程图说明"""
        logger.info("导出工作流程图说明...")
        
        workflow_diagram = """# 图像识别和Prompt生成工作流程

## 1. 视频切片
- 将输入视频分割成多个片段
- 分离音频和视频
- 提取每个切片的基本信息

## 2. 关键帧提取
- 从每个视频切片中提取关键帧
- 保存关键帧用于后续分析

## 3. 图像识别（关键帧分析）
- 使用qwen3-vl-plus模型分析关键帧
- 识别场景内容、物体、人物和动作
- 提取视觉风格和氛围

## 4. 初始Prompt生成
- 基于关键帧分析结果生成初始Prompt
- 包含场景描述、风格要求和技术参数

## 5. Prompt优化
- 使用AI模型优化初始Prompt
- 提升描述的准确性和详细程度
- 确保与原视频内容高度一致

## 6. JSON解析和验证
- 解析Prompt为结构化JSON格式
- 验证Prompt的完整性和有效性
- 提取关键参数用于视频生成

## 7. 一致性检查
- 检查生成的Prompt与原视频的一致性
- 确保场景间的连贯性
- 生成优化建议

## 8. 最终Prompt生成
- 基于一致性检查结果调整Prompt
- 生成最终用于视频生成的Prompt

## 9. 视频生成
- 使用生成的Prompt生成视频片段
- 确保生成视频与Prompt高度一致
- 进行最终的质量检查
"""
        
        workflow_file = os.path.join(self.export_dir, "workflow_diagram.md")
        with open(workflow_file, 'w', encoding='utf-8') as f:
            f.write(workflow_diagram)
        
        logger.info(f"已导出工作流程图说明到 {workflow_file}")
    
    async def run_export(self, video_path: str = None):
        """运行完整的导出流程"""
        logger.info("开始完整导出流程...")
        
        # 1. 导出图像识别代码
        self.export_image_recognition_code()
        
        # 2. 生成并导出Prompt结果
        await self.generate_and_export_prompt_results(video_path)
        
        # 3. 导出工作流程图说明
        self.export_workflow_diagram()
        
        logger.info(f"导出完成！所有结果已保存到 {self.export_dir}")
        logger.info("\n导出的文件包括：")
        for file in os.listdir(self.export_dir):
            file_path = os.path.join(self.export_dir, file)
            if os.path.isfile(file_path):
                logger.info(f"  - {file}")

async def main():
    """主函数"""
    # 解析命令行参数
    video_path = None
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        if not os.path.exists(video_path):
            logger.error(f"视频文件不存在: {video_path}")
            sys.exit(1)
    
    # 创建导出器并运行
    exporter = ImageRecognitionAndPromptExporter()
    await exporter.run_export(video_path)

if __name__ == "__main__":
    asyncio.run(main())
