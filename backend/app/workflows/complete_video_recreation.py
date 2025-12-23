import os
import sys
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import Config
from app.services.video_recreation_service import VideoRecreationService
from app.services.video_service import VideoService
from app.models import db, VideoRecreation

class CompleteVideoRecreationWorkflow:
    
    def __init__(self):
        self.recreation_service = VideoRecreationService()
        self.video_service = VideoService()
        self.workflow_name = "complete_video_recreation"
    
    def log_step(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def create_video_record(self, video_path: str) -> int:
        self.log_step(f"开始创建视频记录: {video_path}")
        
        try:
            # 检查视频文件基本信息
            video_size = os.path.getsize(video_path) / (1024 * 1024)  # MB
            last_modified = datetime.fromtimestamp(os.path.getmtime(video_path))
            
            # 创建视频数据
            video_data = {
                'video_id': f"{self.workflow_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'title': os.path.basename(video_path),
                'description': '完整视频重建',
                'duration': 0,  # 将在处理时更新
                'local_file_path': video_path,
                'create_time': datetime.now(),
                'size_mb': round(video_size, 2)
            }
            
            # 创建视频记录
            video_id = self.video_service.create_video(video_data)
            self.log_step(f"视频记录创建成功，ID: {video_id}")
            return video_id
            
        except Exception as e:
            self.log_step(f"创建视频记录失败: {str(e)}", "ERROR")
            raise
    
    def process_video(self, video_path: str, use_qwen: bool = True, slice_limit: int = 0) -> Dict[str, Any]:
        start_time = time.time()
        self.log_step(f"开始完整视频重建流程: {video_path}")
        self.log_step(f"处理参数: use_qwen={use_qwen}, slice_limit={slice_limit}")
        
        try:
            # 1. 检查视频文件
            if not os.path.exists(video_path):
                raise ValueError(f"视频文件不存在: {video_path}")
            
            # 检查文件格式
            valid_extensions = ['.mp4', '.avi', '.mov', '.flv', '.wmv', '.mkv']
            file_ext = os.path.splitext(video_path)[1].lower()
            if file_ext not in valid_extensions:
                raise ValueError(f"不支持的视频格式: {file_ext}，支持的格式: {', '.join(valid_extensions)}")
            
            self.log_step(f"视频文件检查通过: {video_path}")
            
            # 2. 创建视频记录
            video_id = self.create_video_record(video_path)
            
            # 3. 检查是否存在现有任务
            existing_recreation = self.recreation_service.find_existing_recreation(video_path)
            if existing_recreation and existing_recreation.status == 'completed':
                self.log_step(f"发现已完成的重建任务，直接返回结果")
                return {
                    'success': True,
                    'message': '使用已完成的重建结果',
                    'recreation_id': existing_recreation.id,
                    'final_video_path': existing_recreation.final_video_path,
                    'final_video_with_audio_path': existing_recreation.final_video_with_audio_path,
                    'processing_time': 0
                }
            
            # 4. 开始完整的视频重建流程
            self.log_step(f"开始执行完整重建流程，任务ID: {video_id}")
            
            result = self.recreation_service.process_video_for_recreation(
                video_path=video_path,
                recreation_id=video_id,
                use_qwen=use_qwen,
                slice_limit=slice_limit
            )
            
            # 5. 处理结果
            if result.get('processing_status') == 'success':
                processing_time = time.time() - start_time
                self.log_step(f"视频重建流程完成，耗时: {processing_time:.2f}秒")
                self.log_step(f"最终视频路径: {result.get('final_video_path')}")
                self.log_step(f"带音频最终视频路径: {result.get('final_video_with_audio_path')}")
                
                # 保存结果到文件
                self._save_result(result, video_path)
                
                return {
                    'success': True,
                    'message': '视频重建成功',
                    'recreation_id': result.get('recreation_id'),
                    'final_video_path': result.get('final_video_path'),
                    'final_video_with_audio_path': result.get('final_video_with_audio_path'),
                    'processing_time': processing_time,
                    'scenes_processed': len(result.get('scene_analysis', {}).get('scenes', [])),
                    'video_count': result.get('video_generation', {}).get('successful_count', 0)
                }
            else:
                error_msg = result.get('error', '未知错误')
                self.log_step(f"视频重建失败: {error_msg}", "ERROR")
                return {
                    'success': False,
                    'message': '视频重建失败',
                    'error': error_msg,
                    'recreation_id': result.get('recreation_id')
                }
            
        except Exception as e:
            error_msg = str(e)
            self.log_step(f"视频重建流程异常: {error_msg}", "ERROR")
            return {
                'success': False,
                'message': '视频重建流程异常',
                'error': error_msg
            }
    
    def _save_result(self, result: Dict[str, Any], video_path: str):
        try:
            video_dir = os.path.dirname(video_path)
            result_file = os.path.join(video_dir, f"recreation_result_{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            self.log_step(f"重建结果已保存到: {result_file}")
        except Exception as e:
            self.log_step(f"保存结果文件失败: {str(e)}", "WARNING")
    
    def validate_result(self, result: Dict[str, Any]) -> bool:
        if not result.get('success'):
            self.log_step("结果验证失败: 重建过程未成功", "ERROR")
            return False
        
        # 检查最终视频文件是否存在
        final_video_path = result.get('final_video_path')
        if not final_video_path or not os.path.exists(final_video_path):
            self.log_step(f"结果验证失败: 最终视频文件不存在: {final_video_path}", "ERROR")
            return False
        
        # 检查带音频的最终视频文件是否存在
        final_video_with_audio_path = result.get('final_video_with_audio_path')
        if not final_video_with_audio_path or not os.path.exists(final_video_with_audio_path):
            self.log_step(f"结果验证失败: 带音频的最终视频文件不存在: {final_video_with_audio_path}", "ERROR")
            return False
        
        self.log_step("结果验证通过: 所有文件均存在")
        return True

def run_complete_video_recreation(video_path: str, use_qwen: bool = True, slice_limit: int = 0) -> Dict[str, Any]:
    workflow = CompleteVideoRecreationWorkflow()
    return workflow.process_video(video_path, use_qwen, slice_limit)

if __name__ == "__main__":
    # 示例用法
    import argparse
    
    parser = argparse.ArgumentParser(description="完整视频重建工作流")
    parser.add_argument("video_path", type=str, help="视频文件路径")
    parser.add_argument("--use-qwen", action="store_true", default=True, help="使用Qwen模型进行视频生成")
    parser.add_argument("--slice-limit", type=int, default=0, help="限制处理的切片数量，0表示不限制")
    
    args = parser.parse_args()
    
    # 创建Flask应用上下文
    from app import create_app
    app = create_app()
    
    with app.app_context():
        result = run_complete_video_recreation(args.video_path, args.use_qwen, args.slice_limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))

