"""
影坊工作台流水线：上传 → 解析 → 审核 → 新故事 → 分镜 → 分场景视频 → 拼接 → 导出

本模块集中说明各步骤对应的路由与实现类，并提供分场景视频生成的统一入口，
供 /api/pipeline 与 /api/agent 复用。
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.yingfang_system import STEP_KEY_TO_AGENT_ID

# 步骤标识（与前端 StepIndicator、影坊多 Agent 对齐）
_RAW_WORKFLOW_STEPS: List[Dict[str, str]] = [
    {'key': 'upload', 'label': '上传视频', 'pipeline_route': 'POST /api/pipeline/upload-video'},
    {'key': 'analyze', 'label': '解析（教育专家）', 'pipeline_route': 'POST /api/pipeline/analyze-video/<id>'},
    {'key': 'review', 'label': '审核', 'route': 'POST /api/reviewer/<id>'},
    {'key': 'new_story', 'label': '二创新故事（故事编剧）', 'pipeline_route': 'POST /api/pipeline/generate-new-story/<id>'},
    {'key': 'storyboard', 'label': '分镜（5秒/镜）', 'pipeline_route': 'POST /api/pipeline/generate-storyboard/<id>'},
    {'key': 'scene_videos', 'label': '分场景视频', 'pipeline_route': 'POST /api/pipeline/generate-scene-videos/<id>'},
    {'key': 'combine', 'label': '拼接成片', 'pipeline_route': 'POST /api/pipeline/combine-video/<id>'},
    {'key': 'export', 'label': '导出', 'pipeline_route': 'GET /api/pipeline/export-video/<id>'},
]

WORKFLOW_STEPS: List[Dict[str, Any]] = [
    {**row, 'agent_id': STEP_KEY_TO_AGENT_ID.get(row['key'])}
    for row in _RAW_WORKFLOW_STEPS
]


def run_generate_scene_videos(recreation_id: int) -> Dict[str, Any]:
    """
    分场景视频生成（内部调用 StoryboardToVideoService）。
    返回结构与 storyboard_to_video_service.generate_scene_videos 一致。
    """
    from app.services.storyboard_to_video_service import StoryboardToVideoService

    return StoryboardToVideoService().generate_scene_videos(recreation_id)


def build_scene_video_status(recreation_id: int) -> Dict[str, Any]:
    """供 GET video-status 使用：按场景列出是否已生成视频。"""
    from app.models import RecreationScene, VideoRecreation

    recreation = VideoRecreation.query.get(recreation_id)
    if not recreation:
        return {'success': False, 'error': '项目不存在'}

    scenes = (
        RecreationScene.query.filter_by(recreation_id=recreation_id)
        .order_by(RecreationScene.scene_index)
        .all()
    )

    scene_status = []
    for scene in scenes:
        scene_status.append(
            {
                'scene_index': scene.scene_index,
                'scene_number': scene.scene_index + 1,
                'has_video': bool(scene.generated_video_path),
                'video_path': scene.generated_video_path,
                'status': scene.generation_status or 'pending',
            }
        )

    return {
        'success': True,
        'recreation_id': recreation_id,
        'scenes': scene_status,
        'completed_count': sum(1 for s in scene_status if s['has_video']),
        'total_count': len(scene_status),
    }
