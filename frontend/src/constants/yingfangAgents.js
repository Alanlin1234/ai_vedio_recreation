/**
 * 影坊多 Agent 系统 — 与后端 `app.agents.yingfang_system.YINGFANG_AGENTS` 对齐
 * id 用于 Workspace 状态机；nameZh 用于展示
 */
export const YINGFANG_AGENTS = [
  {
    id: 'education_expert',
    nameZh: '教育专家',
    description: '从原视频提取内容梗概、故事亮点与教育意义，交给后续环节',
  },
  {
    id: 'reviewer',
    nameZh: '审核专员',
    description: '结合你的片子说明与解析结果，从内容、画风、叙事与二创潜力等维度打分并判断是否准入',
  },
  {
    id: 'story_writer',
    nameZh: '故事编剧',
    description: '二创核心：以原教育意义为锚，人物与剧情可大改，写出全新故事',
  },
  {
    id: 'storyboard',
    nameZh: '分镜导演',
    description: '智能规划镜头数量；每镜约5秒，并生成分镜图与图生视频提示词',
  },
  {
    id: 'video_generator',
    nameZh: '视频生成',
    description: '以分镜图为参考，按分镜提示词逐场景生成视频',
  },
  {
    id: 'video_composer',
    nameZh: '视频合成',
    description: '剪辑师：按顺序拼接各段场景视频并导出成片',
  },
]

export function getYingfangAgentName(agentId, t) {
  if (typeof t === 'function') {
    const key = `agents.${agentId}.name`
    const label = t(key)
    return label === key ? agentId : label
  }
  const a = YINGFANG_AGENTS.find((x) => x.id === agentId)
  return a ? a.nameZh : agentId
}
