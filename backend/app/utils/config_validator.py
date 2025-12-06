"""
配置验证工具
用于验证所有Agent的配置完整性和正确性
"""
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self):
        self.required_configs = {
            'HotspotAgent': {
                'required': [],
                'optional': ['douyin_api_key', 'douyin_api_secret', 'douyin_api_endpoint']
            },
            'ScriptAgent': {
                'required': [],
                'optional': ['llm_api_key', 'llm_api_endpoint', 'llm_model']
            },
            'StoryboardAgent': {
                'required': [],
                'optional': []
            },
            'ImageGenerationAgent': {
                'required': [],
                'optional': ['comfyui_url', 'timeout', 'batch_size']
            },
            'ConsistencyAgent': {
                'required': [],
                'optional': ['threshold', 'face_api_key', 'face_api_endpoint', 'vision_api_key', 'vision_api_endpoint']
            },
            'VideoSynthesisAgent': {
                'required': [],
                'optional': ['output_dir']
            },
            'RegenerationAgent': {
                'required': [],
                'optional': ['max_retries', 'consistency_threshold']
            },
            'VideoCreationOrchestrator': {
                'required': [],
                'optional': ['tracking_file', 'comfyui_url', 'timeout', 'batch_size']
            }
        }
    
    def validate_config(self, agent_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证Agent配置
        
        Args:
            agent_name: Agent名称
            config: 配置字典
            
        Returns:
            验证结果，包含成功状态、错误信息和警告信息
        """
        result = {
            'success': True,
            'errors': [],
            'warnings': []
        }
        
        # 检查Agent是否在支持的列表中
        if agent_name not in self.required_configs:
            result['warnings'].append(f"Agent '{agent_name}' 不在支持的配置验证列表中，跳过验证")
            return result
        
        agent_config = self.required_configs[agent_name]
        
        # 检查必需配置项
        for required_key in agent_config['required']:
            if required_key not in config:
                result['success'] = False
                result['errors'].append(f"缺少必需配置项: {required_key}")
        
        # 检查可选配置项的类型
        # TODO: 添加配置项类型检查
        
        # 检查配置值的合理性
        self._check_config_values(agent_name, config, result)
        
        return result
    
    def _check_config_values(self, agent_name: str, config: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        检查配置值的合理性
        
        Args:
            agent_name: Agent名称
            config: 配置字典
            result: 验证结果字典
        """
        
        # 检查ComfyUI URL
        if 'comfyui_url' in config:
            comfyui_url = config['comfyui_url']
            if not isinstance(comfyui_url, str):
                result['errors'].append(f"comfyui_url 必须是字符串类型")
                result['success'] = False
            elif not (comfyui_url.startswith('http://') or comfyui_url.startswith('https://')):
                result['warnings'].append(f"comfyui_url '{comfyui_url}' 可能不是有效的URL，建议使用 http:// 或 https:// 开头")
        
        # 检查超时时间
        if 'timeout' in config:
            timeout = config['timeout']
            if not isinstance(timeout, (int, float)):
                result['errors'].append(f"timeout 必须是数字类型")
                result['success'] = False
            elif timeout <= 0:
                result['errors'].append(f"timeout 必须大于0")
                result['success'] = False
            elif timeout > 3600:  # 超过1小时
                result['warnings'].append(f"timeout {timeout}秒可能过长，建议不超过300秒")
        
        # 检查批处理大小
        if 'batch_size' in config:
            batch_size = config['batch_size']
            if not isinstance(batch_size, int):
                result['errors'].append(f"batch_size 必须是整数类型")
                result['success'] = False
            elif batch_size <= 0:
                result['errors'].append(f"batch_size 必须大于0")
                result['success'] = False
            elif batch_size > 10:  # 超过10个
                result['warnings'].append(f"batch_size {batch_size}可能过大，建议不超过10")
        
        # 检查一致性阈值
        if 'threshold' in config:
            threshold = config['threshold']
            if not isinstance(threshold, (int, float)):
                result['errors'].append(f"threshold 必须是数字类型")
                result['success'] = False
            elif threshold < 0 or threshold > 1:
                result['errors'].append(f"threshold 必须在0到1之间")
                result['success'] = False
        
        # 检查API密钥
        api_keys = ['douyin_api_key', 'llm_api_key', 'face_api_key', 'vision_api_key']
        for api_key in api_keys:
            if api_key in config:
                key_value = config[api_key]
                if not isinstance(key_value, str):
                    result['errors'].append(f"{api_key} 必须是字符串类型")
                    result['success'] = False
                elif not key_value:
                    result['warnings'].append(f"{api_key} 为空字符串，可能导致API调用失败")
    
    def validate_all_configs(self, configs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证所有Agent的配置
        
        Args:
            configs: 包含所有Agent配置的字典，格式为 {agent_name: config_dict}
            
        Returns:
            总体验证结果
        """
        overall_result = {
            'success': True,
            'agent_results': {}
        }
        
        for agent_name, config in configs.items():
            agent_result = self.validate_config(agent_name, config)
            overall_result['agent_results'][agent_name] = agent_result
            
            if not agent_result['success']:
                overall_result['success'] = False
        
        return overall_result
    
    def get_required_configs(self, agent_name: str) -> Dict[str, List[str]]:
        """
        获取Agent的必需配置项和可选配置项
        
        Args:
            agent_name: Agent名称
            
        Returns:
            包含必需配置项和可选配置项的字典
        """
        return self.required_configs.get(agent_name, {
            'required': [],
            'optional': []
        })


# 创建全局ConfigValidator实例
config_validator = None


def get_config_validator() -> ConfigValidator:
    """
    获取全局ConfigValidator实例
    
    Returns:
        ConfigValidator实例
    """
    global config_validator
    if config_validator is None:
        config_validator = ConfigValidator()
    return config_validator
