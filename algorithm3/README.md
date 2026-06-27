<<<<<<< HEAD
# 电商销售数据智能分析平台 - 关联规则算法模块

> 基于 Apriori 和 FP-Growth 算法实现的商品关联规则推荐系统

## 项目简介

本模块负责电商销售数据智能分析平台的**关联产品推荐算法**，通过分析用户购买行为，挖掘商品之间的关联规则，为用户提供个性化商品推荐。

## 功能特性

- **双算法支持**：集成 Apriori 和 FP-Growth 两种经典关联规则挖掘算法
- **任务队列机制**：支持通过数据库任务队列进行异步计算
- **CSV数据导入**：支持 UTF-8、GBK、GB2312 等多种编码格式的 CSV 文件导入
- **智能数据预处理**：自动过滤无效数据，处理退货记录，去重降噪
- **配置灵活**：支持通过 `.env` 文件配置数据库连接和算法参数
- **完整的命令行接口**：提供导入、运行、服务启动等命令

## 技术栈

| 分类 | 技术 | 版本 |
|------|------|------|
| 语言 | Python | 3.8+ |
| 数据库 | MySQL | 8.0+ |
| 数据库驱动 | PyMySQL | 1.1.0+ |
| 配置管理 | python-dotenv | 1.0.0+ |

## 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone <仓库地址>
cd ALG3

# 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据库配置

创建 `.env` 文件并配置数据库连接：

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=ecommerce_analysis

# 服务配置
WORKER_SLEEP_INTERVAL=10
```

### 3. 初始化数据库

```bash
# 创建数据库表
python init_db.py
```

### 4. 导入数据

```bash
# 导入CSV文件（支持自动检测编码）
python run.py import data/sales_data.csv
```

### 5. 运行算法

```bash
# 单次运行（测试）
python run.py runonce --start-date 2025-01-01 --end-date 2025-12-31

# 或启动服务（持续轮询任务队列）
python run.py service --interval 10
```

## 项目结构

```
ALG3/
├── src/                    # 源代码目录
│   ├── sql/                # SQL脚本
│   │   └── schema.sql      # 数据库建表脚本
│   ├── association_algorithm.py  # 关联规则算法实现
│   ├── config.py           # 配置管理
│   ├── csv_importer.py     # CSV数据导入与预处理
│   ├── database.py         # 数据库操作模块
│   └── main.py             # 主程序入口
├── .env                    # 环境变量配置
├── init_db.py              # 数据库初始化脚本
├── requirements.txt        # 依赖列表
├── run.py                  # 命令行入口
├── start_service.bat       # Windows启动脚本
└── README.md               # 项目说明和部署文档
```

## 数据预处理

CSV 数据在导入数据库之前会经过多层预处理，确保数据质量：

### 清洗流程

```
CSV 解析 → 字段验证 → 数据预处理 → 数据库导入
```

### 过滤规则

| 过滤条件 | 处理方式 |
|----------|----------|
| 订单ID为空 | 丢弃整条记录 |
| 商品ID为空 | 丢弃整条记录 |
| 商品名称为空 | 丢弃整条记录 |
| 单价 <= 0 | 丢弃整条记录 |
| 数量 <= 0 | 丢弃整条记录 |
| 日期格式无效 | 丢弃整条记录 |
| 重复记录 | 同一订单同一商品仅保留一条 |
| 退货记录（数量为负） | 标记为 cancelled 状态 |

### 预处理报告示例

```
📊 数据预处理报告
============================================================
原始记录数: 488624
有效记录数: 480000
过滤记录数: 8624
数据有效率: 98.24%
------------------------------------------------------------
📋 过滤原因统计:
  - 无效价格: 4500 条
  - 无效数量: 2300 条
  - 重复记录: 1824 条
============================================================
```

### 预处理设计思想

1. **源头降噪**：在数据入库前过滤无效记录，避免脏数据影响关联规则分析结果
2. **退货处理**：将数量为负的退货记录单独标记，既保留信息又避免干扰正常购买模式
3. **去重防噪**：同一订单同一商品可能出现多次（如用户修改订单），去重保证购物篮准确性
4. **编码自适应**：自动识别 UTF-8、GBK、GB2312 等编码，兼容不同来源的数据文件
5. **失败原因汇总**：解析失败时统计失败原因，方便用户检查和修正原始数据

## 数据库设计

### 核心数据表

| 表名 | 说明 |
|------|------|
| `orders` | 订单表（支持一个订单包含多个商品） |
| `products` | 商品信息表 |
| `users` | 用户信息表 |
| `association_tasks` | 关联规则计算任务表 |
| `association_rules` | 关联规则结果表 |

### 关联规则结果表结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGINT | 主键ID |
| `antecedent` | VARCHAR(500) | 前件商品ID（JSON数组） |
| `consequent` | VARCHAR(500) | 后件商品ID（JSON数组） |
| `antecedent_names` | VARCHAR(800) | 前件商品名称（JSON数组） |
| `consequent_names` | VARCHAR(800) | 后件商品名称（JSON数组） |
| `support` | DECIMAL(8,6) | 支持度 |
| `confidence` | DECIMAL(8,6) | 置信度 |
| `lift` | DECIMAL(10,4) | 提升度 |
| `rule_type` | VARCHAR(20) | 规则类型（product/category） |
| `compute_batch` | VARCHAR(36) | 批次UUID |

## 命令行接口

### 命令列表

```bash
# 导入CSV数据
python run.py import <csv_file> [--batch-size N]

# 生成测试数据
python run.py generate <output_file> [--count N]

# 启动服务（持续轮询任务队列）
python run.py service [--interval N]

# 单次运行分析
python run.py runonce [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]
                      [--min-support 0.01] [--min-confidence 0.3]
                      [--min-lift 1.0] [--algorithm apriori|fpgrowth]

# 检查数据库连接
python run.py checkdb

# 显示配置信息
python src/main.py --show-config
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--start-date` | 开始日期 | 2025-01-01 |
| `--end-date` | 结束日期 | 2025-12-31 |
| `--min-support` | 最小支持度 | 0.01 |
| `--min-confidence` | 最小置信度 | 0.3 |
| `--min-lift` | 最小提升度 | 1.0 |
| `--algorithm` | 算法选择 | apriori |
| `--interval` | 轮询间隔（秒） | 10 |

## 算法参数说明

### 支持度 (Support)
- 定义：规则在所有交易中出现的频率
- 公式：`Support(A→B) = P(A∩B)`
- 范围：0 ~ 1

### 置信度 (Confidence)
- 定义：购买前件后购买后件的概率
- 公式：`Confidence(A→B) = P(B|A) = P(A∩B) / P(A)`
- 范围：0 ~ 1

### 提升度 (Lift)
- 定义：规则的关联强度
- 公式：`Lift(A→B) = P(B|A) / P(B)`
- 范围：> 0
- 解读：Lift > 1 表示正相关，Lift = 1 表示独立，Lift < 1 表示负相关

## 关联规则示例

```
规则 1:
  前件: ['iPhone 15 Pro']
  后件: ['AirPods Pro']
  支持度: 0.045
  置信度: 0.62
  提升度: 3.4

规则 2:
  前件: ['MacBook Pro', 'iPad Air']
  后件: ['Apple Watch']
  支持度: 0.023
  置信度: 0.45
  提升度: 2.8
```

## 与后端对接

### 任务队列机制

1. **后端创建任务**：向 `association_tasks` 表插入记录（status=pending）
2. **算法轮询任务**：定期查询 `association_tasks` 表
3. **执行计算**：更新状态为 running，执行关联规则分析
4. **写入结果**：将规则写入 `association_rules` 表
5. **更新状态**：更新任务状态为 completed 或 failed

### 任务参数（JSON格式）

```json
{
    "startDate": "2025-01-01",
    "endDate": "2025-12-31",
=======
# 算法3 - 关联产品推荐模块

## 功能
- 轮询 `association_tasks` 表，自动执行 pending 的关联规则计算任务
- 使用 Apriori 算法同时挖掘**商品级**和**品类级**关联规则
- 大数据量自动降级（采样、调整参数）
- 失败任务自动重试
- 结果写入 `association_rules` 表，供后端 API 调用

## 文件结构

```
ALG3/
├── src/
│   ├── worker.py        # Worker 主程序，轮询任务、执行计算
│   ├── db.py            # 数据库操作（读写任务表、结果表）
│   ├── mining.py        # Apriori 算法实现
│   ├── config.py        # 数据库配置
│   └── sample_data.py   # 生成测试数据
├── .env                 # 数据库连接配置
├── requirements.txt     # 依赖
└── README.md
```

## 环境要求
- Python 3.9+
- MySQL 5.7+

## 安装
1. 安装依赖：`pip install -r requirements.txt`
2. 修改 `.env` 中的数据库连接信息
3. 确保数据库已有主业务表（order_master、order_item、product、category）

## 运行
```bash
cd src
python worker.py
```

## 数据库表结构

### association_tasks（任务表）
| 字段 | 说明 |
|------|------|
| batch_uuid | 批次ID |
| status | pending / running / completed / failed |
| params | JSON 参数 |
| retry_count | 当前重试次数 |
| max_retries | 最大重试次数 |

### association_rules（结果表）
| 字段 | 说明 |
|------|------|
| antecedent | 前件（商品ID或品类ID列表） |
| consequent | 后件 |
| antecedent_names | 前件名称 |
| consequent_names | 后件名称 |
| support / confidence / lift | 指标 |
| rule_type | product（商品级）或 category（品类级） |
| is_active | 是否启用 |
| expires_at | 过期时间 |

## 任务参数

```sql
INSERT INTO association_tasks (batch_uuid, status, params)
VALUES (
  UUID(),
  'pending',
  '{
    "startDate": "2025-01-01",
    "endDate": "2025-06-30",
>>>>>>> 060a9b060403480af7c8a876efa18fa0af182c05
    "minSupport": 0.01,
    "minConfidence": 0.3,
    "minLift": 1.0,
    "maxLength": 3,
<<<<<<< HEAD
    "algorithm": "apriori"
}
```

## CSV文件格式

| 列名（英文） | 列名（中文） | 必填 | 说明 |
|-------------|-------------|------|------|
| order_id | 订单ID | 是 | |
| product_id | 商品ID | 是 | 数字 |
| product_name | 商品名称 | 是 | |
| category | 品类 | 是 | |
| unit_price | 单价 | 是 | 正数 |
| quantity | 数量 | 是 | 正整数 |
| total_amount | 金额 | 是 | >=0 |
| user_id | 用户ID | 是 | 数字 |
| province | 省份 | 是 | |
| city | 城市 | 否 | |
| order_date | 订单日期 | 是 | YYYY-MM-DD |
| order_status | 订单状态 | 否 | 默认 completed |

## 安全注意事项

1. **数据库密码**：不要将密码硬编码到代码中，使用 `.env` 文件管理
2. **输入验证**：对CSV导入数据进行严格验证，防止SQL注入
3. **日志审计**：记录关键操作日志，便于问题排查
4. **权限控制**：限制数据库用户的操作权限

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

---

**开发团队**：电商销售数据智能分析平台项目组
**版本**：v1.0.0
**最后更新**：2026年
=======
    "maxRetries": 2
  }'
);
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| startDate | 必填 | 开始日期（YYYY-MM-DD） |
| endDate | 必填 | 结束日期 |
| minSupport | 0.01 | 最小支持度 |
| minConfidence | 0.3 | 最小置信度 |
| minLift | 1.0 | 最小提升度 |
| maxLength | 3 | 最大项集长度 |
| maxRetries | 2 | 失败重试次数 |

## 验证结果

```sql
-- 查看任务状态
SELECT batch_uuid, status, total_rules, error_message, completed_at
FROM association_tasks ORDER BY created_at DESC LIMIT 5;

-- 查看规则
SELECT antecedent_names, consequent_names, support, confidence, lift, rule_type
FROM association_rules ORDER BY lift DESC LIMIT 20;

-- 查询某商品推荐
SELECT consequent_names, confidence, lift
FROM association_rules
WHERE JSON_CONTAINS(antecedent, JSON_QUOTE('1'))
  AND is_active = 1 AND (expires_at IS NULL OR expires_at > NOW())
ORDER BY lift DESC LIMIT 5;
```

## Python 调用示例

```python
from db import Database

db = Database()

# 查询商品推荐
recs = db.get_recommendations_by_product(
    product_id=1,
    top_n=5,
    min_confidence=0.3,
    min_lift=1.0
)
for r in recs:
    print(r['consequent_names'], r['confidence'])

# 按批次查询
rules = db.get_rules_by_batch(batch_uuid='xxx', limit=20)

db.close()
```

## 生成测试数据

```bash
cd src
python sample_data.py
```
>>>>>>> 060a9b060403480af7c8a876efa18fa0af182c05
