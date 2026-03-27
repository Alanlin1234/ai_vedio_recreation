import { YINGFANG_AGENTS, getYingfangAgentName } from '../constants/yingfangAgents'

function statusClass(status) {
  if (status === 'running') return 'text-amber-600 bg-amber-50 border-amber-100'
  if (status === 'completed') return 'text-moss bg-moss/5 border-moss/20'
  if (status === 'failed') return 'text-red-600 bg-red-50 border-red-100'
  return 'text-charcoal-400 bg-paper-50 border-charcoal-100'
}

function statusLabel(status) {
  if (status === 'running') return '执行中'
  if (status === 'completed') return '完成'
  if (status === 'failed') return '失败'
  return '待命中'
}

function AgentProgress({ currentAgent, agentStatuses = {}, isRunning }) {
  return (
    <div className="rounded-xl border border-charcoal-100 bg-paper-50/80 p-4">
      <p className="section-label mb-3">影坊多 Agent</p>
      <ul className="space-y-2">
        {YINGFANG_AGENTS.map((a) => {
          const st = agentStatuses[a.id] || 'pending'
          const isCurrent = currentAgent === a.id
          return (
            <li
              key={a.id}
              className={`flex items-start justify-between gap-2 rounded-lg border px-2.5 py-2 text-xs transition-colors ${statusClass(
                st
              )} ${isCurrent ? 'ring-1 ring-moss/30' : ''}`}
            >
              <div className="min-w-0">
                <div className="font-sans font-semibold text-charcoal-700">{a.nameZh}</div>
                <div className="text-[11px] text-charcoal-500 mt-0.5 leading-snug">{a.description}</div>
              </div>
              <span className="flex-shrink-0 font-medium tabular-nums">{statusLabel(st)}</span>
            </li>
          )
        })}
      </ul>
      {currentAgent && (
        <p className="text-xs text-charcoal-600 font-sans mt-3 pt-3 border-t border-charcoal-100">
          当前执行：
          <span className="text-moss font-medium">{getYingfangAgentName(currentAgent)}</span>
        </p>
      )}
      {isRunning && !currentAgent && (
        <p className="text-xs text-charcoal-500 font-sans mt-3">调度中…</p>
      )}
    </div>
  )
}

export default AgentProgress
