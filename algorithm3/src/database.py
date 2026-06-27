# -*- coding: utf-8 -*-
"""
数据库连接和任务管理模块
负责：
1. 数据库连接管理
2. 任务轮询和状态更新
3. 输入数据查询
4. 结果批量写入
"""

import json
import logging
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        self.connection = None
    
    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                charset=self.db_config['charset'],
                cursorclass=DictCursor
            )
            logger.info("数据库连接成功")
            return self.connection
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("数据库连接已关闭")
    
    @contextmanager
    def get_cursor(self):
        """获取数据库游标的上下文管理器"""
        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            cursor.close()


class AssociationTaskManager:
    """关联规则任务管理器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_pending_task(self) -> Optional[Dict[str, Any]]:
        """
        获取一个待处理的任务
        返回: 任务信息字典，包含 batch_uuid, params 等
        """
        with self.db_manager.get_cursor() as cursor:
            sql = """
                SELECT batch_uuid, status, params, created_at
                FROM association_tasks
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            """
            cursor.execute(sql)
            task = cursor.fetchone()
            return task
    
    def start_task(self, batch_uuid: str) -> bool:
        """
        将任务状态更新为 running
        """
        try:
            with self.db_manager.get_cursor() as cursor:
                sql = """
                    UPDATE association_tasks
                    SET status = 'running', started_at = NOW()
                    WHERE batch_uuid = %s AND status = 'pending'
                """
                cursor.execute(sql, (batch_uuid,))
                affected = cursor.rowcount
                if affected > 0:
                    logger.info(f"任务 {batch_uuid} 已开始执行")
                    return True
                return False
        except Exception as e:
            logger.error(f"启动任务失败: {e}")
            return False
    
    def complete_task(self, batch_uuid: str, total_rules: int) -> bool:
        """
        将任务状态更新为 completed
        """
        try:
            with self.db_manager.get_cursor() as cursor:
                sql = """
                    UPDATE association_tasks
                    SET status = 'completed', total_rules = %s, completed_at = NOW()
                    WHERE batch_uuid = %s
                """
                cursor.execute(sql, (total_rules, batch_uuid))
                logger.info(f"任务 {batch_uuid} 已完成，共生成 {total_rules} 条规则")
                return True
        except Exception as e:
            logger.error(f"完成任务失败: {e}")
            return False
    
    def fail_task(self, batch_uuid: str, error_message: str = None) -> bool:
        """
        将任务状态更新为 failed
        """
        try:
            with self.db_manager.get_cursor() as cursor:
                sql = """
                    UPDATE association_tasks
                    SET status = 'failed', completed_at = NOW()
                    WHERE batch_uuid = %s
                """
                cursor.execute(sql, (batch_uuid,))
                logger.error(f"任务 {batch_uuid} 执行失败: {error_message}")
                return True
        except Exception as e:
            logger.error(f"标记任务失败时出错: {e}")
            return False
    
    def get_input_data(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        获取关联规则计算的输入数据
        返回: 订单商品列表，按 order_id 分组后可构建购物篮
        """
        with self.db_manager.get_cursor() as cursor:
            sql = """
                SELECT o.order_id, o.product_id, p.product_name, p.category
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                WHERE o.order_status = 'completed'
                  AND o.order_date BETWEEN %s AND %s
                ORDER BY o.order_id, o.product_id
            """
            cursor.execute(sql, (start_date, end_date))
            results = cursor.fetchall()
            logger.info(f"获取到 {len(results)} 条订单商品记录")
            return results
    
    def get_product_info(self) -> Dict[str, Dict[str, str]]:
        """
        获取商品ID到商品名称和品类的映射
        """
        with self.db_manager.get_cursor() as cursor:
            sql = "SELECT product_id, product_name, category FROM products"
            cursor.execute(sql)
            results = cursor.fetchall()
            return {row['product_id']: {
                'product_name': row['product_name'],
                'category': row['category']
            } for row in results}
    
    def batch_insert_rules(self, rules: List[Dict[str, Any]], batch_uuid: str, batch_size: int = 500) -> int:
        """
        批量插入关联规则结果
        """
        if not rules:
            return 0
        
        inserted_count = 0
        with self.db_manager.get_cursor() as cursor:
            sql = """
                INSERT INTO association_rules
                (antecedent, consequent, antecedent_names, consequent_names,
                 support, confidence, lift, rule_type, compute_batch)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # 分批插入
            for i in range(0, len(rules), batch_size):
                batch = rules[i:i + batch_size]
                values = []
                for rule in batch:
                    values.append((
                        json.dumps(rule['antecedent'], ensure_ascii=False),
                        json.dumps(rule['consequent'], ensure_ascii=False),
                        json.dumps(rule['antecedent_names'], ensure_ascii=False),
                        json.dumps(rule['consequent_names'], ensure_ascii=False),
                        rule['support'],
                        rule['confidence'],
                        rule['lift'],
                        rule['rule_type'],
                        batch_uuid
                    ))
                cursor.executemany(sql, values)
                inserted_count += len(batch)
                logger.info(f"已插入 {inserted_count}/{len(rules)} 条规则")
        
        return inserted_count
    
    def clear_old_rules(self, batch_uuid: str = None):
        """
        清理旧的关联规则结果
        如果指定 batch_uuid，只清理该批次的结果
        """
        with self.db_manager.get_cursor() as cursor:
            if batch_uuid:
                sql = "DELETE FROM association_rules WHERE compute_batch = %s"
                cursor.execute(sql, (batch_uuid,))
                logger.info(f"已清理批次 {batch_uuid} 的旧规则")
            else:
                sql = "TRUNCATE TABLE association_rules"
                cursor.execute(sql)
                logger.info("已清理所有旧规则")


def build_transactions(raw_data: List[Dict[str, Any]]) -> List[List[str]]:
    """
    将原始订单数据构建为购物篮格式
    每个 order_id 对应一个购物篮（商品ID列表）
    """
    from collections import defaultdict
    
    baskets = defaultdict(list)
    for row in raw_data:
        baskets[row['order_id']].append(str(row['product_id']))
    
    transactions = list(baskets.values())
    logger.info(f"构建了 {len(transactions)} 个购物篮")
    return transactions