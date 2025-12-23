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
import asyncio
import json
import os
import random
import re
import time
import urllib
from pathlib import Path
from typing import Union
from urllib.parse import urlencode, quote

# import execjs
import httpx
import qrcode
import yaml

from crawlers.douyin.web.xbogus import XBogus as XB
from crawlers.douyin.web.abogus import ABogus as AB

from crawlers.utils.api_exceptions import (
    APIError,
    APIConnectionError,
    APIResponseError,
    APIUnavailableError,
    APIUnauthorizedError,
    APINotFoundError,
)
from crawlers.utils.logger import logger
from crawlers.utils.utils import (
    gen_random_str,
    get_timestamp,
    extract_valid_urls,
    split_filename,
)

# 配置文件路径
# Read the configuration file
path = os.path.abspath(os.path.dirname(__file__))

# 读取配置文件
with open(f"{path}/config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


# 配置验证函数
def validate_config(config):
    """验证配置文件的有效性"""
    douyin_config = config.get("TokenManager", {}).get("douyin", {})
    headers = douyin_config.get("headers", {})
    
    # 验证Cookie是否存在且不为空
    cookie = headers.get("Cookie", "")
    if not cookie:
        logger.warning("Cookie配置为空，请在config.yaml中配置有效的抖音Cookie")
    
    # 验证User-Agent是否为推荐的默认值
    default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
    current_ua = headers.get("User-Agent", "")
    if current_ua != default_ua:
        logger.warning(f"User-Agent已被修改为: {current_ua}\n建议保持默认值: {default_ua}")
    
    # 验证Referer是否指向抖音官网
    referer = headers.get("Referer", "")
    if "douyin.com" not in referer:
        logger.warning(f"Referer配置不正确: {referer}\n建议设置为: https://www.douyin.com/")
    
    # 验证msToken配置是否存在
    ms_token_config = douyin_config.get("msToken", None)
    if not ms_token_config:
        logger.warning("msToken配置缺失，请检查config.yaml文件")
    
    # 验证ttwid配置是否存在
    ttwid_config = douyin_config.get("ttwid", None)
    if not ttwid_config:
        logger.warning("ttwid配置缺失，请检查config.yaml文件")


# 执行配置验证
validate_config(config)


class TokenManager:
    douyin_manager = config.get("TokenManager").get("douyin")
    token_conf = douyin_manager.get("msToken", None)
    ttwid_conf = douyin_manager.get("ttwid", None)
    proxies_conf = douyin_manager.get("proxies", None)
    proxies = {
        "http://": proxies_conf.get("http", None),
        "https://": proxies_conf.get("https", None),
    }

    @classmethod
    def gen_real_msToken(cls) -> str:

        payload = json.dumps(
            {
                "magic": cls.token_conf["magic"],
                "version": cls.token_conf["version"],
                "dataType": cls.token_conf["dataType"],
                "strData": cls.token_conf["strData"],
                "tspFromClient": get_timestamp(),
            }
        )
        headers = {
            "User-Agent": cls.token_conf["User-Agent"],
            "Content-Type": "application/json",
        }

        transport = httpx.HTTPTransport(retries=5)
        with httpx.Client(transport=transport, proxies=cls.proxies) as client:
            try:
                response = client.post(
                    cls.token_conf["url"], content=payload, headers=headers
                )
                response.raise_for_status()

                msToken = str(httpx.Cookies(response.cookies).get("msToken"))
                if len(msToken) not in [120, 128]:
                    raise APIResponseError("响应内容：{0}， Douyin msToken API 的响应内容不符合要求。".format(msToken))

                return msToken

            # except httpx.RequestError as exc:
            #     raise APIConnectionError(
            #     )
            #
            # except httpx.HTTPStatusError as e:
            #     if e.response.status_code == 401:
            #         raise APIUnauthorizedError(
            #             .format("msToken", "douyin")
            #         )
            #
            #     elif e.response.status_code == 404:
            #     else:
            #         raise APIResponseError(
            #             "链接：{0}，状态码 {1}：{2} ".format(
            #             )
            #         )

            except Exception as e:
                # 返回虚假的msToken (Return a fake msToken)
                logger.error("请求Douyin msToken API时发生错误：{0}".format(e))
                logger.info("将使用本地生成的虚假msToken参数，以继续请求。")
                return cls.gen_false_msToken()

    @classmethod
    def gen_false_msToken(cls) -> str:
        """生成随机msToken (Generate random msToken)"""
        return gen_random_str(126) + "=="

    @classmethod
    def gen_ttwid(cls) -> str:

        transport = httpx.HTTPTransport(retries=5)
        with httpx.Client(transport=transport) as client:
            try:
                response = client.post(
                    cls.ttwid_conf["url"], content=cls.ttwid_conf["data"]
                )
                response.raise_for_status()

                ttwid = str(httpx.Cookies(response.cookies).get("ttwid"))
                return ttwid

            except httpx.RequestError as exc:
                raise APIConnectionError(
                    "请求端点失败，请检查当前网络环境。 链接：{0}，代理：{1}，异常类名：{2}，异常详细信息：{3}"
                    .format(cls.ttwid_conf["url"], cls.proxies, cls.__name__, exc)
                )

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise APIUnauthorizedError(
                        "参数验证失败，请更新 Douyin_TikTok_Download_API 配置文件中的 {0}，以匹配 {1} 新规则"
                        .format("ttwid", "douyin")
                    )

                elif e.response.status_code == 404:
                    raise APINotFoundError("ttwid无法找到API端点")
                else:
                    raise APIResponseError("链接：{0}，状态码 {1}：{2} ".format(
                        e.response.url, e.response.status_code, e.response.text
                    )
                    )


class VerifyFpManager:
    @classmethod
    def gen_verify_fp(cls) -> str:
        base_str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        t = len(base_str)
        milliseconds = int(round(time.time() * 1000))
        base36 = ""
        while milliseconds > 0:
            remainder = milliseconds % 36
            if remainder < 10:
                base36 = str(remainder) + base36
            else:
                base36 = chr(ord("a") + remainder - 10) + base36
            milliseconds = int(milliseconds / 36)
        r = base36
        o = [""] * 36
        o[8] = o[13] = o[18] = o[23] = "_"
        o[14] = "4"

        for i in range(36):
            if not o[i]:
                n = 0 or int(random.random() * t)
                if i == 19:
                    n = 3 & n | 8
                o[i] = base_str[n]

        return "verify_" + r + "_" + "".join(o)

    @classmethod
    def gen_s_v_web_id(cls) -> str:
        return cls.gen_verify_fp()


class BogusManager:

    # 字符串方法生成X-Bogus参数
    @classmethod
    def xb_str_2_endpoint(cls, endpoint: str, user_agent: str) -> str:
        try:
            final_endpoint = XB(user_agent).getXBogus(endpoint)
        except Exception as e:
            raise RuntimeError("生成X-Bogus失败: {0})".format(e))

        return final_endpoint[0]

    # 字典方法生成X-Bogus参数
    @classmethod
    def xb_model_2_endpoint(cls, base_endpoint: str, params: dict, user_agent: str) -> str:
        if not isinstance(params, dict):
            raise TypeError("参数必须是字典类型")

        param_str = "&".join([f"{k}={v}" for k, v in params.items()])

        try:
            xb_value = XB(user_agent).getXBogus(param_str)
        except Exception as e:
            raise RuntimeError("生成X-Bogus失败: {0})".format(e))

        separator = "&" if "?" in base_endpoint else "?"

        final_endpoint = f"{base_endpoint}{separator}{param_str}&X-Bogus={xb_value[1]}"

        return final_endpoint

    # 字符串方法生成A-Bogus参数
    # TODO: 未完成测试，暂时不提交至主分支。
    # @classmethod
    #     try:
    #         # 获取请求参数
    #         # 确定A-Bogus JS文件路径
    #             js_code = file.read()
    #         # 此处需要使用Node环境
    #         # - 安装Node.js
    #         # - 安装execjs库
    #         # - 安装NPM依赖
    #         # - npm install jsdom
    #         node_runtime = execjs.get('Node')
    #         context = node_runtime.compile(js_code)
    #         return a_bougus
    #     except Exception as e:
    #         raise RuntimeError("生成A-Bogus失败: {0})".format(e))

    # 字典方法生成A-Bogus参数，感谢 @JoeanAmier 提供的纯Python版本算法。
    @classmethod
    def ab_model_2_endpoint(cls, params: dict, user_agent: str) -> str:
        if not isinstance(params, dict):
            raise TypeError("参数必须是字典类型")

        try:
            ab_value = AB().get_value(params, )
        except Exception as e:
            raise RuntimeError("生成A-Bogus失败: {0})".format(e))

        return quote(ab_value, safe='')


class SecUserIdFetcher:
    # 预编译正则表达式
    _DOUYIN_URL_PATTERN = re.compile(r"user/([^/?]*)")
    _REDIRECT_URL_PATTERN = re.compile(r"sec_uid=([^&]*)")

    @classmethod
    async def get_sec_user_id(cls, url: str) -> str:

        if not isinstance(url, str):
            raise TypeError("参数必须是字符串类型")

        # 提取有效URL
        url = extract_valid_urls(url)

        if url is None:
            raise (
                APINotFoundError("输入的URL不合法。类名：{0}".format(cls.__name__))
            )

        pattern = (
            cls._REDIRECT_URL_PATTERN
            if "v.douyin.com" in url
            else cls._DOUYIN_URL_PATTERN
        )

        try:
            transport = httpx.AsyncHTTPTransport(retries=5)
            async with httpx.AsyncClient(
                    transport=transport, proxies=TokenManager.proxies, timeout=10
            ) as client:
                response = await client.get(url, follow_redirects=True)
                if response.status_code in {200, 444}:
                    match = pattern.search(str(response.url))
                    if match:
                        return match.group(1)
                    else:
                        raise APIResponseError(
                            "未在响应的地址中找到sec_user_id，检查链接是否为用户主页类名：{0}"
                            .format(cls.__name__)
                        )

                elif response.status_code == 401:
                    raise APIUnauthorizedError("未授权的请求。类名：{0}".format(cls.__name__)
                                               )
                elif response.status_code == 404:
                    raise APINotFoundError("未找到API端点。类名：{0}".format(cls.__name__)
                                           )
                elif response.status_code == 503:
                    raise APIUnavailableError("API服务不可用。类名：{0}".format(cls.__name__)
                                              )
                else:
                    raise APIResponseError("链接：{0}，状态码 {1}：{2} ".format(
                        response.url, response.status_code, response.text
                    )
                    )

        except httpx.RequestError as exc:
            raise APIConnectionError("请求端点失败，请检查当前网络环境。 链接：{0}，代理：{1}，异常类名：{2}，异常详细信息：{3}"
                                     .format(url, TokenManager.proxies, cls.__name__, exc)
                                     )

    @classmethod
    async def get_all_sec_user_id(cls, urls: list) -> list:

        if not isinstance(urls, list):
            raise TypeError("参数必须是列表类型")

        # 提取有效URL
        urls = extract_valid_urls(urls)

        if urls == []:
            raise (
                APINotFoundError("输入的URL List不合法。类名：{0}".format(cls.__name__)
                                 )
            )

        sec_user_ids = [cls.get_sec_user_id(url) for url in urls]
        return await asyncio.gather(*sec_user_ids)


class AwemeIdFetcher:
    # 预编译正则表达式
    _DOUYIN_VIDEO_URL_PATTERN = re.compile(r"video/([^/?]*)")
    _DOUYIN_VIDEO_URL_PATTERN_NEW = re.compile(r"[?&]vid=(\d+)")
    _DOUYIN_NOTE_URL_PATTERN = re.compile(r"note/([^/?]*)")
    _DOUYIN_DISCOVER_URL_PATTERN = re.compile(r"modal_id=([0-9]+)")

    @classmethod
    async def get_aweme_id(cls, url: str) -> str:

        if not isinstance(url, str):
            raise TypeError("参数必须是字符串类型")

        # 重定向到完整链接
        transport = httpx.AsyncHTTPTransport(retries=5)
        async with httpx.AsyncClient(
                transport=transport, proxy=None, timeout=10
        ) as client:
            try:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

                response_url = str(response.url)

                # 按顺序尝试匹配视频ID
                for pattern in [
                    cls._DOUYIN_VIDEO_URL_PATTERN,
                    cls._DOUYIN_VIDEO_URL_PATTERN_NEW,
                    cls._DOUYIN_NOTE_URL_PATTERN,
                    cls._DOUYIN_DISCOVER_URL_PATTERN
                ]:
                    match = pattern.search(response_url)
                    if match:
                        return match.group(1)

                raise APIResponseError("未在响应的地址中找到 aweme_id，检查链接是否为作品页")

            except httpx.RequestError as exc:
                raise APIConnectionError(
                    f"请求端点失败，请检查当前网络环境。链接：{url}，代理：{TokenManager.proxies}，异常类名：{cls.__name__}，异常详细信息：{exc}"
                )

            except httpx.HTTPStatusError as e:
                raise APIResponseError(
                    f"链接：{e.response.url}，状态码 {e.response.status_code}：{e.response.text}"
                )

    @classmethod
    async def get_all_aweme_id(cls, urls: list) -> list:

        if not isinstance(urls, list):
            raise TypeError("参数必须是列表类型")

        # 提取有效URL
        urls = extract_valid_urls(urls)

        if urls == []:
            raise (
                APINotFoundError("输入的URL List不合法。类名：{0}".format(cls.__name__)
                                 )
            )

        aweme_ids = [cls.get_aweme_id(url) for url in urls]
        return await asyncio.gather(*aweme_ids)


class MixIdFetcher:
    # 获取方法同AwemeIdFetcher
    @classmethod
    async def get_mix_id(cls, url: str) -> str:
        return


class WebCastIdFetcher:
    # 预编译正则表达式
    _DOUYIN_LIVE_URL_PATTERN = re.compile(r"live/([^/?]*)")
    # https://live.douyin.com/766545142636
    _DOUYIN_LIVE_URL_PATTERN2 = re.compile(r"http[s]?://live.douyin.com/(\d+)")
    _DOUYIN_LIVE_URL_PATTERN3 = re.compile(r"reflow/([^/?]*)")

    @classmethod
    async def get_webcast_id(cls, url: str) -> str:

        if not isinstance(url, str):
            raise TypeError("参数必须是字符串类型")

        # 提取有效URL
        url = extract_valid_urls(url)

        if url is None:
            raise (
                APINotFoundError("输入的URL不合法。类名：{0}".format(cls.__name__))
            )
        try:
            # 重定向到完整链接
            transport = httpx.AsyncHTTPTransport(retries=5)
            async with httpx.AsyncClient(
                    transport=transport, proxies=TokenManager.proxies, timeout=10
            ) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                url = str(response.url)

                live_pattern = cls._DOUYIN_LIVE_URL_PATTERN
                live_pattern2 = cls._DOUYIN_LIVE_URL_PATTERN2
                live_pattern3 = cls._DOUYIN_LIVE_URL_PATTERN3

                if live_pattern.search(url):
                    match = live_pattern.search(url)
                elif live_pattern2.search(url):
                    match = live_pattern2.search(url)
                elif live_pattern3.search(url):
                    match = live_pattern3.search(url)
                    logger.warning("该链接返回的是room_id，请使用`fetch_user_live_videos_by_room_id`接口"

                                   )
                else:
                    raise APIResponseError("未在响应的地址中找到webcast_id，检查链接是否为直播页"
                                           )

                return match.group(1)

        except httpx.RequestError as exc:
            raise APIConnectionError("请求端点失败，请检查当前网络环境。 链接：{0}，代理：{1}，异常类名：{2}，异常详细信息：{3}"
                                     .format(url, TokenManager.proxies, cls.__name__, exc)
                                     )

        except httpx.HTTPStatusError as e:
            raise APIResponseError("链接：{0}，状态码 {1}：{2} ".format(
                e.response.url, e.response.status_code, e.response.text
            )
            )

    @classmethod
    async def get_all_webcast_id(cls, urls: list) -> list:

        if not isinstance(urls, list):
            raise TypeError("参数必须是列表类型")

        # 提取有效URL
        urls = extract_valid_urls(urls)

        if urls == []:
            raise (
                APINotFoundError("输入的URL List不合法。类名：{0}".format(cls.__name__)
                                 )
            )

        webcast_ids = [cls.get_webcast_id(url) for url in urls]
        return await asyncio.gather(*webcast_ids)


def format_file_name(
        naming_template: str,
        aweme_data: dict = {},
        custom_fields: dict = {},
) -> str:

    # 为不同系统设置不同的文件名长度限制
    os_limit = {
        "win32": 200,
        "cygwin": 60,
        "darwin": 60,
        "linux": 60,
    }

    fields = {
        "create": aweme_data.get("create_time", ""),  # 长度固定19
        "nickname": aweme_data.get("nickname", ""),  # 最长30
        "aweme_id": aweme_data.get("aweme_id", ""),  # 长度固定19
        "desc": split_filename(aweme_data.get("desc", ""), os_limit),
        "uid": aweme_data.get("uid", ""),  # 固定11
    }

    if custom_fields:
        # 更新自定义字段
        fields.update(custom_fields)

    try:
        return naming_template.format(**fields)
    except KeyError as e:
        raise KeyError("文件名模板字段 {0} 不存在，请检查".format(e))


def create_user_folder(kwargs: dict, nickname: Union[str, int]) -> Path:

    # 确定函数参数是否正确
    if not isinstance(kwargs, dict):
        raise TypeError("kwargs 参数必须是字典")

    # 创建基础路径
    base_path = Path(kwargs.get("path", "Download"))

    # 添加下载模式和用户名
    user_path = (
            base_path / "douyin" / kwargs.get("mode", "PLEASE_SETUP_MODE") / str(nickname)
    )

    # 获取绝对路径并确保它存在
    resolve_user_path = user_path.resolve()

    # 创建目录
    resolve_user_path.mkdir(parents=True, exist_ok=True)

    return resolve_user_path


def rename_user_folder(old_path: Path, new_nickname: str) -> Path:
    parent_directory = old_path.parent

    # 构建新目录路径 (Construct the new directory path)
    new_path = old_path.rename(parent_directory / new_nickname).resolve()

    return new_path


def create_or_rename_user_folder(
        kwargs: dict, local_user_data: dict, current_nickname: str
) -> Path:
    user_path = create_user_folder(kwargs, current_nickname)

    if not local_user_data:
        return user_path

    if local_user_data.get("nickname") != current_nickname:
        # 昵称不一致，触发目录更新操作
        user_path = rename_user_folder(user_path, current_nickname)

    return user_path


def show_qrcode(qrcode_url: str, show_image: bool = False) -> None:
    if show_image:
        # 创建并显示QR码图像
        qr_code_img = qrcode.make(qrcode_url)
        qr_code_img.show()
    else:
        # 在控制台以 ASCII 形式打印二维码
        qr = qrcode.QRCode()
        qr.add_data(qrcode_url)
        qr.make(fit=True)
        # 在控制台以 ASCII 形式打印二维码
        qr.print_ascii(invert=True)


def json_2_lrc(data: Union[str, list, dict]) -> str:
    try:
        lrc_lines = []
        for item in data:
            text = item["text"]
            time_seconds = float(item["timeId"])
            minutes = int(time_seconds // 60)
            seconds = int(time_seconds % 60)
            milliseconds = int((time_seconds % 1) * 1000)
            time_str = f"{minutes:02}:{seconds:02}.{milliseconds:03}"
            lrc_lines.append(f"[{time_str}] {text}")
    except KeyError as e:
        raise KeyError("歌词数据字段错误：{0}".format(e))
    except RuntimeError as e:
        raise RuntimeError("生成歌词文件失败：{0}，请检查歌词 `data` 内容".format(e))
    except TypeError as e:
        raise TypeError("歌词数据类型错误：{0}".format(e))
    return "\n".join(lrc_lines)

