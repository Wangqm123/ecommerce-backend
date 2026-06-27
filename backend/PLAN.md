# 电商销售数据智能分析平台 - 后端实现计划

## Context
从零搭建 Node.js + Express + MySQL 后端，为电商销售数据智能分析平台提供数据接口。需要实现：CSV 数据导入、销售分析查询（排名/品类/区域）、核心指标仪表盘、以及对接三位算法同学（RFM、关联规则、时间序列预测）的统一接口层。

## 技术栈
- **运行时**: Node.js + Express
- **数据库**: MySQL (mysql2/promise 连接池)
- **文件上传**: multer
- **CSV 解析**: csv-parser (流式)
- **其他**: dotenv, cors, morgan, uuid

## 项目结构

```
backend/
├── package.json
├── .env / .env.example
├── nodemon.json
├── src/
│   ├── app.js                          # Express 应用入口
│   ├── server.js                       # 启动入口
│   ├── config/db.js                    # MySQL 连接池
│   ├── middleware/
│   │   ├── errorHandler.js             # 统一错误处理
│   │   └── upload.js                   # multer 配置
│   ├── routes/                         # 路由层 (index, dashboard, sales, category, region, upload, rfm, association, forecast)
│   ├── controllers/                    # 控制器层 (对应 routes)
│   ├── services/                       # 业务逻辑层 (对应 controllers)
│   ├── utils/
│   │   ├── response.js                 # 统一响应格式 { code, message, data }
│   │   ├── csvParser.js                # CSV 流式解析 + 字段映射
│   │   └── validator.js                # 数据校验
│   └── sql/schema.sql                  # 全部建表 DDL
└── uploads/                            # CSV 临时存储
```

## 实施步骤

### 阶段一：基础设施
1. 初始化 npm 项目，安装依赖 (express, mysql2, multer, csv-parser, dotenv, cors, morgan, uuid)
2. 创建 `src/app.js` + `src/server.js` Express 骨架
3. 创建 `src/config/db.js` MySQL 连接池
4. 创建 `src/utils/response.js` 统一响应工具
5. 创建 `src/middleware/errorHandler.js` 全局错误处理
6. 配置 CORS、morgan 日志、.env 环境变量
7. **编写并执行 `src/sql/schema.sql`** 建表

### 阶段二：CSV 导入模块
1. 配置 multer (`src/middleware/upload.js`)
2. 实现 CSV 解析 + 字段映射 (`src/utils/csvParser.js`)
3. 实现数据校验 (`src/utils/validator.js`)
4. 实现导入主逻辑 (`src/services/upload.service.js`) — 流式解析 → 校验 → 分批插入(500行/批)
5. 实现 controller + routes (`POST /api/upload/csv`, `GET /api/upload/history`)

### 阶段三：分析查询 API
1. 核心指标: `GET /api/dashboard/kpis`, `GET /api/dashboard/trend`
2. 销售排名: `GET /api/sales/ranking` (支持按销售额/销量排序、品类筛选、日期范围)
3. 品类分析: `GET /api/category/analysis`, `GET /api/category/trend`
4. 区域分析: `GET /api/region/analysis`, `GET /api/region/detail/:province`

### 阶段四：算法集成层
1. 执行算法结果表 DDL (rfm_results, association_rules, forecast_results 及 task 表)
2. 创建数据视图 (v_rfm_input, v_association_input, v_forecast_input)
3. 实现 RFM 模块: trigger → status → result 接口
4. 实现关联规则模块: trigger → status → result → recommend 接口
5. 实现时间序列预测模块: trigger → status → result 接口
6. 编写算法契约文档给算法同事

### 阶段五：完善
1. 请求参数校验中间件
2. 边界条件与异常处理覆盖
3. 大批量 CSV 导入性能验证

## 数据库核心表
- **products**: product_id, product_name, category, unit_price
- **users**: user_id, province, city
- **orders**: order_id, product_id, user_id, quantity, unit_price, total_amount, order_date, order_status
- **order_summary**: order_id, user_id, total_amount, item_count, order_date
- **import_batches**: CSV 导入追踪
- **rfm_results / association_rules / forecast_results**: 算法结果
- **rfm_compute_tasks / association_tasks / forecast_tasks**: 算法任务状态

## 算法集成契约（共享数据库模式）
- 后端负责：建表 + 创建数据视图供算法直接查询 + 创建任务记录
- 算法侧负责：轮询 pending 任务 → 更新为 running → 计算 → 写入结果表 → 更新为 completed/failed
- 前端通过 `GET /api/{module}/status/:batchUuid` 轮询，通过 `GET /api/{module}/result` 获取结果

## 统一 API 响应格式
```json
{ "code": 200, "message": "success", "data": {...} }
```

## 验证方式
1. Postman 测试所有 REST API 端点
2. 准备示例 CSV 文件测试上传导入全流程
3. 检查 MySQL 数据写入正确性
4. 与算法同事确认任务表 + 结果表的读写契约
