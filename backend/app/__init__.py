from flask import Flask
from flask_cors import CORS
import sys
import os

# 添加backend目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from app.models import db

def create_app():
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(Config())
    
    # 初始化数据库
    db.init_app(app)
    
    # 启用CORS
    CORS(app)
    
    # 注册蓝图
    from app.routes.video_routes import video_bp
    from app.routes.author_routes import author_bp
    from app.routes.douyin_routes import douyin_bp
    from app.routes.video_recreation_routes import video_recreation_bp
    # 暂时注释掉agent_bp，因为有导入错误
    # from app.routes.agent_routes import agent_bp
    
    app.register_blueprint(video_bp, url_prefix='/api')
    app.register_blueprint(author_bp, url_prefix='/api')
    app.register_blueprint(douyin_bp, url_prefix='/api')
    app.register_blueprint(video_recreation_bp, url_prefix='/api')
    # app.register_blueprint(agent_bp)
    
    # 创建数据库表
    with app.app_context():
        try:
            db.create_all()
            print("数据库表初始化成功")
        except Exception as e:
            print(f"数据库初始化失败: {str(e)}")
    
    return app