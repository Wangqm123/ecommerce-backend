import pymysql
import random
from datetime import datetime, timedelta
from config import Config

def generate_sample_data():
    conn = pymysql.connect(
        host=Config.DB_HOST, port=Config.DB_PORT,
        user=Config.DB_USER, password=Config.DB_PASSWORD,
        database=Config.DB_NAME
    )
    cursor = conn.cursor()
    
    # 清空旧数据
    cursor.execute("DELETE FROM orders")
    cursor.execute("DELETE FROM products")
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM association_rules")
    cursor.execute("DELETE FROM association_tasks")
    
    # 插入用户
    users = []
    for i in range(1, 101):
        cursor.execute("INSERT INTO users (username, create_time) VALUES (%s, %s)",
                       (f"user{i}", datetime.now() - timedelta(days=random.randint(0, 365))))
        users.append(cursor.lastrowid)
    
    # 插入商品（电子、服装、食品各5个）
    products = []
    product_data = [
        (1, "iPhone 15", "电子产品", 5999),
        (2, "MacBook Pro", "电子产品", 12999),
        (3, "AirPods", "电子产品", 1299),
        (4, "iPad", "电子产品", 3999),
        (5, "Apple Watch", "电子产品", 2999),
        (6, "T恤", "服装", 99),
        (7, "牛仔裤", "服装", 199),
        (8, "羽绒服", "服装", 599),
        (9, "连衣裙", "服装", 299),
        (10, "运动鞋", "服装", 399),
        (11, "牛奶", "食品", 60),
        (12, "面包", "食品", 20),
        (13, "巧克力", "食品", 50),
        (14, "咖啡", "食品", 80),
        (15, "薯片", "食品", 15)
    ]
    for pid, name, category, price in product_data:
        cursor.execute("INSERT INTO products (product_id, product_name, category, unit_price) VALUES (%s, %s, %s, %s)",
                       (pid, name, category, price))
        products.append(pid)
    
    # 生成订单（过去6个月，每个用户1~10单）
    provinces = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '南京']
    for user in users:
        for _ in range(random.randint(1, 10)):
            order_date = datetime.now() - timedelta(days=random.randint(0, 180))
            # 每个订单1~3件商品（扁平化结构，每个商品一行）
            selected = random.sample(products, k=random.randint(1, 3))
            for pid in selected:
                qty = random.randint(1, 3)
                cursor.execute("SELECT unit_price FROM products WHERE product_id=%s", (pid,))
                price = cursor.fetchone()[0]
                total_amount = price * qty
                cursor.execute("""
                    INSERT INTO orders (user_id, product_id, order_date, quantity, total_amount, province)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user, pid, order_date.strftime('%Y-%m-%d'), qty, total_amount, random.choice(provinces)))
    
    conn.commit()
    cursor.close()
    conn.close()
    print("测试数据生成完成！")

if __name__ == "__main__":
    generate_sample_data()
