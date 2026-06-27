# -*- coding: utf-8 -*-
"""
数据导入和算法运行脚本
提供完整的命令行接口
"""

import os
import sys
import argparse
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.csv_importer import parse_csv_file, import_to_database
from src.main import run_service, run_once


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def cmd_import(args):
    """导入CSV数据"""
    from src.csv_importer import parse_csv_file, preprocess_data, import_to_database
    
    print(f"开始导入CSV文件: {args.file}")
    try:
        # 1. 解析CSV文件
        raw_data = parse_csv_file(args.file)
        
        if not raw_data:
            print("CSV文件中没有有效数据")
            return
        
        # 2. 数据预处理（清洗和过滤）
        cleaned_data, report = preprocess_data(raw_data)
        
        if not cleaned_data:
            print("预处理后没有有效数据")
            return
        
        # 3. 导入数据库
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
    """启动算法服务"""
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
    from src.config import DB_CONFIG
    from src.database import DatabaseManager
    
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
  
  # 3. 启动算法服务（持续运行）
  python run.py service --interval 10
  
  # 4. 单次运行分析（测试）
  python run.py runonce --start-date 2025-01-01 --end-date 2025-12-31
  
  # 5. 检查数据库连接
  python run.py checkdb
        """
    )
    
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
    
    # service 命令
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
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == '__main__':
    main()