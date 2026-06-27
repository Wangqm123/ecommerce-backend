# -*- coding: utf-8 -*-
"""
生成示例数据脚本
用于生成测试用的CSV文件
"""

import os
import sys
import csv
import random
import logging
import argparse
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger(__name__)


def generate_sample_csv(output_path, count=100):
    """
    生成示例CSV文件（用于测试）
    
    Args:
        output_path: 输出文件路径
        count: 生成订单数，每个订单包含多个商品
    """
    logger = logging.getLogger(__name__)
    
    categories = ['电子产品', '服装', '食品', '家居', '图书']
    products = {
        '电子产品': ['iPhone 15 Pro', 'AirPods Pro', 'iPad Air', 'MacBook Pro', 'Apple Watch', '华为Mate 60', '小米14', 'OPPO Find X7'],
        '服装': ['T恤', '牛仔裤', '运动鞋', '外套', '连衣裙', '衬衫', '卫衣', '休闲裤'],
        '食品': ['牛奶', '面包', '水果', '零食', '饮料', '饼干', '巧克力', '坚果'],
        '家居': ['床上用品', '厨房用品', '清洁用品', '装饰品', '收纳用品', '灯具', '窗帘', '地毯'],
        '图书': ['小说', '科技书籍', '儿童读物', '工具书', '杂志', '漫画', '传记', '历史']
    }
    
    # 预定义商品ID映射
    product_id_map = {}
    prod_id = 1
    for cat, prods in products.items():
        for prod in prods:
            product_id_map[(cat, prod)] = prod_id
            prod_id += 1
    
    # 预设商品关联组合（用于生成关联规则）
    product_pairs = [
        ('iPhone 15 Pro', 'AirPods Pro'),
        ('iPhone 15 Pro', 'Apple Watch'),
        ('MacBook Pro', 'iPad Air'),
        ('MacBook Pro', 'Apple Watch'),
        ('T恤', '牛仔裤'),
        ('运动鞋', '运动裤'),
        ('面包', '牛奶'),
        ('零食', '饮料'),
        ('床上用品', '窗帘'),
        ('厨房用品', '清洁用品'),
        ('小说', '杂志'),
        ('科技书籍', '工具书')
    ]
    
    provinces = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '南京']
    cities = {
        '北京': ['朝阳区', '海淀区', '西城区'],
        '上海': ['浦东新区', '徐汇区', '静安区'],
        '广州': ['天河区', '越秀区', '海珠区'],
        '深圳': ['南山区', '福田区', '宝安区'],
        '杭州': ['西湖区', '拱墅区', '滨江区'],
        '成都': ['锦江区', '武侯区', '高新区'],
        '武汉': ['武昌区', '汉口区', '汉阳'],
        '南京': ['玄武区', '秦淮区', '鼓楼区']
    }
    
    # 生成日期范围（最近一年）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    total_records = 0
    
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # 写入表头
        writer.writerow(['order_id', 'product_id', 'product_name', 'category', 
                         'unit_price', 'quantity', 'total_amount', 
                         'user_id', 'province', 'city', 'order_date', 'order_status'])
        
        for order_idx in range(count):
            order_id = f'ORD{20250000 + order_idx}'
            user_id = random.randint(10000, 99999)
            province = random.choice(provinces)
            city = random.choice(cities[province])
            order_date = start_date + timedelta(days=random.randint(0, 365))
            order_date_str = order_date.strftime('%Y-%m-%d')
            order_status = 'completed' if random.random() > 0.05 else 'cancelled'
            
            # 每个订单包含2-5个商品
            num_items = random.randint(2, 5)
            added_products = set()
            
            for _ in range(num_items):
                # 尝试使用预定义的商品组合
                available_items = []
                for pair in product_pairs:
                    if pair[0] in added_products and pair[1] not in added_products:
                        available_items.append(pair[1])
                    elif pair[1] in added_products and pair[0] not in added_products:
                        available_items.append(pair[0])
                
                if available_items and random.random() > 0.3:
                    item = random.choice(available_items)
                else:
                    # 随机选择商品
                    category = random.choice(categories)
                    item = random.choice(products[category])
                
                if item in added_products:
                    continue
                added_products.add(item)
                
                # 找到商品对应的分类
                category = None
                for cat, prods in products.items():
                    if item in prods:
                        category = cat
                        break
                
                product_id = product_id_map.get((category, item), random.randint(1, 100))
                unit_price = round(random.uniform(10, 5000), 2)
                quantity = random.randint(1, 5)
                total_amount = round(unit_price * quantity, 2)
                
                writer.writerow([
                    order_id, product_id, item, category,
                    unit_price, quantity, total_amount,
                    user_id, province, city, order_date_str, order_status
                ])
                total_records += 1
    
    logger.info(f"示例CSV文件已生成: {output_path}，共 {total_records} 条记录（{count} 个订单）")


def main():
    """主函数"""
    logger = setup_logging()
    
    parser = argparse.ArgumentParser(description='生成示例数据')
    parser.add_argument('output', help='输出文件路径')
    parser.add_argument('--count', type=int, default=100, help='生成订单数')
    
    args = parser.parse_args()
    
    generate_sample_csv(args.output, args.count)


if __name__ == '__main__':
    main()