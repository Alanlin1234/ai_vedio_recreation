"""
训练数据准备脚本
用于从现有视频生成一致性检测训练数据
"""
import os
import json
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TrainingDataPreparer:
    """训练数据准备器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.output_dir = self.config.get('output_dir', 'data/consistency_dataset')
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.frames_dir = os.path.join(self.output_dir, 'frames')
        os.makedirs(self.frames_dir, exist_ok=True)
    
    def extract_frames_from_video(self, 
                                   video_path: str, 
                                   num_frames: int = 5,
                                   prefix: str = None) -> List[str]:
        """从视频中提取关键帧"""
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logger.error(f"[提取] 无法打开视频: {video_path}")
            return []
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        step = max(1, total_frames // num_frames)
        
        video_name = prefix or Path(video_path).stem
        frame_paths = []
        
        for i in range(num_frames):
            frame_idx = i * step
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            
            ret, frame = cap.read()
            if ret:
                frame_path = os.path.join(self.frames_dir, f"{video_name}_frame_{i:03d}.jpg")
                cv2.imwrite(frame_path, frame)
                frame_paths.append(frame_path)
        
        cap.release()
        return frame_paths
    
    def calculate_ssim(self, image1_path: str, image2_path: str) -> float:
        """计算SSIM"""
        from skimage.metrics import structural_similarity as ssim
        
        img1 = cv2.imread(image1_path, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imread(image2_path, cv2.IMREAD_GRAYSCALE)
        
        if img1 is None or img2 is None:
            return 0.5
        
        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
        
        score, _ = ssim(img1, img2, full=True)
        return float(score)
    
    def calculate_color_similarity(self, image1_path: str, image2_path: str) -> float:
        """计算颜色相似度"""
        img1 = cv2.imread(image1_path)
        img2 = cv2.imread(image2_path)
        
        if img1 is None or img2 is None:
            return 0.5
        
        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
        
        hist1 = cv2.calcHist([img1], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist2 = cv2.calcHist([img2], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        
        hist1 = cv2.normalize(hist1, hist1).flatten()
        hist2 = cv2.normalize(hist2, hist2).flatten()
        
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        return float((correlation + 1) / 2)
    
    def calculate_edge_similarity(self, image1_path: str, image2_path: str) -> float:
        """计算边缘相似度"""
        img1 = cv2.imread(image1_path, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imread(image2_path, cv2.IMREAD_GRAYSCALE)
        
        if img1 is None or img2 is None:
            return 0.5
        
        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
        
        edges1 = cv2.Canny(img1, 100, 200)
        edges2 = cv2.Canny(img2, 100, 200)
        
        intersection = np.logical_and(edges1, edges2).sum()
        union = np.logical_or(edges1, edges2).sum()
        
        if union == 0:
            return 1.0
        
        return float(intersection / union)
    
    def auto_label(self, image1_path: str, image2_path: str) -> Tuple[float, Dict[str, float]]:
        """
        自动标注样本
        返回综合标签和各项分数
        """
        ssim = self.calculate_ssim(image1_path, image2_path)
        color = self.calculate_color_similarity(image1_path, image2_path)
        edge = self.calculate_edge_similarity(image1_path, image2_path)
        
        weights = self.config.get('label_weights', {
            'ssim': 0.5,
            'color': 0.3,
            'edge': 0.2
        })
        
        overall = (
            ssim * weights['ssim'] +
            color * weights['color'] +
            edge * weights['edge']
        )
        
        scores = {
            'ssim': ssim,
            'color': color,
            'edge': edge
        }
        
        return overall, scores
    
    def prepare_from_video_directory(self, 
                                      video_dir: str,
                                      train_ratio: float = 0.8,
                                      min_label: float = 0.3,
                                      max_label: float = 1.0):
        """
        从视频目录准备训练数据
        
        Args:
            video_dir: 视频目录
            train_ratio: 训练集比例
            min_label: 最小标签值（过滤低质量样本）
            max_label: 最大标签值
        """
        video_files = sorted([
            f for f in os.listdir(video_dir) 
            if f.endswith(('.mp4', '.avi', '.mov', '.mkv'))
        ])
        
        logger.info(f"[准备] 发现 {len(video_files)} 个视频文件")
        
        all_samples = []
        
        for i, video_file in enumerate(video_files):
            video_path = os.path.join(video_dir, video_file)
            logger.info(f"[处理] {i+1}/{len(video_files)}: {video_file}")
            
            frames = self.extract_frames_from_video(video_path, num_frames=5)
            
            for j in range(len(frames) - 1):
                frame1 = frames[j]
                frame2 = frames[j + 1]
                
                label, scores = self.auto_label(frame1, frame2)
                
                if min_label <= label <= max_label:
                    sample = {
                        'image1': os.path.relpath(frame1, self.output_dir),
                        'image2': os.path.relpath(frame2, self.output_dir),
                        'label': round(label, 4),
                        'scores': scores,
                        'metadata': {
                            'video': video_file,
                            'frame_indices': [j, j + 1]
                        }
                    }
                    all_samples.append(sample)
        
        logger.info(f"[准备] 生成 {len(all_samples)} 个样本")
        
        np.random.shuffle(all_samples)
        
        split_idx = int(len(all_samples) * train_ratio)
        train_samples = all_samples[:split_idx]
        val_samples = all_samples[split_idx:]
        
        train_data = {'samples': train_samples}
        val_data = {'samples': val_samples}
        
        train_path = os.path.join(self.output_dir, 'consistency_train.json')
        val_path = os.path.join(self.output_dir, 'consistency_val.json')
        
        with open(train_path, 'w', encoding='utf-8') as f:
            json.dump(train_data, f, indent=2, ensure_ascii=False)
        
        with open(val_path, 'w', encoding='utf-8') as f:
            json.dump(val_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[保存] 训练集: {train_path} ({len(train_samples)} 样本)")
        logger.info(f"[保存] 验证集: {val_path} ({len(val_samples)} 样本)")
        
        self._generate_statistics(all_samples)
        
        return train_path, val_path
    
    def prepare_from_scene_pairs(self, 
                                  scene_pairs: List[Dict[str, Any]],
                                  train_ratio: float = 0.8):
        """
        从场景对准备训练数据
        
        Args:
            scene_pairs: 场景对列表，格式:
                [
                    {
                        'scene1': {'video_path': '...', 'keyframes': [...]},
                        'scene2': {'video_path': '...', 'keyframes': [...]},
                        'manual_label': 0.85  # 可选的手动标签
                    }
                ]
        """
        all_samples = []
        
        for i, pair in enumerate(scene_pairs):
            scene1 = pair['scene1']
            scene2 = pair['scene2']
            
            kf1 = scene1.get('keyframes', [])
            kf2 = scene2.get('keyframes', [])
            
            if kf1 and kf2:
                frame1 = kf1[-1] if isinstance(kf1[-1], str) else kf1[-1].get('path', '')
                frame2 = kf2[0] if isinstance(kf2[0], str) else kf2[0].get('path', '')
                
                if os.path.exists(frame1) and os.path.exists(frame2):
                    if 'manual_label' in pair:
                        label = pair['manual_label']
                        scores = {}
                    else:
                        label, scores = self.auto_label(frame1, frame2)
                    
                    sample = {
                        'image1': os.path.relpath(frame1, self.output_dir),
                        'image2': os.path.relpath(frame2, self.output_dir),
                        'label': round(label, 4),
                        'scores': scores,
                        'metadata': {
                            'scene1_video': scene1.get('video_path', ''),
                            'scene2_video': scene2.get('video_path', ''),
                            'pair_id': i
                        }
                    }
                    all_samples.append(sample)
        
        np.random.shuffle(all_samples)
        
        split_idx = int(len(all_samples) * train_ratio)
        train_samples = all_samples[:split_idx]
        val_samples = all_samples[split_idx:]
        
        train_data = {'samples': train_samples}
        val_data = {'samples': val_samples}
        
        train_path = os.path.join(self.output_dir, 'consistency_train.json')
        val_path = os.path.join(self.output_dir, 'consistency_val.json')
        
        with open(train_path, 'w', encoding='utf-8') as f:
            json.dump(train_data, f, indent=2, ensure_ascii=False)
        
        with open(val_path, 'w', encoding='utf-8') as f:
            json.dump(val_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[保存] 训练集: {train_path} ({len(train_samples)} 样本)")
        logger.info(f"[保存] 验证集: {val_path} ({len(val_samples)} 样本)")
        
        return train_path, val_path
    
    def _generate_statistics(self, samples: List[Dict[str, Any]]):
        """生成数据集统计信息"""
        labels = [s['label'] for s in samples]
        
        stats = {
            'total_samples': len(samples),
            'label_statistics': {
                'min': float(np.min(labels)),
                'max': float(np.max(labels)),
                'mean': float(np.mean(labels)),
                'std': float(np.std(labels)),
                'median': float(np.median(labels))
            },
            'label_distribution': {
                '0.0-0.2': len([l for l in labels if 0.0 <= l < 0.2]),
                '0.2-0.4': len([l for l in labels if 0.2 <= l < 0.4]),
                '0.4-0.6': len([l for l in labels if 0.4 <= l < 0.6]),
                '0.6-0.8': len([l for l in labels if 0.6 <= l < 0.8]),
                '0.8-1.0': len([l for l in labels if 0.8 <= l <= 1.0])
            },
            'created_at': datetime.now().isoformat()
        }
        
        stats_path = os.path.join(self.output_dir, 'dataset_statistics.json')
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[统计] 标签均值: {stats['label_statistics']['mean']:.4f}")
        logger.info(f"[统计] 标签标准差: {stats['label_statistics']['std']:.4f}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='准备一致性检测训练数据')
    parser.add_argument('--video-dir', '-v', type=str, required=True,
                       help='视频目录路径')
    parser.add_argument('--output', '-o', type=str, default='data/consistency_dataset',
                       help='输出目录')
    parser.add_argument('--train-ratio', '-r', type=float, default=0.8,
                       help='训练集比例')
    parser.add_argument('--min-label', type=float, default=0.3,
                       help='最小标签值')
    
    args = parser.parse_args()
    
    preparer = TrainingDataPreparer({'output_dir': args.output})
    
    preparer.prepare_from_video_directory(
        video_dir=args.video_dir,
        train_ratio=args.train_ratio,
        min_label=args.min_label
    )


if __name__ == "__main__":
    main()
