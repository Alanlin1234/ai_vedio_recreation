# 在conda虚拟环境中使用数据库的解决方案

## 1. 数据库选择说明

MySQL通常是作为系统级服务安装的，而不是直接在虚拟环境中运行。对于虚拟环境测试，推荐使用**SQLite**作为轻量级替代方案，它：
- 无需单独安装服务
- 无需配置用户名和密码
- 数据存储在单个文件中
- 与SQLAlchemy完美兼容
- 适合开发和测试环境

## 2. 修改项目配置使用SQLite

### 2.1 修改config.py文件

编辑`backend/config.py`文件，将数据库配置改为使用SQLite：

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

### 2.2 修改.env文件（如果存在）

编辑`backend/.env`文件，确保数据库配置正确：

```env
# 使用SQLite数据库
SQLALCHEMY_DATABASE_URI=sqlite:///video_agent.db
```

## 3. 安装SQLite相关依赖

SQLite通常是Python标准库的一部分，无需单独安装。但如果需要，可使用以下命令：

```bash
# 激活conda环境
conda activate video_agent

# 安装SQLAlchemy（如果尚未安装）
pip install sqlalchemy
```

## 4. 验证SQLite配置

### 4.1 测试数据库连接

```bash
# 进入backend目录
cd backend

# 运行Python测试脚本
python -c "
from app import create_app
from app.models import db

app = create_app()
with app.app_context():
    # 创建所有数据库表
    db.create_all()
    print('✅ 数据库表创建成功！')
    print('✅ SQLite数据库配置成功！')
"
```

### 4.2 查看生成的数据库文件

```bash
# 查看当前目录下是否生成了SQLite数据库文件
ls -la video_agent.db
```

## 5. 运行测试脚本

现在您可以直接运行测试脚本，无需启动任何数据库服务：

```bash
# 确保在项目根目录下
python backend/test_local_video_recreation.py /path/to/your/video.mp4
```

## 6. （可选）在虚拟环境中使用MariaDB（MySQL的分支）

如果您确实需要使用MySQL兼容的数据库，可以在conda虚拟环境中安装MariaDB：

### 6.1 安装MariaDB

```bash
# 激活conda环境
conda activate video_agent

# 使用conda安装MariaDB
conda install -c conda-forge mariadb-server -y
```

### 6.2 启动MariaDB服务

```bash
# 初始化MariaDB数据目录
mysql_install_db

# 启动MariaDB服务
mysqld_safe --datadir="$HOME/mysql_data" &
```

### 6.3 配置MariaDB

```bash
# 登录MariaDB
mysql -u root

# 设置密码
ALTER USER 'root'@'localhost' IDENTIFIED BY 'YourPassword';

# 创建数据库
CREATE DATABASE video_agent;

# 退出
EXIT;
```

### 6.4 配置项目使用MariaDB

修改`backend/config.py`：

```python
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:YourPassword@localhost:3306/video_agent'
```

## 7. 常见问题解决

### 7.1 问题：SQLite数据库文件在哪里？

答：数据库文件`video_agent.db`会生成在`backend`目录下。

### 7.2 问题：如何查看SQLite数据库内容？

答：使用SQLite命令行工具：

```bash
# 安装SQLite命令行工具
conda install -c conda-forge sqlite -y

# 查看数据库内容
sqlite3 backend/video_agent.db

# 在SQLite提示符下执行SQL命令
.tables  # 查看所有表
SELECT * FROM douyin_video;  # 查看视频表内容
.quit  # 退出
```

### 7.3 问题：如何重置SQLite数据库？

答：只需删除数据库文件，下次运行时会自动创建：

```bash
rm backend/video_agent.db
```

## 8. 总结

对于conda虚拟环境中的测试，推荐使用SQLite作为数据库，因为：
- 无需安装和配置复杂的数据库服务
- 数据存储在单个文件中，便于管理
- 与项目现有代码完全兼容
- 适合开发和测试场景

按照上述步骤修改配置后，您可以直接运行测试脚本，无需担心数据库服务的启动和管理问题。