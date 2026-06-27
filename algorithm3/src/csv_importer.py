# -*- coding: utf-8 -*-
"""
CSV数据导入脚本
支持从CSV文件导入销售数据到数据库
"""

import os
import sys
import csv
import json
import logging
import argparse
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import DB_CONFIG
from src.database import DatabaseManager


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger(__name__)


def _try_open_file(file_path):
    """
    尝试用多种编码打开文件
    支持: utf-8, gbk, gb2312, cp1252
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件对象和使用的编码
    """
    encodings = ['utf-8-sig', 'gbk', 'gb2312', 'cp1252', 'utf-8']
    
    for encoding in encodings:
        try:
            f = open(file_path, 'r', encoding=encoding)
            # 尝试读取第一行来验证编码
            f.readline()
            f.seek(0)
            return f, encoding
        except UnicodeDecodeError:
            continue
        except Exception as e:
            continue
    
    raise ValueError(f"无法识别文件编码，请尝试手动指定编码。文件: {file_path}")


def preprocess_data(data):
    """
    数据预处理：清洗和过滤无效数据
    
    Args:
        data: 原始数据列表
        
    Returns:
        清洗后的数据列表和处理统计报告
    """
    logger = logging.getLogger(__name__)
    
    report = {
        'total_records': len(data),
        'valid_records': 0,
        'filtered_records': 0,
        'filter_reasons': {
            'empty_order_id': 0,
            'empty_product_id': 0,
            'empty_product_name': 0,
            'invalid_price': 0,
            'invalid_quantity': 0,
            'invalid_date': 0,
            'duplicate': 0,
            'other': 0
        },
        'stats': {
            'unique_orders': 0,
            'unique_products': 0,
            'unique_users': 0,
            'total_amount': 0.0
        }
    }
    
    cleaned_data = []
    seen_records = set()  # 用于去重
    
    for record in data:
        try:
            # 1. 检查关键字段是否为空
            if not record.get('order_id') or str(record['order_id']).strip() == '':
                report['filter_reasons']['empty_order_id'] += 1
                continue
            
            if not record.get('product_id') or str(record['product_id']).strip() == '':
                report['filter_reasons']['empty_product_id'] += 1
                continue
            
            if not record.get('product_name') or str(record['product_name']).strip() == '':
                report['filter_reasons']['empty_product_name'] += 1
                continue
            
            # 2. 检查价格是否有效
            if record.get('unit_price') is None or record['unit_price'] <= 0:
                report['filter_reasons']['invalid_price'] += 1
                continue
            
            # 3. 检查数量是否有效
            if record.get('quantity') is None or record['quantity'] <= 0:
                report['filter_reasons']['invalid_quantity'] += 1
                continue
            
            # 4. 检查日期格式是否有效
            order_date = record.get('order_date', '')
            if order_date and not _is_valid_date(order_date):
                report['filter_reasons']['invalid_date'] += 1
                continue
            
            # 5. 去重检查
            record_key = f"{record['order_id']}_{record['product_id']}"
            if record_key in seen_records:
                report['filter_reasons']['duplicate'] += 1
                continue
            seen_records.add(record_key)
            
            # 6. 标准化数据
            record = _normalize_record(record)
            
            # 7. 添加到清洗后的数据
            cleaned_data.append(record)
            report['valid_records'] += 1
            report['stats']['total_amount'] += record.get('total_amount', 0)
            
        except Exception as e:
            report['filter_reasons']['other'] += 1
            logger.debug(f"记录处理异常: {e}")
            continue
    
    # 统计唯一值
    report['stats']['unique_orders'] = len(set(r['order_id'] for r in cleaned_data))
    report['stats']['unique_products'] = len(set(r['product_id'] for r in cleaned_data))
    report['stats']['unique_users'] = len(set(r['user_id'] for r in cleaned_data if r['user_id'] > 0))
    
    report['filtered_records'] = report['total_records'] - report['valid_records']
    
    # 打印报告
    _print_preprocess_report(report)
    
    return cleaned_data, report


def _is_valid_date(date_str):
    """检查日期字符串是否有效"""
    if not date_str:
        return False
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def _normalize_record(record):
    """标准化记录数据"""
    # 确保 product_id 是整数
    if isinstance(record['product_id'], str) and record['product_id'].isdigit():
        record['product_id'] = int(record['product_id'])
    elif not isinstance(record['product_id'], int):
        record['product_id'] = hash(str(record['product_id'])) % 1000000
    
    # 确保 user_id 是整数
    if not isinstance(record['user_id'], int):
        record['user_id'] = int(record['user_id']) if str(record['user_id']).isdigit() else 0
    
    # 确保价格和金额是浮点数
    record['unit_price'] = float(record['unit_price'])
    record['quantity'] = int(record['quantity'])
    record['total_amount'] = float(record.get('total_amount', record['unit_price'] * record['quantity']))
    
    # 确保字符串字段不为空
    record['product_name'] = str(record.get('product_name', '')).strip() or '未命名商品'
    record['category'] = str(record.get('category', '')).strip() or '未分类'
    record['province'] = str(record.get('province', '')).strip() or '未知地区'
    record['city'] = str(record.get('city', '')).strip()
    record['order_status'] = str(record.get('order_status', '')).strip() or 'completed'
    
    return record


def _print_preprocess_report(report):
    """打印数据预处理报告"""
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("📊 数据预处理报告")
    logger.info("=" * 60)
    logger.info(f"原始记录数: {report['total_records']}")
    logger.info(f"有效记录数: {report['valid_records']}")
    logger.info(f"过滤记录数: {report['filtered_records']}")
    logger.info(f"数据有效率: {report['valid_records'] / report['total_records'] * 100:.2f}%")
    logger.info("-" * 60)
    logger.info("📋 过滤原因统计:")
    for reason, count in report['filter_reasons'].items():
        if count > 0:
            reason_desc = {
                'empty_order_id': '订单ID为空',
                'empty_product_id': '商品ID为空',
                'empty_product_name': '商品名称为空',
                'invalid_price': '价格无效',
                'invalid_quantity': '数量无效',
                'invalid_date': '日期无效',
                'duplicate': '重复记录',
                'other': '其他原因'
            }
            logger.info(f"  - {reason_desc.get(reason, reason)}: {count} 条")
    logger.info("-" * 60)
    logger.info("📈 数据统计:")
    logger.info(f"  - 唯一订单数: {report['stats']['unique_orders']}")
    logger.info(f"  - 唯一商品数: {report['stats']['unique_products']}")
    logger.info(f"  - 唯一用户数: {report['stats']['unique_users']}")
    logger.info(f"  - 总金额: {report['stats']['total_amount']:.2f}")
    logger.info("=" * 60)


def parse_csv_file(file_path):
    """
    解析CSV文件，支持多种格式（包括 Online Retail 数据集）
    
    Args:
        file_path: CSV文件路径
        
    Returns:
        数据列表，每个元素是一行数据的字典
    """
    logger = logging.getLogger(__name__)
    
    # 支持的列名（中英文 + 常见数据集格式）
    column_mapping = {
        'order_id': ['order_id', '订单ID', '订单编号', 'InvoiceNo', 'invoice', 'order', '订单号', '交易号'],
        'product_id': ['product_id', '商品ID', 'StockCode', 'stock_code', '商品代码', '产品ID', 'item_id'],
        'product_name': ['product_name', '商品名称', '产品名称', 'Description', 'description', '商品描述', '名称'],
        'category': ['category', '品类', '类别', '分类', 'Category', 'category_name', '商品类别'],
        'unit_price': ['unit_price', '单价', '价格', 'UnitPrice', 'unit_price', 'price', '售价'],
        'quantity': ['quantity', '数量', '购买数量', 'Quantity', 'qty', '购买量'],
        'total_amount': ['total_amount', '金额', '总价', '订单金额', 'Amount', 'amount', '总计'],
        'user_id': ['user_id', '用户ID', 'CustomerID', 'customer_id', '客户ID', '买家ID'],
        'province': ['province', '省份', 'Province', 'State', 'state', '地区', 'Country', 'country', '国家'],
        'city': ['city', '城市', 'City', 'city_name', '城市名称'],
        'order_date': ['order_date', '订单日期', '日期', 'InvoiceDate', 'invoice_date', '交易日期', '时间'],
        'order_status': ['order_status', '订单状态', '状态', 'Status', 'status']
    }
    
    # 核心必需字段（最少需要这些字段）
    core_required_columns = ['order_id', 'product_id', 'product_name', 'unit_price', 'quantity']
    
    # 可选字段
    optional_columns = ['total_amount', 'user_id', 'category', 'province', 'city', 'order_date', 'order_status']
    
    data = []
    
    # 尝试多种编码打开文件
    f, encoding = _try_open_file(file_path)
    logger.info(f"使用编码 {encoding} 读取文件")
    
    try:
        reader = csv.reader(f)
        header = next(reader)
        
        # 标准化表头
        normalized_header = {}
        for idx, col in enumerate(header):
            col_stripped = col.strip()
            for standard_name, aliases in column_mapping.items():
                # 支持大小写不敏感匹配
                if col_stripped.lower() in [a.lower() for a in aliases]:
                    normalized_header[standard_name] = idx
                    break
        
        # 验证核心必需字段
        missing_core = [col for col in core_required_columns if col not in normalized_header]
        if missing_core:
            raise ValueError(f"CSV文件缺少核心必需字段: {', '.join(missing_core)}\n当前表头: {header}")
        
        logger.info(f"CSV表头解析完成，识别到 {len(normalized_header)} 个字段")
        logger.info(f"映射关系: {json.dumps(normalized_header, ensure_ascii=False)}")
        
        # 检查可选字段（不输出日志）
        missing_optional = [col for col in optional_columns if col not in normalized_header]
        
        # 解析数据行
        row_num = 1
        failed_reasons = {}  # 收集失败原因统计
        for row in reader:
            row_num += 1
            try:
                # 解析核心字段
                order_id = str(row[normalized_header['order_id']]).strip()
                product_id = str(row[normalized_header['product_id']]).strip()
                product_name = row[normalized_header['product_name']].strip()
                unit_price = float(row[normalized_header['unit_price']].strip())
                quantity = int(row[normalized_header['quantity']].strip())
                
                # 解析可选字段（支持默认值）
                # 处理 total_amount（如果缺失则自动计算）
                if 'total_amount' in normalized_header:
                    total_amount = float(row[normalized_header['total_amount']].strip())
                else:
                    total_amount = round(unit_price * quantity, 2)
                
                # 处理 user_id（如果缺失则使用默认值）
                if 'user_id' in normalized_header:
                    user_id_val = str(row[normalized_header['user_id']]).strip()
                    if user_id_val and user_id_val.isdigit():
                        user_id = int(user_id_val)
                    else:
                        user_id = 0  # 未知用户
                else:
                    user_id = 0
                
                # 处理 category（如果缺失则从商品名称推断）
                if 'category' in normalized_header:
                    category = row[normalized_header['category']].strip()
                else:
                    # 尝试从商品名称推断类别
                    category = _infer_category(product_name)
                
                # 处理 province（如果缺失则使用默认值）
                if 'province' in normalized_header:
                    province = row[normalized_header['province']].strip()
                    if not province:
                        province = '未知地区'
                else:
                    province = '未知地区'
                
                # 处理 city
                if 'city' in normalized_header:
                    city = row[normalized_header['city']].strip()
                else:
                    city = ''
                
                # 处理 order_date
                if 'order_date' in normalized_header:
                    order_date = row[normalized_header['order_date']].strip()
                    # 尝试解析不同格式的日期
                    order_date = _parse_date(order_date)
                else:
                    order_date = datetime.now().strftime('%Y-%m-%d')
                
                # 处理 order_status
                if 'order_status' in normalized_header:
                    order_status = row[normalized_header['order_status']].strip().lower()
                    # 标准化状态值
                    if order_status in ['completed', 'success', 'finished', 'ok']:
                        order_status = 'completed'
                    elif order_status in ['cancelled', 'cancel', 'failed', 'refund']:
                        order_status = 'cancelled'
                    else:
                        order_status = 'completed'
                else:
                    order_status = 'completed'
                
                # 验证数据
                if not order_id:
                    raise ValueError("order_id 为空")
                if unit_price <= 0:
                    raise ValueError("单价必须大于0")
                if quantity == 0:
                    raise ValueError("数量不能为0")
                # 处理退货记录（数量为负数）
                if quantity < 0:
                    order_status = 'cancelled'  # 标记为取消状态
                    quantity = abs(quantity)  # 取绝对值保存
                
                record = {
                    'order_id': order_id,
                    'product_id': product_id if product_id.isdigit() else hash(product_id) % 1000000,
                    'product_name': product_name if product_name else f'商品_{product_id}',
                    'category': category if category else '未分类',
                    'unit_price': unit_price,
                    'quantity': quantity,
                    'total_amount': total_amount,
                    'user_id': user_id,
                    'province': province,
                    'city': city,
                    'order_date': order_date,
                    'order_status': order_status
                }
                
                data.append(record)
                
            except Exception as e:
                # 收集失败原因统计
                reason = str(e)
                failed_reasons[reason] = failed_reasons.get(reason, 0) + 1
                continue
    finally:
        f.close()
    
    # 输出简洁的统计信息
    total_rows = row_num - 1  # 减去表头
    success_count = len(data)
    failed_count = total_rows - success_count
    
    logger.info(f"CSV解析完成: 总行数={total_rows}, 成功={success_count}, 失败={failed_count}")
    
    # 只在有失败时输出失败原因汇总
    if failed_count > 0:
        logger.info("失败原因汇总:")
        for reason, count in failed_reasons.items():
            logger.info(f"  - {reason}: {count} 条")
    
    return data


def _infer_category(product_name):
    """
    从商品名称推断类别
    
    Args:
        product_name: 商品名称
        
    Returns:
        推断的类别
    """
    product_name_lower = product_name.lower()
    
    category_keywords = {
        '电子产品': ['phone', 'mobile', 'iphone', 'samsung', 'xiaomi', 'huawei', 'ipad', 'tablet', 
                    'laptop', 'computer', 'headphone', 'earphone', 'speaker', 'charger', 'battery'],
        '服装': ['shirt', 't-shirt', 'pants', 'shoes', 'dress', 'skirt', 'jacket', 'coat', 
                'sweater', 'socks', 'hat', 'cap', 'jeans', 'shorts'],
        '食品': ['food', 'snack', 'drink', 'beverage', 'chocolate', 'candy', 'cookie', 'biscuit',
                'coffee', 'tea', 'milk', 'bread', 'fruit', 'vegetable'],
        '家居': ['home', 'furniture', 'table', 'chair', 'bed', 'sofa', 'lamp', 'curtain',
                'pillow', 'blanket', 'towel', 'kitchen', 'bathroom'],
        '图书': ['book', 'books', 'magazine', 'novel', 'textbook', 'dictionary', 'comic'],
        '玩具': ['toy', 'toys', 'game', 'games', 'doll', 'car', 'train', 'puzzle'],
        '美妆': ['cosmetic', 'makeup', 'lipstick', 'perfume', 'skincare', 'cream', 'lotion'],
        '运动': ['sports', 'sport', 'running', 'basketball', 'football', 'tennis', 'gym', 'yoga']
    }
    
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in product_name_lower:
                return category
    
    return '其他'


def _parse_date(date_str):
    """
    尝试解析多种日期格式
    
    Args:
        date_str: 日期字符串
        
    Returns:
        标准化的日期字符串 (YYYY-MM-DD)
    """
    import re
    
    # 移除引号和空格
    date_str = date_str.strip().strip('\'"')
    
    # 尝试常见格式
    date_patterns = [
        r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})',  # YYYY-MM-DD 或 YYYY/MM/DD
        r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})',  # MM-DD-YYYY 或 DD/MM/YYYY
        r'(\d{4})(\d{2})(\d{2})',              # YYYYMMDD
        r'(\d{1,2}) (\w+) (\d{4})'             # DD Month YYYY
    ]
    
    for pattern in date_patterns:
        match = re.match(pattern, date_str)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                # 判断是否是 YYYY-MM-DD 格式
                if len(groups[0]) == 4:
                    return f"{groups[0]}-{groups[1].zfill(2)}-{groups[2].zfill(2)}"
                else:
                    # DD-MM-YYYY 或 MM-DD-YYYY，尝试判断
                    if int(groups[0]) > 12:
                        # DD-MM-YYYY
                        return f"{groups[2]}-{groups[1].zfill(2)}-{groups[0].zfill(2)}"
                    else:
                        # MM-DD-YYYY
                        return f"{groups[2]}-{groups[0].zfill(2)}-{groups[1].zfill(2)}"
    
    # 如果无法解析，返回今天日期
    return datetime.now().strftime('%Y-%m-%d')


def import_to_database(data, batch_size=1000):
    """
    将数据导入数据库
    
    Args:
        data: 数据列表
        batch_size: 批量插入大小
        
    Returns:
        成功插入的记录数
    """
    logger = logging.getLogger(__name__)
    
    db_manager = DatabaseManager(DB_CONFIG)
    
    try:
        db_manager.connect()
        conn = db_manager.connection
        
        cursor = conn.cursor()
        
        # 禁用外键检查以提高导入速度
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        success_count = 0
        failed_count = 0
        
        # 批量插入商品
        products_data = {}
        for record in data:
            product_id = record['product_id']
            if product_id not in products_data:
                products_data[product_id] = {
                    'product_name': record['product_name'],
                    'category': record['category'],
                    'unit_price': record['unit_price']
                }
        
        product_sql = """
            INSERT INTO products (product_id, product_name, category, unit_price)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE product_name = VALUES(product_name), 
                                   category = VALUES(category),
                                   unit_price = VALUES(unit_price)
        """
        
        product_values = [(k, v['product_name'], v['category'], v['unit_price']) 
                          for k, v in products_data.items()]
        
        cursor.executemany(product_sql, product_values)
        
        # 批量插入用户
        users_data = {}
        for record in data:
            user_id = record['user_id']
            if user_id not in users_data:
                users_data[user_id] = {
                    'province': record['province'],
                    'city': record['city']
                }
        
        # 检查 users 表是否包含 username 字段
        cursor.execute("SHOW COLUMNS FROM users LIKE 'username'")
        has_username = cursor.fetchone() is not None
        
        if has_username:
            user_sql = """
                INSERT INTO users (user_id, username, province, city)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE province = VALUES(province), 
                                       city = VALUES(city)
            """
            user_values = [(k, f'user_{k}', v['province'], v['city']) for k, v in users_data.items()]
        else:
            user_sql = """
                INSERT INTO users (user_id, province, city)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE province = VALUES(province), 
                                       city = VALUES(city)
            """
            user_values = [(k, v['province'], v['city']) for k, v in users_data.items()]
        
        cursor.executemany(user_sql, user_values)
        
        # 批量插入订单
        order_sql = """
            INSERT INTO orders (order_id, product_id, user_id, quantity, 
                               unit_price, total_amount, order_date, 
                               order_status, province, city)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = VALUES(quantity),
                                   unit_price = VALUES(unit_price),
                                   total_amount = VALUES(total_amount),
                                   order_status = VALUES(order_status)
        """
        
        # 分批插入
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            order_values = []
            for record in batch:
                order_values.append((
                    record['order_id'],
                    record['product_id'],
                    record['user_id'],
                    record['quantity'],
                    record['unit_price'],
                    record['total_amount'],
                    record['order_date'],
                    record['order_status'],
                    record['province'],
                    record['city']
                ))
            
            cursor.executemany(order_sql, order_values)
            success_count += len(order_values)
        
        # 恢复外键检查
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        conn.commit()
        cursor.close()
        
        logger.info(f"数据导入完成: 商品={len(product_values)}, 用户={len(user_values)}, 订单={success_count}")
        return success_count
        
    except Exception as e:
        logger.error(f"数据导入失败: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return 0
    finally:
        db_manager.close()


def main():
    """主函数"""
    logger = setup_logging()
    
    parser = argparse.ArgumentParser(description='CSV数据导入工具')
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 导入命令
    import_parser = subparsers.add_parser('import', help='导入CSV数据到数据库')
    import_parser.add_argument('file', help='CSV文件路径')
    import_parser.add_argument('--batch-size', type=int, default=1000, help='批量插入大小')
    
    # 验证命令
    validate_parser = subparsers.add_parser('validate', help='验证CSV文件格式')
    validate_parser.add_argument('file', help='CSV文件路径')
    
    args = parser.parse_args()
    
    if args.command == 'import':
        logger.info(f"开始导入CSV文件: {args.file}")
        try:
            # 1. 解析CSV文件
            raw_data = parse_csv_file(args.file)
            
            if not raw_data:
                logger.warning("CSV文件中没有有效数据")
                return
            
            # 2. 数据预处理（清洗和过滤）
            cleaned_data, report = preprocess_data(raw_data)
            
            if not cleaned_data:
                logger.warning("预处理后没有有效数据")
                return
            
            # 3. 导入数据库
            import_to_database(cleaned_data, args.batch_size)
            
            logger.info(f"✅ 导入完成！共处理 {report['total_records']} 条记录，成功导入 {report['valid_records']} 条")
            
        except Exception as e:
            logger.error(f"导入失败: {e}")
            sys.exit(1)
    
    elif args.command == 'validate':
        logger.info(f"验证CSV文件: {args.file}")
        try:
            data = parse_csv_file(args.file)
            logger.info(f"文件验证通过，共 {len(data)} 条有效记录")
        except Exception as e:
            logger.error(f"文件验证失败: {e}")
            sys.exit(1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()