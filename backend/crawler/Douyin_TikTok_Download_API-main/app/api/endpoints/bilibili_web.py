from fastapi import APIRouter, Body, Query, Request, HTTPException  # 导入FastAPI组件
from app.api.models.APIResponseModel import ResponseModel, ErrorResponseModel  # 导入响应模型

from crawlers.bilibili.web.web_crawler import BilibiliWebCrawler  # 导入哔哩哔哩web爬虫


router = APIRouter()
BilibiliWebCrawler = BilibiliWebCrawler()


# 获取单个视频详情信息
@router.get("/fetch_one_video", response_model=ResponseModel, summary="获取单个视频详情信息/Get single video data")
async def fetch_one_video(request: Request,
                          bv_id: str = Query(example="BV1M1421t7hT", description="作品id/Video id")):
    try:
        data = await BilibiliWebCrawler.fetch_one_video(bv_id)
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


# 获取视频流地址
@router.get("/fetch_video_playurl", response_model=ResponseModel, summary="获取视频流地址/Get video playurl")
async def fetch_one_video(request: Request,
                          bv_id: str = Query(example="BV1y7411Q7Eq", description="作品id/Video id"),
                          cid:str = Query(example="171776208", description="作品cid/Video cid")):
    try:
        data = await BilibiliWebCrawler.fetch_video_playurl(bv_id, cid)
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


# 获取用户发布视频作品数据
@router.get("/fetch_user_post_videos", response_model=ResponseModel,
            summary="获取用户主页作品数据/Get user homepage video data")
async def fetch_user_post_videos(request: Request,
                                 uid: str = Query(example="178360345", description="用户UID"),
                                 pn: int = Query(default=1, description="页码/Page number"),):
    try:
        data = await BilibiliWebCrawler.fetch_user_post_videos(uid, pn)
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


# 获取用户所有收藏夹信息
@router.get("/fetch_collect_folders", response_model=ResponseModel,
            summary="获取用户所有收藏夹信息/Get user collection folders")
async def fetch_collect_folders(request: Request,
                                uid: str = Query(example="178360345", description="用户UID")):
    try:
        data = await BilibiliWebCrawler.fetch_collect_folders(uid)
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


# 获取指定收藏夹内视频数据
@router.get("/fetch_user_collection_videos", response_model=ResponseModel,
            summary="获取指定收藏夹内视频数据/Gets video data from a collection folder")
async def fetch_user_collection_videos(request: Request,
                                       folder_id: str = Query(example="1756059545",
                                                              description="收藏夹id/collection folder id"),
                                       pn: int = Query(default=1, description="页码/Page number")
                                       ):
    try:
        data = await BilibiliWebCrawler.fetch_folder_videos(folder_id, pn)
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


# 获取指定用户的信息
@router.get("/fetch_user_profile", response_model=ResponseModel,
            summary="获取指定用户的信息/Get information of specified user")
async def fetch_collect_folders(request: Request,
                                uid: str = Query(example="178360345", description="用户UID")):
    try:
        data = await BilibiliWebCrawler.fetch_user_profile(uid)
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


# 获取综合热门视频信息
@router.get("/fetch_com_popular", response_model=ResponseModel,
            summary="获取综合热门视频信息/Get comprehensive popular video information")
async def fetch_collect_folders(request: Request,
                                pn: int = Query(default=1, description="页码/Page number")):
    try:
        data = await BilibiliWebCrawler.fetch_com_popular(pn)
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


# 获取指定视频的评论
@router.get("/fetch_video_comments", response_model=ResponseModel,
            summary="获取指定视频的评论/Get comments on the specified video")
async def fetch_collect_folders(request: Request,
                                bv_id: str = Query(example="BV1M1421t7hT", description="作品id/Video id"),
                                pn: int = Query(default=1, description="页码/Page number")):
    try:
        data = await BilibiliWebCrawler.fetch_video_comments(bv_id, pn)
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


# 获取视频下指定评论的回复
@router.get("/fetch_comment_reply", response_model=ResponseModel,
            summary="获取视频下指定评论的回复/Get reply to the specified comment")
async def fetch_collect_folders(request: Request,
                                bv_id: str = Query(example="BV1M1421t7hT", description="作品id/Video id"),
                                pn: int = Query(default=1, description="页码/Page number"),
                                rpid: str = Query(example="237109455120", description="回复id/Reply id")):
    try:
        data = await BilibiliWebCrawler.fetch_comment_reply(bv_id, pn, rpid)
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


# 获取指定用户动态
@router.get("/fetch_user_dynamic", response_model=ResponseModel,
            summary="获取指定用户动态/Get dynamic information of specified user")
async def fetch_collect_folders(request: Request,
                                uid: str = Query(example="16015678", description="用户UID"),
                                offset: str = Query(default="", example="953154282154098691",
                                                    description="开始索引/offset")):
    try:
        data = await BilibiliWebCrawler.fetch_user_dynamic(uid, offset)
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


# 获取视频实时弹幕
@router.get("/fetch_video_danmaku", response_model=ResponseModel, summary="获取视频实时弹幕/Get Video Danmaku")
async def fetch_one_video(request: Request,
                          cid: str = Query(example="1639235405", description="作品cid/Video cid")):
    try:
        data = await BilibiliWebCrawler.fetch_video_danmaku(cid)
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


# 获取指定直播间信息
@router.get("/fetch_live_room_detail", response_model=ResponseModel,
            summary="获取指定直播间信息/Get information of specified live room")
async def fetch_collect_folders(request: Request,
                                room_id: str = Query(example="22816111", description="直播间ID/Live room ID")):
    try:
        data = await BilibiliWebCrawler.fetch_live_room_detail(room_id)
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


# 获取指定直播间视频流
@router.get("/fetch_live_videos", response_model=ResponseModel,
            summary="获取直播间视频流/Get live video data of specified room")
async def fetch_collect_folders(request: Request,
                                room_id: str = Query(example="1815229528", description="直播间ID/Live room ID")):
    try:
        data = await BilibiliWebCrawler.fetch_live_videos(room_id)
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


# 获取指定分区正在直播的主播
@router.get("/fetch_live_streamers", response_model=ResponseModel,
            summary="获取指定分区正在直播的主播/Get live streamers of specified live area")
async def fetch_collect_folders(request: Request,
                                area_id: str = Query(example="9", description="直播分区id/Live area ID"),
                                pn: int = Query(default=1, description="页码/Page number")):
    try:
        data = await BilibiliWebCrawler.fetch_live_streamers(area_id, pn)
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


# 获取所有直播分区列表
@router.get("/fetch_all_live_areas", response_model=ResponseModel,
            summary="获取所有直播分区列表/Get a list of all live areas")
async def fetch_collect_folders(request: Request,):
    try:
        data = await BilibiliWebCrawler.fetch_all_live_areas()
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


# 通过bv号获得视频aid号
@router.get("/bv_to_aid", response_model=ResponseModel, summary="通过bv号获得视频aid号/Generate aid by bvid")
async def fetch_one_video(request: Request,
                          bv_id: str = Query(example="BV1M1421t7hT", description="作品id/Video id")):
    try:
        data = await BilibiliWebCrawler.bv_to_aid(bv_id)
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


# 通过bv号获得视频分p信息
@router.get("/fetch_video_parts", response_model=ResponseModel, summary="通过bv号获得视频分p信息/Get Video Parts By bvid")
async def fetch_one_video(request: Request,
                          bv_id: str = Query(example="BV1vf421i7hV", description="作品id/Video id")):
    try:
        data = await BilibiliWebCrawler.fetch_video_parts(bv_id)
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

