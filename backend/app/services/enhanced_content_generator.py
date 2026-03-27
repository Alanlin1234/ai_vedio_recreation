"""
增强版内容生成服务（故事编剧 Agent）

教育专家已提供：原视频内容理解、故事亮点、教育意义。
故事编剧仅以「教育理念」为硬锚点；须在全新叙事骨架上创作。
须根据原素材体裁匹配语言（儿童活泼、科普严谨等）；禁止「换物种不换剧情」式换皮。
"""

import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class EnhancedContentGenerator:
    """
    故事编剧（二创）：输入为教育专家产出的亮点与教育意义。
    锚点：仅「教育理念 / 价值观内核」必须一脉相承或深化。
    叙事：全新骨架；文体与语气随素材而变；禁止寓言换皮（如仅小猫改刺猬、同一「种错东西」套路）。
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or "sk-5eeb025e53df459b9f8a4b4209bd5fa5"
        import dashscope
        dashscope.api_key = self.api_key

    def generate_enhanced_story(
        self,
        original_analysis: Dict[str, Any],
        highlights: str,
        educational: str,
        creator_notes: str = '',
        full_story_text: str = '',
    ) -> Dict[str, Any]:
        """
        生成二创新故事（故事编剧）

        Args:
            original_analysis: 原视频内容梗概（教育专家提取）
            highlights: 原故事亮点（可作灵感，非硬性约束）
            educational: 原故事教育意义（核心锚点）
            creator_notes: 用户「片子说明」，影响体裁与语气
            full_story_text: 原视频理解全文，用于判断儿童/科普等文体

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
                creator_notes=creator_notes,
                full_story_text=full_story_text,
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
        creator_notes: str = '',
        full_story_text: str = '',
    ) -> str:
        """
        二创新故事：仅以教育理念为锚；禁止换皮；文体与语气随素材变化。
        """
        try:
            from dashscope import Generation

            main_plot = original_analysis.get('main_plot', '')
            characters = original_analysis.get('characters', [])
            emotional_arc = original_analysis.get('emotional_arc', '')
            thematic_elements = original_analysis.get('thematic_elements', [])

            characters_str = json.dumps(characters, ensure_ascii=False, indent=2) if characters else '（原素材未单独列出人物）'

            source_for_tone = (full_story_text or main_plot or '').strip()
            source_for_tone = source_for_tone[:8000]
            notes = (creator_notes or '').strip()[:4000]

            story_prompt = f"""你是「影坊」项目的二创故事编剧。交付物必须是**全新故事**：读者不能说「只是把原片换了个动物/换了个名字」。

━━━━━━━━━━━━━━━━
【唯一硬锚点——教育理念（只保留抽象内核，可换一切具体情节）】
{educational}
━━━━━━━━━━━━━━━━

【文体与语言（必须遵守）】
请先根据下方「原素材全文」与「用户片子说明」判断**体裁与受众**，再据此写作（在正文里自然体现，不要单独列出判断）：
- **儿童向 / 童话、绘本感**：句子短、口语化、节奏轻快，可重复与叠句，**避免**成人化长句与学术腔。
- **科普向 / 知识讲解**：概念准确、逻辑清晰，可用「首先/其次」；**避免**过度拟人化童话腔；比喻要贴切。
- **生活叙事 / 纪实感**：细节真实、对话自然；语气随题材可幽默或克制。
- 若用户「片子说明」明确指定风格或受众，**以用户为准**。

【可读性与主题（硬性）】
1. 全文必须让读者**一眼看出核心主题**（如「诚实」「合作」「面对失败」）：在**开头或结尾**用**一两句直白话**点题，不要藏隐喻。
2. **禁止「文绉绉」**：少用对偶、堆砌形容词、玄学比喻；**禁止**写成散文诗或论文摘要。
3. **对话与互动优先**：正文里**至少约三分之一到一半**应为**直接引语（对话）**或人物之间的互动回合；多写「谁对谁说、怎么回应」，少写独白式景物。**禁止**用大块环境描写、景物铺陈凑字数；环境最多一两笔带过，能听懂即可。
4. 优先推进：**动作 + 对话** 交替推动情节；文采服从于「谁说了什么、做了什么」。
5. 叙事节奏：铺垫→冲突→解决要清楚，不要炫技绕弯。

【明确禁止——「换皮」式假创新（不合格）】
1. **禁止仅替换物种/角色名**而保留同一套经典寓言骨架。例如：原作为「小猫种鱼」类结构，则**禁止**写成「小刺猬种鱼」「小兔子种鱼」等——仍是「错误认知→同一种幽默反转」，属于换皮。
2. **禁止保留同一「核心乌龙类型」**：若原作是「把 A 当成 B 来种/养」的单一误会模型，新故事必须改用**完全不同的冲突类型**（例如：改为「合作验证」「时间延迟」「求助权威」「实验对照」「规则博弈」等），只保留抽象教育命题（如「尊重规律」），**不**复刻同一误会模型。
3. **禁止同构改写**：不得保留与原梗概同一套主线因果顺序；禁止「同一剧情模板 + 微调」。
4. 原片人物名、场景顺序若照搬或轻微替换，视为不合格。

【必须做到（创新硬性要求）】
1. **新叙事骨架**：新的核心冲突与情节走向；没看过原片的人无法反推原剧情。
2. **至少两项明显脱钩**：时空、体裁外壳、主角身份、对立关系、解决方式等中任选**不少于两项**与原作拉开距离（正文里站得住脚）。
3. **亮点与梗概**：仅作灵感；若化用只能是主题神似，**不得**复刻桥段链。
4. **800–1500 字**，结构完整；语言符合上文文体要求；**以对话与互动带戏**，不要用长段写景代替剧情。

【用户片子说明（若有）——优先影响体裁与语气】
{notes if notes else '（用户未填写）'}

【原素材全文——用于判断文体与语气；不是故事大纲，禁止复述其情节链】
{source_for_tone if source_for_tone else '（无）'}

【补充线索（勿当大纲复述）】
· 梗概摘要（勿当成文主线）：{main_plot[:1200] if main_plot else '（无）'}
· 情感线索：{emotional_arc}
· 主题元素：{', '.join(thematic_elements) if thematic_elements else '（未单列）'}
· 人物线索：{characters_str}

【原故事亮点（可选）】
{highlights}

请**直接输出新故事正文**，不要标题、不要创作说明、不要列出与原作差异清单。"""

            if debug_prompts is not None:
                from app.utils.prompt_trace import trace

                debug_prompts.append(
                    trace(
                        'story_writer',
                        '二创新故事',
                        system='资深二创编剧：理念为锚、全新骨架；多对话互动、少写景；主题显豁。',
                        user=story_prompt,
                        model='qwen-plus-latest',
                    )
                )

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {
                        "role": "system",
                        "content": "你是资深二创编剧。锚定教育理念；全新骨架；多写对话与人物互动，少写景与文采；主题清楚；禁止换皮。",
                    },
                    {"role": "user", "content": story_prompt},
                ],
                result_format='message',
                temperature=0.72,
                max_tokens=3500,
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

            highlights_prompt = f"""请分析以下「二创」新故事，写**观众能看懂的**亮点（可与原素材精神呼应，不必字面相同）。

新故事：
{new_story}

【原素材侧的故事亮点（供对照）】
{original_highlights}

【语言要求】
- 像短视频文案：具体、好懂；**禁止**隐喻堆砌、学术名词、玄学形容词。
- combined_highlights 格式：**第一行**写「主题：……」（一句话点明本片讲什么）；**换行**后写「1. … 2. … 3. …」三条，每条≤40字，必须是**具体情节或看点**。

【提炼要求】
1. preserved_highlights：若与新作有呼应，用**人话**一句说明；无明显呼应可写「无」
2. new_highlights：2～4 条短句，写**独有看点**（冲突、反转、人物）
3. combined_highlights：总字数约 120～220 字

请用JSON格式返回：
{{
    "preserved_highlights": ["与原作亮点精神呼应处（如有）"],
    "new_highlights": ["新故事的创新亮点1", "创新亮点2"],
    "combined_highlights": "按上文格式：主题行 + 三条编号要点"
}}"""

            if debug_prompts is not None:
                from app.utils.prompt_trace import trace

                debug_prompts.append(
                    trace(
                        'story_writer',
                        '扩展亮点总结',
                        system='你写看点像给朋友安利：主题一句+三条具体理由，禁止拽文。',
                        user=highlights_prompt,
                        model='qwen-plus-latest',
                    )
                )

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你写看点：主题清楚、三条具体，禁止文绉绉。"},
                    {"role": "user", "content": highlights_prompt},
                ],
                result_format='message',
                temperature=0.5,
                max_tokens=2000,
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

            educational_prompt = f"""请分析以下二创新故事的教育意义，并与「教育专家」给出的原教育意义对照。**写给家长一眼能懂**。

新故事：
{new_story}

【原视频侧的教育意义（锚点）】
{original_educational}

【语言要求】
- **禁止**随意引用教育心理学理论名词（如皮亚杰等）卖弄；用**大白话**。
- combined_educational：**2～4 句短句**，第一句说明「新故事落实了哪条原教育意义」，后面写孩子/观众能带走的一两条**具体启发**；总字数约 80～200 字。

【分析要求】
1. preserved_educational：说明新故事如何承接原教育意义（有情节依据，忌空话）
2. new_educational：若有额外启发再写，没有则写「无」
3. 落脚点应是**可讨论、可模仿**的，不是抽象哲理

请用JSON格式返回：
{{
    "preserved_educational": "对原教育意义核心内核的延续说明（白话）",
    "new_educational": "额外教育价值或写「无」",
    "combined_educational": "综合教育意义：2～4句白话，有重点",
    "age_recommendation": "适合的年龄段"
}}"""

            if debug_prompts is not None:
                from app.utils.prompt_trace import trace

                debug_prompts.append(
                    trace(
                        'story_writer',
                        '扩展教育意义',
                        system='你写教育意义：对照原锚点、白话、可落地，禁止学术腔。',
                        user=educational_prompt,
                        model='qwen-plus-latest',
                    )
                )

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "核对二创是否锚定原教育意义；综合句必须白话、具体。"},
                    {"role": "user", "content": educational_prompt},
                ],
                result_format='message',
                temperature=0.5,
                max_tokens=2000,
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
