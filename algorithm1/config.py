import os
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录下的 .env.example 文件
env_path = Path(__file__).parent / ".env.example"
load_dotenv(dotenv_path=env_path)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "ecommerce_analysis"),
    "charset": "utf8mb4"
}

# 运行模式：'mock' 使用模拟数据（不需要数据库），'real' 使用真实数据库
# 可通过环境变量 FORECAST_MODE 设置，默认为 'real'
MODE = os.getenv("FORECAST_MODE", "real").lower()