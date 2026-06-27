# -*- coding: utf-8 -*-
"""
配置文件 - 数据库连接和算法参数配置
支持从 .env 文件读取配置
"""

import os
import sys
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# MySQL 数据库配置（优先从 .env 读取）
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_DATABASE', os.getenv('DB_NAME', 'ecommerce_analysis')),  # 优先DB_DATABASE
    'charset': 'utf8mb4'
}

# 算法默认参数
ALGORITHM_CONFIG = {
    # 关联规则算法参数
    'min_support': 0.01,        # 最小支持度
    'min_confidence': 0.3,       # 最小置信度
    'min_lift': 1.0,            # 最小提升度
    'max_length': 3,             # 规则最大长度（前件+后件）
    
    # 任务轮询配置（从 .env 读取）
    'poll_interval': int(os.getenv('WORKER_SLEEP_INTERVAL', os.getenv('POLL_INTERVAL', 5))),  # 兼容两种变量名
    'max_batch_size': 1000,     # 批量插入数据库的批次大小
    
    # 日志配置
    'log_level': 'INFO',
    'log_file': 'logs/association_algorithm.log'
}


def validate_config() -> bool:
    """
    验证配置是否有效
    
    Returns:
        True if valid, False otherwise
    """
    errors = []
    
    # 验证数据库配置
    if not DB_CONFIG['host']:
        errors.append("数据库主机地址(DB_HOST)不能为空")
    if not DB_CONFIG['user']:
        errors.append("数据库用户名(DB_USER)不能为空")
    if not DB_CONFIG['database']:
        errors.append("数据库名称(DB_NAME/DB_DATABASE)不能为空")
    if DB_CONFIG['port'] < 1 or DB_CONFIG['port'] > 65535:
        errors.append(f"数据库端口(DB_PORT)必须在1-65535范围内，当前值: {DB_CONFIG['port']}")
    
    # 验证算法参数
    if ALGORITHM_CONFIG['min_support'] <= 0 or ALGORITHM_CONFIG['min_support'] >= 1:
        errors.append(f"最小支持度(min_support)必须在0-1之间，当前值: {ALGORITHM_CONFIG['min_support']}")
    if ALGORITHM_CONFIG['min_confidence'] <= 0 or ALGORITHM_CONFIG['min_confidence'] > 1:
        errors.append(f"最小置信度(min_confidence)必须在0-1之间，当前值: {ALGORITHM_CONFIG['min_confidence']}")
    if ALGORITHM_CONFIG['min_lift'] <= 0:
        errors.append(f"最小提升度(min_lift)必须大于0，当前值: {ALGORITHM_CONFIG['min_lift']}")
    if ALGORITHM_CONFIG['max_length'] < 2:
        errors.append(f"规则最大长度(max_length)必须大于等于2，当前值: {ALGORITHM_CONFIG['max_length']}")
    
    if errors:
        print("配置验证失败:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


def print_config():
    """打印当前配置信息"""
    print("=" * 60)
    print("当前配置信息")
    print("=" * 60)
    print("\n【数据库配置】")
    print(f"  主机: {DB_CONFIG['host']}")
    print(f"  端口: {DB_CONFIG['port']}")
    print(f"  数据库: {DB_CONFIG['database']}")
    print(f"  用户: {DB_CONFIG['user']}")
    print(f"  密码: {'*' * len(DB_CONFIG['password']) if DB_CONFIG['password'] else '(空)'}")
    
    print("\n【算法配置】")
    print(f"  最小支持度: {ALGORITHM_CONFIG['min_support']}")
    print(f"  最小置信度: {ALGORITHM_CONFIG['min_confidence']}")
    print(f"  最小提升度: {ALGORITHM_CONFIG['min_lift']}")
    print(f"  规则最大长度: {ALGORITHM_CONFIG['max_length']}")
    print(f"  轮询间隔: {ALGORITHM_CONFIG['poll_interval']} 秒")
    print(f"  批量插入大小: {ALGORITHM_CONFIG['max_batch_size']}")
    
    print("\n【日志配置】")
    print(f"  日志级别: {ALGORITHM_CONFIG['log_level']}")
    print(f"  日志文件: {ALGORITHM_CONFIG['log_file']}")
    print("=" * 60)


# 为兼容性提供类接口（若其他代码使用Config类）
class Config:
    DB_HOST = DB_CONFIG['host']
    DB_PORT = DB_CONFIG['port']
    DB_USER = DB_CONFIG['user']
    DB_PASSWORD = DB_CONFIG['password']
    DB_NAME = DB_CONFIG['database']
    WORKER_SLEEP_INTERVAL = ALGORITHM_CONFIG['poll_interval']
    
    @classmethod
    def get_db_uri(cls):
        return f"mysql+pymysql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"