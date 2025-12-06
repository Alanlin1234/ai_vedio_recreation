"""
追踪管理器 - 用于记录Agent系统的执行情况
"""
import json
import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TrackingManager:
    """追踪管理器类"""
    
    def __init__(self, tracking_file: str = "agent_tracking.json"):
        """
        初始化追踪管理器
        
        Args:
            tracking_file: 追踪文件路径
        """
        self.tracking_file = tracking_file
        self.current_session_id = None
        self.session_data = {}
        self.start_time = None
        
        # 确保追踪目录存在
        tracking_dir = os.path.dirname(self.tracking_file)
        if tracking_dir and not os.path.exists(tracking_dir):
            os.makedirs(tracking_dir)
        
        # 加载现有追踪数据
        self.load_tracking_data()
    
    def start_session(self, input_params: Dict[str, Any]) -> str:
        """
        开始新的追踪会话
        
        Args:
            input_params: 输入参数
            
        Returns:
            会话ID
        """
        self.current_session_id = f"session_{int(time.time())}_{len(self.session_data) + 1}"
        self.start_time = datetime.now()
        
        # 初始化会话数据
        self.session_data[self.current_session_id] = {
            "session_id": self.current_session_id,
            "start_time": self.start_time.isoformat(),
            "input_params": input_params,
            "agents": {},
            "token_usage": {},
            "time_tracking": {},
            "generated_content": {},
            "file_locations": {},
            "status": "running",
            "errors": []
        }
        
        logger.info(f"开始追踪会话: {self.current_session_id}")
        return self.current_session_id
    
    def record_agent_execution(self, agent_name: str, execution_data: Dict[str, Any]):
        """
        记录Agent执行情况
        
        Args:
            agent_name: Agent名称
            execution_data: 执行数据
        """
        if not self.current_session_id:
            logger.warning("没有活动的追踪会话")
            return
        
        session = self.session_data[self.current_session_id]
        
        # 记录Agent执行
        session["agents"][agent_name] = {
            "execution_time": datetime.now().isoformat(),
            "success": execution_data.get("success", False),
            "input": execution_data.get("input", {}),
            "output": execution_data.get("data", {}),
            "error": execution_data.get("error"),
            "execution_time_seconds": execution_data.get("execution_time", 0)
        }
        
        # 记录token使用
        if "token_usage" in execution_data:
            self._record_token_usage(agent_name, execution_data["token_usage"])
        
        # 记录生成内容
        if "generated_content" in execution_data:
            self._record_generated_content(agent_name, execution_data["generated_content"])
        
        # 记录文件位置
        if "file_locations" in execution_data:
            self._record_file_locations(agent_name, execution_data["file_locations"])
    
    def record_token_usage(self, model_name: str, usage_data: Dict[str, Any]):
        """
        记录token使用情况
        
        Args:
            model_name: 模型名称
            usage_data: 使用数据
        """
        if not self.current_session_id:
            return
        
        session = self.session_data[self.current_session_id]
        
        if model_name not in session["token_usage"]:
            session["token_usage"][model_name] = []
        
        session["token_usage"][model_name].append({
            "timestamp": datetime.now().isoformat(),
            "prompt_tokens": usage_data.get("prompt_tokens", 0),
            "completion_tokens": usage_data.get("completion_tokens", 0),
            "total_tokens": usage_data.get("total_tokens", 0),
            "cost_estimate": usage_data.get("cost_estimate", 0)
        })
    
    def record_time_tracking(self, stage: str, duration: float):
        """
        记录时间追踪
        
        Args:
            stage: 阶段名称
            duration: 耗时(秒)
        """
        if not self.current_session_id:
            return
        
        session = self.session_data[self.current_session_id]
        session["time_tracking"][stage] = duration
    
    def record_generated_content(self, content_type: str, content_data: Dict[str, Any]):
        """
        记录生成的内容
        
        Args:
            content_type: 内容类型
            content_data: 内容数据
        """
        if not self.current_session_id:
            return
        
        session = self.session_data[self.current_session_id]
        
        if content_type not in session["generated_content"]:
            session["generated_content"][content_type] = []
        
        session["generated_content"][content_type].append({
            "timestamp": datetime.now().isoformat(),
            "content": content_data
        })
    
    def record_file_location(self, file_type: str, file_path: str, metadata: Dict[str, Any] = None):
        """
        记录文件位置
        
        Args:
            file_type: 文件类型
            file_path: 文件路径
            metadata: 元数据
        """
        if not self.current_session_id:
            return
        
        session = self.session_data[self.current_session_id]
        
        if file_type not in session["file_locations"]:
            session["file_locations"][file_type] = []
        
        session["file_locations"][file_type].append({
            "timestamp": datetime.now().isoformat(),
            "file_path": file_path,
            "metadata": metadata or {}
        })
    
    def record_error(self, error_data: Dict[str, Any]):
        """
        记录错误信息
        
        Args:
            error_data: 错误数据
        """
        if not self.current_session_id:
            return
        
        session = self.session_data[self.current_session_id]
        session["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "error": error_data
        })
    
    def end_session(self, final_result: Dict[str, Any] = None):
        """
        结束追踪会话
        
        Args:
            final_result: 最终结果
        """
        if not self.current_session_id:
            return
        
        session = self.session_data[self.current_session_id]
        session["end_time"] = datetime.now().isoformat()
        session["status"] = "completed"
        
        # 计算总耗时
        start_time = datetime.fromisoformat(session["start_time"])
        end_time = datetime.fromisoformat(session["end_time"])
        session["total_duration_seconds"] = (end_time - start_time).total_seconds()
        
        # 记录最终结果
        if final_result:
            session["final_result"] = final_result
        
        # 保存追踪数据
        self.save_tracking_data()
        
        logger.info(f"结束追踪会话: {self.current_session_id}, 总耗时: {session['total_duration_seconds']:.2f}秒")
        
        # 重置当前会话
        self.current_session_id = None
    
    def _record_token_usage(self, agent_name: str, token_usage: Dict[str, Any]):
        """内部方法：记录token使用"""
        for model, usage in token_usage.items():
            self.record_token_usage(model, usage)
    
    def _record_generated_content(self, agent_name: str, content: Dict[str, Any]):
        """内部方法：记录生成内容"""
        for content_type, content_data in content.items():
            self.record_generated_content(content_type, content_data)
    
    def _record_file_locations(self, agent_name: str, file_locations: Dict[str, Any]):
        """内部方法：记录文件位置"""
        for file_type, locations in file_locations.items():
            for location in locations:
                self.record_file_location(file_type, location["file_path"], location.get("metadata"))
    
    def load_tracking_data(self):
        """加载追踪数据"""
        try:
            if os.path.exists(self.tracking_file):
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.session_data = data.get("sessions", {})
                logger.info(f"加载追踪数据，共 {len(self.session_data)} 个会话")
            else:
                self.session_data = {}
                logger.info("创建新的追踪文件")
        except Exception as e:
            logger.error(f"加载追踪数据失败: {e}")
            self.session_data = {}
    
    def save_tracking_data(self):
        """保存追踪数据"""
        try:
            # 准备保存的数据
            data_to_save = {
                "last_updated": datetime.now().isoformat(),
                "total_sessions": len(self.session_data),
                "sessions": self.session_data
            }
            
            # 保存到文件
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            
            logger.info(f"追踪数据已保存到: {self.tracking_file}")
        except Exception as e:
            logger.error(f"保存追踪数据失败: {e}")
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话摘要"""
        if session_id not in self.session_data:
            return None
        
        session = self.session_data[session_id]
        
        # 计算token使用总量
        total_tokens = {}
        for model, usages in session.get("token_usage", {}).items():
            total_tokens[model] = {
                "total_prompt_tokens": sum(u.get("prompt_tokens", 0) for u in usages),
                "total_completion_tokens": sum(u.get("completion_tokens", 0) for u in usages),
                "total_tokens": sum(u.get("total_tokens", 0) for u in usages),
                "total_cost": sum(u.get("cost_estimate", 0) for u in usages)
            }
        
        # 计算各阶段耗时
        time_summary = session.get("time_tracking", {})
        
        # 统计生成内容
        content_summary = {}
        for content_type, contents in session.get("generated_content", {}).items():
            content_summary[content_type] = len(contents)
        
        return {
            "session_id": session_id,
            "status": session.get("status", "unknown"),
            "start_time": session.get("start_time"),
            "end_time": session.get("end_time"),
            "total_duration": session.get("total_duration_seconds", 0),
            "agents_executed": list(session.get("agents", {}).keys()),
            "token_usage_summary": total_tokens,
            "time_summary": time_summary,
            "content_summary": content_summary,
            "file_count": sum(len(files) for files in session.get("file_locations", {}).values()),
            "error_count": len(session.get("errors", []))
        }
    
    def get_all_sessions_summary(self) -> List[Dict[str, Any]]:
        """获取所有会话摘要"""
        summaries = []
        for session_id in self.session_data:
            summary = self.get_session_summary(session_id)
            if summary:
                summaries.append(summary)
        
        # 按开始时间排序（最新的在前）
        summaries.sort(key=lambda x: x.get("start_time", ""), reverse=True)
        return summaries