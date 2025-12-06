
#抖音热点采集Agent

from typing import Dict, Any
from .base_agent import BaseAgent
from app.services.douyin_service import DouyinService


class HotspotAgent(BaseAgent):
    """从抖音获取当天热点时评"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("HotspotAgent", config)
        self.douyin_service = DouyinService()
        
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        
        try:
            self.log_execution("start", "开始获取抖音热点")
            
            keywords = input_data.get('keywords', [])
            count = input_data.get('count', 10)
            category = input_data.get('category')
            
            # 获取热点列表
            hotspots = await self._fetch_hotspots(keywords, count, category)
            
            if not hotspots:
                return self.create_result(False, error="未获取到热点数据")
            
            # 选择最合适的热点
            selected_hotspot = self._select_best_hotspot(hotspots, input_data)
            
            self.log_execution("complete", f"成功获取{len(hotspots)}个热点")
            
            return self.create_result(True, {
                'hotspots': hotspots,
                'selected_hotspot': selected_hotspot,
                'total_count': len(hotspots)
            })
            
        except Exception as e:
            self.logger.error(f"获取热点失败: {str(e)}")
            return self.create_result(False, error=str(e))
    
    async def _fetch_hotspots(self, keywords: list, count: int, category: str) -> list:
        """获取热点数据"""
        try:
            # 使用爬虫API服务获取抖音热点
            self.logger.info(f"使用爬虫API获取抖音热点")
            
            # 构建爬虫API请求
            import requests
            from backend.crawler_config.crawler_config import crawler_config
            
            # 调用爬虫API的热点搜索接口
            hot_search_url = crawler_config.get_api_url("fetch_hot_search_result")
            response = requests.get(hot_search_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200 and data.get("data"):
                    hot_search_data = data["data"]
                    
                    # 提取热点列表
                    hot_items = hot_search_data.get("hot_items", [])
                    
                    # 将热点数据转换为统一格式
                    hotspots = []
                    for i, item in enumerate(hot_items[:count]):
                        # 构建热点数据
                        hotspot = {
                            'id': item.get("hot_word", f'hotspot_{i}'),
                            'title': item.get("hot_word", f'热点视频 {i+1}'),
                            'description': item.get("word_scheme", f'通过爬虫获取的热点 {i+1}'),
                            'view_count': item.get("hot_value", 0),
                            'comment_count': 0,  # 热点搜索结果中没有评论数
                            'share_count': 0,  # 热点搜索结果中没有分享数
                            'like_count': 0,  # 热点搜索结果中没有点赞数
                            'category': category or '热点',
                            'keywords': keywords or [item.get("hot_word", "热点")],
                            'url': f'https://www.douyin.com/search/{item.get("hot_word", "热点")}',
                            'cover_url': item.get("hot_img", ""),
                            'author': "抖音热点",
                            'created_at': self._get_current_time()
                        }
                        
                        hotspots.append(hotspot)
                    
                    if hotspots:
                        self.logger.info(f"爬虫API获取到 {len(hotspots)} 个热点")
                        return hotspots
            else:
                self.logger.warning(f"爬虫API请求失败: HTTP {response.status_code}")
        except Exception as e:
            self.logger.warning(f"爬虫API获取热点失败，使用模拟数据: {str(e)}")
        
        # 如果爬虫调用失败，返回模拟数据
        return self._generate_mock_hotspots(keywords, count, category)
    
    def _get_current_time(self):
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    async def _call_douyin_api(self, keywords: list, count: int, category: str) -> list:
        """
        调用抖音API获取热点
        需要的配置:
        API Key
        API Secret
        API Endpoint
        """
        import aiohttp
        import asyncio
        
        # API配置（需要填充）
        api_key = self.config.get('douyin_api_key', '')
        api_secret = self.config.get('douyin_api_secret', '')
        api_endpoint = self.config.get('douyin_api_endpoint', '')
        
        if not api_key or not api_endpoint:
            raise Exception("抖音API未配置")
        
        # 构建请求参数
        params = {
            'keywords': ','.join(keywords) if keywords else '',
            'count': count,
            'category': category or '',
            'api_key': api_key
        }
        
        # 发送请求，添加超时和重试机制
        max_retries = 3
        timeout = 10  # 超时时间10秒
        
        for retry in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        api_endpoint, 
                        params=params,
                        timeout=timeout
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return self._parse_douyin_response(data)
                        else:
                            if retry < max_retries - 1:
                                self.logger.warning(f"API返回错误: {response.status}，准备重试 ({retry + 1}/{max_retries})")
                                await asyncio.sleep(2 ** retry)  # 指数退避
                            else:
                                raise Exception(f"API返回错误: {response.status}")
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if retry < max_retries - 1:
                    self.logger.warning(f"API请求失败: {str(e)}，准备重试 ({retry + 1}/{max_retries})")
                    await asyncio.sleep(2 ** retry)  # 指数退避
                else:
                    raise Exception(f"API请求失败，已达到最大重试次数: {str(e)}")
        
        raise Exception("API请求失败，已达到最大重试次数")
    
    def _parse_douyin_response(self, data: dict) -> list:
        """解析抖音API响应"""
        hotspots = []
        
        # 根据实际API响应格式解析
        # TODO: 根据实际API响应调整解析逻辑
        items = data.get('data', {}).get('items', [])
        
        for item in items:
            hotspots.append({
                'id': item.get('id', ''),
                'title': item.get('title', ''),
                'description': item.get('desc', ''),
                'view_count': item.get('statistics', {}).get('play_count', 0),
                'comment_count': item.get('statistics', {}).get('comment_count', 0),
                'share_count': item.get('statistics', {}).get('share_count', 0),
                'like_count': item.get('statistics', {}).get('digg_count', 0),
                'category': item.get('category', ''),
                'keywords': item.get('keywords', []),
                'url': item.get('share_url', ''),
                'cover_url': item.get('cover', {}).get('url_list', [''])[0],
                'author': item.get('author', {}).get('nickname', ''),
                'created_at': item.get('create_time', '')
            })
        
        return hotspots
    
    def _generate_mock_hotspots(self, keywords: list, count: int, category: str) -> list:
        """模拟数据"""
        import random
        from datetime import datetime, timedelta
        
        mock_titles = [
            " "
        ]
        
        hotspots = []
        for i in range(count):
            base_views = random.randint(500000, 5000000)
            hotspots.append({
                'id': f'hotspot_{i}_{random.randint(1000, 9999)}',
                'title': mock_titles[i % len(mock_titles)],
                'description': f'这是关于{mock_titles[i % len(mock_titles)]}的详细描述。该话题引发了广泛关注和讨论。',
                'view_count': base_views,
                'comment_count': int(base_views * 0.05),
                'share_count': int(base_views * 0.01),
                'like_count': int(base_views * 0.1),
                'category': category or random.choice(['科技', '时事', '娱乐', '财经']),
                'keywords': keywords or ['热点', '话题'],
                'url': f'https://www.douyin.com/video/{random.randint(1000000000, 9999999999)}',
                'cover_url': f'https://example.com/cover_{i}.jpg',
                'author': f'用户{random.randint(1000, 9999)}',
                'created_at': (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat()
            })
        
        return hotspots
    
    def _select_best_hotspot(self, hotspots: list, criteria: Dict[str, Any]) -> Dict[str, Any]:
        #选择最佳热点
        if not hotspots:
            return None
        
        # 计算每个热点的综合得分
        for hotspot in hotspots:
            score = self._calculate_hotspot_score(hotspot, criteria)
            hotspot['score'] = score
        
        # 选择得分最高的
        best_hotspot = max(hotspots, key=lambda x: x.get('score', 0))
        self.logger.info(f"选中热点: {best_hotspot['title']} (得分: {best_hotspot['score']:.2f})")
        
        return best_hotspot
    
    def _calculate_hotspot_score(self, hotspot: Dict, criteria: Dict) -> float:
        """
        计算热点综合得分
        
        评分维度:
        浏览量 (40%)
        互动率 (30%) = (评论数 + 分享数 + 点赞数) / 浏览量
        时效性 (20%)
        关键词匹配度 (10%)
        """
        score = 0.0
        
        # 1. 浏览量得分 (归一化到0-40)
        view_count = hotspot.get('view_count', 0)
        view_score = min(40, (view_count / 1000000) * 10)  # 100万浏览 = 10分
        score += view_score
        
        # 2. 互动率得分 (0-30)
        if view_count > 0:
            comment_count = hotspot.get('comment_count', 0)
            share_count = hotspot.get('share_count', 0)
            like_count = hotspot.get('like_count', 0)
            
            engagement_rate = (comment_count + share_count + like_count) / view_count
            engagement_score = min(30, engagement_rate * 1000)  # 归一化
            score += engagement_score
        
        # 3. 时效性得分 (0-20)
        # 越新的热点得分越高
        try:
            from datetime import datetime
            created_at = hotspot.get('created_at', '')
            if created_at:
                created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                hours_ago = (datetime.now() - created_time).total_seconds() / 3600
                time_score = max(0, 20 - hours_ago)  # 24小时内线性递减
                score += time_score
        except:
            score += 10  # 默认中等时效性
        
        # 4. 关键词匹配度 (0-10)
        criteria_keywords = criteria.get('keywords', [])
        if criteria_keywords:
            hotspot_keywords = hotspot.get('keywords', [])
            hotspot_title = hotspot.get('title', '').lower()
            
            match_count = 0
            for keyword in criteria_keywords:
                if keyword.lower() in hotspot_title or keyword in hotspot_keywords:
                    match_count += 1
            
            keyword_score = (match_count / len(criteria_keywords)) * 10
            score += keyword_score
        else:
            score += 5  # 无关键词要求时给默认分
        
        return score
