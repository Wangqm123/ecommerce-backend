# -*- coding: utf-8 -*-
"""
关联规则算法服务 - 主程序入口
负责：
1. 轮询任务队列
2. 执行关联规则分析
3. 将结果写入数据库
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DB_CONFIG, ALGORITHM_CONFIG, validate_config, print_config
from database import DatabaseManager, AssociationTaskManager, build_transactions
from association_algorithm import run_association_analysis


def setup_logging(log_level: str = 'INFO', log_file: str = None):
    """配置日志"""
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    handlers = [logging.StreamHandler()]
    
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def process_task(task_manager: AssociationTaskManager, task: Dict[str, Any], 
                  config: Dict[str, Any]) -> bool:
    """
    处理单个关联规则计算任务
    
    Args:
        task_manager: 任务管理器
        task: 任务信息
        config: 算法配置
        
    Returns:
        是否成功
    """
    batch_uuid = task['batch_uuid']
    params = json.loads(task['params']) if task['params'] else {}
    
    logger = logging.getLogger(__name__)
    logger.info(f"开始处理任务: {batch_uuid}")
    logger.info(f"任务参数: {params}")
    
    try:
        # 1. 更新任务状态为 running
        if not task_manager.start_task(batch_uuid):
            logger.error(f"无法启动任务 {batch_uuid}")
            return False
        
        # 2. 解析任务参数
        start_date = params.get('startDate', '2025-01-01')
        end_date = params.get('endDate', '2025-12-31')
        min_support = params.get('minSupport', config['min_support'])
        min_confidence = params.get('minConfidence', config['min_confidence'])
        min_lift = params.get('minLift', config['min_lift'])
        max_length = params.get('maxLength', config['max_length'])
        algorithm = params.get('algorithm', 'apriori')  # 可选: apriori 或 fpgrowth
        
        logger.info(f"时间范围: {start_date} ~ {end_date}")
        logger.info(f"算法参数: min_support={min_support}, min_confidence={min_confidence}, "
                   f"min_lift={min_lift}, max_length={max_length}, algorithm={algorithm}")
        
        # 3. 获取输入数据
        raw_data = task_manager.get_input_data(start_date, end_date)
        if not raw_data:
            logger.warning(f"任务 {batch_uuid}: 没有找到符合条件的订单数据")
            task_manager.complete_task(batch_uuid, 0)
            return True
        
        # 4. 构建购物篮
        transactions = build_transactions(raw_data)
        
        # 5. 获取商品信息映射
        product_info = task_manager.get_product_info()
        
        # 6. 执行关联规则分析
        rules = run_association_analysis(
            transactions=transactions,
            product_info=product_info,
            algorithm=algorithm,
            min_support=min_support,
            min_confidence=min_confidence,
            min_lift=min_lift,
            max_length=max_length
        )
        
        # 7. 清理该批次的旧规则（如果有）
        task_manager.clear_old_rules(batch_uuid)
        
        # 8. 批量写入结果
        inserted_count = task_manager.batch_insert_rules(rules, batch_uuid, config['max_batch_size'])
        
        # 9. 更新任务状态为 completed
        task_manager.complete_task(batch_uuid, len(rules))
        
        logger.info(f"任务 {batch_uuid} 完成，共生成 {len(rules)} 条规则，成功写入 {inserted_count} 条")
        return True
        
    except Exception as e:
        logger.error(f"任务 {batch_uuid} 执行失败: {e}", exc_info=True)
        task_manager.fail_task(batch_uuid, str(e))
        return False


def run_service(poll_interval: int = 5, single_run: bool = False):
    """
    运行关联规则服务
    
    Args:
        poll_interval: 轮询间隔（秒）
        single_run: 是否只运行一次（用于测试）
    """
    logger = logging.getLogger(__name__)
    logger.info("关联规则算法服务启动")
    logger.info(f"轮询间隔: {poll_interval} 秒")
    
    # 初始化数据库连接
    db_manager = DatabaseManager(DB_CONFIG)
    db_manager.connect()
    task_manager = AssociationTaskManager(db_manager)
    
    try:
        while True:
            try:
                # 查找待处理任务
                task = task_manager.get_pending_task()
                
                if task:
                    # 处理任务
                    process_task(task_manager, task, ALGORITHM_CONFIG)
                else:
                    logger.debug("没有待处理的任务")
                
                if single_run:
                    break
                
                # 等待下一次轮询
                time.sleep(poll_interval)
                
            except Exception as e:
                logger.error(f"服务运行出错: {e}", exc_info=True)
                time.sleep(poll_interval)
                
    except KeyboardInterrupt:
        logger.info("收到中断信号，服务停止")
    finally:
        db_manager.close()
        logger.info("关联规则算法服务已停止")


def run_once(params: Dict[str, Any] = None):
    """
    单次运行关联规则分析（不依赖任务队列）
    用于测试或手动触发
    
    Args:
        params: 分析参数
    """
    logger = logging.getLogger(__name__)
    
    if params is None:
        params = {
            'startDate': '2025-01-01',
            'endDate': '2025-12-31',
            'minSupport': 0.01,
            'minConfidence': 0.3,
            'minLift': 1.0,
            'maxLength': 3,
            'algorithm': 'apriori'
        }
    
    logger.info(f"单次运行模式，参数: {params}")
    
    # 初始化数据库连接
    db_manager = DatabaseManager(DB_CONFIG)
    db_manager.connect()
    task_manager = AssociationTaskManager(db_manager)
    
    try:
        # 获取输入数据
        raw_data = task_manager.get_input_data(params['startDate'], params['endDate'])
        if not raw_data:
            logger.warning("没有找到符合条件的订单数据")
            return
        
        # 构建购物篮
        transactions = build_transactions(raw_data)
        
        # 获取商品信息
        product_info = task_manager.get_product_info()
        
        # 执行分析
        rules = run_association_analysis(
            transactions=transactions,
            product_info=product_info,
            algorithm=params.get('algorithm', 'apriori'),
            min_support=params.get('minSupport', 0.01),
            min_confidence=params.get('minConfidence', 0.3),
            min_lift=params.get('minLift', 1.0),
            max_length=params.get('maxLength', 3)
        )
        
        # 输出结果
        logger.info(f"分析完成，共生成 {len(rules)} 条规则")
        
        # 打印前10条规则
        print("\n=== Top 10 关联规则 ===")
        for i, rule in enumerate(rules[:10], 1):
            print(f"\n规则 {i}:")
            print(f"  前件: {rule['antecedent_names']} ({rule['antecedent']})")
            print(f"  后件: {rule['consequent_names']} ({rule['consequent']})")
            print(f"  支持度: {rule['support']:.4f}")
            print(f"  置信度: {rule['confidence']:.4f}")
            print(f"  提升度: {rule['lift']:.4f}")
        
        return rules
        
    finally:
        db_manager.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='关联规则算法服务')
    parser.add_argument('--mode', choices=['service', 'once'], default='service',
                       help='运行模式: service(服务模式) 或 once(单次运行)')
    parser.add_argument('--interval', type=int, default=5,
                       help='服务模式下的轮询间隔（秒）')
    parser.add_argument('--start-date', type=str, default='2025-01-01',
                       help='单次运行模式的开始日期')
    parser.add_argument('--end-date', type=str, default='2025-12-31',
                       help='单次运行模式的结束日期')
    parser.add_argument('--min-support', type=float, default=0.01,
                       help='最小支持度')
    parser.add_argument('--min-confidence', type=float, default=0.3,
                       help='最小置信度')
    parser.add_argument('--min-lift', type=float, default=1.0,
                       help='最小提升度')
    parser.add_argument('--algorithm', choices=['apriori', 'fpgrowth'], default='apriori',
                       help='算法选择')
    parser.add_argument('--show-config', action='store_true',
                       help='显示当前配置并退出')
    
    args = parser.parse_args()
    
    # 显示配置并退出
    if args.show_config:
        print_config()
        sys.exit(0)
    
    # 验证配置
    if not validate_config():
        print("\n请检查 .env 文件配置是否正确")
        sys.exit(1)
    
    # 配置日志
    setup_logging(
        log_level=ALGORITHM_CONFIG.get('log_level', 'INFO'),
        log_file=ALGORITHM_CONFIG.get('log_file')
    )
    
    if args.mode == 'service':
        # 服务模式：持续轮询任务队列
        run_service(poll_interval=args.interval)
    else:
        # 单次运行模式
        params = {
            'startDate': args.start_date,
            'endDate': args.end_date,
            'minSupport': args.min_support,
            'minConfidence': args.min_confidence,
            'minLift': args.min_lift,
            'algorithm': args.algorithm
        }
        run_once(params)


if __name__ == '__main__':
    main()