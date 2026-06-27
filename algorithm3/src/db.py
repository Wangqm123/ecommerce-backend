import pymysql
import json
from datetime import datetime, timedelta
from config import Config
import logging
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.connection = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

    def _ensure_connection(self):
        """确保数据库连接有效"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            self.connection = pymysql.connect(
                host=Config.DB_HOST, port=Config.DB_PORT,
                user=Config.DB_USER, password=Config.DB_PASSWORD,
                database=Config.DB_NAME, charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )

    def get_pending_task(self):
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT batch_uuid, params, retry_count 
                FROM association_tasks 
                WHERE status = 'pending' 
                ORDER BY created_at ASC 
                LIMIT 1 
                FOR UPDATE
            """)
            task = cursor.fetchone()
            if not task:
                cursor.execute("""
                    SELECT batch_uuid, params, retry_count 
                    FROM association_tasks 
                    WHERE status = 'failed' 
                      AND retry_count < max_retries
                    ORDER BY created_at ASC 
                    LIMIT 1 
                    FOR UPDATE
                """)
                task = cursor.fetchone()
                if task:
                    cursor.execute("""
                        UPDATE association_tasks 
                        SET status = 'pending', retry_count = retry_count + 1, 
                            started_at = NULL, error_message = NULL 
                        WHERE batch_uuid = %s
                    """, (task['batch_uuid'],))
                    self.connection.commit()
                    cursor.execute("""
                        SELECT batch_uuid, params, retry_count 
                        FROM association_tasks 
                        WHERE batch_uuid = %s
                    """, (task['batch_uuid'],))
                    task = cursor.fetchone()

            if task:
                cursor.execute("""
                    UPDATE association_tasks 
                    SET status = 'running', started_at = NOW() 
                    WHERE batch_uuid = %s AND status = 'pending'
                """, (task['batch_uuid'],))
                self.connection.commit()
                params = json.loads(task['params']) if task['params'] else {}
                return task['batch_uuid'], params, task.get('retry_count', 0)
        return None, None, 0
    
    def update_task_completed(self, batch_uuid, total_rules):
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("""
                UPDATE association_tasks 
                SET status = 'completed', total_rules = %s, completed_at = NOW() 
                WHERE batch_uuid = %s
            """, (total_rules, batch_uuid))
            self.connection.commit()

    def update_task_failed(self, batch_uuid, error_msg=None):
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("""
                UPDATE association_tasks 
                SET status = 'failed', error_message = %s, completed_at = NOW() 
                WHERE batch_uuid = %s
            """, (error_msg, batch_uuid))
            self.connection.commit()

    def update_task_for_retry(self, batch_uuid, new_retry_count):
        """将失败任务回退为 pending 状态"""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("""
                UPDATE association_tasks 
                SET status = 'pending', 
                    retry_count = %s, 
                    started_at = NULL, 
                    error_message = NULL,
                    completed_at = NULL
                WHERE batch_uuid = %s
            """, (new_retry_count, batch_uuid))
            self.connection.commit()

    def get_transactions(self, start_date, end_date, batch_size=5000):
        """分批获取事务数据（按文档规范：从 orders 表读取）"""
        self._ensure_connection()

        with self.connection.cursor() as cursor:
            cursor.execute("SET SESSION group_concat_max_len = 1048576")
        
        offset = 0
        while True:
            sql = """
                SELECT o.order_id, 
                       GROUP_CONCAT(DISTINCT o.product_id SEPARATOR '|') AS product_ids
                FROM orders o
                WHERE o.order_status = 'completed'
                  AND o.order_date BETWEEN %s AND %s
                GROUP BY o.order_id
                ORDER BY o.order_id
                LIMIT %s OFFSET %s
            """
            with self.connection.cursor() as cursor:
                cursor.execute(sql, (start_date, end_date, batch_size, offset))
                rows = cursor.fetchall()
                
                if not rows:
                    break
                
                batch_transactions = []
                for row in rows:
                    if row['product_ids']:
                        product_ids = row['product_ids'].split('|')
                        if product_ids and product_ids[0]:
                            batch_transactions.append(product_ids)
                
                if batch_transactions:
                    yield batch_transactions
            
            offset += batch_size
    
    def get_product_name_map(self, product_ids_set):
        """批量获取商品ID -> 名称映射（按文档规范：从 products 表读取）"""
        self._ensure_connection()
        if not product_ids_set:
            return {}
        placeholders = ','.join(['%s'] * len(product_ids_set))
        sql = f"SELECT product_id, product_name FROM products WHERE product_id IN ({placeholders})"
        with self.connection.cursor() as cursor:
            cursor.execute(sql, list(product_ids_set))
            rows = cursor.fetchall()
        return {str(row['product_id']): row['product_name'] for row in rows}

    def sync_max_retries(self, batch_uuid, max_retries):
        """将 params 中的 maxRetries 同步到任务表"""
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("""
                UPDATE association_tasks 
                SET max_retries = %s 
                WHERE batch_uuid = %s AND max_retries != %s
            """, (max_retries, batch_uuid, max_retries))
            if cursor.rowcount > 0:
                self.connection.commit()
                logger.info(f"任务 {batch_uuid} max_retries 已同步为 {max_retries}")

    def get_product_category_map(self, product_ids_set):
        """批量获取商品ID -> 品类映射（按文档规范：从 products 表读取）"""
        self._ensure_connection()
        if not product_ids_set:
            return {}

        placeholders = ','.join(['%s'] * len(product_ids_set))
        sql = f"""
            SELECT product_id, category 
            FROM products 
            WHERE product_id IN ({placeholders})
        """
        with self.connection.cursor() as cursor:
            cursor.execute(sql, list(product_ids_set))
            rows = cursor.fetchall()

        result = {}
        for row in rows:
            cat_id = str(row['category'])
            result[str(row['product_id'])] = cat_id

        return result

    def insert_rules(self, batch_uuid, rules, expires_days=30):
        """批量插入关联规则（显式设置有效期）"""
        self._ensure_connection()
        if not rules:
            return
        
        expires_at = (datetime.now() + timedelta(days=expires_days)).strftime('%Y-%m-%d %H:%M:%S')
        
        insert_sql = """
            INSERT INTO association_rules 
            (antecedent, consequent, antecedent_names, consequent_names, 
             support, confidence, lift, rule_type, compute_batch, is_active, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with self.connection.cursor() as cursor:
            for rule in rules:
                cursor.execute(insert_sql, (
                    json.dumps(rule['antecedent']),
                    json.dumps(rule['consequent']),
                    json.dumps(rule['antecedent_names']),
                    json.dumps(rule['consequent_names']),
                    rule['support'],
                    rule['confidence'],
                    rule['lift'],
                    rule.get('rule_type', 'product'),
                    batch_uuid,
                    1,
                    expires_at
                ))
            self.connection.commit()

    def get_latest_completed_batch(self):
        self._ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT batch_uuid FROM association_tasks
                WHERE status = 'completed' AND total_rules > 0
                ORDER BY completed_at DESC LIMIT 1
            """)
            row = cursor.fetchone()
            return row['batch_uuid'] if row else None

    def get_recommendations_by_product(self, product_id, top_n=5, batch_uuid=None, 
                                       min_confidence=0.3, min_lift=1.0, 
                                       only_active=True):
        """根据单个商品ID查询推荐（增加过期过滤）"""
        pid = str(product_id)
        if batch_uuid is None:
            batch_uuid = self.get_latest_completed_batch()
            if not batch_uuid:
                return []
        
        conditions = [
            "JSON_CONTAINS(antecedent, JSON_QUOTE(%s))",
            "confidence >= %s",
            "lift >= %s",
            "compute_batch = %s"
        ]
        params = [pid, min_confidence, min_lift, batch_uuid]
        
        if only_active:
            conditions.append("is_active = 1")
            conditions.append("(expires_at IS NULL OR expires_at > NOW())")
        
        where_clause = " AND ".join(conditions)
        
        sql = f"""
            SELECT 
                id,
                antecedent,
                consequent,
                antecedent_names,
                consequent_names,
                support,
                confidence,
                lift,
                compute_batch
            FROM association_rules
            WHERE {where_clause}
            ORDER BY lift DESC, confidence DESC
            LIMIT %s
        """
        params.append(top_n)
        
        with self.connection.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append({
                'rule_id': row['id'],
                'antecedent': json.loads(row['antecedent']),
                'consequent': json.loads(row['consequent']),
                'antecedent_names': json.loads(row['antecedent_names']),
                'consequent_names': json.loads(row['consequent_names']),
                'support': float(row['support']),
                'confidence': float(row['confidence']),
                'lift': float(row['lift']),
                'compute_batch': row['compute_batch']
            })
        return results


    def get_rules_by_batch(self, batch_uuid, limit=100, offset=0, only_active=False):
        """按批次分页查询关联规则"""
        self._ensure_connection()
        
        conditions = ["compute_batch = %s"]
        params = [batch_uuid]
        
        if only_active:
            conditions.append("is_active = 1")
            conditions.append("(expires_at IS NULL OR expires_at > NOW())")
        
        where_clause = " AND ".join(conditions)
        
        sql = f"""
            SELECT 
                id,
                antecedent,
                consequent,
                antecedent_names,
                consequent_names,
                support,
                confidence,
                lift,
                rule_type,
                created_at
            FROM association_rules
            WHERE {where_clause}
            ORDER BY lift DESC, confidence DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        
        with self.connection.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append({
                'rule_id': row['id'],
                'antecedent': json.loads(row['antecedent']),
                'consequent': json.loads(row['consequent']),
                'antecedent_names': json.loads(row['antecedent_names']),
                'consequent_names': json.loads(row['consequent_names']),
                'support': float(row['support']),
                'confidence': float(row['confidence']),
                'lift': float(row['lift']),
                'rule_type': row['rule_type'],
                'created_at': row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else None
            })
        return results

    def close(self):
        self.connection.close()