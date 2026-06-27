import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules
import logging
import random

logger = logging.getLogger(__name__)


def mine_association_rules(transactions, min_support, min_confidence, min_lift, max_length, random_seed=42):
    """
    执行关联规则挖掘
    :param transactions: List[List[str]] 每个订单的商品ID列表
    :param min_support: float
    :param min_confidence: float
    :param min_lift: float
    :param max_length: int 最大项集长度（前件+后件）
    :param random_seed: int 随机种子，保证采样可重现
    :return: List[dict] 符合阈值的规则列表
    """
    if len(transactions) < 2:
        return []
    
    # 快速评估数据规模，自动降级策略
    n_transactions = len(transactions)
    all_items = set()
    for t in transactions:
        all_items.update(t)
    
    n_items = len(all_items)
    original_support = min_support
    original_max_length = max_length
    
    # 大数据量自动调整参数
    if n_items > 2000:
        adjusted_support = min(min_support * 2, 0.1)
        min_support = max(min_support, adjusted_support)
        max_length = min(max_length, 3)
        logger.warning(
            f"商品种类过多({n_items})，动态调整: "
            f"min_support {original_support} -> {min_support}, "
            f"max_length {original_max_length} -> {max_length}"
        )
    
    if n_transactions > 100000:
        random.seed(random_seed)
        sample_size = min(50000, n_transactions)
        transactions = random.sample(transactions, sample_size)
        logger.warning(
            f"订单量过大({n_transactions})，可重现采样 {sample_size} 条 "
            f"(seed={random_seed})"
        )
    
    # 编码事务数据
    te = TransactionEncoder()
    te_ary = te.fit(transactions).transform(transactions)
    df = pd.DataFrame(te_ary, columns=te.columns_)
    
    # 挖掘频繁项集
    frequent_itemsets = apriori(df, min_support=min_support, use_colnames=True, max_len=max_length)
    if frequent_itemsets.empty:
        logger.info(f"未找到频繁项集 (min_support={min_support})")
        return []
    
    # 生成规则
    rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence)
    if rules.empty:
        return []

    # 过滤：总长度不超过 max_length，且提升度达标
    rules = rules[
        (rules['antecedents'].apply(len) + rules['consequents'].apply(len)) <= max_length
    ]
    rules = rules[rules['lift'] >= min_lift]
    
    # 转换结果格式
    result = []
    for _, row in rules.iterrows():
        result.append({
            'antecedent': list(row['antecedents']),
            'consequent': list(row['consequents']),
            'support': round(row['support'], 6),
            'confidence': round(row['confidence'], 6),
            'lift': round(row['lift'], 4)
        })
    
    logger.info(f"挖掘完成：共生成 {len(result)} 条规则")
    return result


def deduplicate_rules(rules):
    """
    去除冗余规则：同一商品组合只保留 lift 最高的方向
    """
    seen = {}
    for rule in rules:
        key = frozenset(rule['antecedent'] + rule['consequent'])
        if key not in seen:
            seen[key] = rule
        else:
            if rule['lift'] > seen[key]['lift']:
                seen[key] = rule
    
    deduped = list(seen.values())
    removed = len(rules) - len(deduped)
    if removed > 0:
        logger.info(f"规则去重：从 {len(rules)} 条去重为 {len(deduped)} 条")
    return deduped