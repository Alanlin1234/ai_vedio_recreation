import sys
import os

# 获取项目根目录（backend目录）
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 获取项目根目录的上级目录（ai-agent-comfy目录）
project_root = os.path.dirname(base_dir)
print("项目根目录:", project_root)

# 添加项目根目录到Python路径
sys.path.append(project_root)
# 打印Python路径以调试
print("Python路径:", sys.path)

# 只在需要时导入Flask相关模块
def create_app():
    """应用工厂函数"""
    from flask import Flask
    from flask_cors import CORS
    from config import Config
    from app.models import db
    
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
    from app.routes.frontend_pipeline_routes import frontend_pipeline_bp
    # 暂时注释掉agent_bp，因为有导入错误
    # from app.routes.agent_routes import agent_bp
    
    app.register_blueprint(video_bp, url_prefix='/api')
    app.register_blueprint(author_bp, url_prefix='/api')
    app.register_blueprint(douyin_bp, url_prefix='/api')
    app.register_blueprint(video_recreation_bp, url_prefix='/api')
    app.register_blueprint(frontend_pipeline_bp, url_prefix='/api/pipeline')
    # app.register_blueprint(agent_bp)
    
    # 创建数据库表
    with app.app_context():
        try:
            db.create_all()
            print("数据库表初始化成功")
        except Exception as e:
            print(f"数据库初始化失败: {str(e)}")
    
    return app