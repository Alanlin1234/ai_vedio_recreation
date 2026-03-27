"""
深度学习特征提取器
用于视频一致性检测的深度学习特征提取
"""
import os
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class DeepFeatureExtractor:
    """深度学习特征提取器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.device = self.config.get('device', 'cpu')
        
        self.clip_model = None
        self.clip_preprocess = None
        self.face_encoder = None
        self.vgg_model = None
        
        self._init_models()
    
    def _init_models(self):
        """初始化所有模型"""
        self._init_clip()
        self._init_face_encoder()
        self._init_vgg()
    
    def _init_clip(self):
        """初始化CLIP模型"""
        try:
            import torch
            from transformers import CLIPProcessor, CLIPModel
            
            model_name = self.config.get('clip_model', 'openai/clip-vit-base-patch32')
            logger.info(f"[CLIP] 加载模型: {model_name}")
            
            self.clip_model = CLIPModel.from_pretrained(model_name)
            self.clip_processor = CLIPProcessor.from_pretrained(model_name)
            
            if torch.cuda.is_available() and self.device == 'cuda':
                self.clip_model = self.clip_model.to('cuda')
            
            logger.info("[CLIP] 模型加载成功")
        except Exception as e:
            logger.warning(f"[CLIP] 模型加载失败: {e}，将使用简化版本")
            self.clip_model = None
            self.clip_processor = None
    
    def _init_face_encoder(self):
        """初始化人脸编码器"""
        try:
            import torch
            from facenet_pytorch import InceptionResnetV1
            
            logger.info("[FaceEncoder] 加载人脸识别模型")
            
            self.face_encoder = InceptionResnetV1(pretrained='vggface2').eval()
            
            if torch.cuda.is_available() and self.device == 'cuda':
                self.face_encoder = self.face_encoder.to('cuda')
            
            logger.info("[FaceEncoder] 模型加载成功")
        except Exception as e:
            logger.warning(f"[FaceEncoder] 模型加载失败: {e}")
            self.face_encoder = None
    
    def _init_vgg(self):
        """初始化VGG感知模型"""
        try:
            import torch
            import torchvision.models as models
            
            logger.info("[VGG] 加载VGG感知模型")
            
            vgg = models.vgg19(pretrained=True).features
            self.vgg_model = vgg.eval()
            
            for param in self.vgg_model.parameters():
                param.requires_grad = False
            
            if torch.cuda.is_available() and self.device == 'cuda':
                self.vgg_model = self.vgg_model.to('cuda')
            
            logger.info("[VGG] 模型加载成功")
        except Exception as e:
            logger.warning(f"[VGG] 模型加载失败: {e}")
            self.vgg_model = None
    
    def extract_clip_embedding(self, image_path: str) -> Optional[np.ndarray]:
        """
        提取CLIP图像嵌入向量
        
        Args:
            image_path: 图像路径
            
        Returns:
            512维的CLIP嵌入向量
        """
        if not self.clip_model or not self.clip_processor:
            return None
        
        try:
            from PIL import Image
            import torch
            
            image = Image.open(image_path).convert('RGB')
            inputs = self.clip_processor(images=image, return_tensors="pt")
            
            if torch.cuda.is_available() and self.device == 'cuda':
                inputs = {k: v.to('cuda') for k, v in inputs.items()}
            
            with torch.no_grad():
                image_features = self.clip_model.get_image_features(**inputs)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            return image_features.cpu().numpy().flatten()
            
        except Exception as e:
            logger.error(f"[CLIP] 特征提取失败: {e}")
            return None
    
    def extract_face_embedding(self, image_path: str) -> Optional[np.ndarray]:
        """
        提取人脸嵌入向量
        
        Args:
            image_path: 图像路径
            
        Returns:
            512维的人脸嵌入向量
        """
        if not self.face_encoder:
            return None
        
        try:
            import torch
            from PIL import Image
            from facenet_pytorch import MTCNN
            
            mtcnn = MTCNN(device=self.device)
            image = Image.open(image_path).convert('RGB')
            
            face = mtcnn(image)
            if face is None:
                logger.warning(f"[FaceEncoder] 未检测到人脸: {image_path}")
                return None
            
            face = face.unsqueeze(0)
            if torch.cuda.is_available() and self.device == 'cuda':
                face = face.to('cuda')
            
            with torch.no_grad():
                embedding = self.face_encoder(face)
            
            return embedding.cpu().numpy().flatten()
            
        except Exception as e:
            logger.error(f"[FaceEncoder] 人脸特征提取失败: {e}")
            return None
    
    def extract_vgg_features(self, image_path: str, layers: List[int] = None) -> Optional[np.ndarray]:
        """
        提取VGG感知特征
        
        Args:
            image_path: 图像路径
            layers: 要提取的层索引列表
            
        Returns:
            VGG特征向量
        """
        if not self.vgg_model:
            return None
        
        try:
            import torch
            from torchvision import transforms
            from PIL import Image
            
            if layers is None:
                layers = [4, 9, 18, 27, 36]
            
            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225])
            ])
            
            image = Image.open(image_path).convert('RGB')
            image_tensor = transform(image).unsqueeze(0)
            
            if torch.cuda.is_available() and self.device == 'cuda':
                image_tensor = image_tensor.to('cuda')
            
            features = []
            with torch.no_grad():
                for i, layer in enumerate(self.vgg_model):
                    image_tensor = layer(image_tensor)
                    if i in layers:
                        features.append(image_tensor.flatten())
            
            combined_features = torch.cat(features)
            return combined_features.cpu().numpy()
            
        except Exception as e:
            logger.error(f"[VGG] 特征提取失败: {e}")
            return None
    
    def extract_all_features(self, image_path: str) -> Dict[str, Any]:
        """
        提取所有深度学习特征
        
        Args:
            image_path: 图像路径
            
        Returns:
            包含所有特征的字典
        """
        features = {
            'clip_embedding': None,
            'face_embedding': None,
            'vgg_features': None
        }
        
        features['clip_embedding'] = self.extract_clip_embedding(image_path)
        features['face_embedding'] = self.extract_face_embedding(image_path)
        features['vgg_features'] = self.extract_vgg_features(image_path)
        
        return features


class DeepSimilarityCalculator:
    """深度学习相似度计算器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.feature_extractor = DeepFeatureExtractor(config)
    
    def calculate_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        if vec1 is None or vec2 is None:
            return 0.0
        
        vec1 = vec1.flatten()
        vec2 = vec2.flatten()
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def calculate_clip_similarity(self, image1_path: str, image2_path: str) -> float:
        """
        计算CLIP语义相似度
        
        Args:
            image1_path: 图像1路径
            image2_path: 图像2路径
            
        Returns:
            CLIP相似度分数 (0-1)
        """
        emb1 = self.feature_extractor.extract_clip_embedding(image1_path)
        emb2 = self.feature_extractor.extract_clip_embedding(image2_path)
        
        if emb1 is None or emb2 is None:
            logger.warning("[CLIP相似度] 无法提取CLIP特征，返回默认值")
            return 0.5
        
        similarity = self.calculate_cosine_similarity(emb1, emb2)
        return (similarity + 1) / 2
    
    def calculate_face_similarity(self, image1_path: str, image2_path: str) -> float:
        """
        计算人脸相似度
        
        Args:
            image1_path: 图像1路径
            image2_path: 图像2路径
            
        Returns:
            人脸相似度分数 (0-1)，如果未检测到人脸返回None
        """
        emb1 = self.feature_extractor.extract_face_embedding(image1_path)
        emb2 = self.feature_extractor.extract_face_embedding(image2_path)
        
        if emb1 is None or emb2 is None:
            return None
        
        similarity = self.calculate_cosine_similarity(emb1, emb2)
        return (similarity + 1) / 2
    
    def calculate_perceptual_similarity(self, image1_path: str, image2_path: str) -> float:
        """
        计算感知相似度（基于VGG特征）
        
        Args:
            image1_path: 图像1路径
            image2_path: 图像2路径
            
        Returns:
            感知相似度分数 (0-1)
        """
        feat1 = self.feature_extractor.extract_vgg_features(image1_path)
        feat2 = self.feature_extractor.extract_vgg_features(image2_path)
        
        if feat1 is None or feat2 is None:
            logger.warning("[感知相似度] 无法提取VGG特征，返回默认值")
            return 0.5
        
        similarity = self.calculate_cosine_similarity(feat1, feat2)
        return (similarity + 1) / 2
    
    def calculate_deep_similarity(self, image1_path: str, image2_path: str) -> Dict[str, Any]:
        """
        计算所有深度学习相似度
        
        Args:
            image1_path: 图像1路径
            image2_path: 图像2路径
            
        Returns:
            包含所有相似度分数的字典
        """
        results = {
            'clip_similarity': None,
            'face_similarity': None,
            'perceptual_similarity': None,
            'overall_deep_similarity': None
        }
        
        results['clip_similarity'] = self.calculate_clip_similarity(image1_path, image2_path)
        results['face_similarity'] = self.calculate_face_similarity(image1_path, image2_path)
        results['perceptual_similarity'] = self.calculate_perceptual_similarity(image1_path, image2_path)
        
        valid_scores = [s for s in [results['clip_similarity'], 
                                    results['perceptual_similarity']] if s is not None]
        
        if results['face_similarity'] is not None:
            valid_scores.append(results['face_similarity'])
        
        if valid_scores:
            results['overall_deep_similarity'] = np.mean(valid_scores)
        else:
            results['overall_deep_similarity'] = 0.5
        
        return results


class OpticalFlowAnalyzer:
    """光流分析器 - 用于检测运动一致性"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
    
    def extract_frames(self, video_path: str, num_frames: int = 10) -> List[np.ndarray]:
        """从视频中提取帧"""
        frames = []
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logger.error(f"[光流分析] 无法打开视频: {video_path}")
            return frames
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        step = max(1, total_frames // num_frames)
        
        for i in range(num_frames):
            frame_idx = i * step
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
        
        cap.release()
        return frames
    
    def calculate_optical_flow(self, frame1: np.ndarray, frame2: np.ndarray) -> np.ndarray:
        """计算两帧之间的光流"""
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        flow = cv2.calcOpticalFlowFarneback(
            gray1, gray2, None,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0
        )
        
        return flow
    
    def calculate_motion_consistency(self, video1_path: str, video2_path: str) -> Dict[str, Any]:
        """
        计算两个视频之间的运动一致性
        
        Args:
            video1_path: 视频1路径
            video2_path: 视频2路径
            
        Returns:
            运动一致性分析结果
        """
        frames1 = self.extract_frames(video1_path, num_frames=5)
        frames2 = self.extract_frames(video2_path, num_frames=5)
        
        if len(frames1) < 2 or len(frames2) < 2:
            return {
                'success': False,
                'motion_consistency': 0.5,
                'error': '帧数不足'
            }
        
        flows1 = []
        flows2 = []
        
        for i in range(len(frames1) - 1):
            flow = self.calculate_optical_flow(frames1[i], frames1[i+1])
            flows1.append(flow)
        
        for i in range(len(frames2) - 1):
            flow = self.calculate_optical_flow(frames2[i], frames2[i+1])
            flows2.append(flow)
        
        avg_flow1 = np.mean(flows1, axis=0)
        avg_flow2 = np.mean(flows2, axis=0)
        
        flow_diff = np.abs(avg_flow1 - avg_flow2)
        flow_diff_norm = np.linalg.norm(flow_diff) / (flow_diff.size ** 0.5)
        
        motion_consistency = 1.0 / (1.0 + flow_diff_norm)
        
        return {
            'success': True,
            'motion_consistency': float(motion_consistency),
            'avg_flow_magnitude_1': float(np.mean(np.linalg.norm(avg_flow1, axis=2))),
            'avg_flow_magnitude_2': float(np.mean(np.linalg.norm(avg_flow2, axis=2))),
            'flow_difference': float(flow_diff_norm)
        }


class EnhancedConsistencyChecker:
    """增强版一致性检查器 - 融合深度学习和VLM"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        self.deep_similarity = DeepSimilarityCalculator(config)
        self.optical_flow = OpticalFlowAnalyzer(config)
        
        self.weights = self.config.get('weights', {
            'clip': 0.25,
            'face': 0.20,
            'perceptual': 0.15,
            'ssim': 0.15,
            'color': 0.10,
            'vlm': 0.15
        })
        
        self.vlm_client = None
        self._init_vlm()
    
    def _init_vlm(self):
        """初始化VLM客户端"""
        try:
            from ..models.vlm_client import VLMClient
            self.vlm_client = VLMClient(self.config.get('models', {}))
            logger.info("[VLM] 客户端初始化成功")
        except Exception as e:
            logger.warning(f"[VLM] 客户端初始化失败: {e}")
    
    def check_consistency(self, 
                          image1_path: str, 
                          image2_path: str,
                          video1_path: str = None,
                          video2_path: str = None) -> Dict[str, Any]:
        """
        综合一致性检查
        
        Args:
            image1_path: 图像1路径（关键帧）
            image2_path: 图像2路径（关键帧）
            video1_path: 视频1路径（可选，用于光流分析）
            video2_path: 视频2路径（可选，用于光流分析）
            
        Returns:
            综合一致性检查结果
        """
        results = {
            'deep_learning_scores': {},
            'traditional_scores': {},
            'vlm_scores': {},
            'motion_scores': {},
            'overall_score': 0.0,
            'passed': False,
            'issues': [],
            'suggestions': []
        }
        
        results['deep_learning_scores'] = self.deep_similarity.calculate_deep_similarity(
            image1_path, image2_path
        )
        
        results['traditional_scores'] = self._calculate_traditional_scores(image1_path, image2_path)
        
        if self.vlm_client:
            results['vlm_scores'] = self._calculate_vlm_scores(image1_path, image2_path)
        
        if video1_path and video2_path:
            results['motion_scores'] = self.optical_flow.calculate_motion_consistency(
                video1_path, video2_path
            )
        
        results['overall_score'] = self._calculate_weighted_score(results)
        
        threshold = self.config.get('threshold', 0.75)
        results['passed'] = results['overall_score'] >= threshold
        
        results['issues'] = self._identify_issues(results)
        results['suggestions'] = self._generate_suggestions(results)
        
        return results
    
    def _calculate_traditional_scores(self, image1_path: str, image2_path: str) -> Dict[str, float]:
        """计算传统CV分数"""
        from .similarity import SimilarityCalculator
        
        calc = SimilarityCalculator(self.config)
        
        return {
            'ssim': calc.calculate_structural_similarity(image1_path, image2_path),
            'color_similarity': calc.calculate_overall_visual_similarity(image1_path, image2_path)
        }
    
    def _calculate_vlm_scores(self, image1_path: str, image2_path: str) -> Dict[str, Any]:
        """计算VLM分数"""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return {'vlm_consistency': 0.8}
            
            result = loop.run_until_complete(
                self.vlm_client.analyze_keyframe_consistency(image1_path, image2_path)
            )
            
            return {
                'vlm_consistency': result.get('consistency_analysis', {}).get('overall_consistency', 0.8)
            }
        except Exception as e:
            logger.error(f"[VLM] 分数计算失败: {e}")
            return {'vlm_consistency': 0.8}
    
    def _calculate_weighted_score(self, results: Dict[str, Any]) -> float:
        """计算加权总分"""
        scores = []
        weights = []
        
        deep = results['deep_learning_scores']
        if deep.get('clip_similarity') is not None:
            scores.append(deep['clip_similarity'])
            weights.append(self.weights['clip'])
        
        if deep.get('face_similarity') is not None:
            scores.append(deep['face_similarity'])
            weights.append(self.weights['face'])
        
        if deep.get('perceptual_similarity') is not None:
            scores.append(deep['perceptual_similarity'])
            weights.append(self.weights['perceptual'])
        
        trad = results['traditional_scores']
        if trad.get('ssim') is not None:
            scores.append(trad['ssim'])
            weights.append(self.weights['ssim'])
        
        if trad.get('color_similarity') is not None:
            scores.append(trad['color_similarity'])
            weights.append(self.weights['color'])
        
        vlm = results['vlm_scores']
        if vlm.get('vlm_consistency') is not None:
            scores.append(vlm['vlm_consistency'])
            weights.append(self.weights['vlm'])
        
        motion = results['motion_scores']
        if motion.get('motion_consistency') is not None:
            scores.append(motion['motion_consistency'])
            weights.append(0.10)
        
        if not scores:
            return 0.5
        
        total_weight = sum(weights)
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        
        return weighted_sum / total_weight
    
    def _identify_issues(self, results: Dict[str, Any]) -> List[str]:
        """识别问题"""
        issues = []
        threshold = self.config.get('issue_threshold', 0.7)
        
        deep = results['deep_learning_scores']
        if deep.get('clip_similarity') is not None and deep['clip_similarity'] < threshold:
            issues.append(f"语义相似度较低 ({deep['clip_similarity']:.2f})")
        
        if deep.get('face_similarity') is not None and deep['face_similarity'] < threshold:
            issues.append(f"人脸一致性较低 ({deep['face_similarity']:.2f})")
        
        trad = results['traditional_scores']
        if trad.get('ssim') is not None and trad['ssim'] < threshold:
            issues.append(f"结构相似度较低 ({trad['ssim']:.2f})")
        
        return issues
    
    def _generate_suggestions(self, results: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        deep = results['deep_learning_scores']
        if deep.get('clip_similarity') is not None and deep['clip_similarity'] < 0.7:
            suggestions.append("建议调整提示词，确保场景语义一致性")
        
        if deep.get('face_similarity') is not None and deep['face_similarity'] < 0.7:
            suggestions.append("建议使用相同的人物参考图，确保人物外观一致")
        
        trad = results['traditional_scores']
        if trad.get('ssim') is not None and trad['ssim'] < 0.7:
            suggestions.append("建议调整生成参数，提高图像结构一致性")
        
        motion = results['motion_scores']
        if motion.get('motion_consistency') is not None and motion['motion_consistency'] < 0.7:
            suggestions.append("建议调整运动参数，确保动作流畅性")
        
        return suggestions
