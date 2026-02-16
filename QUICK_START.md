# 快速启动指南 | Quick Start Guide

## 🚀 5分钟快速上手 | Get Started in 5 Minutes

### 步骤 1: 安装环境 | Step 1: Setup Environment

```bash
# 克隆或下载项目 | Clone or download project
cd warehouse_optimizer

# 安装依赖 | Install dependencies
pip install -r requirements.txt
```

### 步骤 2: 启动应用 | Step 2: Launch Application

```bash
streamlit run app_v2.py
```

浏览器会自动打开 http://localhost:8501

Browser will automatically open http://localhost:8501

### 步骤 3: 使用预设数据测试 | Step 3: Test with Default Data

系统已预设示例数据，可直接测试:

The system comes with sample data pre-loaded:

1. **查看配置 | View Configuration**
   - 点击左侧 "📊 配置 | Configuration"
   - 查看3个仓库、4个配送中心、4条需求记录
   - View 3 warehouses, 4 DCs, 4 demand records

2. **运行优化 | Run Optimization**
   - 点击 "🎯 智能方案 | Smart Allocation"
   - 点击 "🚀 运行优化算法"
   - 查看优化结果
   - Click "🚀 Run Optimization" and view results

3. **对比成本 | Compare Costs**
   - 点击 "📈 成本对比 | Cost Comparison"
   - 分别点击计算客户成本和智能方案成本
   - 查看节省金额
   - Calculate both costs and view savings

### 步骤 4: 自定义数据 | Step 4: Customize Data

#### 方法 1: 在界面编辑 | Method 1: Edit in UI
- 在配置页面直接编辑表格
- Edit tables directly in configuration page

#### 方法 2: 上传CSV | Method 2: Upload CSV
- 使用提供的 `sample_demand_forecast.csv` 作为模板
- Use provided `sample_demand_forecast.csv` as template
- 在 "需求预测" 标签页上传
- Upload in "Demand Forecast" tab

#### 方法 3: 导入JSON配置 | Method 3: Import JSON Config
- 先导出当前配置作为模板
- Export current config as template
- 修改后重新导入
- Modify and re-import

---

## 📝 示例场景 | Example Scenario

### 场景描述 | Scenario Description

**客户情况 | Customer Situation:**
- 产品: Electronics (Product A)
- 需要发货到4个渠道的配送中心
- Need to ship to 4 channel DCs
- 当前做法: 就近发货(距离最近的仓库)
- Current approach: ship from nearest warehouse

**优化目标 | Optimization Goal:**
- 在满足所有需求的前提下
- While meeting all demand
- 最小化总运输成本
- Minimize total transportation cost

### 预期结果 | Expected Results

使用预设数据运行优化:
Running optimization with default data:

- **客户当前成本**: ~$1,200 (简单就近策略)
- **Customer Current Cost**: ~$1,200 (simple nearest strategy)

- **智能优化成本**: ~$900 (线性规划优化)
- **Smart Optimized Cost**: ~$900 (LP optimization)

- **节省**: ~$300 (25%成本降低)
- **Savings**: ~$300 (25% cost reduction)

*实际数字取决于具体的地理位置和运费率*
*Actual numbers depend on specific locations and shipping rates*

---

## 🎯 核心概念 | Core Concepts

### 1. 仓库 (Warehouse)
- 您公司拥有的存储设施
- Your company's storage facilities
- 包含: 位置、容量
- Includes: location, capacity

### 2. 配送中心 (Distribution Center, DC)
- 客户渠道的目标地点
- Target locations for customer channels
- 如: Amazon-CA, Walmart-TX
- E.g.: Amazon-CA, Walmart-TX

### 3. 需求预测 (Demand Forecast)
- 每个DC需要多少产品
- How much product each DC needs
- 基于历史数据或销售预测
- Based on historical data or sales forecast

### 4. 运费率 (Shipping Rate)
- 每单位产品运输100英里的成本
- Cost to ship one unit per 100 miles
- 影响总成本计算
- Affects total cost calculation

---

## 🔧 常用操作 | Common Operations

### 添加新仓库 | Add New Warehouse

1. 进入 "配置" → "仓库" 标签
2. 点击 "➕ 添加仓库"
3. 在展开的编辑器中填写:
   - Name: 仓库名称
   - City: 城市
   - State: 州代码(如 CA, TX)
   - Latitude/Longitude: 经纬度(可用Google Maps查询)
   - Capacity: 容量(单位数)

### 上传需求数据 | Upload Demand Data

1. 准备CSV文件，包含列:
   - Product: 产品名
   - Channel: 渠道名(如 Amazon)
   - State: 州代码
   - Demand_Units: 需求数量

2. 在 "需求预测" 标签页上传

### 调整运费率 | Adjust Shipping Rate

1. 进入 "运费设置" 标签
2. 修改 "每单位每100英里费用"
3. 实时影响成本计算

### 导出分析报告 | Export Analysis Report

1. 运行优化后
2. 进入 "数据管理" 页面
3. 点击 "⬇️ 下载Excel报告"
4. 获得包含3个工作表的Excel文件:
   - Smart Allocation: 智能分配详情
   - Customer Allocation: 客户当前分配
   - Summary: 成本对比汇总

---

## 💡 使用技巧 | Pro Tips

### 技巧 1: 批量导入数据
- 准备好CSV/JSON文件可以快速配置多个场景
- Prepare CSV/JSON files for quick multi-scenario setup

### 技巧 2: 保存配置
- 导出JSON配置文件保存不同客户的设置
- Export JSON configs to save settings for different customers

### 技巧 3: 敏感性分析
- 尝试不同的运费率，观察成本变化
- Try different shipping rates to observe cost changes
- 评估仓库容量限制的影响
- Evaluate impact of warehouse capacity constraints

### 技巧 4: 可视化辅助决策
- 使用地图查看仓库和DC的空间分布
- Use map to view spatial distribution of warehouses and DCs
- 用饼图快速理解分配比例
- Use pie charts to quickly understand allocation ratios

---

## ❓ 常见问题 | FAQ

### Q1: 优化失败怎么办?
**A:** 检查:
- 总需求是否超过总仓库容量?
- 所有地理坐标是否正确?
- 是否有配送中心没有对应的仓库可达?

### Q2: 如何获取经纬度?
**A:** 
- 使用 Google Maps: 右键点击位置 → 复制坐标
- 在线工具: latlong.net

### Q3: 可以处理多个产品吗?
**A:** 可以! 在需求预测中添加不同的产品名即可

### Q4: 运费率如何设定?
**A:** 
- 可以用历史平均值
- 咨询物流公司的报价
- 默认 $0.15/unit/100miles 是一个参考值

### Q5: 能否考虑运输时间?
**A:** 当前版本主要优化成本。可以扩展添加时间窗口约束。

---

## 🎓 下一步学习 | Next Steps

### 初级用户 | Beginner
1. 熟悉界面各个页面
2. 用预设数据运行一次完整流程
3. 尝试修改单个仓库位置，观察结果变化

### 中级用户 | Intermediate
1. 准备真实数据替换示例数据
2. 进行多场景对比分析
3. 导出报告分享给团队

### 高级用户 | Advanced
1. 阅读代码理解优化算法细节
2. 考虑扩展功能(如多周期、库存成本)
3. 集成到现有系统(API调用)

---

**准备好了吗? 让我们开始优化吧! 🚀**

**Ready? Let's start optimizing! 🚀**
