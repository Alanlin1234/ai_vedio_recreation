"""
增强版内容生成服务（故事编剧 Agent）

教育专家已提供：原视频内容理解、故事亮点、教育意义。
故事编剧仅以「教育理念」为硬锚点；须在全新叙事骨架上创作，避免同构改写或「换人称式优化」。
原梗概与亮点置于末段作参照，防止模型复述原剧情线。
"""

import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class EnhancedContentGenerator:
    """
    故事编剧（二创）：输入为教育专家产出的亮点与教育意义。
    锚点：仅「教育理念 / 价值观内核」必须一脉相承或深化。
    叙事：要求全新故事骨架，禁止在原作情节线上做换人称、扩场景式「优化」。
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
        二创新故事：仅以教育理念为锚；情节、人物、时空须与原作明显脱钩，建立新叙事骨架。
        """
        try:
            from dashscope import Generation

            main_plot = original_analysis.get('main_plot', '')
            characters = original_analysis.get('characters', [])
            emotional_arc = original_analysis.get('emotional_arc', '')
            thematic_elements = original_analysis.get('thematic_elements', [])

            characters_str = json.dumps(characters, ensure_ascii=False, indent=2) if characters else '（原素材未单独列出人物）'

            story_prompt = f"""你是「影坊」项目的二创故事编剧。你的交付物必须是**一篇读者读完后不会说「这只是把原片换了个说法」的新故事**——可以借原素材的**主题气质**，但**禁止**在原故事线上做「换人称、加细节、微调结局」式的改写。

━━━━━━━━━━━━━━━━
【唯一硬锚点——教育理念（只保留这个，其余全部可抛弃）】
以下是你必须贯穿到底的价值观与教育命题；成文须让读者明确感受到这一内核（可换人物与情节来呈现）：
{educational}
━━━━━━━━━━━━━━━━

【明确禁止（违反任一条即视为不合格）】
1. **禁止同构改写**：不得保留与原梗概「同一套主线因果」——例如同一组核心矛盾按同样顺序发生、仅换叙述者或略改台词/场景。
2. **禁止「优化式二创」**：禁止写成「同一故事的丰富版 / 导演剪辑版」；禁止让读者一眼看出与原片是同一剧情模板。
3. **禁止过度贴合原设定**：原片的人物名、具体职业组合、标志性场景顺序若照搬或仅做轻微替换，视为不合格。

【必须做到（创新硬性要求）】
1. **新叙事骨架**：建立**新的核心冲突**与**新的情节走向**（起承转合可与原作完全不同）；未看过原片的人，不应能从情节上反推原片剧情。
2. **至少两项「明显脱钩」**：从下面维度中任选**不少于两项**与原作拉开距离——**时空**（古今/虚实/异域）、**体裁外壳**（寓言、科幻、童话、职场、校园、奇幻等）、**主角身份与目标**、**对立关系性质**（人与环境/人与自我/群体与群体等）、**高潮解决方式**。在正文中要站得住脚，不是标签堆砌。
3. **亮点与梗概**：原亮点、原梗概**只作灵感与反例参照**——可完全不用；若化用，只能是「神似」的主题回响，不得复刻桥段链条。
4. 语言生动、有画面感，**800–1500 字**，结构完整有头有尾。

【原视频侧素材（排在最后 intentionally：防止你复述它）】
——下列内容用于理解「原作在讲什么」，**不是**你的故事大纲。请从中**不要**复用具体情节链与人物关系模板。
· 主情节摘要（勿复述为成文主线）：{main_plot}
· 情感线索（勿照搬）：{emotional_arc}
· 主题元素（可抽象继承，勿逐条落实成同一故事）：{', '.join(thematic_elements) if thematic_elements else '（未单列）'}
· 人物/设定线索（可全部废弃）：{characters_str}

【原故事亮点（可选灵感，非义务）】
{highlights}

请**直接输出新故事正文**，不要标题、不要创作说明、不要列出「与原作不同点」的清单。"""

            if debug_prompts is not None:
                from app.utils.prompt_trace import trace

                debug_prompts.append(
                    trace(
                        'story_writer',
                        '二创新故事',
                        system='你是资深二创编剧：只锚定教育理念，拒绝同构改写；擅长借全新叙事骨架与类型外壳完成大胆创新。',
                        user=story_prompt,
                        model='qwen-plus-latest',
                    )
                )

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {
                        "role": "system",
                        "content": "你是资深二创编剧。你只保留「教育理念」这一锚点；必须在全新故事骨架上创作，拒绝换人称、扩写场景式的伪创新。若输出读起来仍像原片的改写版，你会推翻重写。",
                    },
                    {"role": "user", "content": story_prompt},
                ],
                result_format='message',
                temperature=0.96,
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
