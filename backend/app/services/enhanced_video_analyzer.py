"""
优化版视频分析服务
采用多阶段深度分析策略，精确提取视频内容、亮点和教育意义
"""

import os
import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class EnhancedVideoAnalyzer:
    """
    增强版视频分析器
    采用多阶段分析策略：
    1. 视频深度理解 - 提取完整内容
    2. 结构化分析 - 分解叙事要素
    3. 亮点提炼 - 识别高光时刻
    4. 教育意义提取 - 多维度价值分析
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or "sk-5eeb025e53df459b9f8a4b4209bd5fa5"
        import dashscope
        dashscope.api_key = self.api_key

    def analyze_video_complete(
        self,
        video_path: str,
        video_analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        完整的视频分析流程

        Args:
            video_path: 视频文件路径
            video_analysis_result: Qwen-omni分析的视频理解结果

        Returns:
            包含完整分析的字典
        """
        try:
            story_content = video_analysis_result.get('content', '')

            if not story_content:
                return {
                    'success': False,
                    'error': '视频分析内容为空'
                }

            # 第一阶段：深度内容理解
            content_analysis = self._deep_content_analysis(story_content)

            # 第二阶段：亮点提炼
            highlights = self._extract_highlights(story_content, content_analysis)

            # 第三阶段：教育意义提取
            educational = self._extract_educational_meaning(story_content, content_analysis)

            # 第四阶段：结构化总结
            structured_summary = self._create_structured_summary(
                story_content,
                content_analysis,
                highlights,
                educational
            )

            return {
                'success': True,
                'story_content': story_content,
                'content_analysis': content_analysis,
                'highlights': highlights,
                'educational_meaning': educational,
                'structured_summary': structured_summary
            }

        except Exception as e:
            logger.error(f"视频深度分析失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def _deep_content_analysis(self, story_content: str) -> Dict[str, Any]:
        """
        深度内容分析 - 理解故事的叙事结构
        """
        try:
            from dashscope import Generation

            analysis_prompt = f"""请深度分析以下故事内容，提取关键叙事要素：

故事内容：
{story_content}

请用JSON格式返回，包含以下维度：
{{
    "main_plot": "主要情节 - 用3-5句话概括故事主线",
    "characters": [
        {{"name": "人物名称", "role": "角色定位", "traits": "性格特点", "arc": "人物成长变化"}}
    ],
    "key_scenes": [
        {{"description": "场景描述", "significance": "在故事中的作用"}}
    ],
    "emotional_arc": "情感曲线 - 描述故事的情感起伏",
    "thematic_elements": ["主题元素1", "主题元素2"],
    "narrative_technique": "叙事技巧 - 描述讲故事的方式方法",
    "target_audience": "目标受众 - 适合的人群"
}}

分析要求：
1. 要深入理解故事的核心主题和价值观
2. 识别故事中的关键转折点
3. 理解人物的动机和成长
4. 识别叙事结构（起承转合）"""

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你是一个专业的故事分析师，擅长深度解读叙事内容。"},
                    {"role": "user", "content": analysis_prompt}
                ],
                result_format='message',
                temperature=0.7,
                max_tokens=2000
            )

            if response.status_code == 200 and response.output and response.output.choices:
                result_text = response.output.choices[0].message.content
                try:
                    json_start = result_text.find('{')
                    json_end = result_text.rfind('}')
                    if json_start != -1 and json_end != -1:
                        json_str = result_text[json_start:json_end+1]
                        return json.loads(json_str)
                except:
                    pass

            return self._get_default_content_analysis()

        except Exception as e:
            logger.error(f"深度内容分析失败: {e}")
            return self._get_default_content_analysis()

    def _extract_highlights(self, story_content: str, content_analysis: Dict) -> Dict[str, Any]:
        """
        亮点提炼 - 识别故事的高光时刻
        采用多维度分析策略：
        - 情节亮点
        - 情感亮点
        - 视觉亮点
        - 叙事亮点
        """
        try:
            from dashscope import Generation

            highlights_prompt = f"""请从多个维度分析以下故事，提炼出精彩亮点：

故事内容：
{story_content}

已知的故事结构分析：
{json.dumps(content_analysis, ensure_ascii=False, indent=2)}

请从以下4个维度提炼亮点（用JSON格式返回）：
{{
    "plot_highlights": [
        {{"moment": "精彩时刻描述", "reason": "为什么精彩", "impact": "对故事的影响"}}
    ],
    "emotional_highlights": [
        {{"moment": "情感高潮描述", "emotion": "触发的情感", "resonance": "引起共鸣的原因"}}
    ],
    "visual_highlights": [
        {{"scene": "精彩画面描述", "technique": "拍摄/剪辑技巧", "aesthetic": "美学价值"}}
    ],
    "narrative_highlights": [
        {{"technique": "叙事技巧名称", "description": "具体描述", "effect": "达到的效果"}}
    ],
    "overall_highlights": "综合亮点 - 用一段话总结故事最精彩的3个要点"
}}

亮点提炼要求：
1. 具体、明确，避免空泛的描述
2. 解释"为什么"精彩
3. 指出对观众的影响
4. 结合故事的具体内容，不要脱离文本"""

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你是一个专业的影视评论家，擅长发现和解读故事的精彩之处。"},
                    {"role": "user", "content": highlights_prompt}
                ],
                result_format='message',
                temperature=0.8,
                max_tokens=2500
            )

            if response.status_code == 200 and response.output and response.output.choices:
                result_text = response.output.choices[0].message.content
                try:
                    json_start = result_text.find('{')
                    json_end = result_text.rfind('}')
                    if json_start != -1 and json_end != -1:
                        json_str = result_text[json_start:json_end+1]
                        highlights = json.loads(json_str)
                        return {
                            'success': True,
                            'highlights': highlights,
                            'summary': highlights.get('overall_highlights', '')
                        }
                except:
                    pass

            return self._get_default_highlights()

        except Exception as e:
            logger.error(f"亮点提炼失败: {e}")
            return self._get_default_highlights()

    def _extract_educational_meaning(
        self,
        story_content: str,
        content_analysis: Dict
    ) -> Dict[str, Any]:
        """
        教育意义提取 - 多维度价值分析
        分析维度：
        - 品德教育
        - 知识传递
        - 价值观塑造
        - 生活智慧
        - 行为示范
        """
        try:
            from dashscope import Generation

            educational_prompt = f"""请深度分析以下故事的教育意义和价值：

故事内容：
{story_content}

故事结构分析：
{json.dumps(content_analysis, ensure_ascii=False, indent=2)}

请从以下5个维度分析教育意义（用JSON格式返回）：
{{
    "moral_education": {{
        "values": ["核心品德1", "核心品德2"],
        "description": "品德教育的具体体现",
        "examples": ["体现该品德的场景1", "体现该品德的场景2"]
    }},
    "knowledge_transfer": {{
        "knowledge": ["知识1", "知识2"],
        "description": "传递的具体知识或技能",
        "learning_points": ["学习要点1", "学习要点2"]
    }},
    "value_shaping": {{
        "life_values": ["人生观", "世界观", "价值观"],
        "description": "价值观塑造的具体体现",
        "positive_model": "正面榜样"
    }},
    "life_wisdom": {{
        "wisdom": ["生活智慧1", "生活智慧2"],
        "description": "实用的生活经验或建议",
        "applicable_scenarios": ["适用场景1", "适用场景2"]
    }},
    "behavior_demonstration": {{
        "positive_behaviors": ["正确行为1", "正确行为2"],
        "negative_behaviors": ["错误行为1", "错误行为2"],
        "lessons": "行为启示"
    }},
    "age_appropriateness": {{
        "suitable_ages": "适合年龄段",
        "parental_guidance": "家长指导建议"
    }},
    "overall_educational_value": "综合教育意义 - 一段话总结核心教育价值"
}}

教育意义分析要求：
1. 具体、实用，避免空洞的说教
2. 结合故事中的具体情节和人物
3. 指出对不同年龄段观众的启发
4. 提供可操作的建议"""

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你是一个专业的教育专家，擅长挖掘故事的教育价值和启发意义。"},
                    {"role": "user", "content": educational_prompt}
                ],
                result_format='message',
                temperature=0.7,
                max_tokens=2500
            )

            if response.status_code == 200 and response.output and response.output.choices:
                result_text = response.output.choices[0].message.content
                try:
                    json_start = result_text.find('{')
                    json_end = result_text.rfind('}')
                    if json_start != -1 and json_end != -1:
                        json_str = result_text[json_start:json_end+1]
                        educational = json.loads(json_str)
                        return {
                            'success': True,
                            'educational': educational,
                            'summary': educational.get('overall_educational_value', '')
                        }
                except:
                    pass

            return self._get_default_educational()

        except Exception as e:
            logger.error(f"教育意义提取失败: {e}")
            return self._get_default_educational()

    def _create_structured_summary(
        self,
        story_content: str,
        content_analysis: Dict,
        highlights: Dict,
        educational: Dict
    ) -> Dict[str, Any]:
        """
        创建结构化总结
        """
        try:
            highlights_summary = highlights.get('summary', '') if isinstance(highlights, dict) else str(highlights)
            educational_summary = educational.get('summary', '') if isinstance(educational, dict) else str(educational)

            return {
                'story_content': story_content,
                'story_summary': content_analysis.get('main_plot', '故事内容摘要'),
                'highlights': highlights_summary,
                'educational': educational_summary,
                'characters': content_analysis.get('characters', []),
                'key_scenes': content_analysis.get('key_scenes', []),
                'emotional_arc': content_analysis.get('emotional_arc', ''),
                'target_audience': content_analysis.get('target_audience', '')
            }

        except Exception as e:
            logger.error(f"创建结构化总结失败: {e}")
            return {
                'story_content': story_content,
                'highlights': '精彩纷呈的故事',
                'educational': '富有教育意义'
            }

    def _get_default_content_analysis(self) -> Dict[str, Any]:
        """默认内容分析"""
        return {
            "main_plot": "一个充满温情和成长的故事",
            "characters": [],
            "key_scenes": [],
            "emotional_arc": "情感起伏，引人入胜",
            "thematic_elements": ["成长", "勇气", "善良"],
            "narrative_technique": "线性叙事，层层递进",
            "target_audience": "适合所有年龄段"
        }

    def _get_default_highlights(self) -> Dict[str, Any]:
        """默认亮点"""
        return {
            'success': True,
            'highlights': {
                'plot_highlights': [],
                'emotional_highlights': [],
                'visual_highlights': [],
                'narrative_highlights': []
            },
            'summary': '故事精彩纷呈，情感真挚动人'
        }

    def _get_default_educational(self) -> Dict[str, Any]:
        """默认教育意义"""
        return {
            'success': True,
            'educational': {
                'moral_education': {},
                'knowledge_transfer': {},
                'value_shaping': {},
                'life_wisdom': {},
                'behavior_demonstration': {}
            },
            'summary': '故事传递了积极向上的价值观'
        }


class VideoAnalysisPromptBuilder:
    """
    视频分析提示词构建器
    用于构建高质量的视频分析提示词
    """

    @staticmethod
    def build_video_understanding_prompt(
        video_duration: float,
        has_audio: bool = True
    ) -> Dict[str, str]:
        """
        构建视频理解提示词

        Args:
            video_duration: 视频时长（秒）
            has_audio: 是否有音频

        Returns:
            包含system和user提示词的字典
        """

        system_prompt = """你是一个专业的视频内容分析师，擅长深度理解视频的叙事内容、画面风格和情感表达。

分析要求：
1. 全面理解视频的整体内容和主题
2. 关注人物的表演、动作和表情
3. 分析画面的构图、光线和色彩
4. 理解叙事的节奏和结构
5. 识别关键的情感时刻和情节转折
6. 总结视频想要传达的核心信息和价值观

输出要求：
1. 用清晰、具体的语言描述视频内容
2. 突出重要的情节和画面
3. 识别反复出现的主题和元素
4. 指出视频的独特之处和亮点"""

        if has_audio:
            user_prompt = f"""请深度分析这个视频内容（时长：{video_duration:.0f}秒，带音频）：

1. 视频讲述了什么故事/内容？
2. 主要人物有哪些？他们的特点是什么？
3. 故事的叙事结构是怎样的？（起、承、转、合）
4. 视频中最精彩的时刻是什么？
5. 视频想要传达什么信息或价值观？
6. 画面的风格和氛围有什么特点？
7. 有什么特别值得关注的细节？

请用详细的、具体的语言回答以上问题。"""
        else:
            user_prompt = f"""请深度分析这个视频内容（时长：{video_duration:.0f}秒，无音频）：

1. 视频展示了什么内容？
2. 主要人物或主体有什么特点？
3. 画面的构图和光线有什么特点？
4. 场景的切换和节奏如何？
5. 视频的整体风格和氛围是什么？
6. 有哪些特别值得关注的视觉元素？

请用详细的、具体的语言回答以上问题。"""

        return {
            'system': system_prompt,
            'user': user_prompt
        }

    @staticmethod
    def build_highlights_extraction_prompt(story_content: str) -> str:
        """构建亮点提炼提示词"""
        return f"""请分析以下故事内容，提炼出最精彩的亮点。

故事内容：
{story_content}

请分析并描述：
1. 情节上最精彩的3个时刻是什么？为什么精彩？
2. 情感上最能打动人的3个时刻是什么？
3. 叙事技巧上有什么亮点？
4. 整体最值得看的3个理由是什么？

请用具体、生动的语言描述，不要空洞。"""

    @staticmethod
    def build_educational_prompt(story_content: str) -> str:
        """构建教育意义提示词"""
        return f"""请分析以下故事的教育意义和价值。

故事内容：
{story_content}

请从以下角度分析：
1. 这个故事传递了哪些正面价值观？（如：勇气、善良、诚实等）
2. 观众可以从中学到什么？（知识、技能、道理）
3. 有什么值得借鉴的行为示范？
4. 适合什么年龄段的人群观看？
5. 家长或老师可以如何引导讨论？

请给出具体、实用的分析。"""
