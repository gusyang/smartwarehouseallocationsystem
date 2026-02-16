# 智能仓库分配系统 | Smart Warehouse Allocation System

**V2.0** - 一个基于线性规划优化的3PL仓库智能分配系统，支持多周次库存推演与双重费率对比。

**V2.0** - An intelligent warehouse allocation system based on linear programming optimization, supporting multi-week inventory projection and dual-rate comparison.

---

## 🎯 项目功能 | Features

### 中文
- **多周次规划**: 支持未来第3周和第4周的库存与需求分配规划
- **动态库存推演**: 基于当前库存、入库(Incoming)和出库(Outgoing)计划自动计算可用库存
- **双重费率对比**: 深度对比"客户市场费率"与"TMS优惠费率"的成本差异
- **智能优化算法**: 使用 SciPy 线性规划自动计算全局最优分配方案
- **可视化展示**: 交互式地图、图表展示仓库分布和分配结果
- **现代UI设计**: 基于 Streamlit 的现代化界面，提供流畅的用户体验
- **数据管理**: 支持 JSON 配置的导入导出，方便场景保存与复现

### English
- **Multi-Week Planning**: Supports allocation planning for Week 3 and Week 4.
- **Dynamic Inventory**: Automatically calculates available inventory based on Incoming/Outgoing logic.
- **Dual-Rate Comparison**: Deep comparison between "Market Rate" and "TMS Rate".
- **Smart Optimization**: Uses SciPy linear programming for global optimal allocation.
- **Interactive Visualization**: Maps and charts showing warehouse distribution and allocation results
- **Modern UI**: Modernized interface for better user experience.
- **Data Management**: JSON import/export for scenario saving.

---

## 🚀 快速开始 | Quick Start

### 1. 安装依赖 | Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. 运行应用 | Run Application

```bash
streamlit run app_v2.py
```

应用将在浏览器中自动打开，默认地址: http://localhost:8501

The application will automatically open in your browser at: http://localhost:8501

---

## 📋 系统要求 | System Requirements

- Python 3.8+
- 推荐内存 | Recommended RAM: 2GB+
- 支持的操作系统 | Supported OS: Windows, macOS, Linux

---

## 🔧 核心组件说明 | Core Components

### 1. 配置管理 | Configuration Management

#### 仓库配置 | Warehouse Configuration
- 仓库名称、位置(经纬度)、容量
- Warehouse name, location (lat/lon), capacity

#### 配送中心配置 | Distribution Center Configuration
- 渠道(Amazon, Walmart等)、州、城市位置
- Channel (Amazon, Walmart, etc.), state, city location

#### 需求预测 | Demand Forecast
- 产品、渠道、州、需求数量
- Product, channel, state, demand quantity

#### 运费设置 | Shipping Rate Settings
- 基础费率: 每单位每100英里的成本
- Base rate: cost per unit per 100 miles

### 2. 优化算法 | Optimization Algorithm

**目标函数 | Objective Function:**
最小化总运输成本 | Minimize total transportation cost

```
Minimize: Σ (allocation[i,j] × cost_per_unit[i,j])
```

**约束条件 | Constraints:**
1. 满足所有需求 | Meet all demand requirements
   ```
   Σ allocation[i,j] = demand[j]  (for each DC j)
   ```

2. 不超过仓库容量 | Respect warehouse capacity
   ```
   Σ allocation[i,j] ≤ capacity[i]  (for each warehouse i)
   ```

3. 非负约束 | Non-negativity
   ```
   allocation[i,j] ≥ 0
   ```

**求解方法 | Solution Method:**
- 使用 SciPy 的 `linprog` 函数(单纯形法 | Simplex method)
- 高效处理中大规模问题 | Efficiently handles medium to large-scale problems

### 3. 成本计算 | Cost Calculation

**运输成本公式 | Shipping Cost Formula:**
```python
cost = distance (miles) × units × rate_per_unit_per_100miles / 100
```

**距离计算 | Distance Calculation:**
- 使用 `geopy` 库计算地理坐标间的大圆距离(geodesic distance)
- Uses `geopy` library to calculate geodesic distance between coordinates

---

## 📊 使用流程 | Usage Workflow

### 步骤 1: 配置基础数据 | Step 1: Configure Basic Data

1. 进入 "📊 配置 | Configuration" 页面
2. 添加/编辑仓库信息
3. 添加/编辑配送中心信息
4. 上传或手动输入需求预测
5. 设置运费率

### 步骤 2: 运行优化 | Step 2: Run Optimization

1. 进入 "🎯 智能方案 | Smart Allocation" 页面
2. 点击 "🚀 运行优化算法 | Run Optimization"
3. 查看优化结果和分配详情

### 步骤 3: 对比分析 | Step 3: Compare Analysis

1. 进入 "📈 成本对比 | Cost Comparison" 页面
2. 计算客户当前成本(基于最近仓库策略)
3. 计算智能方案成本
4. 查看节省金额和比例

### 步骤 4: 导出报告 | Step 4: Export Report

1. 进入 "📁 数据管理 | Data Management" 页面
2. 导出Excel报告或JSON配置文件

---

## 📈 示例数据说明 | Sample Data Explanation

### 预设数据 | Default Data

系统预设了示例配置:

**仓库 | Warehouses:**
- Warehouse A (Los Angeles, CA)
- Warehouse B (Chicago, IL)
- Warehouse C (New York, NY)

**配送中心 | Distribution Centers:**
- Amazon - CA (San Francisco)
- Walmart - TX (Dallas)
- Target - IL (Chicago)
- Amazon - NY (New York)

**需求预测 | Demand Forecast:**
- Product A 总需求: 14,500 units
- Total demand for Product A: 14,500 units

### 运费率 | Shipping Rate
- 默认: $0.15/unit/100 miles
- Default: $0.15 per unit per 100 miles

---

## 🔍 算法详解 | Algorithm Details

### 线性规划模型 | Linear Programming Model

**决策变量 | Decision Variables:**
```
x[i,j,p] = 从仓库i发送到DC j的产品p的数量
x[i,j,p] = quantity of product p shipped from warehouse i to DC j
```

**数学模型 | Mathematical Model:**

```
Minimize Z = Σ Σ Σ c[i,j,p] × x[i,j,p]

Subject to:
1. Σ x[i,j,p] = D[j,p]  ∀j,p  (满足需求 | meet demand)
   i

2. Σ Σ x[i,j,p] ≤ Cap[i]  ∀i  (容量约束 | capacity constraint)
   j p

3. x[i,j,p] ≥ 0  ∀i,j,p  (非负约束 | non-negativity)
```

**符号说明 | Notation:**
- `c[i,j,p]`: 单位运输成本 | unit shipping cost
- `D[j,p]`: DC j对产品p的需求 | demand at DC j for product p
- `Cap[i]`: 仓库i的容量 | capacity of warehouse i

---

## 🎨 界面功能 | UI Features

### 1. 配置页面 | Configuration Page
- ✏️ 可编辑表格 | Editable tables
- ➕ 动态添加行 | Dynamic row addition
- 📤 CSV上传 | CSV upload
- 💾 配置保存 | Configuration save

### 2. 智能方案页面 | Smart Allocation Page
- 🚀 一键优化 | One-click optimization
- 📊 汇总统计 | Summary statistics
- 🥧 饼图展示 | Pie chart visualization
- 🗺️ 地图可视化 | Map visualization

### 3. 成本对比页面 | Cost Comparison Page
- 💰 成本指标卡 | Cost metric cards
- 📊 柱状图对比 | Bar chart comparison
- 📋 详细对比表 | Detailed comparison tables

### 4. 数据管理页面 | Data Management Page
- 💾 导出JSON配置 | Export JSON configuration
- 📤 导入JSON配置 | Import JSON configuration
- 📊 导出Excel报告 | Export Excel report

---

## 🔄 扩展功能建议 | Extension Suggestions

### 已实现 | Implemented
- ✅ 基础优化算法 | Basic optimization algorithm
- ✅ 成本对比分析 | Cost comparison analysis
- ✅ 交互式可视化 | Interactive visualization
- ✅ 数据导入导出 | Data import/export

### 可扩展 | Potential Extensions
- 🔮 实时运费API集成(UPS/FedEx) | Real-time shipping API integration
- 📊 多周期优化 | Multi-period optimization
- 🌱 碳排放计算 | Carbon emission calculation
- 👥 多用户/多租户支持 | Multi-user/multi-tenant support
- 📈 历史数据分析 | Historical data analysis
- 🤖 需求预测AI模型 | Demand forecasting AI model

---

## 🐛 调试建议 | Debugging Tips

### 常见问题 | Common Issues

1. **优化失败 | Optimization Fails**
   - 检查需求是否超过总仓库容量
   - Check if demand exceeds total warehouse capacity
   - 确保所有地理坐标正确
   - Ensure all geographic coordinates are correct

2. **成本计算异常 | Cost Calculation Anomalies**
   - 验证运费率设置
   - Verify shipping rate settings
   - 检查距离计算结果
   - Check distance calculation results

3. **数据导入错误 | Data Import Errors**
   - 确保CSV列名匹配
   - Ensure CSV column names match
   - 检查数据格式(数值、文本)
   - Check data formats (numeric, text)

### 日志调试 | Logging for Debugging

在代码中添加:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 📞 技术支持 | Technical Support

### 文档 | Documentation
- Streamlit: https://docs.streamlit.io
- SciPy linprog: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html
- Geopy: https://geopy.readthedocs.io

### 问题反馈 | Issue Reporting
如果遇到问题，请提供:
- 错误信息截图 | Error message screenshot
- 输入数据示例 | Sample input data
- 系统环境(Python版本等) | System environment

---

## 📄 许可证 | License

MIT License

---

## 👨‍💻 开发者 | Developer

**技术栈 | Tech Stack:**
- Frontend: Streamlit
- Optimization: SciPy (linprog)
- Visualization: Plotly
- Geospatial: Geopy
- Data: Pandas, NumPy

**版本 | Version:** 1.0.0

**更新日期 | Last Updated:** 2024

---

## 🎓 算法参考 | Algorithm References

1. Dantzig, G. B. (1951). "Application of the Simplex Method to a Transportation Problem"
2. Hitchcock, F. L. (1941). "The Distribution of a Product from Several Sources to Numerous Localities"
3. Operations Research textbooks on Linear Programming

---

**祝使用愉快！ | Happy Optimizing! 🚀**
