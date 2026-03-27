"""
视频一致性检测模型训练框架
支持预训练模型微调和一致性评分模型训练
"""
import os
import json
import random
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
import numpy as np
import cv2
from PIL import Image

logger = logging.getLogger(__name__)


class ConsistencyDataset(Dataset):
    """
    一致性检测数据集
    
    数据格式:
    {
        "samples": [
            {
                "image1": "path/to/image1.jpg",
                "image2": "path/to/image2.jpg",
                "label": 0.85,
                "metadata": {
                    "scene_id": 1,
                    "video_source": "video1.mp4"
                }
            }
        ]
    }
    """
    
    def __init__(self, 
                 data_path: str, 
                 transform=None,
                 feature_extractor=None):
        self.data_path = data_path
        self.transform = transform
        self.feature_extractor = feature_extractor
        
        with open(data_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        self.samples = self.data.get('samples', [])
        
        logger.info(f"[数据集] 加载 {len(self.samples)} 个样本")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        image1 = self._load_image(sample['image1'])
        image2 = self._load_image(sample['image2'])
        label = float(sample.get('label', 0.5))
        
        if self.transform:
            image1 = self.transform(image1)
            image2 = self.transform(image2)
        
        return {
            'image1': image1,
            'image2': image2,
            'label': torch.tensor(label, dtype=torch.float32),
            'metadata': sample.get('metadata', {})
        }
    
    def _load_image(self, path: str) -> Image.Image:
        if not os.path.isabs(path):
            base_dir = os.path.dirname(self.data_path)
            path = os.path.join(base_dir, path)
        
        return Image.open(path).convert('RGB')


class ConsistencyScoringHead(nn.Module):
    """
    一致性评分头
    将多个特征融合并输出一致性分数
    """
    
    def __init__(self, 
                 clip_dim: int = 512,
                 face_dim: int = 512,
                 vgg_dim: int = 8192,
                 hidden_dim: int = 256):
        super().__init__()
        
        total_dim = clip_dim + face_dim + vgg_dim
        
        self.feature_fusion = nn.Sequential(
            nn.Linear(total_dim * 2, hidden_dim * 2),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        self.score_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
        
        self.confidence_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
    
    def forward(self, features1: Dict[str, torch.Tensor], 
                features2: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        feat1 = torch.cat([
            features1.get('clip', torch.zeros(features1.get('clip', torch.zeros(1)).shape[0], 512)),
            features1.get('face', torch.zeros(features1.get('face', torch.zeros(1)).shape[0], 512)),
            features1.get('vgg', torch.zeros(features1.get('vgg', torch.zeros(1)).shape[0], 8192))
        ], dim=-1)
        
        feat2 = torch.cat([
            features2.get('clip', torch.zeros(features2.get('clip', torch.zeros(1)).shape[0], 512)),
            features2.get('face', torch.zeros(features2.get('face', torch.zeros(1)).shape[0], 512)),
            features2.get('vgg', torch.zeros(features2.get('vgg', torch.zeros(1)).shape[0], 8192))
        ], dim=-1)
        
        combined = torch.cat([feat1, feat2], dim=-1)
        
        fused = self.feature_fusion(combined)
        
        score = self.score_head(fused)
        confidence = self.confidence_head(fused)
        
        return {
            'score': score.squeeze(-1),
            'confidence': confidence.squeeze(-1)
        }


class ConsistencyModel(nn.Module):
    """
    完整的一致性检测模型
    包含特征提取器和评分头
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__()
        self.config = config or {}
        
        self.clip_model = None
        self.clip_processor = None
        self.face_encoder = None
        self.vgg_model = None
        
        self.score_head = ConsistencyScoringHead(
            clip_dim=self.config.get('clip_dim', 512),
            face_dim=self.config.get('face_dim', 512),
            vgg_dim=self.config.get('vgg_dim', 8192)
        )
        
        self._init_pretrained_models()
    
    def _init_pretrained_models(self):
        """初始化预训练模型"""
        if self.config.get('use_clip', True):
            try:
                from transformers import CLIPModel, CLIPProcessor
                model_name = self.config.get('clip_model', 'openai/clip-vit-base-patch32')
                self.clip_model = CLIPModel.from_pretrained(model_name)
                self.clip_processor = CLIPProcessor.from_pretrained(model_name)
                logger.info(f"[模型] CLIP加载成功: {model_name}")
            except Exception as e:
                logger.warning(f"[模型] CLIP加载失败: {e}")
        
        if self.config.get('use_face', True):
            try:
                from facenet_pytorch import InceptionResnetV1
                self.face_encoder = InceptionResnetV1(pretrained='vggface2').eval()
                logger.info("[模型] FaceNet加载成功")
            except Exception as e:
                logger.warning(f"[模型] FaceNet加载失败: {e}")
        
        if self.config.get('use_vgg', True):
            try:
                import torchvision.models as models
                self.vgg_model = models.vgg19(pretrained=True).features.eval()
                for param in self.vgg_model.parameters():
                    param.requires_grad = False
                logger.info("[模型] VGG加载成功")
            except Exception as e:
                logger.warning(f"[模型] VGG加载失败: {e}")
    
    def extract_clip_features(self, images: torch.Tensor) -> torch.Tensor:
        """提取CLIP特征"""
        if self.clip_model is None:
            return torch.zeros(images.shape[0], 512, device=images.device)
        
        with torch.no_grad():
            features = self.clip_model.get_image_features(pixel_values=images)
            features = F.normalize(features, dim=-1)
        
        return features
    
    def extract_face_features(self, images: torch.Tensor) -> torch.Tensor:
        """提取人脸特征"""
        if self.face_encoder is None:
            return torch.zeros(images.shape[0], 512, device=images.device)
        
        with torch.no_grad():
            features = self.face_encoder(images)
        
        return features
    
    def extract_vgg_features(self, images: torch.Tensor) -> torch.Tensor:
        """提取VGG感知特征"""
        if self.vgg_model is None:
            return torch.zeros(images.shape[0], 8192, device=images.device)
        
        layers = [4, 9, 18, 27, 36]
        features_list = []
        
        x = images
        with torch.no_grad():
            for i, layer in enumerate(self.vgg_model):
                x = layer(x)
                if i in layers:
                    features_list.append(x.flatten(1))
        
        return torch.cat(features_list, dim=-1)
    
    def forward(self, image1: torch.Tensor, image2: torch.Tensor) -> Dict[str, torch.Tensor]:
        """前向传播"""
        features1 = {
            'clip': self.extract_clip_features(image1),
            'face': self.extract_face_features(image1),
            'vgg': self.extract_vgg_features(image1)
        }
        
        features2 = {
            'clip': self.extract_clip_features(image2),
            'face': self.extract_face_features(image2),
            'vgg': self.extract_vgg_features(image2)
        }
        
        return self.score_head(features1, features2)


class ConsistencyTrainer:
    """一致性模型训练器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        self.device = torch.device(self.config.get('device', 'cuda' if torch.cuda.is_available() else 'cpu'))
        
        self.model = ConsistencyModel(self.config).to(self.device)
        
        self.learning_rate = self.config.get('learning_rate', 1e-4)
        self.weight_decay = self.config.get('weight_decay', 0.01)
        self.epochs = self.config.get('epochs', 50)
        self.batch_size = self.config.get('batch_size', 16)
        
        self.optimizer = AdamW(
            self.model.score_head.parameters(),
            lr=self.learning_rate,
            weight_decay=self.weight_decay
        )
        
        self.scheduler = None
        
        self.output_dir = self.config.get('output_dir', 'checkpoints/consistency_model')
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.best_score = 0.0
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'train_score': [],
            'val_score': []
        }
    
    def prepare_data(self, train_data_path: str, val_data_path: str = None):
        """准备数据"""
        from torchvision import transforms
        
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
        train_dataset = ConsistencyDataset(train_data_path, transform=transform)
        self.train_loader = DataLoader(
            train_dataset, 
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=self.config.get('num_workers', 4)
        )
        
        if val_data_path and os.path.exists(val_data_path):
            val_dataset = ConsistencyDataset(val_data_path, transform=transform)
            self.val_loader = DataLoader(
                val_dataset,
                batch_size=self.batch_size,
                shuffle=False,
                num_workers=self.config.get('num_workers', 4)
            )
        else:
            self.val_loader = None
        
        self.scheduler = CosineAnnealingLR(
            self.optimizer,
            T_max=self.epochs,
            eta_min=self.learning_rate * 0.01
        )
        
        logger.info(f"[训练] 数据准备完成，训练样本: {len(train_dataset)}")
    
    def compute_loss(self, outputs: Dict[str, torch.Tensor], 
                     labels: torch.Tensor) -> torch.Tensor:
        """计算损失"""
        score = outputs['score']
        confidence = outputs['confidence']
        
        mse_loss = F.mse_loss(score, labels)
        
        confidence_target = 1.0 - torch.abs(score - labels)
        confidence_loss = F.binary_cross_entropy(confidence, confidence_target)
        
        consistency_loss = -torch.mean(confidence * torch.log(torch.abs(score - labels) + 1e-6))
        
        total_loss = (
            mse_loss * self.config.get('mse_weight', 1.0) +
            confidence_loss * self.config.get('confidence_weight', 0.5) +
            consistency_loss * self.config.get('consistency_weight', 0.1)
        )
        
        return total_loss
    
    def train_epoch(self) -> Dict[str, float]:
        """训练一个epoch"""
        self.model.train()
        total_loss = 0.0
        total_samples = 0
        correct_predictions = 0
        
        for batch in self.train_loader:
            image1 = batch['image1'].to(self.device)
            image2 = batch['image2'].to(self.device)
            labels = batch['label'].to(self.device)
            
            self.optimizer.zero_grad()
            
            outputs = self.model(image1, image2)
            
            loss = self.compute_loss(outputs, labels)
            
            loss.backward()
            
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            
            self.optimizer.step()
            
            total_loss += loss.item() * labels.size(0)
            total_samples += labels.size(0)
            
            predictions = (outputs['score'] > 0.5).float()
            correct_predictions += (predictions == (labels > 0.5)).sum().item()
        
        avg_loss = total_loss / total_samples
        accuracy = correct_predictions / total_samples
        
        return {'loss': avg_loss, 'accuracy': accuracy}
    
    def validate(self) -> Dict[str, float]:
        """验证"""
        if self.val_loader is None:
            return {'loss': 0.0, 'accuracy': 0.0}
        
        self.model.eval()
        total_loss = 0.0
        total_samples = 0
        correct_predictions = 0
        
        with torch.no_grad():
            for batch in self.val_loader:
                image1 = batch['image1'].to(self.device)
                image2 = batch['image2'].to(self.device)
                labels = batch['label'].to(self.device)
                
                outputs = self.model(image1, image2)
                
                loss = self.compute_loss(outputs, labels)
                
                total_loss += loss.item() * labels.size(0)
                total_samples += labels.size(0)
                
                predictions = (outputs['score'] > 0.5).float()
                correct_predictions += (predictions == (labels > 0.5)).sum().item()
        
        avg_loss = total_loss / total_samples
        accuracy = correct_predictions / total_samples
        
        return {'loss': avg_loss, 'accuracy': accuracy}
    
    def save_checkpoint(self, epoch: int, is_best: bool = False):
        """保存检查点"""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'best_score': self.best_score,
            'history': self.history,
            'config': self.config
        }
        
        checkpoint_path = os.path.join(self.output_dir, f'checkpoint_epoch_{epoch}.pt')
        torch.save(checkpoint, checkpoint_path)
        logger.info(f"[保存] 检查点: {checkpoint_path}")
        
        if is_best:
            best_path = os.path.join(self.output_dir, 'best_model.pt')
            torch.save(checkpoint, best_path)
            logger.info(f"[保存] 最佳模型: {best_path}")
    
    def train(self):
        """完整训练流程"""
        logger.info(f"[训练] 开始训练，设备: {self.device}")
        logger.info(f"[训练] 总epochs: {self.epochs}, 批大小: {self.batch_size}")
        
        for epoch in range(1, self.epochs + 1):
            train_metrics = self.train_epoch()
            val_metrics = self.validate()
            
            self.history['train_loss'].append(train_metrics['loss'])
            self.history['train_score'].append(train_metrics['accuracy'])
            self.history['val_loss'].append(val_metrics['loss'])
            self.history['val_score'].append(val_metrics['accuracy'])
            
            self.scheduler.step()
            
            logger.info(
                f"[Epoch {epoch}/{self.epochs}] "
                f"Train Loss: {train_metrics['loss']:.4f}, "
                f"Train Acc: {train_metrics['accuracy']:.4f}, "
                f"Val Loss: {val_metrics['loss']:.4f}, "
                f"Val Acc: {val_metrics['accuracy']:.4f}"
            )
            
            is_best = val_metrics['accuracy'] > self.best_score
            if is_best:
                self.best_score = val_metrics['accuracy']
            
            if epoch % self.config.get('save_interval', 5) == 0 or is_best:
                self.save_checkpoint(epoch, is_best)
        
        self._save_training_history()
        
        logger.info(f"[训练] 完成，最佳验证准确率: {self.best_score:.4f}")
    
    def _save_training_history(self):
        """保存训练历史"""
        history_path = os.path.join(self.output_dir, 'training_history.json')
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2)
        logger.info(f"[保存] 训练历史: {history_path}")


class DataAnnotator:
    """
    数据标注工具
    用于生成训练数据
    """
    
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.samples = []
    
    def add_sample(self, 
                   image1_path: str, 
                   image2_path: str, 
                   label: float,
                   metadata: Dict[str, Any] = None):
        """添加样本"""
        self.samples.append({
            'image1': image1_path,
            'image2': image2_path,
            'label': label,
            'metadata': metadata or {}
        })
    
    def auto_label_from_ssim(self, image1_path: str, image2_path: str) -> float:
        """使用SSIM自动标注"""
        from skimage.metrics import structural_similarity as ssim
        
        img1 = cv2.imread(image1_path, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imread(image2_path, cv2.IMREAD_GRAYSCALE)
        
        if img1 is None or img2 is None:
            return 0.5
        
        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
        
        score, _ = ssim(img1, img2, full=True)
        return float(score)
    
    def auto_label_from_clip(self, image1_path: str, image2_path: str) -> float:
        """使用CLIP自动标注"""
        try:
            from transformers import CLIPModel, CLIPProcessor
            from PIL import Image
            import torch
            
            model = CLIPModel.from_pretrained('openai/clip-vit-base-patch32')
            processor = CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32')
            
            img1 = Image.open(image1_path).convert('RGB')
            img2 = Image.open(image2_path).convert('RGB')
            
            inputs = processor(images=[img1, img2], return_tensors="pt")
            
            with torch.no_grad():
                features = model.get_image_features(**inputs)
                features = F.normalize(features, dim=-1)
                similarity = F.cosine_similarity(features[0:1], features[1:2])
            
            return float((similarity.item() + 1) / 2)
        except Exception as e:
            logger.warning(f"[自动标注] CLIP失败: {e}")
            return 0.5
    
    def save(self):
        """保存数据集"""
        data = {'samples': self.samples}
        
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[标注] 保存 {len(self.samples)} 个样本到 {self.output_path}")


def create_training_data_from_videos(video_dir: str, output_path: str):
    """
    从视频目录创建训练数据
    
    Args:
        video_dir: 视频目录，包含多个视频切片
        output_path: 输出数据集路径
    """
    annotator = DataAnnotator(output_path)
    
    video_files = sorted([f for f in os.listdir(video_dir) if f.endswith(('.mp4', '.avi', '.mov'))])
    
    for i in range(len(video_files) - 1):
        video1_path = os.path.join(video_dir, video_files[i])
        video2_path = os.path.join(video_dir, video_files[i + 1])
        
        cap1 = cv2.VideoCapture(video1_path)
        cap2 = cv2.VideoCapture(video2_path)
        
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()
        
        if ret1 and ret2:
            temp_dir = os.path.join(os.path.dirname(output_path), 'temp_frames')
            os.makedirs(temp_dir, exist_ok=True)
            
            frame1_path = os.path.join(temp_dir, f'frame_{i}_1.jpg')
            frame2_path = os.path.join(temp_dir, f'frame_{i}_2.jpg')
            
            cv2.imwrite(frame1_path, frame1)
            cv2.imwrite(frame2_path, frame2)
            
            label = annotator.auto_label_from_ssim(frame1_path, frame2_path)
            
            annotator.add_sample(
                frame1_path, frame2_path, label,
                metadata={'video1': video_files[i], 'video2': video_files[i + 1]}
            )
        
        cap1.release()
        cap2.release()
    
    annotator.save()


if __name__ == "__main__":
    config = {
        'device': 'cuda',
        'epochs': 50,
        'batch_size': 16,
        'learning_rate': 1e-4,
        'output_dir': 'checkpoints/consistency_model',
        'use_clip': True,
        'use_face': True,
        'use_vgg': True
    }
    
    trainer = ConsistencyTrainer(config)
    
    trainer.prepare_data(
        train_data_path='data/consistency_train.json',
        val_data_path='data/consistency_val.json'
    )
    
    trainer.train()
