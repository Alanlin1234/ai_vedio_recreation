
#脚本拆解Agent

from typing import Dict, Any, List
from .base_agent import BaseAgent
import re


class ScriptAgent(BaseAgent):
    #负责对视频内容进行脚本拆解
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("ScriptAgent", config)
        
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        
        try:
            if not self.validate_input(input_data, ['hotspot']):
                return self.create_result(False, error="缺少必要的输入参数")
            
            self.log_execution("start", "开始脚本拆解")
            
            hotspot = input_data['hotspot']
            style = input_data.get('style', 'commentary')
            duration = input_data.get('duration', 60)
            
            # 生成脚本
            script = await self._generate_script(hotspot, style, duration)
            
            # 拆解场景
            scenes = self._parse_scenes(script)
            
            # 提取旁白
            narration = self._extract_narration(script)
            
            self.log_execution("complete", f"生成{len(scenes)}个场景")
            
            return self.create_result(True, {
                'script': script,
                'scenes': scenes,
                'narration': narration,
                'total_scenes': len(scenes),
                'estimated_duration': duration
            })
            
        except Exception as e:
            self.logger.error(f"脚本拆解失败: {str(e)}")
            return self.create_result(False, error=str(e))
    
    async def _generate_script(self, hotspot: Dict, style: str, duration: int) -> Dict[str, Any]:
        #生成视频脚本
        try:
            # 使用大模型生成脚本
            content = await self._generate_with_llm(hotspot, style, duration)
        except Exception as e:
            self.logger.warning(f"大模型生成失败，使用模板: {str(e)}")
            content = self._create_sample_script(hotspot, duration)
        
        return {
            'title': hotspot.get('title', ''),
            'theme': hotspot.get('description', ''),
            'style': style,
            'duration': duration,
            'content': content
        }
    
    async def _generate_with_llm(self, hotspot: Dict, style: str, duration: int) -> str:
        
        #使用大模型生成脚本
        
        
        import aiohttp
        import json
        
        # API配置（需要填充）
        api_key = self.config.get('llm_api_key', '')
        api_endpoint = self.config.get('llm_api_endpoint', '')
        model = self.config.get('llm_model', 'gpt-4')
        
        if not api_key or not api_endpoint:
            raise Exception("大模型API未配置")
        
        # 构建提示词
        prompt = self._build_script_prompt(hotspot, style, duration)
        
        # 调用API
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': model,
            'messages': [
                {
                    'role': 'system',
                    'content': '你是一个专业的短视频脚本创作者，擅长创作吸引人的视频内容。'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.7,
            'max_tokens': 2000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_endpoint, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data['choices'][0]['message']['content']
                    return content
                else:
                    error_text = await response.text()
                    raise Exception(f"API返回错误: {response.status}, {error_text}")
    
    def _build_script_prompt(self, hotspot: Dict, style: str, duration: int) -> str:
        #构建脚本生成提示词
        title = hotspot.get('title', '')
        description = hotspot.get('description', '')
        
        prompt = f"""
请为以下热点话题创作一个{duration}秒的短视频脚本。

热点信息:
标题: {title}
描述: {description}

视频要求:
- 风格: {style}
- 时长: {duration}秒
- 目标: 吸引观众，传递信息，引发互动

脚本格式要求:
请按照以下格式输出脚本，每个场景包含时间段、画面描述和旁白:

【场景名称】（开始时间-结束时间秒）
画面：画面的详细描述
旁白：旁白文本

示例:
【开场】（0-3秒）
画面：快速切镜展示热点核心画面，配合动态文字弹出
旁白：你有没有发现，最近{关键词}突然火了？
音效：短促有力的开场音效

请创作完整的脚本，确保内容连贯、吸引人。
"""
        return prompt
    
    def _create_sample_script(self, hotspot: Dict, duration: int) -> str:
        """创建示例脚本（模板方式）"""
        title = hotspot.get('title', '今日热点')
        description = hotspot.get('description', '事件描述')
        
        # 根据时长动态调整场景
        if duration <= 30:
            # 短视频（30秒以内）
            return f"""
【开场】（0-3秒）
画面：震撼的标题卡，快速切换的动态文字效果
旁白：{title}

【主体】（3-{duration-5}秒）
画面：核心内容展示，配合关键信息图表
旁白：{description}

【结尾】（{duration-5}-{duration}秒）
画面：总结画面，引导关注
旁白：关注我，了解更多热点！
"""
        elif duration <= 60:
            # 中等视频（30-60秒）
            return f"""
【开场】（0-5秒）
画面：震撼的标题卡，配合音效
旁白：{title}

【背景介绍】（5-15秒）
画面：相关背景画面，时间线展示
旁白：让我们先了解一下背景。{description[:50]}...

【核心内容】（15-{duration-15}秒）
画面：核心场景展示，多角度呈现
旁白：{description}

【深度分析】（{duration-15}-{duration-5}秒）
画面：数据图表，专家观点
旁白：这背后反映了什么趋势？让我们深入分析...

【结尾】（{duration-5}-{duration}秒）
画面：总结画面，引导互动
旁白：你怎么看？评论区告诉我！
"""
        else:
            # 长视频（60秒以上）
            mid_point = duration // 2
            return f"""
【开场】（0-8秒）
画面：震撼的标题卡，配合动态背景音乐
旁白：大家好，今天我们来聊聊{title}

【背景介绍】（8-20秒）
画面：历史回顾，相关事件时间线
旁白：首先让我们了解一下事情的来龙去脉...

【核心内容1】（20-{mid_point}秒）
画面：核心场景展示，关键人物介绍
旁白：{description}

【核心内容2】（{mid_point}-{duration-25}秒）
画面：多角度分析，数据可视化
旁白：从不同角度来看，这个事件有着深远的影响...

【深度解读】（{duration-25}-{duration-10}秒）
画面：专家观点，行业分析
旁白：业内专家是怎么看的呢？让我们听听他们的观点...

【总结】（{duration-10}-{duration-3}秒）
画面：要点回顾，关键信息总结
旁白：总结一下，这个事件告诉我们...

【结尾】（{duration-3}-{duration}秒）
画面：引导关注，互动提示
旁白：你的看法是什么？欢迎在评论区讨论！记得点赞关注！
"""
    
    def _parse_scenes(self, script: Dict) -> List[Dict[str, Any]]:
        #分析场景
        content = script.get('content', '')
        scenes = []
        
        # 使用正则表达式解析场景
        pattern = r'【(.+?)】（(\d+)-(\d+)秒）\n画面：(.+?)\n旁白：(.+?)(?=\n\n|$)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for idx, match in enumerate(matches):
            scene_name, start_time, end_time, visual, narration = match
            scenes.append({
                'scene_id': idx + 1,
                'name': scene_name.strip(),
                'start_time': int(start_time),
                'end_time': int(end_time),
                'duration': int(end_time) - int(start_time),
                'visual_description': visual.strip(),
                'narration': narration.strip()
            })
        
        return scenes
    
    def _extract_narration(self, script: Dict) -> str:
        """提取完整旁白"""
        content = script.get('content', '')
        pattern = r'旁白：(.+?)(?=\n|$)'
        narrations = re.findall(pattern, content)
        return ' '.join(narrations)
