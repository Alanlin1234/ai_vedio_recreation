"""
增强版内容生成服务（故事编剧 Agent）

教育专家已提供：原视频内容理解、故事亮点、教育意义。
故事编剧在本阶段以「教育意义」为锚点，可对人物、情节、叙事形式做大幅度二创；
亮点与原内容作为灵感来源，不要求逐句保留。
"""

import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class EnhancedContentGenerator:
    """
    故事编剧（二创）：输入为教育专家产出的亮点与教育意义。
    锚点：教育意义必须一脉相承或深化，不得背离。
    自由度：人物、冲突结构、时空与体裁均可大胆改写，以体现「二创」而非微调。
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
        生成二创新故事（故事编剧）

        Args:
            original_analysis: 原视频内容梗概（教育专家提取）
            highlights: 原故事亮点（可作灵感，非硬性约束）
            educational: 原故事教育意义（核心锚点）

        Returns:
            新故事正文，以及与新故事配套的亮点总结与教育意义表述
        """
        try:
            debug_prompts = []
            # 第一步：基于原分析生成创新故事
            new_story = self._generate_innovative_story(
                original_analysis=original_analysis,
                highlights=highlights,
                educational=educational,
                debug_prompts=debug_prompts,
            )

            # 第二步：扩展亮点（保留核心，保持创新）
            expanded_highlights = self._expand_highlights_preserving_core(
                original_highlights=highlights,
                new_story=new_story,
                debug_prompts=debug_prompts,
            )

            # 第三步：扩展教育意义（保留核心，大方向一致）
            expanded_educational = self._expand_educational_preserving_core(
                original_educational=educational,
                new_story=new_story,
                debug_prompts=debug_prompts,
            )

            return {
                'success': True,
                'new_story': new_story,
                'highlights': expanded_highlights,
                'educational': expanded_educational,
                'debug_prompts': debug_prompts,
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
        educational: str,
        debug_prompts: List[Dict[str, Any]] | None = None,
    ) -> str:
        """
        二创新故事：教育意义为锚，人物与剧情可大改。
        """
        try:
            from dashscope import Generation

            main_plot = original_analysis.get('main_plot', '')
            characters = original_analysis.get('characters', [])
            emotional_arc = original_analysis.get('emotional_arc', '')
            thematic_elements = original_analysis.get('thematic_elements', [])

            characters_str = json.dumps(characters, ensure_ascii=False, indent=2) if characters else '（原素材未单独列出人物，可从内容梗概中理解）'

            story_prompt = f"""你是「影坊」项目的二创故事编剧。上游「教育专家」已从原视频中提取素材，你的任务是写出一部**真正的新故事**（二创），而不是小幅润色。

【原视频内容梗概 / 叙事素材】
主情节摘要：{main_plot}
情感线索（若有）：{emotional_arc}
主题元素：{', '.join(thematic_elements) if thematic_elements else '（未单列）'}
可参考的人物/设定线索（仅作灵感，可完全推翻重写）：{characters_str}

【故事亮点（可作灵感，不必在成文中逐条对应）】
{highlights}

【核心锚点——教育意义（必须保留精神内核，可换表达与情节来呈现）】
{educational}

【二创自由度（重要）】
1. **必须守住**：成文必须体现与上述「教育意义」一致或更深化的价值观与启示；不得写成与之无关的另一主题。
2. **允许大胆改写**：人物姓名、身份、关系、时代背景、叙事结构、冲突设置、体裁（如从纪实感改为寓言/科幻外壳等）均可重写，只要服务于同一教育内核。
3. **亮点**：可化用、可升华，也可只保留「神似」；不必保留原视频的具体桥段。
4. 语言生动、有画面感，800–1500 字，结构完整有头有尾。

请直接输出新故事正文，不要标题或创作说明。"""

            if debug_prompts is not None:
                from app.utils.prompt_trace import trace

                debug_prompts.append(
                    trace(
                        'story_writer',
                        '二创新故事',
                        system='你是资深影视/短视频二创编剧，擅长在保留精神内核的前提下彻底重构人物与情节。',
                        user=story_prompt,
                        model='qwen-plus-latest',
                    )
                )

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {
                        "role": "system",
                        "content": "你是资深影视/短视频二创编剧，擅长在保留精神内核的前提下彻底重构人物与情节。",
                    },
                    {"role": "user", "content": story_prompt},
                ],
                result_format='message',
                temperature=0.92,
                max_tokens=3000,
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
        new_story: str,
        debug_prompts: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        """
        扩展亮点 - 保留核心亮点，进行创新扩展
        """
        try:
            from dashscope import Generation

            highlights_prompt = f"""请分析以下「二创」新故事，提炼亮点（可与原素材亮点精神呼应，不必字面相同）。

新故事：
{new_story}

【原素材侧的故事亮点（供对照，不必逐条保留）】
{original_highlights}

【提炼要求】
1. 突出新故事最精彩的情节与情感时刻
2. 若某处与原作亮点有呼应或升华，可在 preserved_highlights 中简要说明；否则可留空或写「精神呼应」
3. new_highlights 写新故事独有的看点
4. combined_highlights 用一段话概括新故事最抓人的 2–4 个要点

请用JSON格式返回：
{{
    "preserved_highlights": ["与原作亮点精神呼应处（如有）"],
    "new_highlights": ["新故事的创新亮点1", "创新亮点2"],
    "combined_highlights": "综合亮点 - 一段话总结"
}}"""

            if debug_prompts is not None:
                from app.utils.prompt_trace import trace

                debug_prompts.append(
                    trace(
                        'story_writer',
                        '扩展亮点总结',
                        system='你擅长总结二创故事看点，并说明与原作亮点的精神呼应（若有）。',
                        user=highlights_prompt,
                        model='qwen-plus-latest',
                    )
                )

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你擅长总结二创故事看点，并说明与原作亮点的精神呼应（若有）。"},
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
        new_story: str,
        debug_prompts: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        """
        扩展教育意义 - 保留核心教育方向，进行深化扩展
        """
        try:
            from dashscope import Generation

            educational_prompt = f"""请分析以下二创新故事的教育意义，并与「教育专家」给出的原教育意义对照。

新故事：
{new_story}

【原视频侧的教育意义（锚点，新故事应与之一致或深化）】
{original_educational}

【分析要求】
1. 说明新故事如何体现或深化上述教育意义（这是二创合法性的核心）
2. 可补充新故事带来的额外教育价值
3. 从品德/知识/生活智慧/行为示范等维度择要分析

请用JSON格式返回：
{{
    "preserved_educational": "对原教育意义核心内核的延续说明",
    "new_educational": "新故事带来的额外教育价值（如有）",
    "combined_educational": "综合教育意义 - 一段话总结",
    "age_recommendation": "适合的年龄段"
}}"""

            if debug_prompts is not None:
                from app.utils.prompt_trace import trace

                debug_prompts.append(
                    trace(
                        'story_writer',
                        '扩展教育意义',
                        system='你负责核对二创故事是否锚定原教育意义，并提炼综合表述。',
                        user=educational_prompt,
                        model='qwen-plus-latest',
                    )
                )

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你负责核对二创故事是否锚定原教育意义，并提炼综合表述。"},
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
