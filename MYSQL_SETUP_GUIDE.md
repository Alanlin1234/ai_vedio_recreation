# MySQL数据库开启和配置指南

## 1. 检查MySQL是否已安装

```bash
# 检查MySQL是否已安装
mysql --version

# 或检查服务是否存在
which mysql
```

如果未安装，先安装MySQL：

```bash
# Ubuntu/Debian系统
sudo apt update
sudo apt install mysql-server -y

# CentOS/RHEL系统
sudo dnf install mysql-server -y
```

## 2. 检查MySQL服务状态

```bash
# Ubuntu/Debian系统
sudo systemctl status mysql

# CentOS/RHEL系统
sudo systemctl status mysqld
```

## 3. 启动MySQL服务

```bash
# Ubuntu/Debian系统
sudo systemctl start mysql

# CentOS/RHEL系统
sudo systemctl start mysqld
```

## 4. 设置MySQL开机自启

```bash
# Ubuntu/Debian系统
sudo systemctl enable mysql

# CentOS/RHEL系统
sudo systemctl enable mysqld
```

## 5. 首次安装MySQL后的配置

### 5.1 设置MySQL根密码

```bash
# Ubuntu/Debian系统
# 首次安装后，MySQL根用户默认没有密码，直接登录
mysql -u root

# CentOS/RHEL系统
# 首次安装后，MySQL会生成一个临时密码
# 查看临时密码
sudo grep 'temporary password' /var/log/mysqld.log

# 使用临时密码登录
mysql -u root -p
```

登录后设置新密码：

```sql
-- 设置新密码
ALTER USER 'root'@'localhost' IDENTIFIED BY 'YourNewPassword123!';

-- 刷新权限
FLUSH PRIVILEGES;

-- 退出MySQL
EXIT;
```

### 5.2 允许MySQL远程访问（可选）

```sql
-- 登录MySQL
mysql -u root -p

-- 允许root用户从任何主机访问
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY 'YourPassword' WITH GRANT OPTION;

-- 刷新权限
FLUSH PRIVILEGES;

-- 退出
EXIT;
```

## 6. 创建视频项目所需的数据库

```bash
# 登录MySQL
mysql -u root -p

-- 创建video_agent数据库
CREATE DATABASE video_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 退出
EXIT;
```

## 7. 测试数据库连接

```bash
# 使用mysql命令测试连接
mysql -u root -p -e "SELECT DATABASE();"

# 使用Python测试连接
python -c "import pymysql; conn = pymysql.connect(host='localhost', user='root', password='YourPassword', database='video_agent'); print('连接成功！'); conn.close()"
```

## 8. 配置.env文件

确保`backend/.env`文件中的数据库配置正确：

```env
# 数据库配置
SQLALCHEMY_DATABASE_URI=mysql+pymysql://root:YourPassword@localhost:3306/video_agent
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=YourPassword
MYSQL_DB=video_agent
```

## 9. 重启MySQL服务（如果需要）

```bash
# Ubuntu/Debian系统
sudo systemctl restart mysql

# CentOS/RHEL系统
sudo systemctl restart mysqld
```

## 10. 常见问题解决

### 10.1 问题：无法连接到MySQL服务器

解决方法：
```bash
# 检查服务是否运行
sudo systemctl status mysql  # Ubuntu/Debian
sudo systemctl status mysqld  # CentOS/RHEL

# 检查MySQL监听的端口
sudo netstat -tlnp | grep mysql

# 检查防火墙设置
# Ubuntu/Debian系统
sudo ufw status
# 允许MySQL端口
sudo ufw allow 3306

# CentOS/RHEL系统
sudo firewall-cmd --list-ports
sudo firewall-cmd --add-port=3306/tcp --permanent
sudo firewall-cmd --reload
```

### 10.2 问题：忘记MySQL密码

解决方法：
```bash
# 停止MySQL服务
sudo systemctl stop mysql  # Ubuntu/Debian
sudo systemctl stop mysqld  # CentOS/RHEL

# 以跳过权限检查的方式启动MySQL
sudo mysqld_safe --skip-grant-tables &

# 登录MySQL
mysql -u root

# 设置新密码
UPDATE mysql.user SET authentication_string=PASSWORD('YourNewPassword') WHERE User='root';
FLUSH PRIVILEGES;
EXIT;

# 重启MySQL服务
sudo systemctl restart mysql  # Ubuntu/Debian
sudo systemctl restart mysqld  # CentOS/RHEL
```

### 10.3 问题：MySQL服务启动失败

解决方法：
```bash
# 查看MySQL错误日志
# Ubuntu/Debian系统
sudo tail -n 100 /var/log/mysql/error.log

# CentOS/RHEL系统
sudo tail -n 100 /var/log/mysqld.log
```

## 11. 验证数据库配置

在项目根目录下运行以下命令，验证数据库连接是否正常：

```bash
# 进入Python交互式环境
python

# 测试数据库连接
>>> from app import create_app
>>> app = create_app()
>>> with app.app_context():
...     from app.models import db
...     db.engine.execute('SELECT 1')
...     print('数据库连接成功！')
```

## 12. 运行测试脚本

配置完成后，重新运行测试脚本：

```bash
python backend/test_local_video_recreation.py /path/to/your/video.mp4
```

## 总结

1. 确保MySQL已安装并启动
2. 设置正确的MySQL根密码
3. 创建`video_agent`数据库
4. 配置`.env`文件中的数据库连接信息
5. 验证数据库连接
6. 运行测试脚本

按照以上步骤配置后，您的测试脚本应该能够成功连接到MySQL数据库并运行。