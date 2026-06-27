# ecommerce-sales-analytics
电商销售数据智能分析平台（销售排行 + RFM用户分层 + 关联推荐 + 时序预测）
# 电商销售数据智能分析平台

> 一站式销售数据分析与智能预测系统，支持RFM用户分层、关联规则推荐、时序销量预测及可视化看板。

## 📊 项目背景
为电商运营提供数据驱动的决策支持，从**商品销售排行**、**地域分布**、**用户价值分层**、**购物篮推荐**到**未来销量预测**，覆盖核心分析场景。

##功能
1.	统计分析商品的销售情况
输出：销售排行：各种商品的销量、销售额
可选：
分类分析：不同品类的销售占比
地域分析：各省份销售分布
2.	分析商品销量的时间变化趋势
输出：预测商品后续销量
3.	分析用户的消费数据
输出：用户价值分层（RFM模型） 参考（购买力、复购率、留存率）
推荐关联产品（分析商品之间的关联性）
4.	核心指标卡片

## 🛠 技术栈
| 角色 | 技术 |
|------|------|
| 前端 | Vue3 / React + ECharts + Axios |
| 后端 | Node.js (Express) / Python (FastAPI) + MySQL |
| 算法 | Python (Pandas, Scikit-learn, MLxtend, Prophet/ARIMA) |
| 数据库 | MySQL 8.0 |
| 部署 | Docker + Nginx（可选） |

## 📁 项目结构

├── backend/ # 后端接口服务（API + 数据导入）
├── frontend/ # 前端可视化界面
├── algorithms/ # 算法模块（RFM、关联规则、时序预测）
├── sql/ # 建表脚本及视图定义
├── docs/ # 接口文档、需求文档
├── scripts/ # 辅助脚本（数据模拟、测试）
└── README.md

## 数据库如下：
1. category 商品分类表
字段：id、分类名、父分类 id
id：分类唯一编号，主键，用来给商品绑定所属分类
分类名：比如手机、电脑、服饰、零食，页面展示 + 分类统计用
父分类 id：做多级分类（一级分类→二级分类）
例：父分类 = 数码，子分类 = 手机、平板
用途：按大类 / 小类做品类销售占比分析
2. product 商品表
字段：id、商品名、分类 id、销售价
id：商品唯一编号，订单明细里靠它关联商品
商品名：前台展示商品名称、销售排行列表展示名字
分类 id：关联分类表，用来按品类汇总销量、销售额
销售价：单品售价，用于计算销售额、均价、销售统计
3. order_master 订单主表
字段：id、订单编号、用户 id、下单时间、实付金额
id：订单主键，关联订单明细表
订单编号：唯一订单号，方便查询、溯源、作业展示
用户 id：关联用户表，定位是谁下的单，用于RFM 用户分层、复购率统计
下单时间：核心！用来做每日 / 每月销量趋势、时间变化分析、销量预测、用户最近消费时间
实付金额：订单总共花了多少钱，统计总销售额、客单价、用户消费购买力
4. order_item 订单明细表（整张最核心）
字段：id、订单 id、商品 id、商品名、购买数量、小计金额
id：明细主键
订单 id：关联订单主表，知道这条明细属于哪个订单
商品 id：关联商品表，精准定位是哪个商品
商品名：冗余保存，方便直接查报表，不用连表也能看到商品名
购买数量：统计单品总销量、做销售排行、时间趋势销量
小计金额：单个商品本次购买的总金额，统计单品销售额、品类销售额
额外用途：商品关联推荐（同一个订单 id 下多个商品，挖掘捆绑购买关系）
5. user_address 用户地址表（地域分析专用）
字段：id、用户 id、省份、城市
id：地址主键
用户 id：关联用户，知道地址属于哪个用户
省份：核心！做各省份销售分布、地域热力分析
城市：细化到城市级别销售统计，作业加分项
6. user 用户表
字段：id、用户名、注册时间
id：用户唯一编号，所有订单、地址都靠它关联
用户名：前台展示、用户管理列表显示
注册时间：用于用户留存率、新增用户统计、新老用户分析

3#数据库代码如下：
CREATE DATABASE IF NOT EXISTS ecommerce_data DEFAULT CHARSET utf8mb4;
USE ecommerce_data;

1.用户表
CREATE TABLE `user` (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL COMMENT '用户名',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间'
)ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

2.用户收货地址表（地域省份分析必备）
CREATE TABLE `user_address` (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  province VARCHAR(20) NOT NULL COMMENT '省份',
  city VARCHAR(20) NOT NULL COMMENT '城市'
)ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户收货地址';

3.商品分类表
CREATE TABLE `category` (
  id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  category_name VARCHAR(50) NOT NULL COMMENT '分类名称',
  parent_id INT UNSIGNED DEFAULT 0 COMMENT '父分类ID'
)ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品分类';

4.商品表
CREATE TABLE `product` (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  category_id INT UNSIGNED NOT NULL COMMENT '所属分类ID',
  product_name VARCHAR(100) NOT NULL COMMENT '商品名称',
  sale_price DECIMAL(10,2) NOT NULL COMMENT '售价'
)ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品';

5.订单主表（时间、用户关联，支撑RFM、时间趋势）
CREATE TABLE `order_master` (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
order_no VARCHAR(32) NOT NULL COMMENT '订单编号',
  user_id BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  order_time DATETIME NOT NULL COMMENT '下单时间',
  total_amount DECIMAL(12,2) NOT NULL COMMENT '订单总金额'
)ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单主表';

6.订单明细表（核心：销量、销售额、关联推荐全靠它）
CREATE TABLE `order_item` (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT UNSIGNED NOT NULL COMMENT '订单ID',
  product_id BIGINT UNSIGNED NOT NULL COMMENT '商品ID',
  buy_num INT NOT NULL COMMENT '购买数量',
  item_amount DECIMAL(12,2) NOT NULL COMMENT '该商品小计金额'
)ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单明细';



