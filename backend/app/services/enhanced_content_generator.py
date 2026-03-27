"""
增强版内容生成服务
基于原故事进行创新，保留亮点和教育意义
"""

import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class EnhancedContentGenerator:
    """
    增强版内容生成器
    核心功能：
    1. 基于原故事创新 - 让故事更吸引人、情节更完善
    2. 保留亮点和教育意义 - 大方向一致，可以略有调整
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or "sk-5eeb025e53df459b9f8a4b4209bd5fa5"
        import dashscope
        dashscope.api_key = self.api_key

    def generate_enhanced_story(
        self,
        original_analysis: Dict[str, Any],
        highlights: str,
        educational: str
    ) -> Dict[str, Any]:
        """
        生成增强版新故事

        Args:
            original_analysis: 原视频的结构化分析结果
            highlights: 原故事亮点
            educational: 原故事教育意义

        Returns:
            包含新故事、扩展的亮点和教育意义的字典
        """
        try:
            # 第一步：基于原分析生成创新故事
            new_story = self._generate_innovative_story(
                original_analysis=original_analysis,
                highlights=highlights,
                educational=educational
            )

            # 第二步：扩展亮点（保留核心，保持创新）
            expanded_highlights = self._expand_highlights_preserving_core(
                original_highlights=highlights,
                new_story=new_story
            )

            # 第三步：扩展教育意义（保留核心，大方向一致）
            expanded_educational = self._expand_educational_preserving_core(
                original_educational=educational,
                new_story=new_story
            )

            return {
                'success': True,
                'new_story': new_story,
                'highlights': expanded_highlights,
                'educational': expanded_educational
            }

        except Exception as e:
            logger.error(f"生成增强版故事失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def _generate_innovative_story(
        self,
        original_analysis: Dict[str, Any],
        highlights: str,
        educational: str
    ) -> str:
        """
        生成创新故事
        在保留核心主题的基础上，让故事更吸引人
        """
        try:
            from dashscope import Generation

            main_plot = original_analysis.get('main_plot', '')
            characters = original_analysis.get('characters', [])
            emotional_arc = original_analysis.get('emotional_arc', '')
            thematic_elements = original_analysis.get('thematic_elements', [])

            characters_str = json.dumps(characters, ensure_ascii=False, indent=2)

            story_prompt = f"""你是一个专业的故事创作者。请基于以下原故事分析，创作一个全新的、更吸引人的故事版本。

【原故事分析】
主情节：{main_plot}
情感曲线：{emotional_arc}
主题元素：{', '.join(thematic_elements)}

【必须保留的元素 - 这些是故事的核心，不能改变】
人物设定：{characters_str}
核心亮点：{highlights}
核心教育意义：{educational}

【创作要求】
1. 保留原故事的核心主题和价值观
2. 保留人物的基本设定和性格特点
3. 可以对情节进行创新：
   - 增加情节的起伏和张力
   - 丰富故事的情感层次
   - 添加更吸引人的叙事技巧
   - 完善故事的逻辑和结构
4. 语言要生动、流畅、有画面感
5. 长度：800-1200字
6. 故事要有头有尾，结构完整

请直接输出新故事内容，不要加标题或说明。"""

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你是一个专业的故事创作者，擅长创作引人入胜的故事。"},
                    {"role": "user", "content": story_prompt}
                ],
                result_format='message',
                temperature=0.85,
                max_tokens=3000
            )

            if response.status_code == 200 and response.output and response.output.choices:
                return response.output.choices[0].message.content

            return f"一个关于{main_plot}的精彩故事..."

        except Exception as e:
            logger.error(f"生成创新故事失败: {e}")
            return f"一个精彩的故事..."

    def _expand_highlights_preserving_core(
        self,
        original_highlights: str,
        new_story: str
    ) -> Dict[str, Any]:
        """
        扩展亮点 - 保留核心亮点，进行创新扩展
        """
        try:
            from dashscope import Generation

            highlights_prompt = f"""请分析以下新故事，提炼出精彩的亮点。

新故事：
{new_story}

【必须参考的原故事亮点 - 这些核心亮点需要在新版本中保留或体现】
{original_highlights}

【提炼要求】
1. 分析新故事中的精彩时刻
2. 确保原故事的核心亮点在新故事中得到保留或更好的体现
3. 可以发现新故事独有的新亮点
4. 从以下维度提炼：
   - 情节亮点（最精彩的3个时刻）
   - 情感亮点（最能打动人的时刻）
   - 叙事亮点（讲述技巧的亮点）

请用JSON格式返回：
{{
    "preserved_highlights": ["保留的原故事亮点1", "保留的原故事亮点2"],
    "new_highlights": ["新故事的创新亮点1", "创新亮点2"],
    "combined_highlights": "综合亮点 - 一段话总结新故事最精彩的3个要点"
}}"""

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你是一个专业的故事评论家，擅长发现故事的精彩亮点。"},
                    {"role": "user", "content": highlights_prompt}
                ],
                result_format='message',
                temperature=0.8,
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

            return {
                'preserved_highlights': [original_highlights],
                'new_highlights': ['故事情节更加丰富'],
                'combined_highlights': original_highlights
            }

        except Exception as e:
            logger.error(f"扩展亮点失败: {e}")
            return {
                'preserved_highlights': [original_highlights],
                'new_highlights': [],
                'combined_highlights': original_highlights
            }

    def _expand_educational_preserving_core(
        self,
        original_educational: str,
        new_story: str
    ) -> Dict[str, Any]:
        """
        扩展教育意义 - 保留核心教育方向，进行深化扩展
        """
        try:
            from dashscope import Generation

            educational_prompt = f"""请分析以下新故事的教育意义。

新故事：
{new_story}

【必须保留的原故事教育意义 - 这些核心教育方向需要保持一致】
{original_educational}

【分析要求】
1. 确保原故事的核心教育意义在新故事中得到体现
2. 可以发现新故事更深层次的教育价值
3. 从以下维度分析：
   - 品德教育（核心价值观）
   - 知识传递（可以学到什么）
   - 生活智慧（实用的启示）
   - 行为示范（正确的行为方式）

请用JSON格式返回：
{{
    "preserved_educational": "保留的原故事核心教育意义",
    "new_educational": "新故事的创新教育价值",
    "combined_educational": "综合教育意义 - 一段话总结核心教育价值",
    "age_recommendation": "适合的年龄段"
}}"""

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你是一个专业的教育专家，擅长挖掘故事的教育价值。"},
                    {"role": "user", "content": educational_prompt}
                ],
                result_format='message',
                temperature=0.8,
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

            return {
                'preserved_educational': original_educational,
                'new_educational': '新故事传递了积极的价值观',
                'combined_educational': original_educational,
                'age_recommendation': '适合所有年龄段'
            }

        except Exception as e:
            logger.error(f"扩展教育意义失败: {e}")
            return {
                'preserved_educational': original_educational,
                'new_educational': '新故事传递了积极的价值观',
                'combined_educational': original_educational,
                'age_recommendation': '适合所有年龄段'
            }


class StoryInnovationStrategies:
    """
    故事创新策略
    提供多种创新方向供选择
    """

    @staticmethod
    def get_innovation_strategies() -> Dict[str, str]:
        """获取可用的创新策略"""
        return {
            "more_dramatic": """
创新方向：增强戏剧性
- 增加情节冲突和张力
- 添加悬念和反转
- 加快叙事节奏
- 强化情感高潮
""",
            "more_emotional": """
创新方向：深化情感
- 增强人物情感表达
- 添加温情感人时刻
- 深化人物内心世界
- 增强观众共鸣
""",
            "more_educational": """
创新方向：强化教育性
- 融入更多生活智慧
- 添加行为示范
- 强化价值观传递
- 增加启发性思考
""",
            "more_interesting": """
创新方向：增加趣味性
- 添加幽默元素
- 使用更生动的语言
- 创造有趣的细节
- 增加互动性
""",
            "more_complete": """
创新方向：完善结构
- 补充故事背景
- 丰富人物设定
- 完善情节逻辑
- 增强结局意义
"""
        }

    @staticmethod
    def build_custom_innovation_prompt(
        original_analysis: Dict,
        strategies: List[str],
        custom_requirements: str = ""
    ) -> str:
        """
        构建自定义创新提示词

        Args:
            original_analysis: 原故事分析
            strategies: 选中的创新策略列表
            custom_requirements: 自定义需求
        """
        strategy_descriptions = []
        for strategy in strategies:
            if strategy in StoryInnovationStrategies.get_innovation_strategies():
                strategy_descriptions.append(
                    StoryInnovationStrategies.get_innovation_strategies()[strategy]
                )

        strategies_text = "\n".join(strategy_descriptions)

        return f"""请基于以下原故事进行创新改编：

【原故事分析】
主情节：{original_analysis.get('main_plot', '')}
人物设定：{json.dumps(original_analysis.get('characters', []), ensure_ascii=False)}
情感曲线：{original_analysis.get('emotional_arc', '')}

【选择的创新方向】
{strategies_text}

【自定义需求】
{custom_requirements}

【创作要求】
1. 保留原故事的核心主题和价值观
2. 按照选择的创新方向进行改编
3. 确保故事结构完整、逻辑通顺
4. 语言生动、有画面感
5. 长度：800-1200字"""
