-- 电商销售数据智能分析平台 - 数据库建表脚本
-- 执行顺序：先创建数据库，再执行此脚本

-- 1. 创建主表 - 商品表
CREATE TABLE IF NOT EXISTS products (
    product_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '商品ID',
    product_name VARCHAR(255) NOT NULL COMMENT '商品名称',
    category VARCHAR(100) NOT NULL COMMENT '品类',
    unit_price DECIMAL(10,2) NOT NULL COMMENT '单价',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品表';

-- 2. 创建主表 - 用户表
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    province VARCHAR(100) COMMENT '省份',
    city VARCHAR(100) COMMENT '城市',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_province (province)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 3. 创建主表 - 订单表
-- 一个订单(order_id)可以包含多个商品(product_id)
CREATE TABLE IF NOT EXISTS orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    order_id VARCHAR(50) NOT NULL COMMENT '订单编号',
    product_id BIGINT NOT NULL COMMENT '商品ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    quantity INT NOT NULL DEFAULT 1 COMMENT '数量',
    unit_price DECIMAL(10,2) NOT NULL COMMENT '单价',
    total_amount DECIMAL(14,2) NOT NULL COMMENT '金额',
    order_date DATE NOT NULL COMMENT '订单日期',
    order_status VARCHAR(20) DEFAULT 'completed' COMMENT '订单状态',
    province VARCHAR(100) COMMENT '省份',
    city VARCHAR(100) COMMENT '城市',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_order_id (order_id),
    INDEX idx_product_id (product_id),
    INDEX idx_user_id (user_id),
    INDEX idx_order_date (order_date),
    INDEX idx_order_status (order_status),
    INDEX idx_province (province),
    INDEX idx_order_user (order_id, user_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';

-- 4. 创建关联规则任务表
CREATE TABLE IF NOT EXISTS association_tasks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    batch_uuid VARCHAR(36) NOT NULL UNIQUE COMMENT '批次UUID',
    status ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending' COMMENT '任务状态',
    params JSON COMMENT '任务参数（JSON格式）',
    total_rules INT DEFAULT 0 COMMENT '生成规则数量',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    started_at DATETIME COMMENT '开始时间',
    completed_at DATETIME COMMENT '完成时间',
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='关联规则任务表';

-- 5. 创建关联规则结果表
CREATE TABLE IF NOT EXISTS association_rules (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    antecedent VARCHAR(500) NOT NULL COMMENT '前件商品ID，JSON数组',
    consequent VARCHAR(500) NOT NULL COMMENT '后件商品ID，JSON数组',
    antecedent_names VARCHAR(800) COMMENT '前件商品名称，JSON数组',
    consequent_names VARCHAR(800) COMMENT '后件商品名称，JSON数组',
    support DECIMAL(8,6) COMMENT '支持度',
    confidence DECIMAL(8,6) COMMENT '置信度',
    lift DECIMAL(10,4) COMMENT '提升度',
    rule_type VARCHAR(20) DEFAULT 'product' COMMENT '规则类型：product或category',
    compute_batch VARCHAR(36) COMMENT '批次UUID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_compute_batch (compute_batch),
    INDEX idx_rule_type (rule_type),
    INDEX idx_lift (lift)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='关联规则结果表';

-- 6. 创建RFM任务表
CREATE TABLE IF NOT EXISTS rfm_compute_tasks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    batch_uuid VARCHAR(36) NOT NULL UNIQUE COMMENT '批次UUID',
    status ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending' COMMENT '任务状态',
    params JSON COMMENT '任务参数（JSON格式）',
    user_count INT DEFAULT 0 COMMENT '用户数量',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    started_at DATETIME COMMENT '开始时间',
    completed_at DATETIME COMMENT '完成时间',
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='RFM计算任务表';

-- 7. 创建RFM结果表
CREATE TABLE IF NOT EXISTS rfm_results (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    recency INT COMMENT '最近消费距今天数',
    frequency INT COMMENT '消费频次（订单数）',
    monetary DECIMAL(14,2) COMMENT '消费总金额',
    r_score INT COMMENT 'R评分 1-5',
    f_score INT COMMENT 'F评分 1-5',
    m_score INT COMMENT 'M评分 1-5',
    rfm_segment VARCHAR(30) COMMENT '分层标签',
    rfm_group VARCHAR(10) COMMENT 'RFM组合',
    compute_batch VARCHAR(36) COMMENT '批次UUID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_user_id (user_id),
    INDEX idx_compute_batch (compute_batch),
    INDEX idx_rfm_segment (rfm_segment)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='RFM结果表';

-- 8. 创建预测任务表
CREATE TABLE IF NOT EXISTS forecast_tasks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    batch_uuid VARCHAR(36) NOT NULL UNIQUE COMMENT '批次UUID',
    status ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending' COMMENT '任务状态',
    params JSON COMMENT '任务参数（JSON格式）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    started_at DATETIME COMMENT '开始时间',
    completed_at DATETIME COMMENT '完成时间',
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预测任务表';

-- 9. 创建预测结果表
CREATE TABLE IF NOT EXISTS forecast_results (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    product_id BIGINT NOT NULL COMMENT '商品ID',
    product_name VARCHAR(255) COMMENT '商品名称',
    forecast_date DATE NOT NULL COMMENT '预测日期',
    predicted_qty INT COMMENT '预测销量',
    lower_bound INT COMMENT '下置信界',
    upper_bound INT COMMENT '上置信界',
    model_name VARCHAR(50) COMMENT '模型名称',
    compute_batch VARCHAR(36) COMMENT '批次UUID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_product_id (product_id),
    INDEX idx_forecast_date (forecast_date),
    INDEX idx_compute_batch (compute_batch)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预测结果表';

-- 10. 创建视图 - 关联规则输入视图
CREATE VIEW IF NOT EXISTS v_association_input AS
SELECT 
    o.order_id, 
    o.product_id, 
    p.product_name, 
    p.category
FROM orders o
JOIN products p ON o.product_id = p.product_id
WHERE o.order_status = 'completed';

-- 11. 创建视图 - RFM输入视图
CREATE VIEW IF NOT EXISTS v_rfm_input AS
SELECT
    o.user_id,
    o.order_id,
    o.order_date,
    o.total_amount
FROM orders o
WHERE o.order_status = 'completed';

-- 12. 创建视图 - 预测输入视图
CREATE VIEW IF NOT EXISTS v_forecast_input AS
SELECT 
    o.product_id, 
    p.product_name, 
    o.order_date,
    SUM(o.quantity) AS daily_quantity, 
    SUM(o.total_amount) AS daily_sales
FROM orders o
JOIN products p ON o.product_id = p.product_id
WHERE o.order_status = 'completed'
GROUP BY o.product_id, p.product_name, o.order_date;

-- 创建索引以提高查询性能
ALTER TABLE orders ADD INDEX idx_order_user (order_id, user_id);
ALTER TABLE orders ADD INDEX idx_order_date_status (order_date, order_status);

-- 创建存储过程：批量导入订单数据
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS batch_insert_orders(
    IN orderData JSON
)
BEGIN
    DECLARE i INT DEFAULT 0;
    DECLARE total INT;
    DECLARE order_item JSON;
    
    SET total = JSON_LENGTH(orderData);
    
    WHILE i < total DO
        SET order_item = JSON_EXTRACT(orderData, CONCAT('$[', i, ']'));
        
        -- 先插入商品（如果不存在）
        INSERT IGNORE INTO products (product_id, product_name, category, unit_price)
        VALUES (
            JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.product_id')),
            JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.product_name')),
            JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.category')),
            JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.unit_price'))
        );
        
        -- 先插入用户（如果不存在）
        INSERT IGNORE INTO users (user_id, province, city)
        VALUES (
            JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.user_id')),
            JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.province')),
            JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.city'))
        );
        
        -- 插入订单
        INSERT INTO orders (order_id, product_id, user_id, quantity, unit_price, total_amount, order_date, order_status, province, city)
        VALUES (
            JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.order_id')),
            JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.product_id')),
            JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.user_id')),
            JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.quantity')),
            JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.unit_price')),
            JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.total_amount')),
            JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.order_date')),
            COALESCE(JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.order_status')), 'completed'),
            JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.province')),
            JSON_UNQUOTE(JSON_EXTRACT(order_item, '$.city'))
        );
        
        SET i = i + 1;
    END WHILE;
END //
DELIMITER ;

-- 创建存储过程：获取待处理的关联规则任务
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS get_pending_association_task(
    OUT task_id BIGINT,
    OUT task_batch_uuid VARCHAR(36),
    OUT task_params JSON
)
BEGIN
    SELECT id, batch_uuid, params INTO task_id, task_batch_uuid, task_params
    FROM association_tasks
    WHERE status = 'pending'
    ORDER BY created_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED;
END //
DELIMITER ;

-- 创建存储过程：更新任务状态为运行中
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS update_task_running(
    IN task_batch_uuid VARCHAR(36)
)
BEGIN
    UPDATE association_tasks
    SET status = 'running', started_at = NOW()
    WHERE batch_uuid = task_batch_uuid AND status = 'pending';
END //
DELIMITER ;

-- 创建存储过程：更新任务状态为完成
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS update_task_completed(
    IN task_batch_uuid VARCHAR(36),
    IN task_total_rules INT
)
BEGIN
    UPDATE association_tasks
    SET status = 'completed', total_rules = task_total_rules, completed_at = NOW()
    WHERE batch_uuid = task_batch_uuid;
END //
DELIMITER ;

-- 创建存储过程：更新任务状态为失败
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS update_task_failed(
    IN task_batch_uuid VARCHAR(36)
)
BEGIN
    UPDATE association_tasks
    SET status = 'failed', completed_at = NOW()
    WHERE batch_uuid = task_batch_uuid;
END //
DELIMITER ;

-- 优化表
ANALYZE TABLE products;
ANALYZE TABLE users;
ANALYZE TABLE orders;
ANALYZE TABLE association_tasks;
ANALYZE TABLE association_rules;

-- 创建事件调度器（可选）
SET GLOBAL event_scheduler = ON;

-- 创建事件：每天凌晨清理7天前的失败任务
DELIMITER //
CREATE EVENT IF NOT EXISTS clean_failed_tasks
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP + INTERVAL 1 HOUR
DO
BEGIN
    DELETE FROM association_tasks WHERE status = 'failed' AND created_at < NOW() - INTERVAL 7 DAY;
    DELETE FROM rfm_compute_tasks WHERE status = 'failed' AND created_at < NOW() - INTERVAL 7 DAY;
    DELETE FROM forecast_tasks WHERE status = 'failed' AND created_at < NOW() - INTERVAL 7 DAY;
END //
DELIMITER ;

-- 显示创建的表
SHOW TABLES;

SELECT '数据库初始化完成' AS message;