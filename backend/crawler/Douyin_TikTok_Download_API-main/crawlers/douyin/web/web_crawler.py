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


import asyncio  # 异步I/O
import os  # 系统操作
import time  # 时间操作
import json  # JSON处理
from urllib.parse import urlencode, quote  # URL编码
import yaml  # 配置文件
import httpx  # HTTP客户端

# 日志
from crawlers.utils.logger import logger

# 基础爬虫客户端和抖音API端点
from crawlers.base_crawler import BaseCrawler
from crawlers.douyin.web.endpoints import DouyinAPIEndpoints
# 抖音接口数据请求模型
from crawlers.douyin.web.models import (
    BaseRequestModel, LiveRoomRanking, PostComments,
    PostCommentsReply, PostDetail,
    UserProfile, UserCollection, UserLike, UserLive,
    UserLive2, UserMix, UserPost
)
# 抖音应用的工具类
from crawlers.douyin.web.utils import (AwemeIdFetcher,  # Aweme ID获取
                                       BogusManager,  # XBogus管理
                                       SecUserIdFetcher,  # 安全用户ID获取
                                       TokenManager,  # 令牌管理
                                       VerifyFpManager,  # 验证管理
                                       WebCastIdFetcher,  # 直播ID获取
                                       extract_valid_urls  # URL提取
                                       )

# 配置文件路径
path = os.path.abspath(os.path.dirname(__file__))

# 读取配置文件
with open(f"{path}/config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


class DouyinWebCrawler:

    # 从配置文件中获取抖音的请求头
    async def get_douyin_headers(self):
        douyin_config = config["TokenManager"]["douyin"]
        kwargs = {
            "headers": {
                "Accept-Language": douyin_config["headers"]["Accept-Language"],
                "User-Agent": douyin_config["headers"]["User-Agent"],
                "Referer": douyin_config["headers"]["Referer"],
                "Cookie": douyin_config["headers"]["Cookie"],
            },
            "proxies": {"http://": douyin_config["proxies"]["http"], "https://": douyin_config["proxies"]["https"]},
        }
        return kwargs

    "-------------------------------------------------------handler接口列表-------------------------------------------------------"

    # 获取单个作品数据
    async def fetch_one_video(self, aweme_id: str):
        # 获取抖音的实时Cookie
        kwargs = await self.get_douyin_headers()
        
        # 优化请求头，确保包含必要的参数
        headers = kwargs["headers"].copy()
        headers.update({
            'Accept': '*/*',
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Origin': 'https://www.douyin.com'
        })
        kwargs["headers"] = headers
        
        # 创建一个基础爬虫
        base_crawler = BaseCrawler(proxies=kwargs["proxies"], crawler_headers=kwargs["headers"])
        async with base_crawler as crawler:
            # 创建一个作品详情的BaseModel参数
            params = PostDetail(aweme_id=aweme_id)
            
            # 生成一个作品详情的带有加密参数的Endpoint
            params_dict = params.dict()
            
            # 使用动态生成的真实msToken
            params_dict["msToken"] = TokenManager().gen_real_msToken()
            logger.info(f"生成的msToken: {params_dict['msToken']}")
            
            a_bogus = BogusManager.ab_model_2_endpoint(params_dict, kwargs["headers"]["User-Agent"])
            endpoint = f"{DouyinAPIEndpoints.POST_DETAIL}?{urlencode(params_dict)}&a_bogus={a_bogus}"
            logger.info(f"完整请求URL: {endpoint}")

            try:
                # 使用BaseCrawler的fetch_get_json方法，它有完善的重试逻辑
                logger.info("使用BaseCrawler的fetch_get_json方法请求API...")
                response_data = await crawler.fetch_get_json(endpoint)
                logger.info(f"API响应: {response_data}")
                
                # 兼容处理：检查响应格式，可能抖音API已更改
                if isinstance(response_data, dict):
                    # 检查是否有其他可能的字段名
                    possible_fields = ['aweme_detail', 'data', 'item_info', 'item_struct']
                    for field in possible_fields:
                        if field in response_data:
                            logger.info(f"发现可能的视频详情字段: {field}")
                            # 如果找到其他字段，将其映射到aweme_detail
                            if field != 'aweme_detail':
                                response_data['aweme_detail'] = response_data[field]
                                logger.info(f"已将{field}字段映射到aweme_detail")
                            break
                    else:
                        logger.warning(f"API响应中未找到已知的视频详情字段，当前字段: {list(response_data.keys())}")
                
                return response_data
            except Exception as e:
                logger.error(f"API请求失败: {e}")
                import traceback
                traceback.print_exc()
                return None
        return None

    # 获取用户发布作品数据
    async def fetch_user_post_videos(self, sec_user_id: str, max_cursor: int, count: int):
        kwargs = await self.get_douyin_headers()
        base_crawler = BaseCrawler(proxies=kwargs["proxies"], crawler_headers=kwargs["headers"])
        async with base_crawler as crawler:
            params = UserPost(sec_user_id=sec_user_id, max_cursor=max_cursor, count=count)
            # endpoint = BogusManager.xb_model_2_endpoint(
            # )
            # response = await crawler.fetch_get_json(endpoint)

            # 生成一个用户发布作品数据的带有a_bogus加密参数的Endpoint
            params_dict = params.dict()
            params_dict["msToken"] = ''
            a_bogus = BogusManager.ab_model_2_endpoint(params_dict, kwargs["headers"]["User-Agent"])
            endpoint = f"{DouyinAPIEndpoints.USER_POST}?{urlencode(params_dict)}&a_bogus={a_bogus}"

            response = await crawler.fetch_get_json(endpoint)
        return response

    # 获取用户喜欢作品数据
    async def fetch_user_like_videos(self, sec_user_id: str, max_cursor: int, count: int):
        kwargs = await self.get_douyin_headers()
        base_crawler = BaseCrawler(proxies=kwargs["proxies"], crawler_headers=kwargs["headers"])
        async with base_crawler as crawler:
            params = UserLike(sec_user_id=sec_user_id, max_cursor=max_cursor, count=count)
            # endpoint = BogusManager.xb_model_2_endpoint(
            # )
            # response = await crawler.fetch_get_json(endpoint)

            params_dict = params.dict()
            params_dict["msToken"] = ''
            a_bogus = BogusManager.ab_model_2_endpoint(params_dict, kwargs["headers"]["User-Agent"])
            endpoint = f"{DouyinAPIEndpoints.USER_FAVORITE_A}?{urlencode(params_dict)}&a_bogus={a_bogus}"

            response = await crawler.fetch_get_json(endpoint)
        return response

    # 获取用户收藏作品数据（用户提供自己的Cookie）
    async def fetch_user_collection_videos(self, cookie: str, cursor: int = 0, count: int = 20):
        kwargs = await self.get_douyin_headers()
        kwargs["headers"]["Cookie"] = cookie
        base_crawler = BaseCrawler(proxies=kwargs["proxies"], crawler_headers=kwargs["headers"])
        async with base_crawler as crawler:
            params = UserCollection(cursor=cursor, count=count)
            endpoint = BogusManager.xb_model_2_endpoint(
                DouyinAPIEndpoints.USER_COLLECTION, params.dict(), kwargs["headers"]["User-Agent"]
            )
            response = await crawler.fetch_post_json(endpoint)
        return response

    # 获取用户合辑作品数据
    async def fetch_user_mix_videos(self, mix_id: str, cursor: int = 0, count: int = 20):
        kwargs = await self.get_douyin_headers()
        base_crawler = BaseCrawler(proxies=kwargs["proxies"], crawler_headers=kwargs["headers"])
        async with base_crawler as crawler:
            params = UserMix(mix_id=mix_id, cursor=cursor, count=count)
            endpoint = BogusManager.xb_model_2_endpoint(
                DouyinAPIEndpoints.MIX_AWEME, params.dict(), kwargs["headers"]["User-Agent"]
            )
            response = await crawler.fetch_get_json(endpoint)
        return response

    # 获取用户直播流数据
    async def fetch_user_live_videos(self, webcast_id: str, room_id_str=""):
        kwargs = await self.get_douyin_headers()
        base_crawler = BaseCrawler(proxies=kwargs["proxies"], crawler_headers=kwargs["headers"])
        async with base_crawler as crawler:
            params = UserLive(web_rid=webcast_id, room_id_str=room_id_str)
            endpoint = BogusManager.xb_model_2_endpoint(
                DouyinAPIEndpoints.LIVE_INFO, params.dict(), kwargs["headers"]["User-Agent"]
            )
            response = await crawler.fetch_get_json(endpoint)
        return response

    # 获取指定用户的直播流数据
    async def fetch_user_live_videos_by_room_id(self, room_id: str):
        kwargs = await self.get_douyin_headers()
        base_crawler = BaseCrawler(proxies=kwargs["proxies"], crawler_headers=kwargs["headers"])
        async with base_crawler as crawler:
            params = UserLive2(room_id=room_id)
            endpoint = BogusManager.xb_model_2_endpoint(
                DouyinAPIEndpoints.LIVE_INFO_ROOM_ID, params.dict(), kwargs["headers"]["User-Agent"]
            )
            response = await crawler.fetch_get_json(endpoint)
        return response

    # 获取直播间送礼用户排行榜
    async def fetch_live_gift_ranking(self, room_id: str, rank_type: int = 30):
        kwargs = await self.get_douyin_headers()
        base_crawler = BaseCrawler(proxies=kwargs["proxies"], crawler_headers=kwargs["headers"])
        async with base_crawler as crawler:
            params = LiveRoomRanking(room_id=room_id, rank_type=rank_type)
            endpoint = BogusManager.xb_model_2_endpoint(
                DouyinAPIEndpoints.LIVE_GIFT_RANK, params.dict(), kwargs["headers"]["User-Agent"]
            )
            response = await crawler.fetch_get_json(endpoint)
        return response

    # 获取指定用户的信息
    async def handler_user_profile(self, sec_user_id: str):
        kwargs = await self.get_douyin_headers()
        base_crawler = BaseCrawler(proxies=kwargs["proxies"], crawler_headers=kwargs["headers"])
        async with base_crawler as crawler:
            params = UserProfile(sec_user_id=sec_user_id)
            endpoint = BogusManager.xb_model_2_endpoint(
                DouyinAPIEndpoints.USER_DETAIL, params.dict(), kwargs["headers"]["User-Agent"]
            )
            response = await crawler.fetch_get_json(endpoint)
        return response

    # 获取指定视频的评论数据
    async def fetch_video_comments(self, aweme_id: str, cursor: int = 0, count: int = 20):
        kwargs = await self.get_douyin_headers()
        base_crawler = BaseCrawler(proxies=kwargs["proxies"], crawler_headers=kwargs["headers"])
        async with base_crawler as crawler:
            params = PostComments(aweme_id=aweme_id, cursor=cursor, count=count)
            endpoint = BogusManager.xb_model_2_endpoint(
                DouyinAPIEndpoints.POST_COMMENT, params.dict(), kwargs["headers"]["User-Agent"]
            )
            response = await crawler.fetch_get_json(endpoint)
        return response

    # 获取指定视频的评论回复数据
    async def fetch_video_comments_reply(self, item_id: str, comment_id: str, cursor: int = 0, count: int = 20):
        kwargs = await self.get_douyin_headers()
        base_crawler = BaseCrawler(proxies=kwargs["proxies"], crawler_headers=kwargs["headers"])
        async with base_crawler as crawler:
            params = PostCommentsReply(item_id=item_id, comment_id=comment_id, cursor=cursor, count=count)
            endpoint = BogusManager.xb_model_2_endpoint(
                DouyinAPIEndpoints.POST_COMMENT_REPLY, params.dict(), kwargs["headers"]["User-Agent"]
            )
            response = await crawler.fetch_get_json(endpoint)
        return response

    # 获取抖音热榜数据
    async def fetch_hot_search_result(self):
        kwargs = await self.get_douyin_headers()
        base_crawler = BaseCrawler(proxies=kwargs["proxies"], crawler_headers=kwargs["headers"])
        async with base_crawler as crawler:
            params = BaseRequestModel()
            endpoint = BogusManager.xb_model_2_endpoint(
                DouyinAPIEndpoints.DOUYIN_HOT_SEARCH, params.dict(), kwargs["headers"]["User-Agent"]
            )
            response = await crawler.fetch_get_json(endpoint)
        return response

    "-------------------------------------------------------utils接口列表-------------------------------------------------------"

    # 生成真实msToken
    async def gen_real_msToken(self, ):
        result = {
            "msToken": TokenManager().gen_real_msToken()
        }
        return result

    # 生成ttwid
    async def gen_ttwid(self, ):
        result = {
            "ttwid": TokenManager().gen_ttwid()
        }
        return result

    # 生成verify_fp
    async def gen_verify_fp(self, ):
        result = {
            "verify_fp": VerifyFpManager.gen_verify_fp()
        }
        return result

    # 生成s_v_web_id
    async def gen_s_v_web_id(self, ):
        result = {
            "s_v_web_id": VerifyFpManager.gen_s_v_web_id()
        }
        return result

    # 使用接口地址生成Xb参数
    async def get_x_bogus(self, url: str, user_agent: str):
        url = BogusManager.xb_str_2_endpoint(url, user_agent)
        result = {
            "url": url,
            "x_bogus": url.split("&X-Bogus=")[1],
            "user_agent": user_agent
        }
        return result

    # 使用接口地址生成Ab参数
    async def get_a_bogus(self, url: str, user_agent: str):
        endpoint = url.split("?")[0]
        # 将URL参数转换为dict
        params = dict([i.split("=") for i in url.split("?")[1].split("&")])
        # 去除URL中的msToken参数
        params["msToken"] = ""
        a_bogus = BogusManager.ab_model_2_endpoint(params, user_agent)
        result = {
            "url": f"{endpoint}?{urlencode(params)}&a_bogus={a_bogus}",
            "a_bogus": a_bogus,
            "user_agent": user_agent
        }
        return result

    # 提取单个用户id
    async def get_sec_user_id(self, url: str):
        return await SecUserIdFetcher.get_sec_user_id(url)

    # 提取列表用户id
    async def get_all_sec_user_id(self, urls: list):
        # 提取有效URL
        urls = extract_valid_urls(urls)

        # 对于URL列表
        return await SecUserIdFetcher.get_all_sec_user_id(urls)

    # 提取单个作品id
    async def get_aweme_id(self, url: str):
        return await AwemeIdFetcher.get_aweme_id(url)

    # 提取列表作品id
    async def get_all_aweme_id(self, urls: list):
        # 提取有效URL
        urls = extract_valid_urls(urls)

        # 对于URL列表
        return await AwemeIdFetcher.get_all_aweme_id(urls)

    # 提取单个直播间号
    async def get_webcast_id(self, url: str):
        return await WebCastIdFetcher.get_webcast_id(url)

    # 提取列表直播间号
    async def get_all_webcast_id(self, urls: list):
        # 提取有效URL
        urls = extract_valid_urls(urls)

        # 对于URL列表
        return await WebCastIdFetcher.get_all_webcast_id(urls)

    async def update_cookie(self, cookie: str):
        global config
        service = "douyin"
        print('DouyinWebCrawler before update', config["TokenManager"][service]["headers"]["Cookie"])
        print('DouyinWebCrawler to update', cookie)
        # 1. 更新内存中的配置（立即生效）
        config["TokenManager"][service]["headers"]["Cookie"] = cookie
        print('DouyinWebCrawler cookie updated', config["TokenManager"][service]["headers"]["Cookie"])
        # 2. 写入配置文件（持久化）
        config_path = f"{path}/config.yaml"
        with open(config_path, 'w', encoding='utf-8') as file:
            yaml.dump(config, file, default_flow_style=False, allow_unicode=True, indent=2)

    async def main(self):
        """-------------------------------------------------------handler接口列表-------------------------------------------------------"""

        # 获取单一视频信息
        # aweme_id = "7372484719365098803"
        # result = await self.fetch_one_video(aweme_id)
        # print(result)

        # 获取用户发布作品数据
        # max_cursor = 0
        # count = 10
        # print(result)

        # 获取用户喜欢作品数据
        # max_cursor = 0
        # count = 10
        # print(result)

        # 获取用户收藏作品数据（用户提供自己的Cookie）
        # cookie = "带上你的Cookie/Put your Cookie here"
        # cursor = 0
        # counts = 20
        # print(result)

        # 获取用户合辑作品数据
        # mix_id = "7348687990509553679"
        # cursor = 0
        # counts = 20
        # print(result)

        # 获取用户直播流数据
        # https://live.douyin.com/285520721194
        # webcast_id = "285520721194"
        # print(result)

        # 获取指定用户的直播流数据
        # # https://live.douyin.com/7318296342189919011
        # room_id = "7318296342189919011"
        # print(result)

        # 获取直播间送礼用户排行榜
        # room_id = "7356585666190461731"
        # rank_type = 30
        # print(result)

        # 获取指定用户的信息
        # print(result)

        # 获取单个视频评论数据
        # aweme_id = "7334525738793618688"
        # result = await self.fetch_video_comments(aweme_id)
        # print(result)

        # 获取单个视频评论回复数据
        # item_id = "7344709764531686690"
        # comment_id = "7346856757471953698"
        # print(result)

        # 获取指定关键词的综合搜索结果
        # keyword = "中华娘"
        # offset = 0
        # count = 20
        # sort_type = "0"
        # publish_time = "0"
        # filter_duration = "0"
        # print(result)

        # 获取抖音热榜数据
        # result = await self.fetch_hot_search_result()
        # print(result)

        """-------------------------------------------------------utils接口列表-------------------------------------------------------"""

        # 获取抖音Web的游客Cookie
        # print(result)

        # 生成真实msToken
        # result = await self.gen_real_msToken()
        # print(result)

        # 生成ttwid
        # result = await self.gen_ttwid()
        # print(result)

        # 生成verify_fp
        # result = await self.gen_verify_fp()
        # print(result)

        # 生成s_v_web_id
        # result = await self.gen_s_v_web_id()
        # print(result)

        # 使用接口地址生成Xb参数
        # result = await self.get_x_bogus(url, user_agent)
        # print(result)

        # 提取单个用户id
        # result = await self.get_sec_user_id(raw_url)
        # print(result)

        # 提取列表用户id
        # raw_urls = [
        #     "https://v.douyin.com/idFqvUms/",
        # ]
        # result = await self.get_all_sec_user_id(raw_urls)
        # print(result)

        # 提取单个作品id
        # result = await self.get_aweme_id(raw_url)
        # print(result)

        # 提取列表作品id
        # raw_urls = [
        #     "https://v.douyin.com/iRNBho6u/",
        # ]
        # result = await self.get_all_aweme_id(raw_urls)
        # print(result)

        # 提取单个直播间号
        # raw_url = "https://live.douyin.com/775841227732"
        # result = await self.get_webcast_id(raw_url)
        # print(result)

        # 提取列表直播间号
        # raw_urls = [
        #     "https://live.douyin.com/775841227732",
        #     "https://v.douyin.com/i8tBR7hX/",
        # ]
        # result = await self.get_all_webcast_id(raw_urls)
        # print(result)

        # 占位
        pass


if __name__ == "__main__":
    # 初始化
    DouyinWebCrawler = DouyinWebCrawler()

    # 开始时间
    start = time.time()

    asyncio.run(DouyinWebCrawler.main())

    # 结束时间
    end = time.time()
    print(f"耗时：{end - start}")

