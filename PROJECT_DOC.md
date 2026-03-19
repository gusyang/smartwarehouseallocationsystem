# Smart Warehouse Allocation System / 智能仓库分配系统 - Business & Logic Overview

---

## 🌍 ENGLISH VERSION

## 🎯 What is this system for?

This is an **intelligent allocation and cost optimization decision-support system** designed for 3PL (Third-Party Logistics) companies.

In actual business scenarios, many customers rely on a "simple nearest" or "fixed origin warehouse" strategy and use standard market shipping rates, leading to significant hidden logistics costs. The core value of this system is to **demonstrate the massive cost differences between the "Customer's Current Plan" and the "3PL Smart Optimization Plan (Omni-network allocation + TMS discounted rates)" through mathematical modeling (Linear Programming). This visually aids sales pitches or helps operation teams optimize existing logistics networks.**

The system simulates order demands and warehouse inventory changes for future weeks (e.g., Week 3 and Week 4) to automatically calculate and output detailed logistics routing and cost comparison reports.

---

## 📦 Core Business Objects & Data Relationships

To ensure accurate calculations, the system maintains the following core business data:

1. **Nodes**:
   - **Warehouses**: Origin warehouses available to us or the customer, characterized by specific geographic addresses and maximum physical storage capacities.
   - **DCs (Distribution Centers)**: The final destinations of the goods (e.g., designated receiving centers for channels like Amazon or Walmart).
2. **Product Data (SKU)**:
   - Records the length, width, height, and weight of each product. This is crucial for accurately calculating how many units can fit into a vehicle during loading.
3. **Carriers & Rates**:
   - Records market logistics providers (like UPS, FedEx) and our own fleet (TMS).
   - Maintains their respective billing rules: charging a base freight rate per mile based on different "distance ranges", including minimum charges and fixed fees.
4. **Vehicles**:
   - Defines transport vehicle dimensions (e.g., 53' Trailer, 40' Trailer), including maximum weight capacity and maximum volume.

---

## ⚙️ Core Business Logic Explained

The essence of this system lies in its underlying simulation and calculation logic, which consists of three main parts:

### 1. Dynamic Inventory Calculation
Instead of only looking at current "static inventory," the system calculates the **Available Inventory** for the target week (Week 3 or Week 4) by incorporating future inbound and outbound plans.

* **Formulas**:
  * `Week 3 Available Inventory = Current Inventory + Week 3 Incoming - Week 1 Outgoing - Week 2 Outgoing`
  * `Week 4 Available Inventory = Current Inventory + Week 3 & 4 Incoming - Week 1 Outgoing - Week 2 Outgoing`
* **Inventory Cost Deduction Logic**: When fulfilling demand, the system **prioritizes using the available inventory within that warehouse**. The logic assumes that fulfilling orders using existing inventory does not incur additional "long-haul replenishment freight costs" (this part of the cost is recorded as $0). Only when local inventory is insufficient and goods must be shipped directly from factories or other locations, the excess portion is fully charged with long-haul transportation costs.

### 2. Precise Unit Cost Calculation
The system automatically converts macro "truckload freight" or "tiered rates" into the most intuitive **"Cost Per Unit"**. This involves:

1. **Calculating SKU Chargeable Weight**: Compares the SKU's actual physical weight with its dimensional weight (`L × W × H ÷ 139`) and takes the larger value as the billing basis.
2. **Calculating Max Vehicle Loading Capacity**: The system sets the vehicle's effective loading rate at **85%** (leaving room for gaps). It then divides the vehicle's usable volume by the SKU volume, and the usable weight by the SKU chargeable weight. The **minimum** of these two values is the maximum number of units the vehicle can carry (Max Units).
3. **Unit Cost Amortization**: Based on the actual geographic distance (straight-line) between the origin warehouse and destination DC, combined with the carrier's mileage rate, the system calculates the total cost of a single trip. This total is then divided by the max units the vehicle can carry, resulting in an accurate **shipping rate for every single unit shipped from A to B**.

### 3. Dual-Scenario Duel & Optimization Algorithm
The system sets up two parallel universes (scenarios) to visually demonstrate the value of optimization:

#### 🔴 Scenario 1: Customer Current Plan
* **Behavioral Pattern**: Customers are often rigid, designating shipments from only a few fixed default warehouses.
* **Rates Used**: Uses standard market carrier rates provided by the customer.
* **Logic Characteristics**: In this mode, the system **ignores warehouse capacity limits**. Even if a warehouse is over capacity, it assumes the customer will forcefully ship from these locations, exposing the high total costs of their rigid strategy.

#### 🟢 Scenario 2: Smart Optimization Plan
* **Behavioral Pattern**: Breaks conventions and optimizes globally. The system opens all available warehouse network nodes for the algorithm to choose from.
* **Rates Used**: Applies the 3PL's proprietary and advantageous TMS (Transportation Management System) internal rates.
* **Logic Characteristics (Linear Programming Algorithm)**: 
  The system utilizes `SciPy`'s linear programming solver to find the global optimal solution. It finds the route combination with the lowest total freight cost while satisfying three strict **constraints**:
  1. **100% Demand Fulfillment**: Every DC's demand for every week must be exactly met, no more and no less.
  2. **Strict Capacity Limits**: Strictly adheres to the maximum physical capacity of each origin warehouse.
  3. **Prioritize Existing Inventory**: Matches the "inventory deduction" logic mentioned above, maximizing the use of existing inventory across warehouses to reduce additional long-haul transfers.

---

## 🚶‍♂️ Typical User Workflow

A business person or analyst typically follows these steps in the system:

1. **Basic Configuration** (Tabs 1-4)
   * Confirm warehouse locations and destination DCs.
   * Maintain SKU dimensions to ensure accurate freight amortization.
   * Input market standard carrier rates and the company's own floor prices.
2. **Define Current Business Status** (Tabs 5-6)
   * Take stock of existing inventory and future scheduling plans.
   * Input the "Week 3 & Week 4 Demand Forecast" provided by the customer.
3. **Set the Baseline Scenario** (Tab 7 - Customer Plan)
   * Select the courier company the customer currently uses.
   * Specify the default warehouses the customer insists on using.
   * Click to generate the customer's baseline plan; the system will simulate their current routes based on nearest-neighbor logic.
4. **One-Click Smart Duel & Analysis** (Run Scenarios & Cost Comparison)
   * Switch to the "Run Scenarios" page to calculate the total cost for both plans with one click.
   * Go to the "Cost Comparison" page, where the system generates a beautiful comparison dashboard and charts.
   * **Sales/Operations can directly screenshot these charts (e.g., "The Smart Plan saved you $5,200 (18% cost reduction) this week and reduced the average long-haul distance by 300 miles") to prove the massive commercial value of the 3PL optimized network to the customer.**


<br><br>

---
---

## 🇨🇳 中文版本 (CHINESE VERSION)

## 🎯 系统是干什么的？

这是一个面向 3PL（第三方物流）企业的**智能分配与成本优化决策支持系统**。

在实际业务中，许多客户往往采用“简单就近”或“固定发货仓”的策略，且使用的是标准市场运费，这会导致隐性的物流成本浪费。本系统的核心价值在于：**通过数学建模（线性规划）全局测算，向客户直观展示“客户当前方案”与“3PL智能优化方案（全网分仓+TMS优惠费率）”之间的巨大成本差异，从而辅助销售打单或帮助运营团队优化现有物流网络。**

系统通过模拟未来特定周次（如第3周和第4周）的订单需求、仓库库存变动，自动计算并输出详尽的物流路线与成本对比报告。

---

## 📦 核心业务对象与数据关系

为了让系统能准确计算，系统内维护了以下几类核心业务数据：

1. **节点数据**：
   - **Warehouses (发货仓库)**：我们或客户可用的起点仓库，具有特定的地理地址和最大物理存储容量。
   - **DCs (配送中心/收货地)**：货物的最终目的地（如Amazon、Walmart等渠道的指定接收仓）。
2. **商品数据 (SKU)**：
   - 记录每种产品的长、宽、高和重量。这是为了后续在车辆装载时，精确计算一辆车到底能装多少件货。
3. **承运商与费率 (Carriers & Rates)**：
   - 记录市面上的物流供应商（如UPS、FedEx）以及我们自有的车队（TMS）。
   - 维护各自的计费规则：按照不同的“里程区间”收取每英里的基础运费，并包含最低消费和固定费用。
4. **车辆类型 (Vehicles)**：
   - 定义运输工具的尺寸（如53尺货柜、40尺货柜）及其最大承重和最大容积。

---

## ⚙️ 核心业务逻辑解析

本系统最精华的部分在于底层的各项推演与计算逻辑，主要包含以下三大块：

### 1. 动态可用库存推演 (Dynamic Inventory Calculation)
系统并非只看当前的“死库存”，而是会结合未来几周的入库与出库计划，推算出目标周（第3周或第4周）的**可用库存**。

* **推演公式**：
  * `第3周可用库存 = 当前库存 + 第3周入库 - 第1周出库 - 第2周出库`
  * `第4周可用库存 = 当前库存 + 第3周与第4周总入库 - 第1周出库 - 第2周出库`
* **库存抵扣成本逻辑**：在满足发货需求时，系统会**优先使用该仓库内的可用库存**。系统逻辑假定：消耗已有库存发货不产生额外的“远程补货干线运费”（这部分成本记为0）。只有当本地库存不足，需要强行从工厂或其他地方现发现调时，超出库存的部分才会全额计算物流干线运输成本。

### 2. 精细化运费折算逻辑 (Unit Cost Calculation)
系统会自动将宏观的“整车运费”或“阶梯费率”折算成最直观的**“单件发货成本 (Cost Per Unit)”**，主要经过以下几步判断：

1. **计算SKU计费重**：对比SKU的实际物理重量和体积重（`长×宽×高 ÷ 139`），取两者中的较大值作为计费依据。
2. **计算单车最大装载量**：系统设定车辆的实际有效装载率为 **85%**（预留空间缝隙）。然后用车辆的可用容积除以SKU体积、可用承重除以SKU计费重，取两者算出来的**最小值**，即为这辆车最多能装载的件数（Max Units）。
3. **单件成本摊销**：根据发货仓到收货仓的实际地理距离（直线距离计算），结合承运商里程费率，计算出单趟运输总价，然后再除以该车能装载的最大件数，最终得出**每一件商品从A地发往B地的精准运费**。

### 3. 双场景博弈与优化算法 (The "Customer vs. Smart" Duel)
系统设置了两个平行宇宙（场景），用于直观展现优化的价值：

#### 🔴 场景一：客户当前方案 (Customer Current Plan)
* **行为模式**：客户通常比较死板，只指定从少数几个固定的默认仓库发货。
* **使用费率**：使用客户自带的市场标准承运商（如普通快递/零担报价）。
* **逻辑特点**：在此模式下，系统**忽略仓库容量上限**。哪怕爆仓，也假定客户会强行使用这几个仓发货，暴露出客户僵化策略下的高昂总成本。

#### 🟢 场景二：系统智能方案 (Smart Optimization Plan)
* **行为模式**：打破常规，全局统筹。系统开放所有可用的仓库网络节点供算法选择。
* **使用费率**：应用 3PL 自有且具有优势的 TMS (运输管理系统) 内部费率。
* **逻辑特点（线性规划算法）**：
  系统底层使用 `SciPy` 的线性规划求解器，寻找全局最优解。它会在满足以下三个硬性**约束条件**的前提下，找出总运费最低的路线组合：
  1. **需求必达**：每个配送中心每一周的需求量必须被 100% 满足，不能多也不能少。
  2. **不超容量**：严格遵守每个发货仓的物理最大容量限制。
  3. **优先清库存**：自动匹配前文提到的“库存抵扣”逻辑，最大化利用各仓现有库存，减少额外的干线运输调拨。

---

## 🚶‍♂️ 典型用户使用流程

一个业务人员或分析师在系统中的操作路径通常如下：

1. **基础配置维护** (Tabs 1-4)
   * 确认各仓库位置、收货方目的地。
   * 维护本次要测算的商品(SKU)尺寸，以确保运费分摊准确。
   * 录入市场主流承运商的费率表以及己方底价。
2. **定义当前业务现状** (Tabs 5-6)
   * 盘点各仓现有库存以及未来的调度计划。
   * 录入客户发来的“第3周、第4周需求预测单”。
3. **设置博弈基准线** (Tab 7 - Customer Plan)
   * 选择客户目前习惯使用的快递公司。
   * 圈定客户目前“死守”的几个发货仓库。
   * 点击生成客户的基础发货计划，系统会按就近原则模拟出客户现在的发货路线。
4. **一键智能对决与分析** (Run Scenarios & Cost Comparison)
   * 切换到“运行场景”页面，一键计算两套方案的总成本。
   * 进入“成本对比”页面，系统会自动生成华丽的对比看板和图表。
   * **业务人员可以直接截取这些图表（例如：本周智能方案为您节省了 $5,200（降本18%），并且平均缩短了300英里的干线距离），向客户证明 3PL 优化网络的巨大商业价值。**
