"""
训练启动脚本
"""
import os
import sys
import yaml
import logging
import argparse
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def train(config_path: str, train_data: str, val_data: str = None):
    """
    启动训练
    
    Args:
        config_path: 配置文件路径
        train_data: 训练数据路径
        val_data: 验证数据路径
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    config['output_dir'] = config.get('output_dir', 'checkpoints/consistency_model')
    config['output_dir'] = f"{config['output_dir']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    from consistency_trainer import ConsistencyTrainer
    
    trainer = ConsistencyTrainer(config)
    
    trainer.prepare_data(train_data, val_data)
    
    trainer.train()
    
    logger.info("[完成] 训练完成!")
    logger.info(f"[完成] 最佳模型保存在: {config['output_dir']}/best_model.pt")


def prepare_data(video_dir: str, output_dir: str, train_ratio: float = 0.8):
    """
    准备训练数据
    
    Args:
        video_dir: 视频目录
        output_dir: 输出目录
        train_ratio: 训练集比例
    """
    from prepare_training_data import TrainingDataPreparer
    
    preparer = TrainingDataPreparer({'output_dir': output_dir})
    
    train_path, val_path = preparer.prepare_from_video_directory(
        video_dir=video_dir,
        train_ratio=train_ratio
    )
    
    logger.info(f"[完成] 数据准备完成!")
    logger.info(f"[完成] 训练数据: {train_path}")
    logger.info(f"[完成] 验证数据: {val_path}")
    
    return train_path, val_path


def main():
    parser = argparse.ArgumentParser(description='视频一致性检测模型训练')
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    train_parser = subparsers.add_parser('train', help='训练模型')
    train_parser.add_argument('--config', '-c', type=str, 
                             default='train_config.yaml',
                             help='配置文件路径')
    train_parser.add_argument('--train-data', '-t', type=str, required=True,
                             help='训练数据路径')
    train_parser.add_argument('--val-data', '-v', type=str, default=None,
                             help='验证数据路径')
    
    prepare_parser = subparsers.add_parser('prepare', help='准备训练数据')
    prepare_parser.add_argument('--video-dir', '-i', type=str, required=True,
                               help='视频目录')
    prepare_parser.add_argument('--output', '-o', type=str, 
                               default='data/consistency_dataset',
                               help='输出目录')
    prepare_parser.add_argument('--train-ratio', '-r', type=float, default=0.8,
                               help='训练集比例')
    
    full_parser = subparsers.add_parser('full', help='完整流程：准备数据 + 训练')
    full_parser.add_argument('--video-dir', '-i', type=str, required=True,
                            help='视频目录')
    full_parser.add_argument('--config', '-c', type=str,
                            default='train_config.yaml',
                            help='配置文件路径')
    full_parser.add_argument('--train-ratio', '-r', type=float, default=0.8,
                            help='训练集比例')
    
    args = parser.parse_args()
    
    if args.command == 'train':
        train(args.config, args.train_data, args.val_data)
    
    elif args.command == 'prepare':
        prepare_data(args.video_dir, args.output, args.train_ratio)
    
    elif args.command == 'full':
        output_dir = 'data/consistency_dataset'
        train_path, val_path = prepare_data(
            args.video_dir, output_dir, args.train_ratio
        )
        train(args.config, train_path, val_path)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
