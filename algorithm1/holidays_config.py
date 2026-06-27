# holidays_config.py
"""
节假日配置文件
定义中国电商重要促销日和法定节假日
"""

import pandas as pd
from datetime import datetime, timedelta


def get_chinese_holidays(year_start: int, year_end: int) -> pd.DataFrame:
    """
    获取指定年份范围内的中国节假日和电商大促日

    返回 DataFrame 包含两列：
    - ds: 日期
    - holiday: 节假日名称
    """
    holidays = []

    # 固定日期节假日
    fixed_holidays = [
        # (月, 日, 名称)
        (1, 1, "元旦"),
        (5, 1, "劳动节"),
        (10, 1, "国庆节"),
    ]

    # 电商大促日
    sales_events = [
        (6, 18, "618大促"),
        (11, 11, "双11"),
        (12, 12, "双12"),
    ]

    # 春节（农历，这里简化为1月底到2月中，实际使用时可以手动指定或导入）
    # 为了简化，我们只处理日期范围
    spring_festival_ranges = []
    for year in range(year_start, year_end + 1):
        # 春节一般在1月底或2月初，这里简化为2月1日前后的10天
        spring_start = datetime(year, 2, 1) - timedelta(days=7)
        spring_end = datetime(year, 2, 1) + timedelta(days=7)
        spring_festival_ranges.append((spring_start, spring_end, f"{year}年春节"))

    # 生成固定节假日
    for year in range(year_start, year_end + 1):
        for month, day, name in fixed_holidays:
            try:
                date = datetime(year, month, day)
                holidays.append({"ds": date, "holiday": name})
            except ValueError:
                pass

        for month, day, name in sales_events:
            try:
                date = datetime(year, month, day)
                holidays.append({"ds": date, "holiday": name})
                # 大促前后各加一天，效应持续
                holidays.append({"ds": date - timedelta(days=1), "holiday": f"{name}_前日"})
                holidays.append({"ds": date + timedelta(days=1), "holiday": f"{name}_后日"})
            except ValueError:
                pass

    # 生成春节日期范围
    for start_date, end_date, name in spring_festival_ranges:
        current = start_date
        while current <= end_date:
            holidays.append({"ds": current, "holiday": name})
            current += timedelta(days=1)

    # 周末标记（可选，Prophet 会自动处理周期性，这里不添加）

    df = pd.DataFrame(holidays)
    df['ds'] = pd.to_datetime(df['ds'])
    return df


def get_default_holidays(data_start_date: str, data_end_date: str) -> pd.DataFrame:
    """
    根据数据时间范围获取节假日
    参数格式: 'YYYY-MM-DD'
    """
    start_year = int(data_start_date[:4])
    end_year = int(data_end_date[:4])
    return get_chinese_holidays(start_year, end_year)