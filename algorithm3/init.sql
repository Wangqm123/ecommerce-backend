-- 关联规则任务表
CREATE TABLE IF NOT EXISTS `association_tasks` (
    `id` INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    `batch_uuid` VARCHAR(36) NOT NULL COMMENT '批次UUID',
    `status` ENUM('pending','running','completed','failed') DEFAULT 'pending',
    `params` JSON COMMENT '任务参数: {startDate, endDate, minSupport, minConfidence, minLift, maxLength, maxRetries}',
    `total_rules` INT DEFAULT 0,
    `error_message` TEXT,
    `retry_count` INT DEFAULT 0 COMMENT '已重试次数',
    `max_retries` INT DEFAULT 2 COMMENT '最大重试次数',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `started_at` DATETIME,
    `completed_at` DATETIME,
    UNIQUE KEY `uk_batch_uuid` (`batch_uuid`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='关联规则计算任务';

-- 关联规则结果表
CREATE TABLE IF NOT EXISTS `association_rules` (
    `id` BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    `antecedent` VARCHAR(500) NOT NULL COMMENT '前件商品ID(JSON数组)',
    `consequent` VARCHAR(500) NOT NULL COMMENT '后件商品ID(JSON数组)',
    `antecedent_names` VARCHAR(800) NOT NULL COMMENT '前件商品名称(JSON数组)',
    `consequent_names` VARCHAR(800) NOT NULL COMMENT '后件商品名称(JSON数组)',
    `support` DECIMAL(8,6) NOT NULL,
    `confidence` DECIMAL(8,6) NOT NULL,
    `lift` DECIMAL(10,4) NOT NULL,
    `rule_type` VARCHAR(20) DEFAULT 'product' COMMENT 'product 或 category',
    `compute_batch` VARCHAR(36) NOT NULL,
    `is_active` TINYINT DEFAULT 1 COMMENT '是否有效',
    `expires_at` DATETIME DEFAULT NULL COMMENT '规则过期时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY `idx_batch` (`compute_batch`),
    KEY `idx_lift` (`lift`),
    KEY `idx_active` (`is_active`, `expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='关联规则结果';