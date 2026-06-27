# 算法1 - 商品销量时间序列预测服务

## 功能说明

本服务负责电商销售数据的**时间序列预测**，包括：
- 轮询 `forecast_tasks` 表，发现 `pending` 任务
- 从 `orders` 和 `products` 表读取历史销量数据
- 训练时序模型（Prophet 或简单移动平均）
- 增加异常检测预处理（Isolation Forest）
- 增加节假日特征（双11、618、春节等）
- 将预测结果写入 `forecast_results` 表

## 环境要求

| 依赖 | 版本要求 |
|------|----------|
| Python | 3.9 或更高 |
| MySQL | 8.0 或更高 |
| pip | 最新版 |

## 快速开始

### 1. 克隆代码并进入目录

```bash
git clone <仓库地址>
cd algorithms/forecast   # 根据实际项目结构调整