import pandas as pd

class DataService:
    @staticmethod
    
    def __init__(self):
        """初始化DataService类"""
        pass

    def process_video_data(json_data):
        try:
            return {
                "video_info": {
                    "视频标题": json_data["data"]["desc"],
                    "视频描述": json_data["data"]["share_info"]["share_desc_info"],
                    "视频创建时间": (pd.Timestamp(json_data["data"]["create_time"], unit="s")+ pd.Timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S"),
                    "视频时长": json_data["data"]["duration"],
                    "视频ID": json_data["data"]["aweme_id"],
                    "视频唯一标识符": json_data["data"]["video"]["play_addr"]["url_list"][0]
                },
                "statistics": {
                    "视频播放量": json_data["data"]["statistics"]["play_count"],
                    "视频点赞数": json_data["data"]["statistics"]["digg_count"],
                    "视频评论数": json_data["data"]["statistics"]["comment_count"],
                    "视频分享数": json_data["data"]["statistics"]["share_count"],
                    "视频收藏数": json_data["data"]["statistics"]["collect_count"]
                },
                "author_info": {
                    "作者昵称": json_data["data"]["author"]["nickname"],
                    "作者唯一ID": json_data["data"]["author"]["unique_id"],
                    "作者ID": json_data["data"]["author"]["uid"],
                    "作者签名": json_data["data"]["author"]["signature"],
                    "作者粉丝数": json_data["data"]["author"]["follower_count"],
                    "作者关注数": json_data["data"]["author"]["following_count"],
                    "作者获得的点赞数": json_data["data"]["author"]["total_favorited"]
                }
            }
        except Exception as e:
            raise Exception(f"视频数据处理失败: {str(e)}")

    @staticmethod
    def save_to_excel(data, output_path="video_info.xlsx"):
        try:
            with pd.ExcelWriter(output_path) as writer:
                pd.DataFrame([data["video_info"]]).to_excel(writer, sheet_name='视频信息', index=False)
                pd.DataFrame([data["statistics"]]).to_excel(writer, sheet_name='统计数据', index=False)
                pd.DataFrame([data["author_info"]]).to_excel(writer, sheet_name='作者信息', index=False)
            return output_path
        except Exception as e:
            raise Exception(f"Excel文件保存失败: {str(e)}")

    @staticmethod
    def save_to_database(data):
        
        video_info = data["video_info"]
        statistics = data["statistics"]
        author_info = data["author_info"]
        
        params = (
            video_info.get("视频标题"),
            video_info.get("视频描述"),
            video_info.get("视频创建时间"),
            video_info.get("视频时长"),
            video_info.get("视频ID"),
            video_info.get("视频唯一标识符"),
            statistics.get("视频播放量"),
            statistics.get("视频点赞数"),
            statistics.get("视频评论数"),
            statistics.get("视频分享数"),
            statistics.get("视频收藏数"),
            author_info.get("作者昵称"),
            author_info.get("作者唯一ID"),
            author_info.get("作者ID"),
            author_info.get("作者签名"),
            author_info.get("作者粉丝数"),
            author_info.get("作者关注数"),
            author_info.get("作者获得的点赞数"),
            author_info.get("作者总作品数")
        )
        
        try:
            DBService.execute_update(insert_sql, params)
            return True
        except Exception as e:
            raise Exception(f"保存到数据库失败: {str(e)}")

    @staticmethod
    def create_video(data):
        """新增视频数据"""
        try:
            DBService.execute_update(insert_sql, DataService._prepare_params(data))
            return True
        except Exception as e:
            raise Exception(f"新增视频数据失败: {str(e)}")

    @staticmethod
    def get_video_by_id(video_id):
        """根据ID查询视频数据"""
        query_sql = "SELECT * FROM douyin_videos WHERE video_id = %s"
        try:
            result = DBService.execute_query(query_sql, (video_id,))
            return result[0] if result else None
        except Exception as e:
            raise Exception(f"查询视频数据失败: {str(e)}")

    @staticmethod
    def update_video(video_id, data):
        """更新视频数据"""
        try:
            params = DataService._prepare_params(data)
            params.append(video_id)
            DBService.execute_update(update_sql, params)
            return True
        except Exception as e:
            raise Exception(f"更新视频数据失败: {str(e)}")

    @staticmethod
    def delete_video(video_id):
        """删除视频数据"""
        delete_sql = "DELETE FROM douyin_videos WHERE video_id = %s"
        try:
            DBService.execute_update(delete_sql, (video_id,))
            return True
        except Exception as e:
            raise Exception(f"删除视频数据失败: {str(e)}")

    @staticmethod
    def _prepare_params(data):
        """准备SQL参数"""
        video_info = data["video_info"]
        statistics = data["statistics"]
        author_info = data["author_info"]
        
        return [
            video_info.get("视频标题"),
            video_info.get("视频描述"),
            video_info.get("视频创建时间"),
            video_info.get("视频时长"),
            video_info.get("视频ID"),
            video_info.get("视频唯一标识符"),
            statistics.get("视频播放量"),
            statistics.get("视频点赞数"),
            statistics.get("视频评论数"),
            statistics.get("视频分享数"),
            statistics.get("视频收藏数"),
            author_info.get("作者昵称"),
            author_info.get("作者唯一ID"),
            author_info.get("作者ID"),
            author_info.get("作者签名"),
            author_info.get("作者粉丝数"),
            author_info.get("作者关注数"),
            author_info.get("作者获得的点赞数"),
            author_info.get("作者总作品数")
        ]

    @staticmethod
    def create_author(data):
        """新增作者数据"""
        try:
            DBService.execute_update(insert_sql, DataService._prepare_author_params(data))
            return True
        except Exception as e:
            raise Exception(f"新增作者数据失败: {str(e)}")

    @staticmethod
    def get_author_by_uid(author_uid):
        """根据UID查询作者数据"""
        query_sql = "SELECT * FROM douyin_authors WHERE author_uid = %s"
        try:
            result = DBService.execute_query(query_sql, (author_uid,))
            return result[0] if result else None
        except Exception as e:
            raise Exception(f"查询作者数据失败: {str(e)}")

    @staticmethod
    def update_author(author_uid, data):
        """更新作者数据"""
        try:
            params = DataService._prepare_author_params(data)
            params.append(author_uid)
            DBService.execute_update(update_sql, params)
            return True
        except Exception as e:
            raise Exception(f"更新作者数据失败: {str(e)}")

    @staticmethod
    def delete_author(author_uid):
        """删除作者数据"""
        delete_sql = "DELETE FROM douyin_authors WHERE author_uid = %s"
        try:
            DBService.execute_update(delete_sql, (author_uid,))
            return True
        except Exception as e:
            raise Exception(f"删除作者数据失败: {str(e)}")

    @staticmethod
    def _prepare_author_params(data):
        """准备作者SQL参数"""
        return [
            data.get("author_uid"),
            data.get("author_nickname"),
            data.get("author_unique_id"),
            data.get("author_signature"),
            data.get("author_follower_count"),
            data.get("author_following_count"),
            data.get("author_total_favorited"),
            data.get("author_aweme_count")
        ]

    # 在DataService类中添加新方法
    @staticmethod
    def save_video_to_database(video_info):
        """保存视频信息到数据库"""
        from service.db_service import DBService
        
        try:
            # 使用现有的create_video方法
            DBService.create_video(video_info)
            return True
        except Exception as e:
            print(f"保存视频到数据库失败: {str(e)}")
            return False

    @staticmethod
    def get_all_authors():
        """获取所有作者列表"""
        try:
            from service.db_service import DBService
            
            
            result = DBService.execute_query(query_sql)
            
            # 转换为字典格式
            authors = []
            for row in result:
                authors.append({
                    'author_unique_id': row[0],
                    'author_nickname': row[1]
                })
            
            return authors
            
        except Exception as e:
            print(f"获取作者列表失败: {str(e)}")
            return []
