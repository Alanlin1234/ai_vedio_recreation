from flask import Blueprint, request, jsonify, current_app, send_from_directory
from app.models import db, VideoRecreation, RecreationScene, RecreationLog
from app.services.efficient_video_analyzer import EfficientVideoAnalyzerWithHighlights
from app.services.enhanced_content_generator import EnhancedContentGenerator
from app.services.content_generation_service import ContentGenerationService
from app.services.scene_segmentation_service import SceneSegmentationService
from app.services.camera_script_generator import CameraScriptGenerator
from app.services.video_recreation_service import VideoRecreationService
from app.services.storyboard_generator import StoryboardGenerator
from datetime import datetime
import os
import uuid
import traceback
import asyncio
import logging

logger = logging.getLogger(__name__)

frontend_pipeline_bp = Blueprint('frontend_pipeline', __name__)


@frontend_pipeline_bp.route('/upload-video', methods=['POST'])
def upload_video():
    try:
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': '没有找到视频文件'}), 400

        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({'success': False, 'error': '没有选择视频文件'}), 400

        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'user_videos')
        os.makedirs(upload_dir, exist_ok=True)

        file_ext = os.path.splitext(video_file.filename)[1]
        unique_filename = f"video_{uuid.uuid4().hex[:12]}{file_ext}"
        video_path = os.path.join(upload_dir, unique_filename)

        video_file.save(video_path)

        recreation = VideoRecreation(
            original_video_id=f"user_{uuid.uuid4().hex}",
            original_video_path=video_path,
            recreation_name=os.path.splitext(video_file.filename)[0],
            status='pending',
            created_at=datetime.now()
        )
        db.session.add(recreation)
        db.session.commit()

        return jsonify({
            'success': True,
            'recreation_id': recreation.id,
            'video_path': video_path,
            'filename': video_file.filename
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@frontend_pipeline_bp.route('/analyze-video/<int:recreation_id>', methods=['POST'])
def analyze_video(recreation_id):
    try:
        recreation = VideoRecreation.query.get(recreation_id)
        if not recreation:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        video_path = recreation.original_video_path
        if not os.path.exists(video_path):
            return jsonify({'success': False, 'error': '视频文件不存在'}), 400

        video_analyzer = EfficientVideoAnalyzerWithHighlights()

        print(f"[视频分析] 开始高效分析视频: {video_path}")
        result = asyncio.run(video_analyzer.analyze_video_complete(video_path=video_path))

        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', '视频分析失败')
            }), 500

        story_content = result.get('content', '')
        highlights = result.get('highlights', '')
        educational = result.get('educational_meaning', '')

        print(f"[视频分析] 高效分析完成")
        print(f"[视频分析] - 关键帧: {result.get('keyframes_count', 0)}帧")
        print(f"[视频分析] - 耗时: {result.get('time_cost', 0)}秒")
        print(f"[视频分析] - 亮点: {str(highlights)[:100]}...")
        print(f"[视频分析] - 教育: {str(educational)[:100]}...")

        recreation.video_understanding = story_content
        recreation.understanding_model = 'EfficientVideoAnalyzer'
        recreation.status = 'completed'
        db.session.commit()

        return jsonify({
            'success': True,
            'recreation_id': recreation_id,
            'story_content': story_content,
            'highlights': highlights if highlights else '暂无亮点描述',
            'educational_meaning': educational if educational else '暂无教育意义描述',
            'analysis_metadata': {
                'keyframes_count': result.get('keyframes_count', 0),
                'time_cost': result.get('time_cost', 0),
                'transcription_length': len(result.get('transcription', '') or '')
            }
        })

    except Exception as e:
        print(f"[视频分析] 错误: {e}")
        traceback.print_exc()
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@frontend_pipeline_bp.route('/generate-new-story/<int:recreation_id>', methods=['POST'])
def generate_new_story(recreation_id):
    try:
        recreation = VideoRecreation.query.get(recreation_id)
        if not recreation:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        data = request.get_json() or {}

        original_story = recreation.video_understanding or ''
        original_highlights = data.get('original_highlights', '')
        original_educational = data.get('original_educational', '')

        if not original_story:
            return jsonify({
                'success': False,
                'error': '没有原故事内容，请先分析视频'
            }), 400

        print(f"[新故事生成] 开始生成新故事...")

        from app.services.enhanced_content_generator import EnhancedContentGenerator
        content_generator = EnhancedContentGenerator()

        original_analysis = {
            'main_plot': original_story[:500],
            'characters': [],
            'emotional_arc': '',
            'thematic_elements': []
        }

        enhanced_result = content_generator.generate_enhanced_story(
            original_analysis=original_analysis,
            highlights=original_highlights,
            educational=original_educational
        )

        if enhanced_result.get('success'):
            new_story = enhanced_result.get('new_story', '')
            highlights_data = enhanced_result.get('highlights', {})
            educational_data = enhanced_result.get('educational', {})

            combined_highlights = highlights_data.get('combined_highlights', original_highlights)
            combined_educational = educational_data.get('combined_educational', original_educational)

            print(f"[新故事生成] 新故事生成成功")
            print(f"[新故事生成] - 亮点: {combined_highlights[:100]}...")
            print(f"[新故事生成] - 教育意义: {combined_educational[:100]}...")

            recreation.new_script_content = new_story
            recreation.status = 'completed'
            db.session.commit()

            return jsonify({
                'success': True,
                'recreation_id': recreation_id,
                'new_story': new_story,
                'highlights': combined_highlights,
                'highlights_details': highlights_data,
                'educational_meaning': combined_educational,
                'educational_details': educational_data
            })
        else:
            return jsonify({
                'success': False,
                'error': enhanced_result.get('error', '新故事生成失败')
            }), 500

    except Exception as e:
        print(f"[新故事生成] 错误: {e}")
        traceback.print_exc()
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@frontend_pipeline_bp.route('/generate-storyboard/<int:recreation_id>', methods=['POST'])
def generate_storyboard(recreation_id):
    try:
        recreation = VideoRecreation.query.get(recreation_id)
        if not recreation:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        story_content = recreation.new_script_content or recreation.video_understanding
        if not story_content:
            return jsonify({'success': False, 'error': '没有故事内容'}), 400

        request_data = request.get_json() or {}
        scene_count = request_data.get('scene_count', 6)

        output_dir = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            'storyboards',
            f'recreation_{recreation_id}'
        )

        from app.services.storyboard_generator import StoryboardGenerator
        storyboard_generator = StoryboardGenerator()

        print(f"[分镜图生成] 开始生成{scene_count}个分镜...")
        storyboard_result = storyboard_generator.generate_storyboard(
            story_content=story_content,
            scene_count=scene_count,
            output_dir=output_dir,
            generate_images=True
        )

        if not storyboard_result.get('success'):
            return jsonify({
                'success': False,
                'error': storyboard_result.get('error', '分镜图生成失败')
            }), 500

        scenes = storyboard_result.get('scenes', [])

        for idx, scene in enumerate(scenes):
            image_path = scene.get('image')
            
            scene_obj = RecreationScene(
                recreation_id=recreation_id,
                scene_index=idx,
                start_time=idx * 5,
                end_time=(idx + 1) * 5,
                duration=scene.get('duration', 5),
                shot_type=scene.get('shot_type', ''),
                description=scene.get('description', ''),
                plot=scene.get('plot', ''),
                dialogue=scene.get('dialogue', ''),
                video_prompt=scene.get('prompt', ''),
                generated_image_path=image_path,
                generation_status='pending',
                created_at=datetime.now()
            )
            db.session.add(scene_obj)
            
            scene_num = idx + 1
            scene['scene_number'] = scene_num
            if image_path and os.path.exists(image_path):
                scene['image'] = f"/api/pipeline/storyboard-image/{recreation_id}/{scene_num}"
                logger.info(f"[分镜图] 场景{scene_num} 图片路径: {scene['image']}")
            else:
                scene['image'] = None
                logger.warning(f"[分镜图] 场景{scene_num} 图片不存在: {image_path}")

        recreation.status = 'completed'
        db.session.commit()

        return jsonify({
            'success': True,
            'recreation_id': recreation_id,
            'storyboard': scenes,
            'style_guide': storyboard_result.get('style_guide', {}),
            'has_images': storyboard_result.get('has_images', False)
        })

    except Exception as e:
        print(f"[分镜图生成] 错误: {e}")
        traceback.print_exc()
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@frontend_pipeline_bp.route('/generate-scene-videos/<int:recreation_id>', methods=['POST'])
def generate_scene_videos(recreation_id):
    try:
        recreation = VideoRecreation.query.get(recreation_id)
        if not recreation:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        from app.services.storyboard_to_video_service import StoryboardToVideoService
        video_service = StoryboardToVideoService()

        result = video_service.generate_scene_videos(recreation_id)

        if result.get('success'):
            recreation.status = 'completed'
            db.session.commit()

        return jsonify(result)

    except Exception as e:
        print(f"[分场景视频生成] 错误: {e}")
        traceback.print_exc()
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@frontend_pipeline_bp.route('/combine-video/<int:recreation_id>', methods=['POST'])
def combine_video(recreation_id):
    try:
        recreation = VideoRecreation.query.get(recreation_id)
        if not recreation:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        scenes = RecreationScene.query.filter_by(
            recreation_id=recreation_id,
            generation_status='completed'
        ).order_by(RecreationScene.scene_index).all()

        if not scenes:
            return jsonify({'success': False, 'error': '没有成功生成的场景视频'}), 400

        video_service = VideoRecreationService()
        task_dir = video_service.create_task_directory(recreation_id, recreation.original_video_path)

        video_paths = [scene.generated_video_path for scene in scenes if scene.generated_video_path]

        final_video_path = os.path.join(task_dir, 'final', f'final_video_{recreation_id}.mp4')
        os.makedirs(os.path.dirname(final_video_path), exist_ok=True)

        from app.services.ffmpeg_service import FFmpegService
        ffmpeg_service = FFmpegService()

        final_video = asyncio.run(ffmpeg_service.concatenate_videos(video_paths, final_video_path))

        if final_video and os.path.exists(final_video):
            recreation.final_video_path = final_video
            recreation.composition_status = 'completed'
            recreation.status = 'completed'
            recreation.completed_at = datetime.now()

            video_info = asyncio.run(ffmpeg_service.get_video_info(final_video))
            if video_info:
                recreation.total_duration = video_info.get('duration', 0)
                recreation.video_resolution = video_info.get('resolution', '')
                recreation.video_fps = video_info.get('fps', 0)

            db.session.commit()

            return jsonify({
                'success': True,
                'recreation_id': recreation_id,
                'final_video_path': final_video,
                'video_info': video_info
            })
        else:
            return jsonify({'success': False, 'error': '视频合成失败'}), 500

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@frontend_pipeline_bp.route('/export-video/<int:recreation_id>', methods=['GET'])
def export_video(recreation_id):
    try:
        recreation = VideoRecreation.query.get(recreation_id)
        if not recreation or not recreation.final_video_path:
            return jsonify({'success': False, 'error': '视频不存在'}), 404

        video_dir = os.path.dirname(recreation.final_video_path)
        video_filename = os.path.basename(recreation.final_video_path)

        return send_from_directory(
            video_dir,
            video_filename,
            as_attachment=True,
            download_name=f'generated_video_{recreation_id}.mp4'
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@frontend_pipeline_bp.route('/storyboard-image/<int:recreation_id>/<int:scene_number>', methods=['GET'])
def get_storyboard_image(recreation_id, scene_number):
    """获取分镜图"""
    try:
        from flask import send_from_directory
        
        image_dir = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            'storyboards',
            f'recreation_{recreation_id}'
        )
        
        image_filename = f"scene_{scene_number:02d}.png"
        image_path = os.path.join(image_dir, image_filename)
        
        if os.path.exists(image_path):
            return send_from_directory(image_dir, image_filename)
        else:
            return jsonify({'success': False, 'error': '图片不存在'}), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@frontend_pipeline_bp.route('/project/<int:recreation_id>', methods=['GET'])
def get_project(recreation_id):
    try:
        recreation = VideoRecreation.query.get(recreation_id)
        if not recreation:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        scenes = RecreationScene.query.filter_by(recreation_id=recreation_id).order_by(
            RecreationScene.scene_index
        ).all()

        scene_dicts = []
        for scene in scenes:
            scene_dict = scene.to_dict()
            scene_num = scene.scene_index + 1
            image_dir = os.path.join(
                current_app.config['UPLOAD_FOLDER'],
                'storyboards',
                f'recreation_{recreation_id}'
            )
            image_filename = f"scene_{scene_num:02d}.png"
            image_path = os.path.join(image_dir, image_filename)
            
            if os.path.exists(image_path):
                scene_dict['image'] = f"/api/pipeline/storyboard-image/{recreation_id}/{scene_num}"
            else:
                scene_dict['image'] = None
            scene_dicts.append(scene_dict)

        return jsonify({
            'success': True,
            'project': recreation.to_dict(),
            'scenes': scene_dicts
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
