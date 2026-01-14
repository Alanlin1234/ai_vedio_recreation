#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
导出已有的图像识别代码和Prompt结果脚本

该脚本用于直接导出项目中已有的图像识别代码和生成的prompt结果，不重新分析视频：
1. 导出核心图像识别代码
2. 收集并整理已有的prompt结果
3. 生成便于查看的报告
"""

import sys
import os
import time
import json
import shutil
import logging
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExistingPromptExporter:
    """导出已有的Prompt结果和图像识别代码"""
    
    def __init__(self):
        self.export_dir = f"exported_existing_results_{int(time.time())}"
        os.makedirs(self.export_dir, exist_ok=True)
        self.prompt_files = []
        logger.info(f"导出目录: {self.export_dir}")
    
    def find_existing_prompt_files(self):
        """查找所有已有的prompt结果文件"""
        logger.info("开始查找已有的prompt结果文件...")
        
        # 搜索所有generated_prompts目录下的JSON文件
        search_patterns = [
            "**/generated_prompts/**/*.json",
            "**/downloads/generated_prompts/*.json"
        ]
        
        for pattern in search_patterns:
            import glob
            found_files = glob.glob(pattern, recursive=True)
            self.prompt_files.extend(found_files)
        
        # 去重
        self.prompt_files = list(set(self.prompt_files))
        logger.info(f"找到 {len(self.prompt_files)} 个prompt结果文件")
        
        # 按时间排序（最新的在前）
        self.prompt_files.sort(key=os.path.getmtime, reverse=True)
        
        # 保存文件列表
        with open(os.path.join(self.export_dir, "prompt_files_list.txt"), 'w', encoding='utf-8') as f:
            for file_path in self.prompt_files:
                mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(file_path)))
                f.write(f"{mtime} - {file_path}\n")
    
    def export_image_recognition_code(self):
        """导出图像识别相关的核心代码"""
        logger.info("开始导出图像识别代码...")
        
        # 创建代码导出目录
        code_dir = os.path.join(self.export_dir, "image_recognition_code")
        os.makedirs(code_dir, exist_ok=True)
        
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
                if not os.path.exists(file_path):
                    logger.warning(f"文件 {file_path} 不存在")
                    continue
                    
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
                        code_dir,
                        f"{os.path.basename(config['file_path'])}_{method}.py"
                    )
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(f"# 从 {config['file_path']} 导出的 {method} 方法\n\n")
                        f.write(method_code)
                    
                    logger.info(f"已导出方法 {method} 到 {output_file}")
                    
            except Exception as e:
                logger.error(f"导出 {config['file_path']} 时出错: {str(e)}")
    
    def export_recent_prompts(self, max_files: int = 5):
        """导出最近生成的几个prompt结果"""
        logger.info(f"开始导出最近的 {max_files} 个prompt结果...")
        
        # 创建prompt结果导出目录
        prompts_dir = os.path.join(self.export_dir, "recent_prompts")
        os.makedirs(prompts_dir, exist_ok=True)
        
        # 处理最近的几个文件
        for i, file_path in enumerate(self.prompt_files[:max_files]):
            try:
                logger.info(f"处理文件 {i+1}/{max_files}: {file_path}")
                
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 解析JSON
                prompt_data = json.loads(content)
                
                # 提取关键信息
                export_data = {
                    "file_path": file_path,
                    "video_path": prompt_data.get("video_path", ""),
                    "timestamp": prompt_data.get("timestamp", ""),
                    "prompt_type": prompt_data.get("prompt_type", ""),
                    "scene_count": prompt_data.get("scene_count", 0),
                    "scenes": []
                }
                
                # 只提取每个场景的关键信息
                for scene in prompt_data.get("scenes", []):
                    scene_info = {
                        "scene_id": scene.get("scene_id", ""),
                        "start_time": scene.get("start_time", 0),
                        "end_time": scene.get("end_time", 0),
                        "duration": scene.get("duration", 0),
                        "description": scene.get("description", ""),
                        "video_prompt": scene.get("video_prompt", ""),
                        "style_elements": scene.get("style_elements", {})
                    }
                    export_data["scenes"].append(scene_info)
                
                # 生成导出文件名
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                export_file = os.path.join(prompts_dir, f"prompt_{i+1}_{base_name}.json")
                
                # 保存导出结果
                with open(export_file, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"已导出prompt结果到 {export_file}")
                
            except Exception as e:
                logger.error(f"处理文件 {file_path} 时出错: {str(e)}")
    
    def generate_prompt_summary(self):
        """生成prompt结果的汇总报告"""
        logger.info("开始生成prompt汇总报告...")
        
        # 分析所有prompt文件
        summary_data = {
            "total_files": len(self.prompt_files),
            "by_video": {},
            "by_type": {},
            "by_date": {}
        }
        
        for file_path in self.prompt_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.loads(f.read())
                
                # 按视频分组
                video_path = data.get("video_path", "unknown")
                if video_path not in summary_data["by_video"]:
                    summary_data["by_video"][video_path] = []
                summary_data["by_video"][video_path].append(file_path)
                
                # 按类型分组
                prompt_type = data.get("prompt_type", "unknown")
                summary_data["by_type"][prompt_type] = summary_data["by_type"].get(prompt_type, 0) + 1
                
                # 按日期分组
                mtime = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(file_path)))
                summary_data["by_date"][mtime] = summary_data["by_date"].get(mtime, 0) + 1
                
            except Exception as e:
                logger.error(f"分析文件 {file_path} 时出错: {str(e)}")
        
        # 生成汇总报告
        report_content = f"# Prompt结果汇总报告\n\n"
        report_content += f"**总文件数**: {summary_data['total_files']}\n\n"
        
        # 按类型统计
        report_content += "## 按类型统计\n\n"
        for prompt_type, count in sorted(summary_data["by_type"].items(), key=lambda x: x[1], reverse=True):
            report_content += f"- {prompt_type}: {count} 个文件\n"
        
        # 按日期统计
        report_content += "\n## 按日期统计\n\n"
        for date, count in sorted(summary_data["by_date"].items(), reverse=True):
            report_content += f"- {date}: {count} 个文件\n"
        
        # 按视频统计
        report_content += "\n## 按视频统计\n\n"
        for video_path, files in summary_data["by_video"].items():
            report_content += f"### {os.path.basename(video_path)}\n"
            report_content += f"文件数: {len(files)}\n"
            report_content += "最近文件: "
            # 按时间排序
            files.sort(key=os.path.getmtime, reverse=True)
            for file in files[:3]:
                mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(file)))
                report_content += f"{mtime} - {os.path.basename(file)} | "
            if len(files) > 3:
                report_content += f"... 等 {len(files)} 个文件\n"
            else:
                report_content += "\n"
        
        # 保存报告
        report_file = os.path.join(self.export_dir, "prompt_summary.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"已生成汇总报告到 {report_file}")
    
    def run_export(self):
        """运行完整的导出流程"""
        logger.info("开始完整导出流程...")
        
        # 1. 查找已有的prompt结果文件
        self.find_existing_prompt_files()
        
        # 2. 导出图像识别代码
        self.export_image_recognition_code()
        
        # 3. 导出最近的几个prompt结果
        self.export_recent_prompts(max_files=5)
        
        # 4. 生成汇总报告
        self.generate_prompt_summary()
        
        logger.info(f"导出完成！所有结果已保存到 {self.export_dir}")
        logger.info("\n导出的文件包括：")
        
        # 列出导出的主要文件
        export_files = []
        for root, dirs, files in os.walk(self.export_dir):
            for file in files:
                export_files.append(os.path.join(root, file))
        
        for file_path in sorted(export_files):
            logger.info(f"  - {file_path}")

def main():
    """主函数"""
    # 创建导出器并运行
    exporter = ExistingPromptExporter()
    exporter.run_export()

if __name__ == "__main__":
    main()
