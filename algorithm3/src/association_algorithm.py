# -*- coding: utf-8 -*-
"""
关联规则算法模块
实现 Apriori 算法和 FP-Growth 算法进行商品关联分析
"""

import logging
from typing import List, Dict, Set, Tuple, Any, Optional
from itertools import combinations
from collections import defaultdict
import time

logger = logging.getLogger(__name__)


class AprioriAlgorithm:
    """
    Apriori 关联规则挖掘算法实现
    
    核心思想：
    1. 通过逐层搜索找出频繁项集
    2. 利用 Apriori 性质剪枝（频繁项集的子集也必须是频繁的）
    3. 从频繁项集生成关联规则
    """
    
    def __init__(self, min_support: float = 0.01, min_confidence: float = 0.3, 
                 min_lift: float = 1.0, max_length: int = 3):
        """
        初始化算法参数
        
        Args:
            min_support: 最小支持度阈值
            min_confidence: 最小置信度阈值
            min_lift: 最小提升度阈值
            max_length: 规则最大长度（前件+后件的最大项数）
        """
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_lift = min_lift
        self.max_length = max_length
    
    def fit(self, transactions: List[List[str]]) -> Tuple[Dict[frozenset, float], int]:
        """
        执行 Apriori 算法，找出所有频繁项集
        
        Args:
            transactions: 交易数据，每个交易是一个商品ID列表
            
        Returns:
            frequent_itemsets: 频繁项集及其支持度
            total_transactions: 总交易数
        """
        total_transactions = len(transactions)
        if total_transactions == 0:
            return {}, 0
        
        logger.info(f"开始 Apriori 算法，共 {total_transactions} 个交易，最小支持度: {self.min_support}")
        start_time = time.time()
        
        # 第一步：生成频繁1-项集
        frequent_itemsets = {}
        item_counts = defaultdict(int)
        
        for transaction in transactions:
            for item in transaction:
                item_counts[frozenset([item])] += 1
        
        # 筛选满足最小支持度的1-项集
        min_count = self.min_support * total_transactions
        frequent_1 = {itemset: count / total_transactions 
                      for itemset, count in item_counts.items() 
                      if count >= min_count}
        frequent_itemsets.update(frequent_1)
        
        logger.info(f"频繁1-项集数量: {len(frequent_1)}")
        
        # 迭代生成 k-项集
        k = 2
        prev_frequent = set(frequent_1.keys())
        
        while prev_frequent and k <= self.max_length:
            # 生成候选 k-项集
            candidates = self._generate_candidates(prev_frequent, k)
            
            if not candidates:
                break
            
            # 统计候选集的支持度
            candidate_counts = defaultdict(int)
            for transaction in transactions:
                transaction_set = set(transaction)
                for candidate in candidates:
                    if candidate.issubset(transaction_set):
                        candidate_counts[candidate] += 1
            
            # 筛选频繁 k-项集
            frequent_k = {itemset: count / total_transactions 
                          for itemset, count in candidate_counts.items() 
                          if count >= min_count}
            
            if not frequent_k:
                break
            
            frequent_itemsets.update(frequent_k)
            prev_frequent = set(frequent_k.keys())
            
            logger.info(f"频繁{k}-项集数量: {len(frequent_k)}")
            k += 1
        
        elapsed = time.time() - start_time
        logger.info(f"Apriori 算法完成，共找到 {len(frequent_itemsets)} 个频繁项集，耗时 {elapsed:.2f} 秒")
        
        return frequent_itemsets, total_transactions
    
    def _generate_candidates(self, prev_frequent: Set[frozenset], k: int) -> Set[frozenset]:
        """
        从频繁 (k-1)-项集生成候选 k-项集
        使用 Fk-1 × Fk-1 方法
        """
        candidates = set()
        prev_list = list(prev_frequent)
        
        for i in range(len(prev_list)):
            for j in range(i + 1, len(prev_list)):
                # 合并两个 (k-1)-项集
                union_set = prev_list[i] | prev_list[j]
                if len(union_set) == k:
                    # Apriori 剪枝：检查所有 (k-1)-子集是否都是频繁的
                    all_subsets_frequent = True
                    for subset in combinations(union_set, k - 1):
                        if frozenset(subset) not in prev_frequent:
                            all_subsets_frequent = False
                            break
                    if all_subsets_frequent:
                        candidates.add(union_set)
        
        return candidates
    
    def generate_rules(self, frequent_itemsets: Dict[frozenset, float], 
                       total_transactions: int,
                       product_info: Optional[Dict[str, Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """
        从频繁项集生成关联规则
        
        Args:
            frequent_itemsets: 频繁项集及其支持度
            total_transactions: 总交易数
            product_info: 商品ID到商品名称的映射（可选）
            
        Returns:
            rules: 关联规则列表
        """
        rules = []
        logger.info("开始生成关联规则...")
        
        for itemset, support in frequent_itemsets.items():
            if len(itemset) < 2:
                continue  # 单项集无法生成规则
            
            # 生成所有可能的前件和后件组合
            for i in range(1, len(itemset)):
                for antecedent in combinations(itemset, i):
                    antecedent = frozenset(antecedent)
                    consequent = itemset - antecedent
                    
                    if not consequent:
                        continue
                    
                    # 计算置信度
                    antecedent_support = frequent_itemsets.get(antecedent, 0)
                    if antecedent_support == 0:
                        continue
                    
                    confidence = support / antecedent_support
                    
                    # 计算提升度
                    consequent_support = frequent_itemsets.get(consequent, 0)
                    if consequent_support == 0:
                        continue
                    
                    lift = confidence / consequent_support
                    
                    # 筛选满足阈值的规则
                    if confidence >= self.min_confidence and lift >= self.min_lift:
                        rule = {
                            'antecedent': sorted(list(antecedent)),
                            'consequent': sorted(list(consequent)),
                            'support': round(support, 6),
                            'confidence': round(confidence, 6),
                            'lift': round(lift, 4),
                            'rule_type': 'product'
                        }
                        
                        # 添加商品名称
                        if product_info:
                            rule['antecedent_names'] = [
                                product_info.get(pid, {}).get('product_name', pid)
                                for pid in rule['antecedent']
                            ]
                            rule['consequent_names'] = [
                                product_info.get(pid, {}).get('product_name', pid)
                                for pid in rule['consequent']
                            ]
                        else:
                            rule['antecedent_names'] = rule['antecedent']
                            rule['consequent_names'] = rule['consequent']
                        
                        rules.append(rule)
        
        # 按提升度降序排序
        rules.sort(key=lambda x: x['lift'], reverse=True)
        
        logger.info(f"共生成 {len(rules)} 条关联规则")
        return rules


class FPGrowthAlgorithm:
    """
    FP-Growth 关联规则挖掘算法实现
    
    核心思想：
    1. 构建 FP 树压缩数据
    2. 通过条件模式基递归挖掘频繁项集
    3. 无需生成候选项集，效率更高
    """
    
    def __init__(self, min_support: float = 0.01, min_confidence: float = 0.3,
                 min_lift: float = 1.0, max_length: int = 3):
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_lift = min_lift
        self.max_length = max_length
    
    class FPNode:
        """FP 树节点"""
        def __init__(self, item: str, parent: 'FPGrowthAlgorithm.FPNode' = None):
            self.item = item
            self.count = 1
            self.parent = parent
            self.children = {}
            self.link = None  # 同类项的链接
        
        def increment(self):
            self.count += 1
    
    def fit(self, transactions: List[List[str]]) -> Tuple[Dict[frozenset, int], int]:
        """
        执行 FP-Growth 算法
        
        Args:
            transactions: 交易数据
            
        Returns:
            frequent_itemsets: 频繁项集及其支持计数
            total_transactions: 总交易数
        """
        total_transactions = len(transactions)
        if total_transactions == 0:
            return {}, 0
        
        logger.info(f"开始 FP-Growth 算法，共 {total_transactions} 个交易，最小支持度: {self.min_support}")
        start_time = time.time()
        
        min_count = int(self.min_support * total_transactions)
        
        # 第一步：统计单项频率
        item_counts = defaultdict(int)
        for transaction in transactions:
            for item in transaction:
                item_counts[item] += 1
        
        # 过滤低频项并排序
        frequent_items = {item: count for item, count in item_counts.items() 
                         if count >= min_count}
        sorted_items = sorted(frequent_items.items(), key=lambda x: (-x[1], x[0]))
        
        # 第二步：构建 FP 树
        root = self.FPNode(None)
        header_table = {item: [count, None] for item, count in sorted_items}
        
        for transaction in transactions:
            # 过滤并排序交易中的项
            filtered = [item for item in transaction if item in frequent_items]
            filtered.sort(key=lambda x: (-frequent_items[x], x))
            
            # 插入到 FP 树
            current = root
            for item in filtered:
                if item in current.children:
                    current.children[item].increment()
                else:
                    new_node = self.FPNode(item, current)
                    current.children[item] = new_node
                    
                    # 更新头表链接
                    if header_table[item][1] is None:
                        header_table[item][1] = new_node
                    else:
                        node = header_table[item][1]
                        while node.link:
                            node = node.link
                        node.link = new_node
                
                current = current.children[item]
        
        # 第三步：从 FP 树挖掘频繁项集
        frequent_itemsets = {}
        
        # 添加单项频繁集
        for item, count in frequent_items.items():
            frequent_itemsets[frozenset([item])] = count
        
        # 递归挖掘
        for item in reversed([x[0] for x in sorted_items]):
            suffixes = self._find_prefix_paths(header_table[item][1])
            conditional_tree = self._build_conditional_tree(suffixes, min_count)
            
            if conditional_tree:
                conditional_patterns = self._mine_patterns(conditional_tree, min_count)
                for pattern in conditional_patterns:
                    itemset = frozenset(pattern) | frozenset([item])
                    if len(itemset) <= self.max_length:
                        count = self._get_pattern_count(conditional_tree, pattern)
                        frequent_itemsets[itemset] = count
        
        elapsed = time.time() - start_time
        logger.info(f"FP-Growth 算法完成，共找到 {len(frequent_itemsets)} 个频繁项集，耗时 {elapsed:.2f} 秒")
        
        return frequent_itemsets, total_transactions
    
    def _find_prefix_paths(self, node: FPNode) -> List[List[str]]:
        """查找前缀路径"""
        paths = []
        while node:
            path = []
            current = node.parent
            while current and current.item:
                path.append(current.item)
                current = current.parent
            if path:
                paths.append((path, node.count))
            node = node.link
        return paths
    
    def _build_conditional_tree(self, suffixes: List[Tuple], min_count: int) -> Dict:
        """构建条件树"""
        tree = defaultdict(int)
        for path, count in suffixes:
            for item in path:
                tree[item] += count
        return {k: v for k, v in tree.items() if v >= min_count}
    
    def _mine_patterns(self, tree: Dict, min_count: int) -> List[List[str]]:
        """从条件树挖掘模式"""
        patterns = []
        items = list(tree.keys())
        
        for i in range(1, len(items) + 1):
            for combo in combinations(items, i):
                patterns.append(list(combo))
        
        return patterns
    
    def _get_pattern_count(self, tree: Dict, pattern: List[str]) -> int:
        """获取模式的支持计数"""
        return min(tree.get(item, 0) for item in pattern) if pattern else 0
    
    def generate_rules(self, frequent_itemsets: Dict[frozenset, int],
                       total_transactions: int,
                       product_info: Optional[Dict[str, Dict[str, str]]] = None) -> List[Dict[str, Any]]:
        """生成关联规则"""
        rules = []
        
        # 将支持计数转换为支持度
        itemsets_with_support = {k: v / total_transactions for k, v in frequent_itemsets.items()}
        
        for itemset, support in itemsets_with_support.items():
            if len(itemset) < 2:
                continue
            
            for i in range(1, len(itemset)):
                for antecedent in combinations(itemset, i):
                    antecedent = frozenset(antecedent)
                    consequent = itemset - antecedent
                    
                    if not consequent:
                        continue
                    
                    antecedent_support = itemsets_with_support.get(antecedent, 0)
                    if antecedent_support == 0:
                        continue
                    
                    confidence = support / antecedent_support
                    
                    consequent_support = itemsets_with_support.get(consequent, 0)
                    if consequent_support == 0:
                        continue
                    
                    lift = confidence / consequent_support
                    
                    if confidence >= self.min_confidence and lift >= self.min_lift:
                        rule = {
                            'antecedent': sorted(list(antecedent)),
                            'consequent': sorted(list(consequent)),
                            'support': round(support, 6),
                            'confidence': round(confidence, 6),
                            'lift': round(lift, 4),
                            'rule_type': 'product'
                        }
                        
                        if product_info:
                            rule['antecedent_names'] = [
                                product_info.get(pid, {}).get('product_name', pid)
                                for pid in rule['antecedent']
                            ]
                            rule['consequent_names'] = [
                                product_info.get(pid, {}).get('product_name', pid)
                                for pid in rule['consequent']
                            ]
                        else:
                            rule['antecedent_names'] = rule['antecedent']
                            rule['consequent_names'] = rule['consequent']
                        
                        rules.append(rule)
        
        rules.sort(key=lambda x: x['lift'], reverse=True)
        return rules


def run_association_analysis(transactions: List[List[str]], 
                            product_info: Dict[str, Dict[str, str]],
                            algorithm: str = 'apriori',
                            min_support: float = 0.01,
                            min_confidence: float = 0.3,
                            min_lift: float = 1.0,
                            max_length: int = 3) -> List[Dict[str, Any]]:
    """
    执行关联规则分析的统一入口
    
    Args:
        transactions: 交易数据列表
        product_info: 商品信息映射
        algorithm: 算法选择 ('apriori' 或 'fpgrowth')
        min_support: 最小支持度
        min_confidence: 最小置信度
        min_lift: 最小提升度
        max_length: 规则最大长度
        
    Returns:
        关联规则列表
    """
    logger.info(f"使用 {algorithm} 算法进行关联规则分析")
    
    if algorithm.lower() == 'fpgrowth':
        algo = FPGrowthAlgorithm(
            min_support=min_support,
            min_confidence=min_confidence,
            min_lift=min_lift,
            max_length=max_length
        )
        frequent_itemsets, total = algo.fit(transactions)
    else:
        algo = AprioriAlgorithm(
            min_support=min_support,
            min_confidence=min_confidence,
            min_lift=min_lift,
            max_length=max_length
        )
        frequent_itemsets, total = algo.fit(transactions)
    
    rules = algo.generate_rules(frequent_itemsets, total, product_info)
    
    return rules