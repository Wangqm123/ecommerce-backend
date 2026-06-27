# -*- coding: utf-8 -*-
"""
数据导入和算法运行脚本
提供完整的命令行接口
"""

import os
import sys
import argparse
import logging
import json
import threading
import time
from typing import Dict, List, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.csv_importer import parse_csv_file, import_to_database
from src.main import run_service, run_once
from src.config import DB_CONFIG
from src.database import DatabaseManager

# Flask 相关
try:
    from flask import Flask, jsonify, request
except ImportError:
    Flask = None
    jsonify = None
    request = None


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
logger = logging.getLogger("association_server")


def cmd_import(args):
    """导入CSV数据"""
    from src.csv_importer import parse_csv_file, preprocess_data, import_to_database
    
    print(f"开始导入CSV文件: {args.file}")
    try:
        raw_data = parse_csv_file(args.file)
        if not raw_data:
            print("CSV文件中没有有效数据")
            return
        cleaned_data, report = preprocess_data(raw_data)
        if not cleaned_data:
            print("预处理后没有有效数据")
            return
        success_count = import_to_database(cleaned_data, args.batch_size)
        print(f"导入完成，成功插入 {success_count} 条记录")
    except Exception as e:
        print(f"导入失败: {e}")
        sys.exit(1)


def cmd_generate(args):
    """生成示例数据"""
    from generate_sample_data import generate_sample_csv
    generate_sample_csv(args.output, args.count)
    print(f"示例CSV文件已生成: {args.output}")


def cmd_service(args):
    """启动算法服务（纯轮询，无HTTP）"""
    print(f"启动关联规则算法服务，轮询间隔: {args.interval} 秒")
    print("按 Ctrl+C 停止服务")
    run_service(poll_interval=args.interval)


def cmd_runonce(args):
    """单次运行分析"""
    params = {
        'startDate': args.start_date,
        'endDate': args.end_date,
        'minSupport': args.min_support,
        'minConfidence': args.min_confidence,
        'minLift': args.min_lift,
        'algorithm': args.algorithm
    }
    print(f"单次运行关联规则分析")
    print(f"参数: {params}")
    run_once(params)


def cmd_checkdb(args):
    """检查数据库连接"""
    print("检查数据库连接...")
    print(f"数据库配置:")
    print(f"  主机: {DB_CONFIG['host']}")
    print(f"  端口: {DB_CONFIG['port']}")
    print(f"  数据库: {DB_CONFIG['database']}")
    print(f"  用户: {DB_CONFIG['user']}")
    
    try:
        db = DatabaseManager(DB_CONFIG)
        db.connect()
        with db.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM orders")
            result = cursor.fetchone()
            print(f"✓ orders 表记录数: {result['count']}")
            cursor.execute("SELECT COUNT(*) as count FROM products")
            result = cursor.fetchone()
            print(f"✓ products 表记录数: {result['count']}")
            cursor.execute("SELECT COUNT(*) as count FROM users")
            result = cursor.fetchone()
            print(f"✓ users 表记录数: {result['count']}")
            cursor.execute("SELECT COUNT(*) as count FROM association_tasks")
            result = cursor.fetchone()
            print(f"✓ association_tasks 表记录数: {result['count']}")
            cursor.execute("SELECT COUNT(*) as count FROM association_rules")
            result = cursor.fetchone()
            print(f"✓ association_rules 表记录数: {result['count']}")
        db.close()
        print("\n✓ 数据库连接成功！")
    except Exception as e:
        print(f"\n✗ 数据库连接失败: {e}")
        print("\n请检查:")
        print("  1. MySQL 服务是否启动")
        print("  2. 数据库配置是否正确 (.env 文件)")
        print("  3. 数据库表是否已创建 (src/sql/schema.sql)")
        sys.exit(1)


# ===================================================================
# HTTP 服务模式（用于 Railway 部署）
# ===================================================================

def _poll_loop(stop_event: threading.Event, interval: int = 10):
    """后台轮询线程"""
    logger.info("后台轮询线程启动，间隔=%ds", interval)
    while not stop_event.is_set():
        try:
            # 调用原有的 run_once 处理一个 pending 任务
            # 但 run_once 会自己连接数据库，我们直接调用
            from src.main import run_once as _run_once
            # 从数据库获取一个 pending 任务
            db = DatabaseManager(DB_CONFIG)
            db.connect()
            with db.get_cursor() as cursor:
                cursor.execute(
                    "SELECT batch_uuid FROM association_tasks "
                    "WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1"
                )
                task = cursor.fetchone()
            db.close()
            if task:
                logger.info("发现 pending 任务 %s，开始处理", task['batch_uuid'])
                # 调用原有的 run_once 传入参数（但原 run_once 需要 params，我们直接构造）
                # 更可靠：直接用 src/main 中的 execute_task
                from src.main import execute_task
                db = DatabaseManager(DB_CONFIG)
                db.connect()
                with db.get_cursor() as cursor:
                    cursor.execute(
                        "SELECT * FROM association_tasks WHERE batch_uuid = %s",
                        (task['batch_uuid'],)
                    )
                    full_task = cursor.fetchone()
                if full_task:
                    execute_task(db.connection, full_task)
                db.close()
            else:
                logger.debug("暂无 pending 任务")
        except Exception as e:
            logger.error("轮询异常: %s", e)
        stop_event.wait(interval)


def run_http_server(port: int = None):
    """启动 HTTP 服务 + 后台轮询"""
    if port is None:
        port = int(os.getenv("PORT", 5000))
    
    if Flask is None:
        print("错误: Flask 未安装，请安装: pip install flask")
        sys.exit(1)
    
    app = Flask(__name__)
    stop_event = threading.Event()
    
    # 启动后台轮询
    poller = threading.Thread(
        target=_poll_loop,
        args=(stop_event, int(os.getenv("POLL_INTERVAL", "10"))),
        daemon=True
    )
    poller.start()
    logger.info("HTTP 服务启动，端口=%d，后台轮询已就绪", port)
    
    @app.route("/api/association/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})
    
    @app.route("/api/association/process-pending", methods=["POST"])
    def process_pending():
        """立即处理一个 pending 任务"""
        try:
            db = DatabaseManager(DB_CONFIG)
            db.connect()
            with db.get_cursor() as cursor:
                cursor.execute(
                    "SELECT batch_uuid FROM association_tasks "
                    "WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1"
                )
                task = cursor.fetchone()
            if not task:
                db.close()
                return jsonify({"code": 200, "processed": 0})
            # 执行任务
            from src.main import execute_task
            with db.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM association_tasks WHERE batch_uuid = %s",
                    (task['batch_uuid'],)
                )
                full_task = cursor.fetchone()
            if full_task:
                execute_task(db.connection, full_task)
            db.close()
            return jsonify({
                "code": 200,
                "processed": 1,
                "batch_uuid": task['batch_uuid']
            })
        except Exception as e:
            logger.exception("process-pending 异常")
            return jsonify({"code": 500, "message": str(e)}), 500
    
    try:
        app.run(host="0.0.0.0", port=port, debug=False)
    finally:
        stop_event.set()


# ===================================================================
# 主入口
# ===================================================================

def main():
    """主函数"""
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description='电商销售数据智能分析平台 - 算法模块',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 1. 导入CSV数据
  python run.py import data/sales_data.csv
  
  # 2. 生成测试数据
  python run.py generate data/test_data.csv --count 1000
  
  # 3. 启动算法服务（持续运行，纯轮询）
  python run.py service --interval 10
  
  # 4. 启动 HTTP 服务（用于 Railway 部署）
  python run.py --server --port 5000
  
  # 5. 单次运行分析（测试）
  python run.py runonce --start-date 2025-01-01 --end-date 2025-12-31
  
  # 6. 检查数据库连接
  python run.py checkdb
        """
    )
    
    # 全局参数
    parser.add_argument("--server", action="store_true", help="启动 HTTP 服务模式（用于 Railway）")
    parser.add_argument("--port", type=int, default=None, help="HTTP 端口（默认从环境变量 PORT 读取）")
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # import 命令
    import_parser = subparsers.add_parser('import', help='导入CSV数据到数据库')
    import_parser.add_argument('file', help='CSV文件路径')
    import_parser.add_argument('--batch-size', type=int, default=1000, help='批量插入大小')
    import_parser.set_defaults(func=cmd_import)
    
    # generate 命令
    gen_parser = subparsers.add_parser('generate', help='生成示例CSV文件')
    gen_parser.add_argument('output', help='输出文件路径')
    gen_parser.add_argument('--count', type=int, default=100, help='生成记录数')
    gen_parser.set_defaults(func=cmd_generate)
    
    # service 命令（纯轮询）
    service_parser = subparsers.add_parser('service', help='启动算法服务（持续轮询）')
    service_parser.add_argument('--interval', type=int, default=10, help='轮询间隔（秒）')
    service_parser.set_defaults(func=cmd_service)
    
    # runonce 命令
    once_parser = subparsers.add_parser('runonce', help='单次运行关联规则分析')
    once_parser.add_argument('--start-date', type=str, default='2025-01-01', help='开始日期')
    once_parser.add_argument('--end-date', type=str, default='2025-12-31', help='结束日期')
    once_parser.add_argument('--min-support', type=float, default=0.01, help='最小支持度')
    once_parser.add_argument('--min-confidence', type=float, default=0.3, help='最小置信度')
    once_parser.add_argument('--min-lift', type=float, default=1.0, help='最小提升度')
    once_parser.add_argument('--algorithm', choices=['apriori', 'fpgrowth'], default='apriori', help='算法选择')
    once_parser.set_defaults(func=cmd_runonce)
    
    # checkdb 命令
    checkdb_parser = subparsers.add_parser('checkdb', help='检查数据库连接和表结构')
    checkdb_parser.set_defaults(func=cmd_checkdb)
    
    # 解析参数
    args = parser.parse_args()
    
    # 如果指定了 --server，直接启动 HTTP 服务（忽略其他命令）
    if args.server:
        run_http_server(args.port)
        return
    
    # 否则执行子命令
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == '__main__':
    main()