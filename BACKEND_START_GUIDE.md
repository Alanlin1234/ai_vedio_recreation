# 后端服务启动指南

## 1. 后端服务与数据库关系

是的，后端服务包含数据库功能。当前项目使用SQLAlchemy作为ORM框架，可以配置使用不同的数据库后端：

- **默认配置**：MySQL数据库
- **推荐配置**：SQLite数据库（适合开发和测试）

## 2. 数据库配置

### 2.1 推荐：使用SQLite数据库

SQLite是一个轻量级数据库，无需单独安装服务，适合开发和测试环境。

#### 2.1.1 修改配置文件

编辑`backend/config.py`文件，将数据库配置改为SQLite：

```python
# 将原来的MySQL配置替换为SQLite配置
SQLALCHEMY_DATABASE_URI = 'sqlite:///video_agent.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,
    'echo': False
}

# 删除或注释掉原来的MySQL配置
# MYSQL_HOST = 'localhost'
# MYSQL_PORT = 3306
# MYSQL_USER = 'root'
# MYSQL_PASSWORD = '123456'
# MYSQL_DB = 'video_agent'
```

#### 2.1.2 修改.env文件（如果存在）

```env
# 使用SQLite数据库
SQLALCHEMY_DATABASE_URI=sqlite:///video_agent.db
```

### 2.2 可选：使用MySQL数据库

如果您确实需要使用MySQL，请确保：
- MySQL服务已安装并运行
- 已创建`video_agent`数据库
- 配置文件中的数据库连接信息正确

## 3. 安装依赖

### 3.1 激活conda环境

```bash
conda activate video_agent
```

### 3.2 安装项目依赖

```bash
# 进入backend目录
cd backend

# 安装所有依赖
pip install -r requirements.txt

# 安装缺失的依赖（如果有）
pip install flask flask-cors flask-sqlalchemy sqlalchemy
```

## 4. 启动后端服务

### 4.1 基本启动方式

```bash
# 确保在backend目录下
cd backend

# 启动Flask应用
python run.py
```

### 4.2 使用uvicorn启动（推荐）

```bash
# 使用uvicorn启动，支持热重载
uvicorn run:app --host 0.0.0.0 --port 5000 --reload
```

### 4.3 服务启动成功的标志

```
* Serving Flask app 'app' (lazy loading)
* Environment: production
  WARNING: This is a development server. Do not use it in a production deployment.
  Use a production WSGI server instead.
* Debug mode: on
* Running on all addresses.  
  WARNING: This is a development server. Do not use it in a production deployment.
* Running on http://127.0.0.1:5000/
* Restarting with stat
* Debugger is active!
* Debugger PIN: 123-456-789
数据库表初始化成功
```

## 5. 测试后端服务

### 5.1 检查服务是否正常运行

```bash
# 使用curl测试根路径
curl -I http://localhost:5000/

# 预期响应
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
```

### 5.2 测试API端点

```bash
# 测试视频API
curl http://localhost:5000/api/videos
```

## 6. 数据库初始化

后端服务启动时，会自动执行数据库初始化：

1. 在`app/__init__.py`的`create_app()`函数中
2. 调用`db.init_app(app)`初始化数据库连接
3. 调用`db.create_all()`创建所有数据库表
4. 初始化成功会输出：`数据库表初始化成功`

## 7. 常见问题解决

### 7.1 问题：数据库初始化失败

**解决方法**：
- 检查配置文件中的数据库连接信息是否正确
- 确保数据库服务正在运行（如果使用MySQL）
- 尝试删除SQLite数据库文件后重新启动：`rm backend/video_agent.db`

### 7.2 问题：端口被占用

**解决方法**：
- 使用不同的端口启动服务：`python run.py --port 5001`
- 或使用uvicorn指定端口：`uvicorn run:app --port 5001`

### 7.3 问题：依赖缺失

**解决方法**：
- 确保所有依赖已正确安装：`pip install -r requirements.txt`
- 检查是否有缺失的依赖并手动安装

## 8. 服务管理

### 8.1 停止服务

- 在终端中按`Ctrl + C`停止服务

### 8.2 重启服务

- 直接重新运行启动命令
- 如果使用`--reload`参数，修改代码后服务会自动重启

## 9. 生产环境部署建议

对于生产环境，建议：
- 使用MySQL或PostgreSQL数据库
- 使用Gunicorn或uWSGI作为WSGI服务器
- 配置Nginx作为反向代理
- 启用HTTPS
- 配置数据库备份策略

## 10. 总结

启动后端服务的步骤：

1. **配置数据库**：修改`config.py`使用SQLite
2. **安装依赖**：`pip install -r requirements.txt`
3. **启动服务**：`python run.py` 或 `uvicorn run:app --reload`
4. **测试服务**：使用curl或浏览器访问`http://localhost:5000/`

后端服务启动后，数据库会自动初始化，您可以开始使用API端点或运行测试脚本。