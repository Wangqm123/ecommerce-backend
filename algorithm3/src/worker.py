from config import Config
import time
import logging
import traceback
from datetime import datetime
from db import Database
from mining import mine_association_rules, deduplicate_rules

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AssociationWorker:
    def __init__(self):
        self.db = Database()
    
    def _parse_params(self, params):
        """解析并校验任务参数，校验失败直接抛出异常"""
        start_date = params.get('startDate')
        end_date = params.get('endDate')
        if not start_date or not end_date:
            raise ValueError("缺少 startDate 或 endDate 参数")

        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("日期格式必须为 YYYY-MM-DD")
        
        if start_dt > end_dt:
            raise ValueError("startDate 不能晚于 endDate")
        
        days_range = (end_dt - start_dt).days
        if days_range > 730:
            raise ValueError("时间范围不能超过2年")
        if days_range < 1:
            raise ValueError("时间范围至少需要1天")

        try:
            min_support = float(params.get('minSupport', 0.01))
            min_confidence = float(params.get('minConfidence', 0.3))
            min_lift = float(params.get('minLift', 1.0))
            max_length = int(params.get('maxLength', 3))
            max_retries = int(params.get('maxRetries', 2))
        except (ValueError, TypeError) as e:
            raise ValueError(f"数值参数格式错误: {e}")

        if not (0 < min_support <= 1):
            raise ValueError("minSupport 必须在 (0, 1] 之间")
        if not (0 < min_confidence <= 1):
            raise ValueError("minConfidence 必须在 (0, 1] 之间")
        if min_lift < 0:
            raise ValueError("minLift 必须 >= 0")
        if max_length < 2:
            raise ValueError("maxLength 必须 >= 2")
        if max_retries < 0 or max_retries > 10:
            raise ValueError("maxRetries 必须在 [0, 10] 之间")

        return start_date, end_date, min_support, min_confidence, min_lift, max_length, max_retries

    def run_task(self, batch_uuid, params, retry_count=0):
        logger.info(f"开始处理任务 {batch_uuid}, 重试次数 {retry_count}, 参数: {params}")
        start_time = time.time()
        
        max_retries = 2  # 默认值，防止异常时未赋值
        
        try:
            # 解析参数（含校验）
            start_date, end_date, min_support, min_confidence, min_lift, max_length, max_retries = self._parse_params(params)

            self.db.sync_max_retries(batch_uuid, max_retries)
            
            # 1. 获取事务数据（扁平化批次）
            transactions = []
            for batch in self.db.get_transactions(start_date, end_date):
                transactions.extend(batch)
            
            if not transactions:
                logger.warning(f"任务 {batch_uuid} 时间范围内无订单数据")
                self.db.update_task_completed(batch_uuid, 0)
                return
            
            n_orders = len(transactions)
            n_items = len(set(item for t in transactions for item in t))
            logger.info(f"任务 {batch_uuid} 加载数据：{n_orders} 笔订单，{n_items} 种商品")
            
            # 2. 挖掘单品规则
            product_rules = mine_association_rules(
                transactions, min_support, min_confidence, min_lift, max_length
            )
            
            # 3. 挖掘品类规则（支持度不低于 0.001）
            category_rules = []
            category_map = self.db.get_product_category_map(
                set(item for t in transactions for item in t)
            )
            if category_map:
                category_transactions = []
                for t in transactions:
                    cats = [category_map.get(pid, pid) for pid in t]
                    category_transactions.append(list(set(cats)))
                
                # 品类支持度有下限，避免 DECIMAL(8,6) 存储极小值
                category_min_support = max(min_support * 0.5, 0.001)
                
                category_rules = mine_association_rules(
                    category_transactions,
                    category_min_support,
                    min_confidence, 
                    min_lift, 
                    max_length
                )
                for r in category_rules:
                    r['rule_type'] = 'category'
                
                logger.info(f"品类规则挖掘: 支持度阈值 {min_support} -> {category_min_support}, "
                           f"生成 {len(category_rules)} 条规则")
            
            # 4. 合并并去重
            for r in product_rules:
                r['rule_type'] = 'product'
            
            all_rules = product_rules + category_rules
            all_rules = deduplicate_rules(all_rules)
            
            if not all_rules:
                logger.info(f"任务 {batch_uuid} 未生成任何满足条件的规则")
                self.db.update_task_completed(batch_uuid, 0)
                return
            
            # 5. 获取商品名称映射（仅 product 类型）
            all_product_ids = set()
            for rule in all_rules:
                if rule.get('rule_type') == 'product':
                    all_product_ids.update(rule['antecedent'])
                    all_product_ids.update(rule['consequent'])
            
            name_map = self.db.get_product_name_map(all_product_ids) if all_product_ids else {}
            
            # 6. 为每条规则补充名称
            for rule in all_rules:
                if rule.get('rule_type') == 'product':
                    rule['antecedent_names'] = [name_map.get(pid, pid) for pid in rule['antecedent']]
                    rule['consequent_names'] = [name_map.get(pid, pid) for pid in rule['consequent']]
                else:
                    # category 类型：名称即品类ID本身
                    rule['antecedent_names'] = rule['antecedent']
                    rule['consequent_names'] = rule['consequent']
            
            # 7. 写入数据库
            self.db.insert_rules(batch_uuid, all_rules)
            self.db.update_task_completed(batch_uuid, len(all_rules))
            
            duration = time.time() - start_time
            logger.info(f"任务 {batch_uuid} 完成，生成 {len(all_rules)} 条规则，耗时 {duration:.2f}s")
            
        except Exception as e:
            error_msg = traceback.format_exc()
            logger.error(f"任务 {batch_uuid} 失败 (第 {retry_count+1} 次尝试): {error_msg}")
            
            if retry_count < max_retries:
                self.db.update_task_for_retry(batch_uuid, retry_count + 1)
                logger.info(f"任务 {batch_uuid} 已回退为 pending，将在下次轮询重试 (第 {retry_count + 1} 次)")
            else:
                self.db.update_task_failed(batch_uuid, str(e))
                logger.error(f"任务 {batch_uuid} 已达到最大重试次数 {max_retries}，标记为 failed")
    
    def run_forever(self):
        logger.info("关联规则Worker启动，开始轮询任务...")
        while True:
            try:
                batch_uuid, params, retry_count = self.db.get_pending_task()
                if batch_uuid:
                    self.run_task(batch_uuid, params, retry_count)
                else:
                    time.sleep(Config.WORKER_SLEEP_INTERVAL)
            except KeyboardInterrupt:
                logger.info("Worker停止")
                break
            except Exception as e:
                logger.error(f"Worker异常: {traceback.format_exc()}")
                time.sleep(Config.WORKER_SLEEP_INTERVAL)
        self.db.close()

if __name__ == "__main__":
    worker = AssociationWorker()
    worker.run_forever()