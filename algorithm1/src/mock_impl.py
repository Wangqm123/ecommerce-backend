import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from config import MODE


class MockTaskFetcher:
    """模拟任务获取器"""

    def __init__(self):
        self.tasks = []
        self.next_batch = 1
        # 预先创建一个测试任务
        self._add_test_task()

    def _add_test_task(self):
        task = {
            "batch_uuid": f"mock-batch-{self.next_batch:03d}",
            "params": json.dumps({
                "startDate": "2024-01-01",
                "endDate": "2025-12-31",
                "forecastDays": 30,
                "targetProductIds": [],  # 空表示预测所有商品
                "model": "prophet"
            }),
            "status": "pending"
        }
        self.tasks.append(task)
        self.next_batch += 1

    def fetch_pending_task(self) -> Optional[Dict[str, Any]]:
        for task in self.tasks:
            if task["status"] == "pending":
                task["status"] = "processing"
                return task
        # 没有 pending 任务时，可选自动添加新任务用于持续测试（注释掉）
        # self._add_test_task()
        # return self.fetch_pending_task()
        return None

    def update_task_status(self, batch_uuid: str, status: str, error_msg: str = None):
        for task in self.tasks:
            if task["batch_uuid"] == batch_uuid:
                task["status"] = status
                print(f"[Mock] Task {batch_uuid} -> {status}")
                if error_msg:
                    print(f"[Mock] Error: {error_msg}")
                return


class MockTrainingDataProvider:
    """生成模拟销量数据"""

    def __init__(self):
        # 生成三个商品，2024-01-01 到 2025-12-31 的日销量数据（带周期和噪声）
        dates = pd.date_range("2024-01-01", "2025-12-31")  # 这是 datetime 类型
        self.products = [
            (1, "iPhone 15 Pro"),
            (2, "AirPods Pro"),
            (3, "MacBook Pro")
        ]
        data = []
        np.random.seed(42)
        for pid, pname in self.products:
            for dt in dates:
                # 模拟季节性：夏季高，冬季低 + 趋势增长
                month = dt.month
                trend = 1 + 0.0003 * (dt - dates[0]).days  # 轻微增长
                seasonal = 20 * np.sin(2 * np.pi * (month - 1) / 12)  # 年周期
                base = 50 + seasonal
                noise = np.random.normal(0, 10)
                qty = max(0, int((base + noise) * trend))
                data.append([pid, pname, dt, qty])  # 直接使用 Timestamp
        self.df = pd.DataFrame(data, columns=["product_id", "product_name", "order_date", "daily_quantity"])

    def get_training_data(self, start_date: str, end_date: str, product_ids: List[int] = None) -> pd.DataFrame:
        # 将字符串转换为 datetime，以便与 df 中的 order_date 比较
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        df = self.df[(self.df["order_date"] >= start) & (self.df["order_date"] <= end)]
        if product_ids:
            df = df[df["product_id"].isin(product_ids)]
        return df


class MockResultWriter:
    """模拟结果写入：保存到 CSV 文件"""

    def write_forecast_results(self, batch_uuid: str, product_id: int, product_name: str,
                               forecasts_df: pd.DataFrame, model_name: str):
        filename = f"forecast_{batch_uuid}_{product_id}.csv"
        forecasts_df.to_csv(filename, index=False)
        print(f"[Mock] Saved forecasts for {product_name} to {filename}")