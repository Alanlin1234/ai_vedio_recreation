import cv2
import numpy as np
import os
import asyncio
from typing import Dict, Any

# 尝试导入阿里云图像相似度API模块，如果失败则继续使用本地实现
try:
    from alibabacloud_imagerecog20190930.client import Client as imagerecog20190930Client
    from alibabacloud_tea_openapi import models as open_api_models
    ALIBABA_CLOUD_AVAILABLE = True
except ImportError:
    print("[警告] 阿里云图像相似度API模块未安装，将使用本地相似度计算")
    ALIBABA_CLOUD_AVAILABLE = False

class SimilarityCalculator:
    def __init__(self, config: Dict[str, Any] = None):
# 初始化相似度计算器
        self.config = config or {}
        self.aliyun_client = None
        self.vlm_client = None
        
        # 初始化客户端
        self._init_clients()
    
    def _init_clients(self):
        """初始化所有客户端"""
        # 初始化VLM客户端（优先使用）
        self._init_vlm_client()
        # 初始化阿里云图像相似度API客户端（备选）
        self._init_aliyun_client()
    
    def _init_vlm_client(self):
        """初始化VLM客户端"""
        try:
            from ..models.vlm_client import VLMClient
            self.vlm_client = VLMClient(self.config.get('models', {}))
            vlm_model_name = self.config.get('models', {}).get('vlm_model', 'qwen3-vl')
            print(f"[成功] VLM客户端初始化完成，将优先使用{vlm_model_name}计算图像相似度")
        except Exception as e:
            print(f"[错误] 初始化VLM客户端失败: {e}")
            self.vlm_client = None
    
    def _init_aliyun_client(self):
        """初始化阿里云图像相似度API客户端"""
        try:
            # 检查阿里云模块是否可用
            if not ALIBABA_CLOUD_AVAILABLE:
                print("[警告] 阿里云图像相似度API模块未安装，将使用本地相似度计算")
                return
            
            access_key_id = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID", self.config.get('aliyun_access_key_id'))
            access_key_secret = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET", self.config.get('aliyun_access_key_secret'))
            region_id = os.getenv("ALIBABA_CLOUD_REGION_ID", self.config.get('aliyun_region_id', 'cn-shanghai'))
            
            if not access_key_id or not access_key_secret:
                print("[警告] 阿里云API密钥未配置，将使用本地相似度计算")
                return
            
            config = open_api_models.Config(
                access_key_id=access_key_id,
                access_key_secret=access_key_secret,
                region_id=region_id
            )
            
            self.aliyun_client = imagerecog20190930Client(config)
            print("[成功] 阿里云图像相似度API客户端初始化完成")
        except Exception as e:
            print(f"[错误] 初始化阿里云客户端失败: {e}")
    
    def calculate_clip_similarity(self, image1_path: str, image2_path: str) -> float:
# 使用CLIP模型计算图像相似度
        # 检查文件是否存在
        if not os.path.exists(image1_path) or not os.path.exists(image2_path):
            raise FileNotFoundError("图像文件不存在")
        
        # 优先使用VLM客户端计算图像相似度
        if self.vlm_client:
            try:
                vlm_model_name = self.config.get('models', {}).get('vlm_model', 'qwen3-vl')
                print(f"[VLM API] 使用{vlm_model_name}计算图像相似度: {image1_path} vs {image2_path}")
                
                # 运行异步VLM方法
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环已经在运行，使用create_task
                    result = loop.run_until_complete(
                        self.vlm_client.analyze_keyframe_consistency(image1_path, image2_path)
                    )
                else:
                    # 否则直接运行
                    result = loop.run_until_complete(
                        self.vlm_client.analyze_keyframe_consistency(image1_path, image2_path)
                    )
                
                # 提取相似度分数
                similarity = result.get('consistency_analysis', {}).get('overall_consistency', 0.0)
                print(f"[VLM API] 相似度分数: {similarity}")
                
                return similarity
            except Exception as e:
                print(f"[错误] VLM图像相似度计算失败: {e}")
                # 回退到其他方法
        
        # 其次使用阿里云图像相似度API
        if ALIBABA_CLOUD_AVAILABLE and self.aliyun_client:
            try:
                print(f"[阿里云API] 计算图像相似度: {image1_path} vs {image2_path}")
                
                # 构建请求
                from alibabacloud_imagerecog20190930 import models as imagerecog_20190930_models
                
                request = imagerecog_20190930_models.CompareImageRequest(
                    image_url_object_a=image1_path,
                    image_url_object_b=image2_path
                )
                
                # 发送请求
                response = self.aliyun_client.compare_image(request)
                
                # 提取相似度分数
                similarity = response.body.data.confidence
                print(f"[阿里云API] 相似度分数: {similarity}")
                
                return similarity
            except Exception as e:
                print(f"[错误] 阿里云图像相似度计算失败: {e}")
                # 回退到本地实现
        
        print(f"[本地计算] 计算图像相似度: {image1_path} vs {image2_path}")
        
        # 本地实现：读取图像
        image1 = cv2.imread(image1_path)
        image2 = cv2.imread(image2_path)
        
        if image1 is None or image2 is None:
            raise ValueError("无法读取图像")
        
        # 转换为灰度图
        gray1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
        
        # 调整大小以提高计算速度
        gray1 = cv2.resize(gray1, (128, 128))
        gray2 = cv2.resize(gray2, (128, 128))
        
        # 使用结构相似度作为近似
        ssim_score = self.calculate_structural_similarity(image1_path, image2_path)
        
        # 模拟CLIP相似度，结合SSIM和直方图相似度
        hist_score = self.calculate_histogram_similarity(
            cv2.calcHist([image1], [0], None, [256], [0, 256]),
            cv2.calcHist([image2], [0], None, [256], [0, 256])
        )
        
        # 加权平均
        result = (ssim_score * 0.7 + hist_score * 0.3)
        print(f"[本地计算] 相似度分数: {result}")
        return result
    
    def calculate_histogram_similarity(self, hist1: np.ndarray, hist2: np.ndarray) -> float:
# 计算直方图相似度
        # 确保直方图是一维的
        hist1 = hist1.flatten()
        hist2 = hist2.flatten()
        
        # 使用相关性方法计算相似度
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        
        # 相关性范围是[-1, 1]，转换为[0, 1]
        similarity = (correlation + 1) / 2
        
        return similarity
    
    def calculate_structural_similarity(self, image1_path: str, image2_path: str) -> float:
# 计算结构相似度
        from skimage.metrics import structural_similarity as ssim
        
        # 检查文件是否存在
        if not os.path.exists(image1_path) or not os.path.exists(image2_path):
            raise FileNotFoundError("图像文件不存在")
        
        # 读取图像
        image1 = cv2.imread(image1_path)
        image2 = cv2.imread(image2_path)
        
        if image1 is None or image2 is None:
            raise ValueError("无法读取图像")
        
        # 转换为灰度图
        gray1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
        
        # 调整图像大小以匹配
        if gray1.shape != gray2.shape:
            gray2 = cv2.resize(gray2, gray1.shape[::-1])
        
        # 计算SSIM
        ssim_score, _ = ssim(gray1, gray2, full=True)
        
        return ssim_score
    
    def calculate_color_similarity(self, features1: Dict[str, Any], features2: Dict[str, Any]) -> float:
# 计算颜色相似度
        # 计算每个通道的直方图相似度
        sim_b = self.calculate_histogram_similarity(
            features1['color_histograms']['blue'],
            features2['color_histograms']['blue']
        )
        sim_g = self.calculate_histogram_similarity(
            features1['color_histograms']['green'],
            features2['color_histograms']['green']
        )
        sim_r = self.calculate_histogram_similarity(
            features1['color_histograms']['red'],
            features2['color_histograms']['red']
        )
        
        # 平均三个通道的相似度
        return (sim_b + sim_g + sim_r) / 3
    
    def calculate_overall_visual_similarity(self, image1_path: str, image2_path: str) -> float:
# 计算整体视觉相似度
        from .feature_extractor import FeatureExtractor
        
        extractor = FeatureExtractor()
        
        # 提取特征
        features1 = extractor.extract_keyframe_features(image1_path)
        features2 = extractor.extract_keyframe_features(image2_path)
        
        # 计算颜色相似度
        color_sim = self.calculate_color_similarity(features1, features2)
        
        # 计算结构相似度
        ssim_score = self.calculate_structural_similarity(image1_path, image2_path)
        
        # 加权平均
        return (color_sim * 0.6 + ssim_score * 0.4)

