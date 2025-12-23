import datetime
import requests
from DrissionPage import Chromium
import sys
import os
from moviepy.editor import VideoFileClip
import asyncio
import httpx

from utils import time_utils
from config import Config
from utils.time_utils import is_recent_time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.data_service import DataService
from app.services.video_service import VideoService
import pandas as pd
from datetime import datetime
from crawler_config.crawler_config import crawler_config

config = Config()

class DouyinCrawlerClient:
    """抖音爬虫服务客户端"""
    
    def __init__(self, base_url=None, timeout=None):
        # 直接硬编码正确的爬虫服务URL，避免配置问题
        self.base_url = base_url or "http://localhost:8081"
        self.timeout = timeout or 30
        self.client = None
    
    async def get_video_info(self, aweme_id_or_url: str, max_retries=3, retry_delay=1):
        """获取单个视频信息，带有重试机制"""
        for retry in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    url = f"{self.base_url}/api/hybrid/video_data"
                    
                    # 判断输入是视频ID还是完整URL
                    if aweme_id_or_url.startswith("http"):
                        # 如果是完整URL（包括短链接），直接使用
                        video_url = aweme_id_or_url
                    else:
                        # 如果是视频ID，构建完整URL
                        video_url = f"https://www.douyin.com/video/{aweme_id_or_url}"
                    
                    params = {"url": video_url}
                    
                    response = await client.get(url, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        return self._parse_video_data(data)
                    else:
                        print(f"获取视频信息失败: {response.status_code}")
                        if retry < max_retries - 1:
                            print(f"{retry+1}次重试失败，{retry_delay}秒后重试...")
                            await asyncio.sleep(retry_delay)
                        else:
                            return None
            except Exception as e:
                print(f"调用爬虫服务异常: {e}")
                if retry < max_retries - 1:
                    print(f"{retry+1}次重试失败，{retry_delay}秒后重试...")
                    await asyncio.sleep(retry_delay)
                else:
                    return None
    
    async def get_user_videos(self, sec_user_id: str, count: int = 20):
        """获取用户主页作品"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/fetch_user_post_videos"
                params = {
                    "sec_user_id": sec_user_id,
                    "count": count,
                    "max_cursor": 0
                }
                
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_user_videos(data)
                else:
                    print(f"获取用户作品失败: {response.status_code}")
                    return None
        except Exception as e:
            print(f"调用爬虫服务异常: {e}")
            return None
    
    async def get_user_info(self, sec_user_id: str):
        """获取用户信息"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/fetch_user_profile"
                params = {"sec_user_id": sec_user_id}
                
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_user_info(data)
                else:
                    print(f"获取用户信息失败: {response.status_code}")
                    return None
        except Exception as e:
            print(f"调用爬虫服务异常: {e}")
            return None
    
    def _parse_video_data(self, data: dict):
        """解析视频数据"""
        if not data.get("data"):
            return {}
        
        video_data = data["data"]
        return {
            "aweme_id": video_data.get("aweme_id"),
            "desc": video_data.get("desc", ""),
            "author": video_data.get("author", {}).get("nickname", ""),
            "author_id": video_data.get("author", {}).get("sec_uid", ""),
            "video_url": video_data.get("video", {}).get("play_addr", {}).get("url_list", [""])[0],
            "cover_url": video_data.get("video", {}).get("cover", {}).get("url_list", [""])[0],
            "duration": video_data.get("video", {}).get("duration", 0),
            "statistics": {
                "digg_count": video_data.get("statistics", {}).get("digg_count", 0),
                "comment_count": video_data.get("statistics", {}).get("comment_count", 0),
                "share_count": video_data.get("statistics", {}).get("share_count", 0),
                "play_count": video_data.get("statistics", {}).get("play_count", 0)
            },
            "create_time": video_data.get("create_time", 0)
        }
    
    def _parse_user_videos(self, data: dict):
        """解析用户作品列表"""
        if not data.get("data") or not data["data"].get("aweme_list"):
            return []
        
        videos = []
        for video_data in data["data"]["aweme_list"]:
            videos.append(self._parse_video_data({"data": video_data}))
        
        return videos
    
    def _parse_user_info(self, data: dict):
        """解析用户信息"""
        if not data.get("data") or not data["data"].get("user"):
            return {}
        
        user_data = data["data"]["user"]
        return {
            'nickname': user_data.get("nickname", ""),
            'followers_count': user_data.get("follower_count", 0),
            'following_count': user_data.get("following_count", 0),
            'total_favorited': user_data.get("total_favorited", 0),
            'signature': user_data.get("signature", ""),
            'sec_uid': user_data.get("sec_uid", ""),
            'uid': user_data.get("uid", ""),
            'unique_id': user_data.get("unique_id", ""),
            'cover_url': user_data.get("cover_url", [{}])[0].get("url_list", [""])[0] if user_data.get("cover_url") else "",
            'avatar_larger_url': user_data.get("avatar_larger", {}).get("url_list", [""])[0] if user_data.get("avatar_larger") else "",
            'share_url': user_data.get("share_info", {}).get("share_url", "") if user_data.get("share_info") else ""
        }


class DouyinService:
    _scheduler = None
    _crawler_client = None
    
    @staticmethod
    def get_crawler_client():
        """获取爬虫客户端实例"""
        if DouyinService._crawler_client is None:
            DouyinService._crawler_client = DouyinCrawlerClient()
        return DouyinService._crawler_client
    
    @staticmethod
    def use_crawler_service():
        """检查是否使用爬虫服务"""
        return crawler_config.is_crawler_available()
    
    @staticmethod
    def init_scheduler():
        if DouyinService._scheduler is None:
            DouyinService._scheduler = BackgroundScheduler()
            DouyinService._scheduler.start()
    
    @staticmethod
    def schedule_daily_crawl(author_name, hour=0, minute=0):
        """每天定时爬取指定作者的最新视频"""
        DouyinService.init_scheduler()
        
        trigger = CronTrigger(hour=hour, minute=minute)
        DouyinService._scheduler.add_job(
            DouyinService.crawl_videos,
            trigger=trigger,
            args=[author_name],
            id=f'douyin_crawl_{author_name}',
            replace_existing=True
        )
    
    @staticmethod
    def get_video_link(url):
        api_url = f"{crawler_config.CRAWLER_BASE_URL}/api/hybrid/video_data"
        try:
            response = requests.get(api_url, params={"url": url})
            response.raise_for_status()
            return response.json()["data"]["video"]["play_addr"]["url_list"][0]
        except Exception as e:
            raise Exception(f"获取视频链接失败: {str(e)}")

    @staticmethod
    def download_video(url):
        browser = Chromium()
        try:
            tab = browser.get_tab()
            download_result = tab.download(url)
            if not (isinstance(download_result, tuple) and len(download_result) > 0):
                raise Exception("下载失败")
                
            old_file_path = download_result[1]
            new_file_path = os.path.join(
                config.UPLOAD_FOLDER,
                f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            )
            os.rename(old_file_path, new_file_path)
            return new_file_path
        except Exception as e:
            raise Exception(f"视频下载失败: {str(e)}")
        finally:
            browser.close()

    @staticmethod
    def crawl_videos(name):
        try:
            dp = Chromium(1122)
            tab = dp.get_tab()
            tab.get(f'https://www.douyin.com/search/{name}?type=video')
            
            video_list = tab.eles('@class=SwZLHMKk SEbmeLLH')
            downloaded_files = []
            
            for v_item in video_list:
                if is_recent_time(v_item.ele('@class=faDtinfi').text):
                    url = v_item.ele('@@class=hY8lWHgA _4furHfW@@tag()=a')
                    download_link = DouyinService.get_video_link(url.link)
                    downloaded_files.append(DouyinService.download_video(download_link))
                else:
                    break
                    
            return downloaded_files
        except Exception as e:
            raise Exception(f"抖音视频爬取失败: {str(e)}")

    @staticmethod
    def crawl_all_authors_videos():
        """爬取所有作者的最新视频"""
        try:
            # 从数据库获取所有作者列表
            authors = DataService.get_all_authors()
            for author in authors:
                DouyinService.crawl_videos(author['author_unique_id'])
        except Exception as e:
            print(f"定时爬取任务失败: {str(e)}")

    @staticmethod
    def fetch_author_info(sec_uid):
        """根据sec_uid获取作者信息"""
        api_url = f"{crawler_config.CRAWLER_BASE_URL}/api/douyin/web/handler_user_profile"
        
        try:
            # 调用外部API获取作者信息
            response = requests.get(api_url, params={"sec_user_id": sec_uid})
            response.raise_for_status()
            
            # 解析JSON数据
            data = response.json()
            user_info = data["data"]["user"]
            
            # 提取有用信息并清洗数据
            cleaned_data = {
                'nickname': user_info.get("nickname", ""),
                'followers_count': user_info.get("follower_count", 0),
                'following_count': user_info.get("following_count", 0),
                'total_favorited': user_info.get("total_favorited", 0),
                'signature': user_info.get("signature", ""),
                'sec_uid': user_info.get("sec_uid", ""),
                'uid': user_info.get("uid", ""),
                'unique_id': user_info.get("unique_id", ""),
                'cover_url': None,
                'avatar_larger_url': None,
                'share_url': ""
            }
            
            # 安全地提取封面图片链接
            if user_info.get("cover_url") and len(user_info["cover_url"]) > 0:
                if user_info["cover_url"][0].get("url_list") and len(user_info["cover_url"][0]["url_list"]) > 0:
                    cleaned_data['cover_url'] = user_info["cover_url"][0]["url_list"][0]
            
            # 安全地提取头像链接
            if user_info.get("avatar_larger") and user_info["avatar_larger"].get("url_list"):
                if len(user_info["avatar_larger"]["url_list"]) > 0:
                    cleaned_data['avatar_larger_url'] = user_info["avatar_larger"]["url_list"][0]
            
            # 安全地提取分享链接
            if user_info.get("share_info") and user_info["share_info"].get("share_url"):
                cleaned_data['share_url'] = user_info["share_info"]["share_url"]
            
            return cleaned_data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"调用抖音API失败: {str(e)}")
        except KeyError as e:
            raise Exception(f"API返回数据格式错误，缺少字段: {str(e)}")
        except Exception as e:
            raise Exception(f"获取作者信息失败: {str(e)}")

    @staticmethod
    def crawl_user_today_videos(sec_uid):
        """根据用户唯一ID爬取当天发布的视频"""
        import os
        import json
        from datetime import datetime
        
        try:
            # 创建video文件夹（如果不存在）
            video_base_dir = os.path.join(os.getcwd(), 'video')
            if not os.path.exists(video_base_dir):
                os.makedirs(video_base_dir)
            
            current_time = datetime.now().strftime("%Y%m%d")
            # 创建以当天时间的文件夹
            author_dir = os.path.join(video_base_dir, current_time)
            if not os.path.exists(author_dir):
                os.makedirs(author_dir)
            
            downloaded_videos = []
            total = 0

            video_list = DouyinService.fetch_user_post_videos(sec_uid, 0, 5)
            if video_list:
                for video_id in video_list:
                    video_info = DouyinService.get_video_info(f'https://www.douyin.com/video/{video_id}')
                    if video_info:
                        # 下载视频到指定文件夹
                        local_file_path = DouyinService.download_video_to_folder(video_info.get("video_uri"), author_dir, video_info['video_id'])
                                
                        # 添加本地文件路径到视频信息
                        video_info['local_file_path'] = local_file_path
                                
                        # 保存到数据库 - 使用DBService而不是DataService
                        VideoService.create_video(video_info)
                                
                        downloaded_videos.append(video_info)
                        total += 1

                return total
                        
        except Exception as e:
            if 'dp' in locals():
                dp.close()
            raise Exception(f"爬取用户视频失败: {str(e)}")
    
    @staticmethod
    def get_video_info(video_url):
        """获取视频详细信息 - 支持爬虫服务和原有API"""
        # 提取视频ID
        if '/video/' in video_url:
            aweme_id = video_url.split('/video/')[-1].split('?')[0]
        else:
            aweme_id = video_url
        
        # 优先使用爬虫服务
        if DouyinService.use_crawler_service():
            try:
                # 异步调用爬虫服务
                async def fetch_video_info():
                    client = DouyinService.get_crawler_client()
                    return await client.get_video_info(aweme_id)
                
                # 运行异步函数
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                crawler_data = loop.run_until_complete(fetch_video_info())
                loop.close()
                
                if crawler_data:
                    # 转换为原有格式
                    return {
                        'title': crawler_data.get('desc', ''),
                        'description': crawler_data.get('desc', ''),
                        'create_time': crawler_data.get('create_time', 0),
                        'duration': crawler_data.get('duration', 0),
                        'video_id': crawler_data.get('aweme_id', ''),
                        'video_url': crawler_data.get('video_url', ''),
                        'play_count': crawler_data.get('statistics', {}).get('play_count', 0),
                        'digg_count': crawler_data.get('statistics', {}).get('digg_count', 0),
                        'comment_count': crawler_data.get('statistics', {}).get('comment_count', 0),
                        'share_count': crawler_data.get('statistics', {}).get('share_count', 0),
                        'collect_count': 0,  # 爬虫服务可能不提供收藏数
                        'author_nickname': crawler_data.get('author', ''),
                        'author_unique_id': crawler_data.get('author_id', ''),
                        'author_uid': crawler_data.get('author_id', ''),
                        'author_signature': '',
                        'author_follower_count': 0,
                        'author_following_count': 0,
                        'author_total_favorited': 0,
                        'dynamic_cover_url': crawler_data.get('cover_url', ''),
                        'video_quality_high': '',
                        'video_quality_medium': '',
                        'video_quality_low': '',
                        'tags': []
                    }
            except Exception as e:
                print(f"爬虫服务获取视频信息失败，回退到原有API: {e}")
        
        # 回退到原有API
        api_url = f"{crawler_config.CRAWLER_BASE_URL}/api/hybrid/video_data"
        try:
            response = requests.get(api_url, params={"url": video_url})
            response.raise_for_status()
            
            data = response.json()["data"]
        
            # 处理视频数据 - 使用正确的DataService
            processed_data = DataService.process_video_data({"data": data})
            
            # 转换为数据库格式
            video_info = {
                'title': processed_data['video_info']['视频标题'],
                'description': processed_data['video_info']['视频描述'],
                'create_time': processed_data['video_info']['视频创建时间'],
                'duration': processed_data['video_info']['视频时长'],
                'video_id': processed_data['video_info']['视频ID'],
                'video_uri': processed_data['video_info']['视频唯一标识符'],
                'play_count': processed_data['statistics']['视频播放量'],
                'digg_count': processed_data['statistics']['视频点赞数'],
                'comment_count': processed_data['statistics']['视频评论数'],
                'share_count': processed_data['statistics']['视频分享数'],
                'collect_count': processed_data['statistics']['视频收藏数'],
                'author_nickname': processed_data['author_info']['作者昵称'],
                'author_unique_id': processed_data['author_info']['作者唯一ID'],
                'author_uid': processed_data['author_info']['作者ID'],
                'author_signature': processed_data['author_info']['作者签名'],
                'author_follower_count': processed_data['author_info']['作者粉丝数'],
                'author_following_count': processed_data['author_info']['作者关注数'],
                'author_total_favorited': processed_data['author_info']['作者获得的点赞数'],
                'dynamic_cover_url': data.get('video', {}).get('dynamic_cover', {}).get('url_list', [''])[0],
                'video_quality_high': '',
                'video_quality_medium': '',
                'video_quality_low': '',
                'tags': []
            }
            
            return video_info
            
        except Exception as e:
            print(f"获取视频信息失败: {str(e)}")
            return None
    
    @staticmethod
    def download_video_to_folder(url, folder_path, video_id):
        print(f"开始下载视频: {url}")
        print(f"文件夹路径: {folder_path}")
        print(f"视频ID: {video_id}")
        """下载视频到指定文件夹"""
        dp = None
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                print(f"第{attempt + 1}次尝试下载...")
                
                # 创建浏览器实例，增加超时设置
                dp = Chromium(1122)
                tab = dp.get_tab()
                
                # 设置页面超时时间为60秒
                tab.set.timeouts(60)
                
                # 访问下载页面
                tab.get(url)
                
                # 增加等待时间，确保页面完全加载
                tab.wait(5)
                
                # 开始下载，设置更长的超时时间
                print(f"开始下载文件...")
                download_result = tab.download(url, timeout=120)  # 120秒超时
                print(f"下载完成: {download_result}")

                if not (isinstance(download_result, tuple) and len(download_result) > 0):
                    raise Exception("下载失败：返回结果格式错误")
                    
                old_file_path = download_result[1]
                
                # 检查文件是否存在
                if not os.path.exists(old_file_path):
                    raise Exception(f"下载的文件不存在: {old_file_path}")
                
                # 生成新的文件名
                new_file_name = f"{video_id}.mp4"
                new_file_path = os.path.join(folder_path, new_file_name)
                
                # 重命名文件
                try:
                    os.rename(old_file_path, new_file_path)
                    print(f"文件已从 '{old_file_path}' 重命名为 '{new_file_path}'")
                    
                    # 验证文件大小
                    file_size = os.path.getsize(new_file_path)
                    print(f"下载完成，文件大小: {file_size} 字节")
                    
                    if file_size < 1024:  # 文件太小，可能下载失败
                        raise Exception(f"下载的文件太小，可能下载失败: {file_size} 字节")
                    
                    # 使用 moviepy 将 MP4 转换为 MP3
                    try:
                        print(f"开始转换视频为音频...")
                        
                        # 生成 MP3 文件路径
                        mp3_file_name = f"{video_id}.mp3"
                        mp3_file_path = os.path.join(folder_path, mp3_file_name)
                        
                        # 加载视频文件
                        video_clip = VideoFileClip(new_file_path)
                        
                        # 提取音频并保存为 MP3
                        audio_clip = video_clip.audio
                        audio_clip.write_audiofile(mp3_file_path)
                        
                        # 关闭文件句柄
                        audio_clip.close()
                        video_clip.close()
                        
                        print(f"音频转换完成: {mp3_file_path}")
                        
                        # 验证 MP3 文件是否创建成功
                        if os.path.exists(mp3_file_path):
                            mp3_size = os.path.getsize(mp3_file_path)
                            print(f"MP3 文件大小: {mp3_size} 字节")
                        else:
                            print("警告: MP3 文件创建失败")
                            
                    except ImportError:
                        print("警告: moviepy 库未安装，跳过音频转换")
                    except Exception as e:
                        print(f"音频转换失败: {str(e)}")
                        # 音频转换失败不影响视频下载的成功
                    
                    return new_file_path
                    
                except Exception as e:
                    print(f"重命名文件时出错：{e}")
                    raise
                
            except Exception as e:
                print(f"第{attempt + 1}次下载失败: {str(e)}")
                
                if dp:
                    try:
                        dp.quit()
                    except:
                        pass
                    dp = None
                
                if attempt < max_retries - 1:
                    print(f"等待5秒后重试...")
                    import time
                    time.sleep(5)
                else:
                    raise Exception(f"下载失败，已重试{max_retries}次: {str(e)}")
            
            finally:
                if dp:
                    try:
                        dp.quit()
                    except:
                        pass

    @staticmethod
    def fetch_user_post_videos(user_url, max_count=10):
        """获取用户发布视频 - 支持爬虫服务和原有API"""
        # 提取用户ID
        if '/user/' in user_url:
            user_id = user_url.split('/user/')[-1].split('?')[0]
        else:
            user_id = user_url
        
        # 优先使用爬虫服务
        if DouyinService.use_crawler_service():
            try:
                # 异步调用爬虫服务
                async def fetch_user_videos():
                    client = DouyinService.get_crawler_client()
                    return await client.get_user_videos(user_id, max_count)
                
                # 运行异步函数
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                crawler_data = loop.run_until_complete(fetch_user_videos())
                loop.close()
                
                if crawler_data:
                    # 转换为原有格式
                    videos = []
                    for video_data in crawler_data:
                        video_info = {
                            'title': video_data.get('desc', ''),
                            'description': video_data.get('desc', ''),
                            'create_time': video_data.get('create_time', 0),
                            'duration': video_data.get('duration', 0),
                            'video_id': video_data.get('aweme_id', ''),
                            'video_uri': video_data.get('video_url', ''),
                            'play_count': video_data.get('statistics', {}).get('play_count', 0),
                            'digg_count': video_data.get('statistics', {}).get('digg_count', 0),
                            'comment_count': video_data.get('statistics', {}).get('comment_count', 0),
                            'share_count': video_data.get('statistics', {}).get('share_count', 0),
                            'collect_count': 0,  # 爬虫服务可能不提供收藏数
                            'author_nickname': video_data.get('author', ''),
                            'author_unique_id': video_data.get('author_id', ''),
                            'author_uid': video_data.get('author_id', ''),
                            'author_signature': '',
                            'author_follower_count': 0,
                            'author_following_count': 0,
                            'author_total_favorited': 0,
                            'dynamic_cover_url': video_data.get('cover_url', ''),
                            'video_quality_high': '',
                            'video_quality_medium': '',
                            'video_quality_low': '',
                            'tags': []
                        }
                        videos.append(video_info)
                    return videos
            except Exception as e:
                print(f"爬虫服务获取用户发布视频失败，回退到原有API: {e}")
        
        # 回退到原有API
        api_url = f"{crawler_config.CRAWLER_BASE_URL}/api/hybrid/user_post_videos"
        try:
            response = requests.get(api_url, params={
                "url": user_url,
                "max_count": max_count
            })
            response.raise_for_status()
            
            data = response.json()["data"]
        
            # 处理视频数据
            processed_data = DataService.process_video_data({"data": data})
            
            # 转换为数据库格式
            videos = []
            for video_data in processed_data.get('videos', []):
                video_info = {
                    'title': video_data['video_info']['视频标题'],
                    'description': video_data['video_info']['视频描述'],
                    'create_time': video_data['video_info']['视频创建时间'],
                    'duration': video_data['video_info']['视频时长'],
                    'video_id': video_data['video_info']['视频ID'],
                    'video_uri': video_data['video_info']['视频唯一标识符'],
                    'play_count': video_data['statistics']['视频播放量'],
                    'digg_count': video_data['statistics']['视频点赞数'],
                    'comment_count': video_data['statistics']['视频评论数'],
                    'share_count': video_data['statistics']['视频分享数'],
                    'collect_count': video_data['statistics']['视频收藏数'],
                    'author_nickname': video_data['author_info']['作者昵称'],
                    'author_unique_id': video_data['author_info']['作者唯一ID'],
                    'author_uid': video_data['author_info']['作者ID'],
                    'author_signature': video_data['author_info']['作者签名'],
                    'author_follower_count': video_data['author_info']['作者粉丝数'],
                    'author_following_count': video_data['author_info']['作者关注数'],
                    'author_total_favorited': video_data['author_info']['作者获得的点赞数'],
                    'dynamic_cover_url': video_data.get('video', {}).get('dynamic_cover', {}).get('url_list', [''])[0],
                    'video_quality_high': '',
                    'video_quality_medium': '',
                    'video_quality_low': '',
                    'tags': []
                }
                videos.append(video_info)
            
            return videos
            
        except Exception as e:
            print(f"获取用户发布视频失败: {str(e)}")
            return []
