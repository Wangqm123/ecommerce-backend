"""
算法2 - RFM 用户分群 配置
按实际环境修改数据库连接参数，或通过环境变量覆盖。
"""
import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_DATABASE", "ecommerce_analysis"),
    "charset": "utf8mb4",
}

# 轮询间隔（秒）
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))

# 单次最多处理任务数
MAX_BATCH_TASKS = int(os.getenv("MAX_BATCH_TASKS", "1"))

# RFM 评分方式: quantile（五分位） 或 fixed（固定阈值）
DEFAULT_SCORING_METHOD = os.getenv("SCORING_METHOD", "quantile")

# 固定阈值（仅在 scoring_method=fixed 时生效）
FIXED_THRESHOLDS = {
    "recency":    [30, 60, 90, 180],   # 天
    "frequency":  [20, 10, 5, 2],      # 次
    "monetary":   [50000, 20000, 10000, 5000],  # 元
}

# RFM 分层规则：高于阈值视为"高"（阈值=3，即分数1-5中≥3为高）
RFM_SEGMENT_THRESHOLD = 3

# 用户分层定义 (R高/R低, F高/F低, M高/M低)
SEGMENT_DEFINITIONS = {
    ("高", "高", "高"): "重要价值客户",
    ("高", "低", "高"): "重要发展客户",
    ("低", "高", "高"): "重要保持客户",
    ("低", "低", "高"): "重要挽留客户",
    ("高", "高", "低"): "一般价值客户",
    ("高", "低", "低"): "一般发展客户",
    ("低", "高", "低"): "一般保持客户",
    ("低", "低", "低"): "一般挽留客户",
}

# 购买力分层（基于 M 评分）
PURCHASING_POWER_MAP = {
    5: "高购买力",
    4: "中高购买力",
    3: "中购买力",
    2: "中低购买力",
    1: "低购买力",
}

# 日志级别
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
