"""
Agent基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """所有Agent的基类"""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None, tracking_manager=None):
        self.name = name
        self.config = config or {}
        self.tracking_manager = tracking_manager
        self.logger = logging.getLogger(f"Agent.{name}")
        
        # 验证配置
        from app.utils.config_validator import get_config_validator
        validator = get_config_validator()
        validation_result = validator.validate_config(name, self.config)
        
        # 记录验证结果
        if not validation_result['success']:
            for error in validation_result['errors']:
                self.logger.error(f"配置验证失败: {error}")
        
        for warning in validation_result['warnings']:
            self.logger.warning(f"配置警告: {warning}")
        
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行Agent的主要逻辑"""
        pass
    
    def log_execution(self, stage: str, data: Any, execution_time: float = 0.0, token_usage: Dict[str, Any] = None, generated_content: Dict[str, Any] = None, file_locations: Dict[str, Any] = None):
        """记录执行日志"""
        self.logger.info(f"[{self.name}] {stage}: {data}")
        
        # 记录追踪数据
        if self.tracking_manager:
            execution_data = {
                "success": True,
                "input": {"stage": stage, "data": data},
                "data": data,
                "execution_time": execution_time
            }
            
            if token_usage:
                execution_data["token_usage"] = token_usage
            if generated_content:
                execution_data["generated_content"] = generated_content
            if file_locations:
                execution_data["file_locations"] = file_locations
            
            self.tracking_manager.record_agent_execution(self.name, execution_data)
        
    def validate_input(self, input_data: Dict[str, Any], required_fields: list) -> bool:
        """验证输入数据"""
        for field in required_fields:
            if field not in input_data:
                self.logger.error(f"Missing required field: {field}")
                return False
        return True
    
    def create_result(self, success: bool, data: Any = None, error: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建标准化的返回结果"""
        result = {
            'agent': self.name,
            'success': success,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        if not success and error:
            # 增强错误信息，包含更多上下文
            result['error'] = error
            result['error_details'] = {
                'agent_name': self.name,
                'error_type': type(error).__name__ if isinstance(error, Exception) else 'Unknown',
                'timestamp': result['timestamp']
            }
            
            # 添加额外上下文信息
            if context:
                result['error_details']['context'] = context
        
        return result
    
    def _measure_execution_time(self, func):
        """
        测量函数执行时间的装饰器
        
        Args:
            func: 要测量的函数
            
        Returns:
            包装后的函数
        """
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 记录时间追踪
            if self.tracking_manager:
                self.tracking_manager.record_time_tracking(f"{self.name}_execution", execution_time)
            
            return result, execution_time
        return wrapper
    
    def record_token_usage(self, model_name: str, prompt_tokens: int = 0, 
                          completion_tokens: int = 0, total_tokens: int = 0,
                          cost_estimate: float = 0.0):
        """
        记录token使用情况
        
        Args:
            model_name: 模型名称
            prompt_tokens: 提示token数量
            completion_tokens: 完成token数量
            total_tokens: 总token数量
            cost_estimate: 成本估算
        """
        if self.tracking_manager:
            usage_data = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost_estimate": cost_estimate
            }
            self.tracking_manager.record_token_usage(model_name, usage_data)
    
    def record_generated_content(self, content_type: str, content_data: Dict[str, Any]):
        """
        记录生成的内容
        
        Args:
            content_type: 内容类型
            content_data: 内容数据
        """
        if self.tracking_manager:
            self.tracking_manager.record_generated_content(content_type, content_data)
    
    def record_file_location(self, file_type: str, file_path: str, metadata: Dict[str, Any] = None):
        """
        记录文件位置
        
        Args:
            file_type: 文件类型
            file_path: 文件路径
            metadata: 元数据
        """
        if self.tracking_manager:
            self.tracking_manager.record_file_location(file_type, file_path, metadata)
    
    def record_error(self, error_data: Dict[str, Any]):
        """
        记录错误信息
        
        Args:
            error_data: 错误数据
        """
        if self.tracking_manager:
            self.tracking_manager.record_error(error_data)
