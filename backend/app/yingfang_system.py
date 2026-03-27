"""
影坊多 Agent 系统（Yingfang Multi-Agent System）

将 Pipeline 各阶段映射为六个具名 Agent，与前端 `YINGFANG_AGENTS` 的 id 一一对应：
education_expert、reviewer、story_writer、storyboard、video_generator、video_composer。

本模块置于 app 包根下，避免 `import app.agents` 时加载可选/遗留 Agent 依赖。

上传（upload）由网关/路由直接处理，不绑定独立 Agent；导出与拼接同属 video_composer 职责延伸。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class YingfangAgentMeta:
    """单个影坊 Agent 的元数据。"""

    id: str
    name_zh: str
    description: str
    step_keys: Tuple[str, ...]


# 展示顺序即协作顺序（与前端侧栏一致）
YINGFANG_AGENTS: Tuple[YingfangAgentMeta, ...] = (
    YingfangAgentMeta(
        id='education_expert',
        name_zh='教育专家',
        description='从原视频中提取：内容梗概、故事亮点、教育意义，供后续编剧与审核使用',
        step_keys=('analyze',),
    ),
    YingfangAgentMeta(
        id='reviewer',
        name_zh='审核专员',
        description='结合片子说明与解析结果，从内容/画风/叙事等维度打分并判断是否适合二创',
        step_keys=('review',),
    ),
    YingfangAgentMeta(
        id='story_writer',
        name_zh='故事编剧',
        description='二创编剧：以教育专家给出的教育意义为核心锚点，人物与情节可大胆重构，实现真正的新故事',
        step_keys=('new_story',),
    ),
    YingfangAgentMeta(
        id='storyboard',
        name_zh='分镜导演',
        description='依据故事编剧剧本智能规划镜头数；每镜约5秒成片，并生成分镜图与视频提示词',
        step_keys=('storyboard',),
    ),
    YingfangAgentMeta(
        id='video_generator',
        name_zh='视频生成',
        description='以分镜图为输入、结合分镜提示词逐场景生成视频（每段约5秒）',
        step_keys=('scene_videos',),
    ),
    YingfangAgentMeta(
        id='video_composer',
        name_zh='视频合成',
        description='剪辑师：按顺序拼接各场景视频为成片，并支持导出',
        step_keys=('combine', 'export'),
    ),
)

# 流水线步骤 key → Agent id（upload 不绑定 Agent）
STEP_KEY_TO_AGENT_ID: Dict[str, Optional[str]] = {
    'upload': None,
    'analyze': 'education_expert',
    'review': 'reviewer',
    'new_story': 'story_writer',
    'storyboard': 'storyboard',
    'scene_videos': 'video_generator',
    'combine': 'video_composer',
    'export': 'video_composer',
}

_AGENT_IDS = {a.id for a in YINGFANG_AGENTS}


class YingfangMultiAgentSystem:
    """影坊多 Agent 系统入口：查询元数据、步骤与 Agent 的对应关系。"""

    agents: Tuple[YingfangAgentMeta, ...] = YINGFANG_AGENTS

    @classmethod
    def list_agents(cls) -> List[Dict[str, Any]]:
        """供 API 返回的序列化列表。"""
        out: List[Dict[str, Any]] = []
        for a in cls.agents:
            d = asdict(a)
            d['step_keys'] = list(a.step_keys)
            out.append(d)
        return out

    @classmethod
    def agent_id_for_step(cls, step_key: str) -> Optional[str]:
        return STEP_KEY_TO_AGENT_ID.get(step_key)

    @classmethod
    def validate_agent_id(cls, agent_id: str) -> bool:
        return agent_id in _AGENT_IDS
