# Copyright (C) 2021 Evil0ctal
#
#
# You may obtain a copy of the License at:
# http://www.apache.org/licenses/LICENSE-2.0
#
# limitations under the License.
# 　　　　 　　  ＿＿
# 　　　 　　 ／＞　　フ
# 　　　 　　| 　_　 _ l
# 　 　　 　／` ミ＿xノ
# 　　 　 /　　　 　 |       Feed me Stars ⭐ ️
# 　　　 /　 ヽ　　 ﾉ
# 　 　 │　　|　|　|
# 　／￣|　　 |　|　|
# 　| (￣ヽ＿_ヽ_)__)
# 　＼二つ
#
# Contributor Link:
# - https://github.com/Evil0ctal
# - https://github.com/Johnserf-Seed
#


# FastAPI APP
import uvicorn
from fastapi import FastAPI
from app.api.router import router as api_router

# PyWebIO APP
from app.web.app import MainView
from pywebio.platform.fastapi import asgi_app

# OS
import os

# YAML
import yaml

# Load Config

# 读取上级再上级目录的配置文件
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
with open(config_path, 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)


Host_IP = config['API']['Host_IP']
Host_Port = config['API']['Host_Port']

# API Tags
tags_metadata = [
    {
        "name": "Hybrid-API",
        "description": "**(混合数据接口/Hybrid-API data endpoints)**",
    },
    {
        "name": "Douyin-Web-API",
        "description": "**(抖音Web数据接口/Douyin-Web-API data endpoints)**",
    },
    {
        "name": "TikTok-Web-API",
        "description": "**(TikTok-Web-API数据接口/TikTok-Web-API data endpoints)**",
    },
    {
        "name": "TikTok-App-API",
        "description": "**(TikTok-App-API数据接口/TikTok-App-API data endpoints)**",
    },
    {
        "name": "Bilibili-Web-API",
        "description": "**(Bilibili-Web-API数据接口/Bilibili-Web-API data endpoints)**",
    },
    {
        "name": "iOS-Shortcut",
        "description": "**(iOS快捷指令数据接口/iOS-Shortcut data endpoints)**",
    },
    {
        "name": "Download",
        "description": "**(下载数据接口/Download data endpoints)**",
    },
]

version = config['API']['Version']
update_time = config['API']['Update_Time']
environment = config['API']['Environment']


docs_url = config['API']['Docs_URL']
redoc_url = config['API']['Redoc_URL']

app = FastAPI(
    title="Douyin TikTok Download API",
    description=description,
    version=version,
    openapi_tags=tags_metadata,
    docs_url=docs_url,  # 文档路径
    redoc_url=redoc_url,  # redoc文档路径
)

# API router
app.include_router(api_router, prefix="/api")

# PyWebIO APP
if config['Web']['PyWebIO_Enable']:
    webapp = asgi_app(lambda: MainView().main_view())
    app.mount("/", webapp)

if __name__ == '__main__':
    uvicorn.run(app, host=Host_IP, port=Host_Port)

