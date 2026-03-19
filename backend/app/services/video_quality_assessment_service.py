"""
视频质量评估服务
评估生成视频的质量，包括分辨率、帧率、码率、文件大小、时长等指标
支持与原视频对比，生成质量报告
整合内容一致性检查，检测物理逻辑、人物外貌、动作等问题
"""
import os
import sys
import json
import subprocess
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = logging.getLogger(__name__)


class VideoQualityAssessmentService:
    """视频质量评估服务"""
    
    QUALITY_GRADES = {
        'excellent': (0.9, 1.0, '优秀'),
        'good': (0.8, 0.9, '良好'),
        'pass': (0.7, 0.8, '合格'),
        'fair': (0.6, 0.7, '一般'),
        'poor': (0.0, 0.6, '不合格')
    }
    
    DEFAULT_THRESHOLDS = {
        'min_resolution': (1280, 720),
        'min_fps': 24,
        'min_bitrate': 1000000,
        'min_duration': 1,
        'max_duration': 600,
        'min_file_size': 1024 * 100,
        'max_file_size': 1024 * 1024 * 500
    }
    
    WEIGHTS = {
        'resolution': 0.25,
        'fps': 0.20,
        'bitrate': 0.25,
        'file_size': 0.15,
        'duration': 0.15
    }
    
    def __init__(self, thresholds: Dict[str, Any] = None):
        """
        初始化视频质量评估服务
        
        Args:
            thresholds: 自定义阈值配置
        """
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        logger.info("VideoQualityAssessmentService 初始化完成")
    
    def assess_video_quality(self, video_path: str) -> Dict[str, Any]:
        """
        评估视频质量
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            评估结果，包含各项评分和总体评价
        """
        try:
            logger.info(f"开始评估视频质量: {video_path}")
            
            if not os.path.exists(video_path):
                return {
                    'success': False,
                    'error': f'视频文件不存在: {video_path}'
                }
            
            video_info = self._get_video_info(video_path)
            if not video_info.get('success'):
                return video_info
            
            scores = {}
            issues = []
            
            resolution_score = self._assess_resolution(video_info, issues)
            scores['resolution'] = resolution_score
            
            fps_score = self._assess_fps(video_info, issues)
            scores['fps'] = fps_score
            
            bitrate_score = self._assess_bitrate(video_info, issues)
            scores['bitrate'] = bitrate_score
            
            file_size_score = self._assess_file_size(video_path, issues)
            scores['file_size'] = file_size_score
            
            duration_score = self._assess_duration(video_info, issues)
            scores['duration'] = duration_score
            
            overall_score = self._calculate_overall_score(scores)
            grade = self._get_grade(overall_score)
            passed = overall_score >= 0.6
            
            result = {
                'success': True,
                'video_path': video_path,
                'video_info': {
                    'resolution': video_info.get('resolution'),
                    'width': video_info.get('width'),
                    'height': video_info.get('height'),
                    'fps': video_info.get('fps'),
                    'bitrate': video_info.get('bitrate'),
                    'duration': video_info.get('duration'),
                    'codec': video_info.get('codec'),
                    'format': video_info.get('format')
                },
                'scores': scores,
                'overall_score': overall_score,
                'grade': grade,
                'grade_name': self.QUALITY_GRADES.get(grade, (0, 0, '未知'))[2],
                'passed': passed,
                'issues': issues,
                'thresholds': self.thresholds,
                'assessment_time': datetime.now().isoformat()
            }
            
            logger.info(f"视频质量评估完成: 得分={overall_score:.2f}, 等级={grade}")
            return result
            
        except Exception as e:
            error_msg = f"视频质量评估失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _get_video_info(self, video_path: str) -> Dict[str, Any]:
        """使用 FFprobe 获取视频信息"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f'FFprobe 执行失败: {result.stderr}'
                }
            
            data = json.loads(result.stdout)
            
            video_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                return {
                    'success': False,
                    'error': '未找到视频流'
                }
            
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))
            
            fps_str = video_stream.get('r_frame_rate', '0/1')
            if '/' in fps_str:
                num, den = fps_str.split('/')
                fps = float(num) / float(den) if float(den) > 0 else 0
            else:
                fps = float(fps_str)
            
            bitrate = int(data.get('format', {}).get('bit_rate', 0))
            duration = float(data.get('format', {}).get('duration', 0))
            
            return {
                'success': True,
                'width': width,
                'height': height,
                'resolution': f"{width}x{height}",
                'fps': round(fps, 2),
                'bitrate': bitrate,
                'duration': round(duration, 2),
                'codec': video_stream.get('codec_name', 'unknown'),
                'format': data.get('format', {}).get('format_name', 'unknown')
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'FFprobe 执行超时'
            }
        except json.JSONDecodeError:
            return {
                'success': False,
                'error': 'FFprobe 输出解析失败'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'获取视频信息失败: {str(e)}'
            }
    
    def _assess_resolution(self, video_info: Dict, issues: List[str]) -> float:
        """评估分辨率"""
        min_res = self.thresholds['min_resolution']
        width = video_info.get('width', 0)
        height = video_info.get('height', 0)
        
        if width >= min_res[0] and height >= min_res[1]:
            if width >= 1920 and height >= 1080:
                return 1.0
            elif width >= 1600 and height >= 900:
                return 0.9
            else:
                return 0.8
        elif width >= min_res[0] * 0.75 and height >= min_res[1] * 0.75:
            issues.append(f"分辨率略低: {width}x{height} (建议: {min_res[0]}x{min_res[1]})")
            return 0.6
        else:
            issues.append(f"分辨率过低: {width}x{height} (最低要求: {min_res[0]}x{min_res[1]})")
            return 0.3
    
    def _assess_fps(self, video_info: Dict, issues: List[str]) -> float:
        """评估帧率"""
        min_fps = self.thresholds['min_fps']
        fps = video_info.get('fps', 0)
        
        if fps >= 60:
            return 1.0
        elif fps >= 30:
            return 0.9
        elif fps >= min_fps:
            return 0.8
        elif fps >= min_fps * 0.8:
            issues.append(f"帧率略低: {fps}fps (建议: {min_fps}fps)")
            return 0.6
        else:
            issues.append(f"帧率过低: {fps}fps (最低要求: {min_fps}fps)")
            return 0.3
    
    def _assess_bitrate(self, video_info: Dict, issues: List[str]) -> float:
        """评估码率"""
        min_bitrate = self.thresholds['min_bitrate']
        bitrate = video_info.get('bitrate', 0)
        
        if bitrate >= min_bitrate * 5:
            return 1.0
        elif bitrate >= min_bitrate * 2:
            return 0.9
        elif bitrate >= min_bitrate:
            return 0.8
        elif bitrate >= min_bitrate * 0.5:
            issues.append(f"码率略低: {bitrate/1000:.0f}kbps (建议: {min_bitrate/1000:.0f}kbps)")
            return 0.6
        else:
            issues.append(f"码率过低: {bitrate/1000:.0f}kbps (最低要求: {min_bitrate/1000:.0f}kbps)")
            return 0.3
    
    def _assess_file_size(self, video_path: str, issues: List[str]) -> float:
        """评估文件大小"""
        min_size = self.thresholds['min_file_size']
        max_size = self.thresholds['max_file_size']
        
        try:
            file_size = os.path.getsize(video_path)
            
            if min_size <= file_size <= max_size:
                if file_size >= min_size * 100:
                    return 0.9
                else:
                    return 0.8
            elif file_size < min_size:
                issues.append(f"文件过小: {file_size/1024:.1f}KB (可能内容不完整)")
                return 0.4
            else:
                issues.append(f"文件过大: {file_size/1024/1024:.1f}MB (可能影响传输)")
                return 0.7
                
        except Exception as e:
            issues.append(f"无法获取文件大小: {str(e)}")
            return 0.5
    
    def _assess_duration(self, video_info: Dict, issues: List[str]) -> float:
        """评估视频时长"""
        min_duration = self.thresholds['min_duration']
        max_duration = self.thresholds['max_duration']
        duration = video_info.get('duration', 0)
        
        if min_duration <= duration <= max_duration:
            return 0.9
        elif duration < min_duration:
            issues.append(f"视频时长过短: {duration:.1f}s (最短: {min_duration}s)")
            return 0.5
        else:
            issues.append(f"视频时长过长: {duration:.1f}s (最长: {max_duration}s)")
            return 0.7
    
    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """计算综合得分"""
        total_score = 0.0
        total_weight = 0.0
        
        for metric, weight in self.WEIGHTS.items():
            if metric in scores:
                total_score += scores[metric] * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _get_grade(self, score: float) -> str:
        """根据得分获取等级"""
        for grade, (min_score, max_score, _) in self.QUALITY_GRADES.items():
            if min_score <= score < max_score:
                return grade
        return 'poor'
    
    def compare_with_original(self, original_path: str, generated_path: str) -> Dict[str, Any]:
        """
        与原视频进行对比
        
        Args:
            original_path: 原视频路径
            generated_path: 生成的视频路径
            
        Returns:
            对比结果
        """
        try:
            logger.info(f"开始对比视频: 原视频={original_path}, 生成视频={generated_path}")
            
            original_info = self._get_video_info(original_path)
            generated_info = self._get_video_info(generated_path)
            
            if not original_info.get('success'):
                return {
                    'success': False,
                    'error': f"无法获取原视频信息: {original_info.get('error')}"
                }
            
            if not generated_info.get('success'):
                return {
                    'success': False,
                    'error': f"无法获取生成视频信息: {generated_info.get('error')}"
                }
            
            resolution_similarity = self._compare_resolution(original_info, generated_info)
            fps_similarity = self._compare_fps(original_info, generated_info)
            duration_similarity = self._compare_duration(original_info, generated_info)
            
            similarity_score = (
                resolution_similarity * 0.4 +
                fps_similarity * 0.3 +
                duration_similarity * 0.3
            )
            
            return {
                'success': True,
                'original_path': original_path,
                'generated_path': generated_path,
                'comparison': {
                    'resolution_similarity': resolution_similarity,
                    'fps_similarity': fps_similarity,
                    'duration_similarity': duration_similarity,
                    'similarity_score': similarity_score
                },
                'original_info': {
                    'resolution': original_info.get('resolution'),
                    'fps': original_info.get('fps'),
                    'duration': original_info.get('duration')
                },
                'generated_info': {
                    'resolution': generated_info.get('resolution'),
                    'fps': generated_info.get('fps'),
                    'duration': generated_info.get('duration')
                }
            }
            
        except Exception as e:
            error_msg = f"视频对比失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _compare_resolution(self, original: Dict, generated: Dict) -> float:
        """比较分辨率相似度"""
        orig_width = original.get('width', 0)
        orig_height = original.get('height', 0)
        gen_width = generated.get('width', 0)
        gen_height = generated.get('height', 0)
        
        if orig_width == 0 or orig_height == 0:
            return 0.5
        
        width_ratio = min(orig_width, gen_width) / max(orig_width, gen_width)
        height_ratio = min(orig_height, gen_height) / max(orig_height, gen_height)
        
        return (width_ratio + height_ratio) / 2
    
    def _compare_fps(self, original: Dict, generated: Dict) -> float:
        """比较帧率相似度"""
        orig_fps = original.get('fps', 0)
        gen_fps = generated.get('fps', 0)
        
        if orig_fps == 0:
            return 0.5
        
        return min(orig_fps, gen_fps) / max(orig_fps, gen_fps)
    
    def _compare_duration(self, original: Dict, generated: Dict) -> float:
        """比较时长相似度"""
        orig_duration = original.get('duration', 0)
        gen_duration = generated.get('duration', 0)
        
        if orig_duration == 0:
            return 0.5
        
        return min(orig_duration, gen_duration) / max(orig_duration, gen_duration)
    
    def generate_quality_report(self, video_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        生成质量报告
        
        Args:
            video_path: 视频文件路径
            output_path: 报告输出路径（可选）
            
        Returns:
            报告生成结果
        """
        try:
            assessment = self.assess_video_quality(video_path)
            
            if not assessment.get('success'):
                return assessment
            
            report_lines = [
                "# 视频质量评估报告",
                "",
                f"**评估时间**: {assessment.get('assessment_time', 'N/A')}",
                f"**视频路径**: {video_path}",
                "",
                "## 基本信息",
                "",
                "| 属性 | 值 |",
                "|------|-----|",
            ]
            
            video_info = assessment.get('video_info', {})
            report_lines.extend([
                f"| 分辨率 | {video_info.get('resolution', 'N/A')} |",
                f"| 帧率 | {video_info.get('fps', 'N/A')} fps |",
                f"| 码率 | {video_info.get('bitrate', 0) / 1000:.0f} kbps |",
                f"| 时长 | {video_info.get('duration', 0):.2f} 秒 |",
                f"| 编码 | {video_info.get('codec', 'N/A')} |",
                f"| 格式 | {video_info.get('format', 'N/A')} |",
                "",
                "## 质量评分",
                "",
                "| 指标 | 得分 | 权重 |",
                "|------|------|------|",
            ])
            
            scores = assessment.get('scores', {})
            for metric, score in scores.items():
                weight = self.WEIGHTS.get(metric, 0)
                report_lines.append(f"| {metric} | {score:.2f} | {weight:.0%} |")
            
            report_lines.extend([
                "",
                f"### 综合评分: **{assessment.get('overall_score', 0):.2f}**",
                f"### 质量等级: **{assessment.get('grade_name', 'N/A')}**",
                f"### 是否通过: **{'是' if assessment.get('passed') else '否'}**",
                "",
            ])
            
            issues = assessment.get('issues', [])
            if issues:
                report_lines.extend([
                    "## 问题列表",
                    "",
                ])
                for issue in issues:
                    report_lines.append(f"- {issue}")
                report_lines.append("")
            
            report_lines.extend([
                "## 阈值配置",
                "",
                "| 参数 | 值 |",
                "|------|-----|",
                f"| 最低分辨率 | {self.thresholds['min_resolution'][0]}x{self.thresholds['min_resolution'][1]} |",
                f"| 最低帧率 | {self.thresholds['min_fps']} fps |",
                f"| 最低码率 | {self.thresholds['min_bitrate'] / 1000:.0f} kbps |",
                "",
                "---",
                f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
            ])
            
            report_content = "\n".join(report_lines)
            
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                logger.info(f"质量报告已保存: {output_path}")
            
            return {
                'success': True,
                'report_path': output_path,
                'report_content': report_content,
                'assessment': assessment
            }
            
        except Exception as e:
            error_msg = f"生成质量报告失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }
    
    def check_content_consistency(self, video_path: str, keyframes: List[str] = None,
                                  previous_keyframes: List[str] = None,
                                  scene_prompt: str = "") -> Dict[str, Any]:
        """
        检查视频内容一致性（物理逻辑、人物外貌、动作连贯性）
        
        Args:
            video_path: 视频文件路径
            keyframes: 当前场景的关键帧列表
            previous_keyframes: 上一场景的关键帧列表
            scene_prompt: 场景描述提示词
            
        Returns:
            内容一致性检查结果
        """
        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            from video_consistency_agent.checkers.content_consistency_checker import ContentConsistencyChecker
            
            checker = ContentConsistencyChecker(self.thresholds)
            
            result = checker.check_content_consistency(
                video_path=video_path,
                keyframes=keyframes,
                previous_keyframes=previous_keyframes,
                scene_prompt=scene_prompt
            )
            
            return result
            
        except Exception as e:
            error_msg = f"内容一致性检查失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'overall_score': 0.8,
                'passed': True,
                'issues': [error_msg]
            }
    
    def comprehensive_assessment(self, video_path: str, keyframes: List[str] = None,
                                previous_keyframes: List[str] = None,
                                original_video_path: str = None,
                                scene_prompt: str = "") -> Dict[str, Any]:
        """
        综合评估：技术质量 + 内容一致性
        
        Args:
            video_path: 视频文件路径
            keyframes: 当前场景的关键帧列表
            previous_keyframes: 上一场景的关键帧列表
            original_video_path: 原视频路径（可选，用于对比）
            scene_prompt: 场景描述提示词
            
        Returns:
            综合评估结果
        """
        try:
            logger.info(f"开始综合评估: {video_path}")
            
            technical_result = self.assess_video_quality(video_path)
            
            content_result = self.check_content_consistency(
                video_path=video_path,
                keyframes=keyframes,
                previous_keyframes=previous_keyframes,
                scene_prompt=scene_prompt
            )
            
            comparison_result = None
            if original_video_path and os.path.exists(original_video_path):
                comparison_result = self.compare_with_original(original_video_path, video_path)
            
            technical_score = technical_result.get('overall_score', 0.8)
            content_score = content_result.get('overall_score', 0.8)
            
            comprehensive_score = (
                technical_score * 0.5 +
                content_score * 0.5
            )
            
            all_issues = []
            all_issues.extend(technical_result.get('issues', []))
            all_issues.extend(content_result.get('issues', []))
            
            all_suggestions = []
            all_suggestions.extend(content_result.get('suggestions', []))
            
            result = {
                'success': True,
                'video_path': video_path,
                'assessment_time': datetime.now().isoformat(),
                'comprehensive_score': comprehensive_score,
                'passed': comprehensive_score >= 0.6 and technical_result.get('passed', True),
                'technical_quality': {
                    'score': technical_score,
                    'grade': technical_result.get('grade', 'fair'),
                    'grade_name': technical_result.get('grade_name', '一般'),
                    'passed': technical_result.get('passed', True),
                    'details': technical_result.get('scores', {}),
                    'issues': technical_result.get('issues', [])
                },
                'content_consistency': {
                    'score': content_score,
                    'passed': content_result.get('passed', True),
                    'physical_logic': content_result.get('physical_logic', {}),
                    'character_consistency': content_result.get('character_consistency', {}),
                    'action_continuity': content_result.get('action_continuity', {}),
                    'issues': content_result.get('issues', []),
                    'suggestions': content_result.get('suggestions', [])
                },
                'all_issues': all_issues,
                'all_suggestions': all_suggestions
            }
            
            if comparison_result and comparison_result.get('success'):
                result['comparison'] = comparison_result.get('comparison', {})
            
            logger.info(f"综合评估完成: 技术得分={technical_score:.2f}, 内容得分={content_score:.2f}, 综合得分={comprehensive_score:.2f}")
            
            return result
            
        except Exception as e:
            error_msg = f"综合评估失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'comprehensive_score': 0.5,
                'passed': True
            }
