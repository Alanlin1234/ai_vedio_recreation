import os
import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Tuple
from .models import SliceAnalysis, DirectorDecision

logger = logging.getLogger(__name__)


class DirectorRuleEngine:
    """规则引擎 - 快速初筛，基于视觉特征分析"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.motion_threshold = self.config.get('motion_threshold', 0.3)
        self.scene_change_threshold = self.config.get('scene_change_threshold', 0.5)
        self.similarity_threshold = self.config.get('similarity_threshold', 0.7)
        self.complexity_threshold = self.config.get('complexity_threshold', 0.6)

    def analyze_all_slices(self, slices: List[Dict[str, Any]]) -> List[SliceAnalysis]:
        """分析所有切片"""
        analyses = []
        
        for i, slice_info in enumerate(slices):
            analysis = self.analyze_slice(slice_info, i)
            analyses.append(analysis)
        
        return analyses

    def analyze_slice(self, slice_info: Dict[str, Any], index: int) -> SliceAnalysis:
        """分析单个切片"""
        keyframes = slice_info.get('keyframes', [])
        
        motion_intensity = self._calculate_motion_intensity(keyframes)
        visual_complexity = self._calculate_visual_complexity(keyframes)
        color_variance = self._calculate_color_variance(keyframes)
        keyframe_similarity = self._calculate_keyframe_similarity(keyframes)
        has_scene_change = self._detect_scene_change(keyframes)
        
        suggested_action = self._suggest_action(
            motion_intensity, visual_complexity, keyframe_similarity, has_scene_change
        )
        
        confidence = self._calculate_confidence(
            motion_intensity, visual_complexity, keyframe_similarity
        )
        
        return SliceAnalysis(
            slice_index=index,
            motion_intensity=motion_intensity,
            visual_complexity=visual_complexity,
            color_variance=color_variance,
            keyframe_similarity=keyframe_similarity,
            has_scene_change=has_scene_change,
            suggested_action=suggested_action,
            confidence=confidence
        )

    def _calculate_motion_intensity(self, keyframes: List[str]) -> float:
        """计算运动强度（基于关键帧差异）"""
        if not keyframes or len(keyframes) < 2:
            return 0.0
        
        valid_keyframes = [kf for kf in keyframes if os.path.exists(kf)]
        if len(valid_keyframes) < 2:
            return 0.0
        
        total_diff = 0.0
        count = 0
        
        for i in range(len(valid_keyframes) - 1):
            try:
                # 使用numpy读取图像，避免OpenCV中文路径问题
                img1 = cv2.imdecode(np.fromfile(valid_keyframes[i], dtype=np.uint8), cv2.IMREAD_COLOR)
                img2 = cv2.imdecode(np.fromfile(valid_keyframes[i + 1], dtype=np.uint8), cv2.IMREAD_COLOR)
                
                if img1 is None or img2 is None:
                    continue
                
                img1_gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
                img2_gray = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
                
                img1_resized = cv2.resize(img1_gray, (256, 256))
                img2_resized = cv2.resize(img2_gray, (256, 256))
                
                diff = cv2.absdiff(img1_resized, img2_resized)
                mean_diff = np.mean(diff) / 255.0
                
                total_diff += mean_diff
                count += 1
                
            except Exception as e:
                logger.warning(f"计算运动强度时出错: {e}")
                continue
        
        return total_diff / count if count > 0 else 0.0

    def _calculate_visual_complexity(self, keyframes: List[str]) -> float:
        """计算视觉复杂度（基于边缘密度）"""
        if not keyframes:
            return 0.0
        
        valid_keyframes = [kf for kf in keyframes if os.path.exists(kf)]
        if not valid_keyframes:
            return 0.0
        
        total_complexity = 0.0
        count = 0
        
        for kf in valid_keyframes:
            try:
                # 使用numpy读取图像，避免OpenCV中文路径问题
                img = cv2.imdecode(np.fromfile(kf, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    continue
                
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                gray_resized = cv2.resize(gray, (256, 256))
                
                edges = cv2.Canny(gray_resized, 50, 150)
                edge_density = np.sum(edges > 0) / (256 * 256)
                
                total_complexity += edge_density
                count += 1
                
            except Exception as e:
                logger.warning(f"计算视觉复杂度时出错: {e}")
                continue
        
        return total_complexity / count if count > 0 else 0.0

    def _calculate_color_variance(self, keyframes: List[str]) -> float:
        """计算色彩变化程度"""
        if not keyframes:
            return 0.0
        
        valid_keyframes = [kf for kf in keyframes if os.path.exists(kf)]
        if not valid_keyframes:
            return 0.0
        
        all_colors = []
        
        for kf in valid_keyframes:
            try:
                # 使用numpy读取图像，避免OpenCV中文路径问题
                img = cv2.imdecode(np.fromfile(kf, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    continue
                
                img_resized = cv2.resize(img, (64, 64))
                mean_color = np.mean(img_resized, axis=(0, 1))
                all_colors.append(mean_color)
                
            except Exception as e:
                logger.warning(f"计算色彩变化时出错: {e}")
                continue
        
        if len(all_colors) < 2:
            return 0.0
        
        colors_array = np.array(all_colors)
        variance = np.mean(np.var(colors_array, axis=0))
        
        return min(variance / 10000.0, 1.0)

    def _calculate_keyframe_similarity(self, keyframes: List[str]) -> float:
        """计算关键帧之间的相似度"""
        if not keyframes or len(keyframes) < 2:
            return 1.0
        
        valid_keyframes = [kf for kf in keyframes if os.path.exists(kf)]
        if len(valid_keyframes) < 2:
            return 1.0
        
        total_similarity = 0.0
        count = 0
        
        for i in range(len(valid_keyframes) - 1):
            try:
                # 使用numpy读取图像
                img1 = cv2.imdecode(np.fromfile(valid_keyframes[i], dtype=np.uint8), cv2.IMREAD_COLOR)
                img2 = cv2.imdecode(np.fromfile(valid_keyframes[i + 1], dtype=np.uint8), cv2.IMREAD_COLOR)
                
                if img1 is None or img2 is None:
                    continue
                
                hist1 = self._calculate_histogram(img1)
                hist2 = self._calculate_histogram(img2)
                
                similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
                total_similarity += max(0, similarity)
                count += 1
                
            except Exception as e:
                logger.warning(f"计算关键帧相似度时出错: {e}")
                continue
        
        return total_similarity / count if count > 0 else 1.0

    def _calculate_histogram(self, img: np.ndarray) -> np.ndarray:
        """计算图像直方图"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        return hist

    def _detect_scene_change(self, keyframes: List[str]) -> bool:
        """检测是否有场景变化"""
        if not keyframes or len(keyframes) < 2:
            return False
        
        similarity = self._calculate_keyframe_similarity(keyframes)
        return similarity < self.scene_change_threshold

    def _suggest_action(self, motion_intensity: float, visual_complexity: float,
                       keyframe_similarity: float, has_scene_change: bool) -> str:
        """根据分析结果建议动作"""
        if has_scene_change:
            return "split"
        
        if keyframe_similarity > self.similarity_threshold and motion_intensity < self.motion_threshold:
            return "merge"
        
        if motion_intensity > self.motion_threshold and visual_complexity > self.complexity_threshold:
            return "split"
        
        return "keep"

    def _calculate_confidence(self, motion_intensity: float, 
                             visual_complexity: float, 
                             keyframe_similarity: float) -> float:
        """计算分析置信度"""
        variance = np.var([motion_intensity, visual_complexity, keyframe_similarity])
        confidence = 1.0 - min(variance * 2, 0.5)
        return max(0.5, confidence)

    def get_merge_suggestions(self, analyses: List[SliceAnalysis]) -> List[Tuple[int, int]]:
        """获取可合并的切片对"""
        merge_pairs = []
        
        for i in range(len(analyses) - 1):
            curr = analyses[i]
            next_a = analyses[i + 1]
            
            if (curr.suggested_action == "merge" and 
                next_a.suggested_action == "merge" and
                curr.keyframe_similarity > self.similarity_threshold):
                merge_pairs.append((i, i + 1))
        
        return merge_pairs

    def get_split_suggestions(self, analyses: List[SliceAnalysis]) -> List[int]:
        """获取需要拆分的切片索引"""
        split_indices = []
        
        for i, analysis in enumerate(analyses):
            if analysis.suggested_action == "split":
                split_indices.append(i)
        
        return split_indices

    def calculate_suggested_scene_count(self, analyses: List[SliceAnalysis]) -> int:
        """计算建议的场景数量"""
        base_count = len(analyses)
        
        merge_pairs = self.get_merge_suggestions(analyses)
        merge_reduction = len(merge_pairs)
        
        split_indices = self.get_split_suggestions(analyses)
        split_increase = len(split_indices)
        
        suggested_count = base_count - merge_reduction + split_increase
        
        return max(1, suggested_count)

    def get_initial_suggestion(self, slices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取初步调整建议"""
        analyses = self.analyze_all_slices(slices)
        
        merge_pairs = self.get_merge_suggestions(analyses)
        split_indices = self.get_split_suggestions(analyses)
        suggested_count = self.calculate_suggested_scene_count(analyses)
        
        return {
            'analyses': [a.to_dict() for a in analyses],
            'merge_pairs': merge_pairs,
            'split_indices': split_indices,
            'suggested_scene_count': suggested_count,
            'original_count': len(slices)
        }
