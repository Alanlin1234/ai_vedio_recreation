import { useMemo, useState } from 'react'
import { CaretDown, CaretRight, Trash } from '@phosphor-icons/react'
import { getYingfangAgentName } from '../constants/yingfangAgents'

function Block({ label, text }) {
  if (text == null || text === '') return null
  return (
    <div className="space-y-1">
      <div className="text-[11px] font-medium text-charcoal-400 uppercase tracking-wide">{label}</div>
      <pre className="text-xs leading-relaxed whitespace-pre-wrap break-words bg-charcoal-50 border border-charcoal-100 rounded-lg p-3 max-h-48 overflow-y-auto text-charcoal-700 font-mono">
        {typeof text === 'string' ? text : JSON.stringify(text, null, 2)}
      </pre>
    </div>
  )
}

export default function PromptDebugPanel({ entries, onClear }) {
  const [open, setOpen] = useState(true)
  const count = entries?.length ?? 0

  const grouped = useMemo(() => {
    const list = entries || []
    const byAgent = {}
    list.forEach((e, i) => {
      const id = e.agent_id || 'unknown'
      if (!byAgent[id]) byAgent[id] = []
      byAgent[id].push({ ...e, _i: i })
    })
    return byAgent
  }, [entries])

  if (count === 0) {
    return (
      <div className="rounded-xl border border-dashed border-charcoal-200 bg-charcoal-50/50 px-4 py-3 text-xs text-charcoal-400">
        完成「解析 / 审核 / 编剧 / 分镜 / 视频生成」等步骤后，此处会显示各 Agent 调用模型时使用的提示词（调试）。
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-moss/20 bg-white shadow-sm overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-2 px-4 py-3 text-left bg-moss/5 hover:bg-moss/10 transition-colors"
      >
        <span className="flex items-center gap-2 text-sm font-semibold text-moss-600">
          {open ? <CaretDown size={18} /> : <CaretRight size={18} />}
          提示词调试
          <span className="font-normal text-charcoal-400">({count} 条)</span>
        </span>
        {onClear && (
          <span
            role="button"
            tabIndex={0}
            onClick={(ev) => {
              ev.stopPropagation()
              onClear()
            }}
            onKeyDown={(ev) => {
              if (ev.key === 'Enter' || ev.key === ' ') {
                ev.preventDefault()
                ev.stopPropagation()
                onClear()
              }
            }}
            className="inline-flex items-center gap-1 text-xs text-charcoal-400 hover:text-caramel-500"
          >
            <Trash size={14} />
            清空
          </span>
        )}
      </button>
      {open && (
        <div className="px-3 pb-3 max-h-[min(70vh,520px)] overflow-y-auto space-y-4">
          {Object.entries(grouped).map(([agentId, items]) => (
            <div key={agentId} className="space-y-2">
              <div className="text-xs font-semibold text-charcoal-600 border-b border-charcoal-100 pb-1">
                {getYingfangAgentName(agentId)}
                <span className="font-mono font-normal text-charcoal-400 ml-2">{agentId}</span>
              </div>
              <ul className="space-y-3 pl-1">
                {items.map((e) => (
                  <li
                    key={`${e._i}-${e.step}`}
                    className="rounded-lg border border-charcoal-100 bg-paper p-3 space-y-2"
                  >
                    <div className="text-sm font-medium text-charcoal-800">{e.step}</div>
                    {e.model && (
                      <div className="text-[11px] text-charcoal-400">模型: {e.model}</div>
                    )}
                    <Block label="System" text={e.system} />
                    <Block label="User" text={e.user} />
                    <Block label="完整提示 / Body" text={e.body} />
                    {e.extra && Object.keys(e.extra).length > 0 && (
                      <Block label="Extra" text={JSON.stringify(e.extra, null, 2)} />
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
