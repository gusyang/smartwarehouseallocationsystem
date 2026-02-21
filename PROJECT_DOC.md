# 智能仓库分配系统 (Warehouse Optimizer)

## 项目概述

智能仓库分配系统是一个基于线性规划(Linear Programming)优化的3PL(第三方物流)仓库智能分配决策支持系统。该系统帮助物流企业优化仓库到配送中心的货物分配方案，最小化运输成本。

### 核心功能

| 功能 | 说明 |
|------|------|
| 多周次规划 | 支持第3周和第4周的库存与需求分配规划 |
| 动态库存推演 | 基于当前库存、入库(Incoming)和出库(Outgoing)自动计算可用库存 |
| Carrier维护 | 支持多种承运商，包括自有TMS车队(LTL/FTL) |
| 车辆容量计算 | 基于SKU尺寸和车辆类型计算装载量，运费分摊到单位 |
| 双重费率对比 | 对比客户当前carrier费率与TMS优惠费率 |
| 智能优化算法 | 使用SciPy线性规划计算全局最优分配方案 |
| SQLite持久化 | 数据存储在本地SQLite数据库 |
| 可视化展示 | 交互式地图、图表展示仓库分布和分配结果 |

---

## 技术架构

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Streamlit |
| 数据处理 | Pandas, NumPy |
| 优化求解 | SciPy (linprog with HiGHS solver) |
| 地理计算 | Geopy (geodesic distance) |
| 可视化 | Plotly |
| 数据库 | SQLite |

### 依赖安装

```bash
pip install -r requirements.txt
```

---

## 快速启动

### 启动应用

```bash
streamlit run app_v2.py
```

应用将在浏览器中打开，默认地址: http://localhost:8501

---

## 数据结构

### 数据库表

| 表名 | 说明 |
|------|------|
| warehouses | 仓库基本信息(名称、地址、容量) |
| sku | 产品SKU(尺寸、重量) |
| carriers | 承运商(含TMS LTL/FTL) |
| rates | 承运商费率(按距离区间) |
| vehicles | 车辆类型(53'/40' Trailer) |
| warehouse_inventory | 当前库存(仓库+SKU) |
| warehouse_schedule | 入库/出库计划 |
| distribution_centers | 配送中心 |
| demand_forecast | 需求预测 |
| customer_allocation_plan | 客户当前分配方案 |
| customer_settings | 客户设置(选择的carrier) |

### 默认承运商

- UPS (LTL)
- FedEx (LTL)
- XPO (FTL)
- Old Dominion (LTL)
- **TMS (LTL)** - 自有车队
- **TMS (FTL)** - 自有车队

### 默认车辆

- 53' Trailer: 636×96×108 inches, 最大45000 lbs
- 40' Trailer: 480×96×108 inches, 最大40000 lbs

---

## 系统使用流程

### Tab 1: Warehouses
配置仓库基本信息(名称、地址、最大容量)

### Tab 2: DC (Distribution Centers)
配置配送中心信息

### Tab 3: SKU
维护产品SKU的长、宽、高、重量

### Tab 4: Carriers & Rates
- 添加/编辑承运商
- 配置承运商的费率(按距离区间)
- 支持LTL/FTL模式

### Tab 5: Inventory & Schedule
- 维护当前库存(仓库+SKU)
- 配置入库/出库计划(Week 1-4)
- 查看可用库存预测

### Tab 6: Demand Forecast
配置需求预测(第3周和第4周)

### Tab 7: Customer Plan
- 选择客户使用的Carrier
- 选择TMS Carrier(只用TMS)
- 选择车辆类型
- 查看计算的单位运费
- 配置仓库选择
- 生成客户方案

---

## 运费计算逻辑

### 单位运费计算

```
1. 计算体积重: dim_weight = (L × W × H) / 139
2. 计费重量: chargeable_weight = max(actual_weight, dim_weight)
3. 计算车辆装载量:
   - usable_volume = vehicle_volume × 0.85
   - usable_weight = max_weight × 0.85
   - max_units = min(usable_volume/sku_volume, usable_weight/sku_weight)
4. 运输成本: total_cost = max(minimum, chargeable_weight × rate × distance / 100 + fixed)
5. 单位成本: cost_per_unit = total_cost / max_units
```

### 优化算法

使用SciPy linprog求解运输问题:
- 目标: 最小化总运输成本
- 约束: 满足需求、仓库容量限制

---

## 项目文件结构

```
Warehouse-optimizer/
├── app_v2.py              # 主应用(推荐使用)
├── db.py                  # SQLite数据库模块
├── requirements.txt        # Python依赖
├── sample_demand_forecast.csv  # 示例需求数据
├── PROJECT_DOC.md         # 项目文档
├── ALGORITHM_TECH_DOC.md  # 算法技术文档
├── QUICK_START.md         # 快速开始指南
├── DEPLOYMENT.md          # 部署指南
└── README.md              # 项目说明
```

---

## 版本说明

### V2.0 (app_v2.py)
- SQLite持久化
- SKU维度管理
- Carrier & Rates维护
- 车辆容量计算
- TMS车队支持(LTL/FTL)
- 客户Carrier选择

### V1.0 (app.py)
- 基础优化功能
- 单一费率
