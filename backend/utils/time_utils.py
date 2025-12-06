def is_recent_time(time_str):
    """判断时间字符串是否为当天发布"""
    from datetime import datetime, timedelta
    
    # 处理小时、分钟、秒的情况（当天发布）
    if '小时' in time_str or '分钟' in time_str or '秒' in time_str:
        return True
    
    # 处理"今天"的情况
    if '今天' in time_str:
        return True
    
    # 处理具体日期的情况
    if '-' in time_str:
        try:
            # 假设格式为 MM-DD
            today = datetime.now()
            if time_str == today.strftime('%m-%d'):
                return True
        except:
            pass
    
    return False


def is_today(date_str):
    """
    判断给定的日期字符串是否是当天
    
    参数:
    date_str: 日期字符串，格式如 "2025-05-30 09:00:22" 或 "2025-05-30"
    
    返回:
    bool: 如果是当天返回True，否则返回False
    """
    from datetime import datetime
    
    try:
        # 尝试解析不同的日期格式
        if len(date_str) > 10:  # 包含时间的格式
            given_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        else:  # 只有日期的格式
            given_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        # 获取当前日期
        today = datetime.now()
        
        # 比较年月日是否相同
        return (given_date.year == today.year and 
                given_date.month == today.month and 
                given_date.day == today.day)
    
    except ValueError:
        # 如果日期格式不正确，返回False
        return False