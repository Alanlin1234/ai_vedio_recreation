import importlib
import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root = os.path.dirname(base_dir)
sys.path.append(project_root)


def create_app():
    """应用工厂函数"""
    from flask import Flask
    from flask_cors import CORS
    from config import Config
    from app.models import db, ensure_default_user, ensure_video_recreation_schema

    app = Flask(__name__)
    app.config.from_object(Config())

    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
    app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)

    db.init_app(app)

    CORS(
        app,
        supports_credentials=True,
        resources={
            r'/api/*': {
                'origins': [
                    'http://localhost:3000',
                    'http://127.0.0.1:3000',
                    'http://localhost:5173',
                    'http://127.0.0.1:5173',
                ],
                'allow_headers': ['Content-Type', 'Authorization'],
                'methods': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
            }
        },
    )

    from app.routes.frontend_pipeline_routes import frontend_pipeline_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.review_routes import review_bp

    app.register_blueprint(frontend_pipeline_bp, url_prefix='/api/pipeline')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(review_bp, url_prefix='/api')

    for mod_name, bp_name in [
        ('video_routes', 'video_bp'),
        ('author_routes', 'author_bp'),
        ('douyin_routes', 'douyin_bp'),
        ('video_recreation_routes', 'video_recreation_bp'),
    ]:
        try:
            mod = importlib.import_module(f'app.routes.{mod_name}')
            app.register_blueprint(getattr(mod, bp_name), url_prefix='/api')
        except (ImportError, AttributeError):
            pass

    try:
        from app.routes.agent_routes import agent_bp

        app.register_blueprint(agent_bp)
    except ImportError:
        pass

    with app.app_context():
        try:
            db.create_all()
            ensure_video_recreation_schema()
            ensure_default_user()
            print('数据库表初始化成功')
        except Exception as e:
            print(f'数据库初始化失败: {str(e)}')

    return app
