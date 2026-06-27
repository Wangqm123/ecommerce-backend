# -*- coding: utf-8 -*-
"""
数据库初始化脚本
用于创建表结构
"""

import os
import sys
import pymysql
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def execute_sql_file(filepath):
    """执行 SQL 文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    statements = []
    current_statement = []
    in_delimiter = False
    current_delimiter = ';'
    
    for line in sql_content.split('\n'):
        if line.strip().upper().startswith('DELIMITER'):
            parts = line.strip().split()
            if len(parts) > 1:
                current_delimiter = parts[1]
                in_delimiter = True
            continue
        
        if current_delimiter in line and not in_delimiter:
            current_statement.append(line)
            statements.append('\n'.join(current_statement))
            current_statement = []
        else:
            current_statement.append(line)
    
    if current_statement:
        statements.append('\n'.join(current_statement))
    
    return statements

def main():
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'ecommerce_analysis'),
        'charset': 'utf8mb4'
    }
    
    print("Database config:")
    print("  Host: %s" % db_config['host'])
    print("  Port: %d" % db_config['port'])
    print("  Database: %s" % db_config['database'])
    print("  User: %s" % db_config['user'])
    
    try:
        conn = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            charset='utf8mb4'
        )
        
        cursor = conn.cursor()
        
        cursor.execute("CREATE DATABASE IF NOT EXISTS %s CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci" % db_config['database'])
        print("OK: Database %s created or exists" % db_config['database'])
        
        cursor.execute("USE %s" % db_config['database'])
        print("OK: Selected database %s" % db_config['database'])
        
        sql_file = os.path.join(os.path.dirname(__file__), 'src/sql/schema.sql')
        
        if not os.path.exists(sql_file):
            print("ERROR: SQL file not found: %s" % sql_file)
            sys.exit(1)
        
        statements = execute_sql_file(sql_file)
        print("OK: Read %d SQL statements" % len(statements))
        
        for i, stmt in enumerate(statements, 1):
            stmt = stmt.strip()
            if not stmt or stmt.startswith('--'):
                continue
            try:
                cursor.execute(stmt)
                conn.commit()
                print("OK: Executed statement %d" % i)
            except Exception as e:
                print("ERROR: Failed to execute statement %d: %s" % (i, e))
                conn.rollback()
        
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print("\nOK: Created %d tables:" % len(tables))
        for table in tables:
            print("  - %s" % table[0])
        
        cursor.close()
        conn.close()
        
        print("\nDatabase initialization completed successfully!")
        
    except Exception as e:
        print("\nERROR: Database connection or execution failed: %s" % e)
        sys.exit(1)

if __name__ == '__main__':
    main()