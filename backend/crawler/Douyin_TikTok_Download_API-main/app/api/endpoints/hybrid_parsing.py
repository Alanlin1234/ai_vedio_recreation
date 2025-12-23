import asyncio

from fastapi import APIRouter, Body, Query, Request, HTTPException  # 导入FastAPI组件

from app.api.models.APIResponseModel import ResponseModel, ErrorResponseModel  # 导入响应模型

# 爬虫/Crawler
from crawlers.hybrid.hybrid_crawler import HybridCrawler  # 导入混合爬虫

HybridCrawler = HybridCrawler()  # 实例化混合爬虫

router = APIRouter()


@router.get("/video_data", response_model=ResponseModel, tags=["Hybrid-API"],
            summary="混合解析单一视频接口/Hybrid parsing single video endpoint")
async def hybrid_parsing_single_video(request: Request,
                                      url: str = Query(example="https://v.douyin.com/L4FJNR3/"),
                                      minimal: bool = Query(default=False)):
    try:
        # 解析视频/Parse video
        data = await HybridCrawler.hybrid_parsing_single_video(url=url, minimal=minimal)
        # 返回数据/Return data
        return ResponseModel(code=200,
                             router=request.url.path,
                             data=data)
    except Exception as e:
        status_code = 400
        detail = ErrorResponseModel(code=status_code,
                                    router=request.url.path,
                                    params=dict(request.query_params),
                                    )
        raise HTTPException(status_code=status_code, detail=detail.dict())

# 更新Cookie
@router.post("/update_cookie",
             response_model=ResponseModel,
             summary="更新Cookie/Update Cookie")
async def update_cookie_api(request: Request,
                           service: str = Body(example="douyin", description="服务名称/Service name"),
                           cookie: str = Body(example="YOUR_NEW_COOKIE", description="新的Cookie值/New Cookie value")):
    try:
        if service == "douyin":
            from crawlers.douyin.web.web_crawler import DouyinWebCrawler
            douyin_crawler = DouyinWebCrawler()
            await douyin_crawler.update_cookie(cookie)
            return ResponseModel(code=200,
                                router=request.url.path,
                                data={"message": f"Cookie for {service} updated successfully"})
        elif service == "tiktok":
            # 这里可以添加TikTok的cookie更新逻辑
            # tiktok_crawler = TikTokWebCrawler()
            # await tiktok_crawler.update_cookie(cookie)
            return ResponseModel(code=200,
                                router=request.url.path,
                                data={"message": f"Cookie for {service} will be updated (not implemented yet)"})
        elif service == "bilibili":
            # 这里可以添加Bilibili的cookie更新逻辑
            # bilibili_crawler = BilibiliWebCrawler()
            # await bilibili_crawler.update_cookie(cookie)
            return ResponseModel(code=200,
                                router=request.url.path,
                                data={"message": f"Cookie for {service} will be updated (not implemented yet)"})
        else:
            raise ValueError(f"Service '{service}' is not supported. Supported services: douyin, tiktok, bilibili")
    except Exception as e:
        status_code = 400
        detail = ErrorResponseModel(code=status_code,
                                    router=request.url.path,
                                    params=dict(request.query_params),
                                    )
        raise HTTPException(status_code=status_code, detail=detail.dict())
