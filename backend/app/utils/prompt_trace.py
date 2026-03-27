"""调试：统一收集各 Agent 调用模型时使用的提示词结构，供 API 返回与前端展示。"""
from __future__ import annotations

from typing import Any, Dict, Optional


def trace(
    agent_id: str,
    step: str,
    *,
    system: Optional[str] = None,
    user: Optional[str] = None,
    body: Optional[str] = None,
    model: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        'agent_id': agent_id,
        'step': step,
        'system': system,
        'user': user,
        'body': body,
        'model': model,
        'extra': extra or {},
    }
