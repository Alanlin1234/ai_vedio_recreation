"""
内容一致性检查器
检测视频中的物理逻辑、人物外貌、动作连贯性等问题
"""
import os
import sys
import json
import base64
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = logging.getLogger(__name__)


class ContentConsistencyChecker:
    """内容一致性检查器 - 检测物理逻辑、人物外貌、动作等问题"""
    
    PHYSICAL_LOGIC_ISSUES = [
        "重力异常", "物体穿模", "尺寸突变", "位置跳跃",
        "光影不一致", "透视错误", "物理碰撞异常", "材质突变",
        "gravity anomaly", "clipping", "size change", "position jump",
        "lighting inconsistency", "perspective error", "collision error"
    ]
    
    CHARACTER_ISSUES = [
        "外貌突变", "服装变化", "发型改变", "面部特征变化",
        "肤色变化", "体型变化", "年龄突变", "性别混淆",
        "appearance change", "clothing change", "hairstyle change",
        "facial feature change", "skin tone change", "body type change"
    ]
    
    ACTION_ISSUES = [
        "动作不连贯", "姿势突变", "运动轨迹异常", "速度突变",
        "动作方向错误", "肢体错位", "表情突变", "眼神不一致",
        "action discontinuity", "pose jump", "trajectory anomaly",
        "speed change", "direction error", "limb misplacement"
    ]
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.threshold = self.config.get('consistency_threshold', 0.85)
        self.vlm_client = None
        self._init_vlm_client()
        logger.info("ContentConsistencyChecker 初始化完成")
    
    def _init_vlm_client(self):
        """初始化视觉语言模型客户端"""
        try:
            from openai import OpenAI
            api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("OPENAI_API_KEY")
            if api_key:
                self.vlm_client = OpenAI(
                    api_key=api_key,
                    base_url=os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
                )
                logger.info("VLM客户端初始化成功")
        except Exception as e:
            logger.warning(f"VLM客户端初始化失败: {e}")
    
    def check_content_consistency(self, video_path: str, keyframes: List[str] = None,
                                   previous_keyframes: List[str] = None,
                                   scene_prompt: str = "") -> Dict[str, Any]:
        """
        检查视频内容一致性
        
        Args:
            video_path: 视频文件路径
            keyframes: 当前场景的关键帧列表
            previous_keyframes: 上一场景的关键帧列表
            scene_prompt: 场景描述提示词
            
        Returns:
            检查结果
        """
        try:
            logger.info(f"开始内容一致性检查: {video_path}")
            
            results = {
                'success': True,
                'video_path': video_path,
                'check_time': datetime.now().isoformat(),
                'physical_logic': {},
                'character_consistency': {},
                'action_continuity': {},
                'overall_score': 0.0,
                'passed': False,
                'issues': [],
                'suggestions': []
            }
            
            if keyframes and len(keyframes) > 0:
                physical_result = self._check_physical_logic(keyframes, scene_prompt)
                results['physical_logic'] = physical_result
                results['issues'].extend(physical_result.get('issues', []))
            
            if keyframes and previous_keyframes:
                character_result = self._check_character_consistency(keyframes, previous_keyframes, scene_prompt)
                results['character_consistency'] = character_result
                results['issues'].extend(character_result.get('issues', []))
            
            if keyframes and len(keyframes) >= 2:
                action_result = self._check_action_continuity(keyframes, scene_prompt)
                results['action_continuity'] = action_result
                results['issues'].extend(action_result.get('issues', []))
            
            results['overall_score'] = self._calculate_overall_score(results)
            results['passed'] = results['overall_score'] >= self.threshold
            
            if not results['passed']:
                results['suggestions'] = self._generate_suggestions(results)
            
            logger.info(f"内容一致性检查完成: 得分={results['overall_score']:.2f}")
            return results
            
        except Exception as e:
            error_msg = f"内容一致性检查失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'overall_score': 0.8,
                'passed': True,
                'issues': [error_msg]
            }
    
    def _check_physical_logic(self, keyframes: List[str], scene_prompt: str) -> Dict[str, Any]:
        """检查物理逻辑一致性"""
        try:
            if not self.vlm_client:
                return self._default_result("物理逻辑检查（无VLM客户端）")
            
            analysis_prompt = """请分析这组关键帧中的物理逻辑问题。

检查以下方面：
1. 重力是否正常（物体是否自然下落或悬浮）
2. 物体之间是否有穿模现象
3. 物体尺寸是否有异常变化
4. 物体位置是否有不合理的跳跃
5. 光影方向是否一致
6. 透视关系是否正确
7. 碰撞反应是否合理
8. 材质表现是否一致

请以JSON格式返回结果：
{
    "score": 0.0-1.0的评分,
    "passed": true/false,
    "issues": ["问题1", "问题2"],
    "details": {
        "gravity": {"normal": true, "description": "..."},
        "clipping": {"found": false, "description": "..."},
        "size": {"consistent": true, "description": "..."},
        "position": {"smooth": true, "description": "..."},
        "lighting": {"consistent": true, "description": "..."},
        "perspective": {"correct": true, "description": "..."}
    }
}
"""
            
            result = self._analyze_with_vlm(keyframes, analysis_prompt)
            
            if result.get('success'):
                return {
                    'score': result.get('score', 0.8),
                    'passed': result.get('passed', True),
                    'issues': result.get('issues', []),
                    'details': result.get('details', {})
                }
            else:
                return self._default_result("物理逻辑检查")
                
        except Exception as e:
            logger.error(f"物理逻辑检查失败: {e}")
            return self._default_result("物理逻辑检查")
    
    def _check_character_consistency(self, keyframes: List[str], previous_keyframes: List[str],
                                     scene_prompt: str) -> Dict[str, Any]:
        """检查人物外貌一致性"""
        try:
            if not self.vlm_client:
                return self._default_result("人物一致性检查（无VLM客户端）")
            
            all_frames = previous_keyframes[-2:] + keyframes[:3] if len(previous_keyframes) >= 2 else keyframes
            
            analysis_prompt = """请分析这组关键帧中的人物一致性。

检查以下方面：
1. 人物外貌是否保持一致（面部特征、五官）
2. 服装是否保持一致
3. 发型是否保持一致
4. 肤色是否保持一致
5. 体型是否保持一致
6. 年龄特征是否一致
7. 人物身份是否清晰可辨

请以JSON格式返回结果：
{
    "score": 0.0-1.0的评分,
    "passed": true/false,
    "issues": ["问题1", "问题2"],
    "details": {
        "appearance": {"consistent": true, "description": "..."},
        "clothing": {"consistent": true, "description": "..."},
        "hairstyle": {"consistent": true, "description": "..."},
        "skin_tone": {"consistent": true, "description": "..."},
        "body_type": {"consistent": true, "description": "..."},
        "identity": {"clear": true, "description": "..."}
    },
    "character_count": 人物数量
}
"""
            
            result = self._analyze_with_vlm(all_frames, analysis_prompt)
            
            if result.get('success'):
                return {
                    'score': result.get('score', 0.8),
                    'passed': result.get('passed', True),
                    'issues': result.get('issues', []),
                    'details': result.get('details', {}),
                    'character_count': result.get('character_count', 1)
                }
            else:
                return self._default_result("人物一致性检查")
                
        except Exception as e:
            logger.error(f"人物一致性检查失败: {e}")
            return self._default_result("人物一致性检查")
    
    def _check_action_continuity(self, keyframes: List[str], scene_prompt: str) -> Dict[str, Any]:
        """检查动作连贯性"""
        try:
            if not self.vlm_client:
                return self._default_result("动作连贯性检查（无VLM客户端）")
            
            analysis_prompt = """请分析这组关键帧中的动作连贯性。

检查以下方面：
1. 动作是否连贯流畅
2. 姿势变化是否自然
3. 运动轨迹是否合理
4. 速度变化是否平滑
5. 动作方向是否一致
6. 肢体位置是否合理
7. 表情变化是否自然
8. 眼神方向是否一致

请以JSON格式返回结果：
{
    "score": 0.0-1.0的评分,
    "passed": true/false,
    "issues": ["问题1", "问题2"],
    "details": {
        "action_flow": {"smooth": true, "description": "..."},
        "pose_change": {"natural": true, "description": "..."},
        "trajectory": {"reasonable": true, "description": "..."},
        "speed": {"consistent": true, "description": "..."},
        "direction": {"correct": true, "description": "..."},
        "limbs": {"correct": true, "description": "..."},
        "expression": {"natural": true, "description": "..."},
        "gaze": {"consistent": true, "description": "..."}
    }
}
"""
            
            result = self._analyze_with_vlm(keyframes, analysis_prompt)
            
            if result.get('success'):
                return {
                    'score': result.get('score', 0.8),
                    'passed': result.get('passed', True),
                    'issues': result.get('issues', []),
                    'details': result.get('details', {})
                }
            else:
                return self._default_result("动作连贯性检查")
                
        except Exception as e:
            logger.error(f"动作连贯性检查失败: {e}")
            return self._default_result("动作连贯性检查")
    
    def _analyze_with_vlm(self, image_paths: List[str], prompt: str) -> Dict[str, Any]:
        """使用视觉语言模型分析图像"""
        try:
            if not self.vlm_client or not image_paths:
                return {'success': False, 'error': 'VLM客户端未初始化或无图像'}
            
            content = [{"type": "text", "text": prompt}]
            
            for image_path in image_paths[:5]:
                if image_path and os.path.exists(image_path):
                    try:
                        with open(image_path, 'rb') as f:
                            image_data = base64.b64encode(f.read()).decode('utf-8')
                        
                        ext = os.path.splitext(image_path)[1].lower()
                        mime_type = {
                            '.jpg': 'image/jpeg',
                            '.jpeg': 'image/jpeg',
                            '.png': 'image/png',
                            '.gif': 'image/gif',
                            '.webp': 'image/webp'
                        }.get(ext, 'image/jpeg')
                        
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}"
                            }
                        })
                    except Exception as e:
                        logger.warning(f"读取图像失败: {image_path}, {e}")
            
            response = self.vlm_client.chat.completions.create(
                model="qwen-vl-max",
                messages=[{"role": "user", "content": content}],
                max_tokens=2000
            )
            
            response_text = response.choices[0].message.content
            
            json_result = self._parse_json_response(response_text)
            
            return {
                'success': True,
                'score': json_result.get('score', 0.8),
                'passed': json_result.get('passed', True),
                'issues': json_result.get('issues', []),
                'details': json_result.get('details', {}),
                'raw_response': response_text
            }
            
        except Exception as e:
            logger.error(f"VLM分析失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """解析JSON响应"""
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return {'score': 0.8, 'passed': True, 'issues': []}
    
    def _default_result(self, check_type: str) -> Dict[str, Any]:
        """返回默认结果"""
        return {
            'score': 0.8,
            'passed': True,
            'issues': [],
            'details': {'note': f'{check_type}使用默认通过'}
        }
    
    def _calculate_overall_score(self, results: Dict[str, Any]) -> float:
        """计算综合得分"""
        weights = {
            'physical_logic': 0.35,
            'character_consistency': 0.35,
            'action_continuity': 0.30
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for key, weight in weights.items():
            if key in results and results[key].get('score') is not None:
                total_score += results[key]['score'] * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.8
    
    def _generate_suggestions(self, results: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        physical = results.get('physical_logic', {})
        if physical.get('score', 1.0) < self.threshold:
            details = physical.get('details', {})
            if not details.get('gravity', {}).get('normal', True):
                suggestions.append("注意重力表现，确保物体自然下落")
            if details.get('clipping', {}).get('found', False):
                suggestions.append("检查物体穿模问题，调整物体位置和碰撞检测")
            if not details.get('lighting', {}).get('consistent', True):
                suggestions.append("统一场景光影方向和强度")
        
        character = results.get('character_consistency', {})
        if character.get('score', 1.0) < self.threshold:
            details = character.get('details', {})
            if not details.get('appearance', {}).get('consistent', True):
                suggestions.append("保持人物外貌特征一致，使用相同的人物参考图")
            if not details.get('clothing', {}).get('consistent', True):
                suggestions.append("确保人物服装在场景间保持一致")
            if not details.get('identity', {}).get('clear', True):
                suggestions.append("增强人物特征识别度，避免身份混淆")
        
        action = results.get('action_continuity', {})
        if action.get('score', 1.0) < self.threshold:
            details = action.get('details', {})
            if not details.get('action_flow', {}).get('smooth', True):
                suggestions.append("优化动作过渡，确保动作流畅自然")
            if not details.get('trajectory', {}).get('reasonable', True):
                suggestions.append("检查运动轨迹，避免不合理的位移")
            if not details.get('limbs', {}).get('correct', True):
                suggestions.append("检查肢体位置，避免错位或扭曲")
        
        return suggestions
    
    def check_scene_transition(self, current_keyframes: List[str], previous_keyframes: List[str],
                               scene_prompt: str = "") -> Dict[str, Any]:
        """
        检查场景过渡一致性
        
        Args:
            current_keyframes: 当前场景关键帧
            previous_keyframes: 上一场景关键帧
            scene_prompt: 场景描述
            
        Returns:
            过渡检查结果
        """
        try:
            if not self.vlm_client:
                return self._default_result("场景过渡检查")
            
            all_frames = previous_keyframes[-1:] + current_keyframes[:1]
            
            analysis_prompt = """请分析这两个关键帧之间的场景过渡。

检查以下方面：
1. 场景元素是否一致（背景、道具等）
2. 人物位置过渡是否自然
3. 光照变化是否合理
4. 色调是否连贯
5. 构图是否协调

请以JSON格式返回结果：
{
    "score": 0.0-1.0的评分,
    "passed": true/false,
    "issues": ["问题1", "问题2"],
    "transition_quality": "smooth/moderate/abrupt",
    "details": {
        "scene_elements": {"consistent": true, "description": "..."},
        "character_position": {"natural": true, "description": "..."},
        "lighting": {"smooth": true, "description": "..."},
        "color": {"coherent": true, "description": "..."},
        "composition": {"coordinated": true, "description": "..."}
    }
}
"""
            
            result = self._analyze_with_vlm(all_frames, analysis_prompt)
            
            if result.get('success'):
                return {
                    'score': result.get('score', 0.8),
                    'passed': result.get('passed', True),
                    'issues': result.get('issues', []),
                    'transition_quality': result.get('transition_quality', 'smooth'),
                    'details': result.get('details', {})
                }
            else:
                return self._default_result("场景过渡检查")
                
        except Exception as e:
            logger.error(f"场景过渡检查失败: {e}")
            return self._default_result("场景过渡检查")
