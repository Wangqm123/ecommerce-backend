-- ============================================================
-- 电商销售数据智能分析平台 - 建表 DDL
-- 数据库: ecommerce_analysis | 字符集: utf8mb4
-- ============================================================

CREATE TABLE IF NOT EXISTS `products` (
    `product_id`   BIGINT       NOT NULL,
    `product_name` VARCHAR(255) NOT NULL,
    `category`     VARCHAR(255) NOT NULL,
    `unit_price`   DECIMAL(14,2) NOT NULL,
    PRIMARY KEY (`product_id`),
    INDEX `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `users` (
    `user_id`  BIGINT       NOT NULL,
    `province` VARCHAR(100) NOT NULL,
    `city`     VARCHAR(100) DEFAULT '',
    PRIMARY KEY (`user_id`),
    INDEX `idx_province` (`province`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `orders` (
    `order_id`     VARCHAR(50)   NOT NULL,
    `product_id`   BIGINT        NOT NULL,
    `user_id`      BIGINT        NOT NULL,
    `quantity`     INT           NOT NULL,
    `unit_price`   DECIMAL(14,2) NOT NULL,
    `total_amount` DECIMAL(14,2) NOT NULL,
    `order_date`   DATE          NOT NULL,
    `order_status` VARCHAR(20)   DEFAULT 'completed',
    PRIMARY KEY (`order_id`, `product_id`),
    INDEX `idx_order_date` (`order_date`),
    INDEX `idx_product_id` (`product_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_order_status` (`order_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `order_summary` (
    `order_id`     VARCHAR(50)   NOT NULL,
    `user_id`      BIGINT        NOT NULL,
    `total_amount` DECIMAL(14,2) NOT NULL,
    `item_count`   INT           NOT NULL,
    `order_date`   DATE          NOT NULL,
    PRIMARY KEY (`order_id`),
    INDEX `idx_os_user_id` (`user_id`),
    INDEX `idx_os_order_date` (`order_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `import_batches` (
    `id`           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `file_name`    VARCHAR(255) NOT NULL,
    `file_size`    BIGINT       DEFAULT 0,
    `total_rows`   INT          DEFAULT 0,
    `success_rows` INT          DEFAULT 0,
    `failed_rows`  INT          DEFAULT 0,
    `status`       ENUM('processing','completed','failed') DEFAULT 'processing',
    `error_log`    TEXT,
    `imported_at`  DATETIME     DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `rfm_compute_tasks` (
    `id`            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `batch_uuid`    VARCHAR(36)  NOT NULL,
    `status`        ENUM('pending','running','completed','failed') DEFAULT 'pending',
    `params`        JSON,
    `user_count`    INT          DEFAULT 0,
    `error_message` TEXT,
    `created_at`    DATETIME     DEFAULT CURRENT_TIMESTAMP,
    `started_at`    DATETIME,
    `completed_at`  DATETIME,
    UNIQUE KEY `uk_rfm_batch` (`batch_uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `rfm_results` (
    `id`            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `user_id`       BIGINT        NOT NULL,
    `recency`       INT           NOT NULL,
    `frequency`     INT           NOT NULL,
    `monetary`      DECIMAL(14,2) NOT NULL,
    `r_score`       INT           NOT NULL,
    `f_score`       INT           NOT NULL,
    `m_score`       INT           NOT NULL,
    `rfm_segment`   VARCHAR(30),
    `rfm_group`     VARCHAR(10),
    `compute_batch` VARCHAR(36)   NOT NULL,
    INDEX `idx_rfmres_batch` (`compute_batch`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `association_tasks` (
    `id`            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `batch_uuid`    VARCHAR(36)  NOT NULL,
    `status`        ENUM('pending','running','completed','failed') DEFAULT 'pending',
    `params`        JSON,
    `total_rules`   INT          DEFAULT 0,
    `error_message` TEXT,
    `retry_count`   INT          DEFAULT 0,
    `max_retries`   INT          DEFAULT 2,
    `created_at`    DATETIME     DEFAULT CURRENT_TIMESTAMP,
    `started_at`    DATETIME,
    `completed_at`  DATETIME,
    UNIQUE KEY `uk_assoc_batch` (`batch_uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `association_rules` (
    `id`               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `antecedent`        VARCHAR(500) NOT NULL,
    `consequent`        VARCHAR(500) NOT NULL,
    `antecedent_names`  VARCHAR(800) NOT NULL,
    `consequent_names`  VARCHAR(800) NOT NULL,
    `support`           DECIMAL(8,6) NOT NULL,
    `confidence`        DECIMAL(8,6) NOT NULL,
    `lift`              DECIMAL(10,4) NOT NULL,
    `rule_type`         VARCHAR(20)  DEFAULT 'product',
    `compute_batch`     VARCHAR(36)  NOT NULL,
    `is_active`         TINYINT      DEFAULT 1,
    `expires_at`        DATETIME,
    `created_at`        DATETIME     DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_ar_batch` (`compute_batch`),
    INDEX `idx_ar_lift` (`lift`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `forecast_tasks` (
    `id`            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `batch_uuid`    VARCHAR(36)  NOT NULL,
    `status`        ENUM('pending','running','completed','failed') DEFAULT 'pending',
    `params`        JSON,
    `error_message` TEXT,
    `created_at`    DATETIME     DEFAULT CURRENT_TIMESTAMP,
    `started_at`    DATETIME,
    `completed_at`  DATETIME,
    UNIQUE KEY `uk_fc_batch` (`batch_uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `forecast_results` (
    `id`            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `product_id`    BIGINT       NOT NULL,
    `product_name`  VARCHAR(255) NOT NULL,
    `forecast_date` DATE         NOT NULL,
    `predicted_qty` INT          NOT NULL,
    `lower_bound`   INT,
    `upper_bound`   INT,
    `model_name`    VARCHAR(50),
    `compute_batch` VARCHAR(36)  NOT NULL,
    INDEX `idx_fr_batch` (`compute_batch`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 算法输入视图
CREATE OR REPLACE VIEW `v_rfm_input` AS
SELECT o.user_id, DATEDIFF(CURDATE(), MAX(o.order_date)) AS recency,
       COUNT(DISTINCT o.order_id) AS frequency, SUM(o.total_amount) AS monetary
FROM orders o WHERE o.order_status = 'completed' GROUP BY o.user_id;

CREATE OR REPLACE VIEW `v_association_input` AS
SELECT o.order_id, o.product_id, p.product_name, p.category
FROM orders o JOIN products p ON o.product_id = p.product_id
WHERE o.order_status = 'completed' ORDER BY o.order_id;

CREATE OR REPLACE VIEW `v_forecast_input` AS
SELECT o.product_id, p.product_name, o.order_date,
       SUM(o.quantity) AS daily_quantity, SUM(o.total_amount) AS daily_sales
FROM orders o JOIN products p ON o.product_id = p.product_id
WHERE o.order_status = 'completed'
GROUP BY o.product_id, p.product_name, o.order_date
ORDER BY o.product_id, o.order_date;
