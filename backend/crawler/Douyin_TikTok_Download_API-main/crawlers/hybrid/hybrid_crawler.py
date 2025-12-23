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
#

import asyncio
import re
import httpx

from crawlers.douyin.web.web_crawler import DouyinWebCrawler  # 导入抖音Web爬虫
from crawlers.tiktok.web.web_crawler import TikTokWebCrawler  # 导入TikTok Web爬虫
from crawlers.tiktok.app.app_crawler import TikTokAPPCrawler  # 导入TikTok App爬虫
from crawlers.bilibili.web.web_crawler import BilibiliWebCrawler  # 导入Bilibili Web爬虫
from crawlers.utils.logger import logger  # 导入日志记录器


class HybridCrawler:
    def __init__(self):
        self.DouyinWebCrawler = DouyinWebCrawler()
        self.TikTokWebCrawler = TikTokWebCrawler()
        self.TikTokAPPCrawler = TikTokAPPCrawler()
        self.BilibiliWebCrawler = BilibiliWebCrawler()

    async def get_bilibili_bv_id(self, url: str) -> str:
        # 如果是 b23.tv 短链，需要重定向获取真实URL
        if "b23.tv" in url:
            async with httpx.AsyncClient() as client:
                response = await client.head(url, follow_redirects=True)
                url = str(response.url)
        
        # 从URL中提取BV号
        bv_pattern = r'(?:video\/|\/)(BV[A-Za-z0-9]+)'
        match = re.search(bv_pattern, url)
        if match:
            return match.group(1)
        else:
            raise ValueError(f"Cannot extract BV ID from URL: {url}")

    async def hybrid_parsing_single_video(self, url: str, minimal: bool = False):
        # 解析抖音视频/Parse Douyin video
        if "douyin" in url:
            platform = "douyin"
            logger.info(f"开始处理抖音视频: {url}")
            aweme_id = await self.DouyinWebCrawler.get_aweme_id(url)
            logger.info(f"获取到抖音视频ID: {aweme_id}")
            data = await self.DouyinWebCrawler.fetch_one_video(aweme_id)
            logger.debug(f"抖音API原始响应: {data}")
            
            # 检查API响应是否包含错误信息
            if isinstance(data, dict):
                # 检查filter_detail中的错误信息
                if data.get("filter_detail"):
                    filter_detail = data.get("filter_detail")
                    error_msg = filter_detail.get("detail_msg", "未知错误")
                    logger.error(f"抖音API返回错误信息: {error_msg}")
                    logger.error(f"错误详情: {filter_detail}")
                    raise ValueError(f"抖音API返回错误: {error_msg}")
                
                # 获取视频详情
                data = data.get("aweme_detail")
                if not data:
                    logger.error(f"未能获取到视频详情，API响应中aweme_detail字段为空")
                    raise ValueError("未能获取到视频详情")
            # $.aweme_detail.aweme_type
            aweme_type = data.get("aweme_type")
            logger.info(f"抖音视频类型: {aweme_type}")
        # 解析TikTok视频/Parse TikTok video
        elif "tiktok" in url:
            platform = "tiktok"
            aweme_id = await self.TikTokWebCrawler.get_aweme_id(url)

            # data = data.get("itemInfo").get("itemStruct")

            data = await self.TikTokAPPCrawler.fetch_one_video(aweme_id)
            # $.imagePost exists if aweme_type is photo
            aweme_type = data.get("aweme_type")
        # 解析Bilibili视频/Parse Bilibili video
        elif "bilibili" in url or "b23.tv" in url:
            platform = "bilibili"
            aweme_id = await self.get_bilibili_bv_id(url)  # BV号作为统一的video_id
            response = await self.BilibiliWebCrawler.fetch_one_video(aweme_id)
            data = response.get('data', {})  # 提取data部分
            # Bilibili只有视频类型，aweme_type设为0(video)
            aweme_type = 0
        else:
            raise ValueError("hybrid_parsing_single_video: Cannot judge the video source from the URL.")

        # 检查是否需要返回最小数据/Check if minimal data is required
        if not minimal:
            return data

        url_type_code_dict = {
            # common
            0: 'video',
            # Douyin
            2: 'image',
            4: 'video',
            68: 'image',
            # TikTok
            51: 'video',
            55: 'video',
            58: 'video',
            61: 'video',
            150: 'image'
        }
        # 判断链接类型/Judge link type
        url_type = url_type_code_dict.get(aweme_type, 'video')
        # print(f"url_type: {url_type}")


        # 根据平台适配字段映射
        if platform == 'bilibili':
            result_data = {
                'type': url_type,
                'platform': platform,
                'video_id': aweme_id,
                'desc': data.get("title"),  # Bilibili使用title
                'create_time': data.get("pubdate"),  # Bilibili使用pubdate
                'author': data.get("owner"),  # Bilibili使用owner
                'music': None,  # Bilibili没有音乐信息
                'statistics': data.get("stat"),  # Bilibili使用stat
                'cover_data': {},  # 将在各平台处理中填充
                'hashtags': None,  # Bilibili没有hashtags概念
            }
        else:
            result_data = {
                'type': url_type,
                'platform': platform,
                'video_id': aweme_id,
                'desc': data.get("desc"),
                'create_time': data.get("create_time"),
                'author': data.get("author"),
                'music': data.get("music"),
                'statistics': data.get("statistics"),
                'cover_data': {},  # 将在各平台处理中填充
                'hashtags': data.get('text_extra'),
            }
        api_data = None
        # 判断链接类型并处理数据/Judge link type and process data
        # 抖音数据处理/Douyin data processing
        if platform == 'douyin':
            # 填充封面数据
            result_data['cover_data'] = {
                'cover': data.get("video", {}).get("cover"),
                'origin_cover': data.get("video", {}).get("origin_cover"),
                'dynamic_cover': data.get("video", {}).get("dynamic_cover")
            }
            # 抖音视频数据处理/Douyin video data processing
            if url_type == 'video':
                logger.info("开始处理抖音视频URL生成")
                # 安全获取视频相关字段，避免KeyError
                video = data.get('video', {})
                play_addr = video.get('play_addr', {})
                uri = play_addr.get('uri', '')
                url_list = play_addr.get('url_list', [])
                
                logger.debug(f"视频基础信息: uri={uri}, url_list长度={len(url_list)}")
                logger.debug(f"视频完整数据: {video}")
                
                # 多种URL生成策略
                wm_video_url_HQ = url_list[0] if url_list else ''
                wm_video_url = ''
                nwm_video_url_HQ = ''
                nwm_video_url = ''
                
                # 策略1：使用API返回的完整URL
                if wm_video_url_HQ:
                    logger.info(f"使用策略1生成URL，API返回的高清URL: {wm_video_url_HQ}")
                    # 注意：直接替换playwm为play可能不再适用于新的URL格式
                    # 新的URL格式已经不包含playwm/play关键字，而是通过其他参数控制水印
                    nwm_video_url_HQ = wm_video_url_HQ
                    # 添加额外的参数来获取无水印视频
                    if '?' in nwm_video_url_HQ:
                        nwm_video_url_HQ += '&is_play_url=1&source=PackSourceEnum_AWEME_DETAIL'
                    else:
                        nwm_video_url_HQ += '?is_play_url=1&source=PackSourceEnum_AWEME_DETAIL'
                    logger.info(f"生成的无水印高清URL: {nwm_video_url_HQ}")
                
                # 策略2：如果API返回的URL无效或缺失，使用拼接URL
                if uri:
                    logger.info(f"使用策略2生成URL，视频URI: {uri}")
                    wm_video_url = f"https://aweme.snssdk.com/aweme/v1/playwm/?video_id={uri}&radio=1080p&line=0"
                    nwm_video_url = f"https://aweme.snssdk.com/aweme/v1/play/?video_id={uri}&ratio=1080p&line=0"
                    logger.info(f"拼接的有水印URL: {wm_video_url}")
                    logger.info(f"拼接的无水印URL: {nwm_video_url}")
                    # 如果策略1失败，使用策略2的高清URL
                    if not wm_video_url_HQ:
                        logger.info("策略1失败，使用策略2的高清URL作为备选")
                        wm_video_url_HQ = wm_video_url
                        nwm_video_url_HQ = nwm_video_url
                
                # 策略3：尝试使用其他可能的URL格式
                if not wm_video_url and video.get('download_addr'):
                    logger.info("使用策略3生成URL，尝试从download_addr获取")
                    download_url_list = video.get('download_addr', {}).get('url_list', [])
                    if download_url_list:
                        logger.info(f"从download_addr获取到URL: {download_url_list[0]}")
                        wm_video_url = download_url_list[0]
                        wm_video_url_HQ = download_url_list[0]
                        # 注意：直接替换playwm为play可能不再适用于新的URL格式
                        nwm_video_url = wm_video_url
                        nwm_video_url_HQ = wm_video_url_HQ
                        # 添加额外的参数来获取无水印视频
                        if '?' in nwm_video_url:
                            nwm_video_url += '&is_play_url=1&source=PackSourceEnum_AWEME_DETAIL'
                        else:
                            nwm_video_url += '?is_play_url=1&source=PackSourceEnum_AWEME_DETAIL'
                        if '?' in nwm_video_url_HQ:
                            nwm_video_url_HQ += '&is_play_url=1&source=PackSourceEnum_AWEME_DETAIL'
                        else:
                            nwm_video_url_HQ += '?is_play_url=1&source=PackSourceEnum_AWEME_DETAIL'
                        logger.info(f"生成的有水印URL: {wm_video_url}")
                        logger.info(f"生成的无水印URL: {nwm_video_url}")
                
                # 验证生成的URL
                if not wm_video_url and not nwm_video_url:
                    logger.error("所有URL生成策略均失败，未能获取到有效视频URL")
                    logger.error(f"视频数据: {video}")
                else:
                    logger.info("视频URL生成成功")
                    logger.info(f"最终有水印高清URL: {wm_video_url_HQ}")
                    logger.info(f"最终无水印高清URL: {nwm_video_url_HQ}")
                
                api_data = {
                    'video_data':
                        {
                            'wm_video_url': wm_video_url,
                            'wm_video_url_HQ': wm_video_url_HQ,
                            'nwm_video_url': nwm_video_url,
                            'nwm_video_url_HQ': nwm_video_url_HQ,
                            'uri': uri,
                            'url_list_count': len(url_list)
                        }
                }
            # 抖音图片数据处理/Douyin image data processing
            elif url_type == 'image':
                # 无水印图片列表/No watermark image list
                no_watermark_image_list = []
                # 有水印图片列表/With watermark image list
                watermark_image_list = []
                
                # 安全获取图片列表，避免KeyError
                images = data.get('images', [])
                
                # 遍历图片列表/Traverse image list
                for i in images:
                    # 安全获取图片URL，避免KeyError
                    url_list = i.get('url_list', [])
                    download_url_list = i.get('download_url_list', [])
                    
                    if url_list:
                        no_watermark_image_list.append(url_list[0])
                    if download_url_list:
                        watermark_image_list.append(download_url_list[0])
                
                api_data = {
                    'image_data':
                        {
                            'no_watermark_image_list': no_watermark_image_list,
                            'watermark_image_list': watermark_image_list,
                            'image_count': len(images)
                        }
                }
        # TikTok数据处理/TikTok data processing
        elif platform == 'tiktok':
            # 填充封面数据
            result_data['cover_data'] = {
                'cover': data.get("video", {}).get("cover"),
                'origin_cover': data.get("video", {}).get("origin_cover"),
                'dynamic_cover': data.get("video", {}).get("dynamic_cover")
            }
            # TikTok视频数据处理/TikTok video data processing
            if url_type == 'video':
                # 将信息储存在字典中/Store information in a dictionary
                # wm_video = data['video']['downloadAddr']
                wm_video = (
                    data.get('video', {})
                    .get('download_addr', {})
                    .get('url_list', [None])[0]
                )

                api_data = {
                    'video_data':
                        {
                            'wm_video_url': wm_video,
                            'wm_video_url_HQ': wm_video,
                            # 'nwm_video_url': data['video']['playAddr'],
                            'nwm_video_url': data['video']['play_addr']['url_list'][0],
                            'nwm_video_url_HQ': data['video']['bit_rate'][0]['play_addr']['url_list'][0]
                        }
                }
            # TikTok图片数据处理/TikTok image data processing
            elif url_type == 'image':
                # 无水印图片列表/No watermark image list
                no_watermark_image_list = []
                # 有水印图片列表/With watermark image list
                watermark_image_list = []
                for i in data['image_post_info']['images']:
                    no_watermark_image_list.append(i['display_image']['url_list'][0])
                    watermark_image_list.append(i['owner_watermark_image']['url_list'][0])
                api_data = {
                    'image_data':
                        {
                            'no_watermark_image_list': no_watermark_image_list,
                            'watermark_image_list': watermark_image_list
                        }
                }
        # Bilibili数据处理/Bilibili data processing
        elif platform == 'bilibili':
            # 填充封面数据
            result_data['cover_data'] = {
                'cover': data.get("pic"),  # Bilibili使用pic作为封面
                'origin_cover': data.get("pic"),
                'dynamic_cover': data.get("pic")
            }
            # Bilibili只有视频，直接处理视频数据
            if url_type == 'video':
                # 获取视频播放地址需要额外调用API
                cid = data.get('cid')  # 获取cid
                if cid:
                    # 获取播放链接，cid需要转换为字符串
                    playurl_data = await self.BilibiliWebCrawler.fetch_video_playurl(aweme_id, str(cid))
                    # 从播放数据中提取URL
                    dash = playurl_data.get('data', {}).get('dash', {})
                    video_list = dash.get('video', [])
                    audio_list = dash.get('audio', [])
                    
                    # 选择最高质量的视频流
                    video_url = video_list[0].get('baseUrl') if video_list else None
                    audio_url = audio_list[0].get('baseUrl') if audio_list else None
                    
                    api_data = {
                        'video_data': {
                            'wm_video_url': video_url,
                            'wm_video_url_HQ': video_url,
                            'nwm_video_url': video_url,  # Bilibili没有水印概念
                            'nwm_video_url_HQ': video_url,
                            'audio_url': audio_url,  # Bilibili音视频分离
                            'cid': cid,  # 保存cid供后续使用
                        }
                    }
                else:
                    api_data = {
                        'video_data': {
                            'wm_video_url': None,
                            'wm_video_url_HQ': None,
                            'nwm_video_url': None,
                            'nwm_video_url_HQ': None,
                            'error': 'Failed to get cid for video playback'
                        }
                    }
        # 更新数据/Update data
        result_data.update(api_data)
        return result_data

    async def main(self):
        # url = "https://v.douyin.com/L4FJNR3/"
        url = "https://www.tiktok.com/@flukegk83/video/7360734489271700753"
        minimal = True
        result = await self.hybrid_parsing_single_video(url, minimal=minimal)
        print(result)

        # 占位
        pass


if __name__ == '__main__':
    # 实例化混合爬虫/Instantiate hybrid crawler
    hybird_crawler = HybridCrawler()
    # 运行测试代码/Run test code
    asyncio.run(hybird_crawler.main())

