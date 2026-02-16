# 优化算法技术文档 | Optimization Algorithm Technical Documentation

## 📐 数学模型详解 | Mathematical Model Details

### 问题定义 | Problem Definition

这是一个经典的**运输问题(Transportation Problem)**，是线性规划的一个特例。

This is a classic **Transportation Problem**, a special case of linear programming.

### 1. 集合定义 | Set Definitions

- **I**: 仓库集合 | Set of warehouses
  - I = {1, 2, ..., m}
  - m = 仓库总数 | total number of warehouses

- **J**: 配送中心集合 | Set of distribution centers
  - J = {1, 2, ..., n}
  - n = DC总数 | total number of DCs

- **P**: 产品集合 | Set of products
  - P = {1, 2, ..., k}
  - k = 产品种类数 | number of product types

### 2. 参数定义 | Parameter Definitions

**c[i,j,p]**: 运输成本系数 | Transportation cost coefficient
```
c[i,j,p] = distance[i,j] × rate / 100
```
- distance[i,j]: 从仓库i到DC j的距离(英里) | Distance from warehouse i to DC j (miles)
- rate: 运费率($/unit/100miles) | Shipping rate ($/unit/100miles)

**D[j,p]**: 需求量 | Demand quantity
- DC j 对产品 p 的需求 | Demand at DC j for product p

**Cap[i]**: 容量 | Capacity
- 仓库 i 的最大容量 | Maximum capacity of warehouse i

### 3. 决策变量 | Decision Variables

**x[i,j,p]**: 分配量 | Allocation quantity
- 从仓库 i 发送到 DC j 的产品 p 的数量
- Quantity of product p shipped from warehouse i to DC j
- x[i,j,p] ≥ 0 (非负约束 | non-negativity constraint)

### 4. 目标函数 | Objective Function

**最小化总运输成本 | Minimize Total Transportation Cost:**

```
Minimize Z = Σ Σ Σ c[i,j,p] × x[i,j,p]
            i∈I j∈J p∈P
```

在代码中:
```python
c = allocation_df['Cost_Per_Unit'].values
# Objective: minimize c^T × x
```

### 5. 约束条件 | Constraints

#### 约束 1: 需求满足约束 | Constraint 1: Demand Satisfaction

每个DC的每种产品需求必须完全满足:

Every demand at each DC for each product must be fully satisfied:

```
Σ x[i,j,p] = D[j,p]    ∀j∈J, ∀p∈P
i∈I
```

这是**等式约束(Equality Constraint)**

**物理意义**: 不能少发(缺货)也不能多发(浪费)

**Physical meaning**: Cannot under-ship (shortage) or over-ship (waste)

在代码中:
```python
# For each unique (channel, state, product) combination
A_eq = constraint matrix for demand
b_eq = demand values
```

#### 约束 2: 容量约束 | Constraint 2: Capacity Constraint

从每个仓库发出的总量不能超过其容量:

Total shipments from each warehouse cannot exceed its capacity:

```
Σ Σ x[i,j,p] ≤ Cap[i]    ∀i∈I
j∈J p∈P
```

这是**不等式约束(Inequality Constraint)**

**物理意义**: 仓库存储有限，不能超出物理容量

**Physical meaning**: Warehouse storage is limited, cannot exceed physical capacity

在代码中:
```python
# For each warehouse
A_ub = constraint matrix for capacity
b_ub = capacity limits
```

#### 约束 3: 非负约束 | Constraint 3: Non-negativity Constraint

分配量不能为负:

Allocation quantities cannot be negative:

```
x[i,j,p] ≥ 0    ∀i∈I, ∀j∈J, ∀p∈P
```

在代码中:
```python
bounds = [(0, None) for _ in range(n_vars)]
```

---

## 🔍 算法实现细节 | Algorithm Implementation Details

### 第一步: 数据准备 | Step 1: Data Preparation

```python
def optimize_allocation():
    # 1. 获取基础数据
    warehouses = st.session_state.warehouses
    demand = st.session_state.demand_forecast
    
    # 2. 计算距离矩阵
    distance_matrix = calculate_distance_matrix()
    
    # 3. 计算运输成本矩阵
    shipping_costs = calculate_shipping_costs(distance_matrix, rate)
```

**关键点**:
- 使用 `geopy.distance.geodesic` 计算球面距离
- Uses `geopy.distance.geodesic` to calculate great-circle distance
- 考虑地球曲率，比欧几里得距离更准确
- Accounts for Earth's curvature, more accurate than Euclidean distance

### 第二步: 构建决策变量映射 | Step 2: Build Decision Variable Mapping

```python
allocation_data = []

for _, d in demand.iterrows():
    channel = d['Channel']
    state = d['State']
    demand_units = d['Demand_Units']
    product = d['Product']
    
    # 找到所有可行的仓库-DC配对
    relevant_costs = shipping_costs[
        (shipping_costs['DC_Channel'] == channel) & 
        (shipping_costs['DC_State'] == state)
    ]
    
    for _, cost in relevant_costs.iterrows():
        allocation_data.append({
            'Product': product,
            'Warehouse': cost['Warehouse'],
            'Channel': channel,
            'State': state,
            'Demand': demand_units,
            'Cost_Per_Unit': cost['Cost_Per_Unit'],
            'Distance_Miles': cost['Distance_Miles']
        })
```

**结果**: 每一行代表一个决策变量 x[i,j,p]

**Result**: Each row represents a decision variable x[i,j,p]

### 第三步: 构建约束矩阵 | Step 3: Build Constraint Matrices

#### 需求约束矩阵 | Demand Constraint Matrix

```python
demand_constraints = []
demand_bounds = []

unique_demands = allocation_df.groupby(['Product', 'Channel', 'State'])['Demand'].first()

for (product, channel, state), demand_val in unique_demands.items():
    constraint = np.zeros(n_vars)
    
    # 对应该(product, channel, state)的所有变量系数设为1
    mask = (
        (allocation_df['Product'] == product) & 
        (allocation_df['Channel'] == channel) & 
        (allocation_df['State'] == state)
    )
    constraint[mask] = 1
    
    demand_constraints.append(constraint)
    demand_bounds.append(demand_val)
```

**矩阵形式**:
```
A_eq × x = b_eq

其中每一行对应一个需求约束
Where each row corresponds to one demand constraint
```

**示例 | Example**:
```
如果有4个决策变量:
x1: Warehouse A → Amazon-CA, Product A
x2: Warehouse B → Amazon-CA, Product A
x3: Warehouse C → Amazon-CA, Product A
x4: Warehouse A → Walmart-TX, Product A

对于 Amazon-CA 的 Product A 需求 = 5000:
约束: 1×x1 + 1×x2 + 1×x3 + 0×x4 = 5000
Constraint row: [1, 1, 1, 0]
```

#### 容量约束矩阵 | Capacity Constraint Matrix

```python
capacity_constraints = []
capacity_bounds = []

for wh_name in warehouses['Name']:
    constraint = np.zeros(n_vars)
    
    # 对应该仓库的所有变量系数设为1
    mask = allocation_df['Warehouse'] == wh_name
    constraint[mask] = 1
    
    capacity_constraints.append(constraint)
    capacity_bounds.append(capacity_value)
```

**矩阵形式**:
```
A_ub × x ≤ b_ub

其中每一行对应一个仓库的容量限制
Where each row corresponds to one warehouse capacity limit
```

### 第四步: 求解线性规划 | Step 4: Solve Linear Programming

```python
from scipy.optimize import linprog

result = linprog(
    c,              # 目标函数系数 | objective coefficients
    A_ub=A_ub,      # 不等式约束左侧 | inequality constraint LHS
    b_ub=b_ub,      # 不等式约束右侧 | inequality constraint RHS
    A_eq=A_eq,      # 等式约束左侧 | equality constraint LHS
    b_eq=b_eq,      # 等式约束右侧 | equality constraint RHS
    bounds=bounds,  # 变量边界 | variable bounds
    method='highs'  # 算法选择 | algorithm choice
)
```

**算法选择**: `highs` (HiGHS solver)
- 现代化的单纯形法实现
- Modern implementation of simplex method
- 比传统方法更快更稳定
- Faster and more stable than traditional methods
- 适合中大规模问题(数千变量)
- Suitable for medium to large problems (thousands of variables)

**其他可选算法 | Alternative Algorithms**:
- `interior-point`: 内点法 | Interior-point method
- `revised simplex`: 修正单纯形法 | Revised simplex method

### 第五步: 提取结果 | Step 5: Extract Results

```python
if result.success:
    allocation_df['Allocated_Units'] = result.x
    allocation_df['Total_Cost'] = allocation_df['Allocated_Units'] * allocation_df['Cost_Per_Unit']
    
    # 过滤掉接近零的分配
    allocation_df = allocation_df[allocation_df['Allocated_Units'] > 0.01].copy()
    
    total_cost = result.fun
```

**结果解释**:
- `result.x`: 最优解向量 | Optimal solution vector
- `result.fun`: 最优目标值 | Optimal objective value
- `result.success`: 求解是否成功 | Whether solve succeeded

---

## 🧮 计算复杂度分析 | Computational Complexity Analysis

### 变量数量 | Number of Variables

```
n_vars = |I| × |J| × |P|
       = m × n × k
```

**示例 | Example**:
- 3个仓库 × 4个DC × 2种产品 = 24个变量
- 3 warehouses × 4 DCs × 2 products = 24 variables

### 约束数量 | Number of Constraints

```
n_constraints_eq = |J| × |P|  (需求约束)
                 = n × k

n_constraints_ub = |I|        (容量约束)
                 = m
```

**总约束数**: n×k + m

**Total constraints**: n×k + m

### 时间复杂度 | Time Complexity

**单纯形法 | Simplex Method**:
- 最坏情况: O(2^n) (极少发生)
- Worst case: O(2^n) (rarely occurs)
- 平均情况: O(n^2 × m) 到 O(n^3)
- Average case: O(n^2 × m) to O(n^3)
- 实际中通常很快(多项式时间)
- Usually fast in practice (polynomial time)

**可处理规模 | Solvable Scale**:
- 小规模: <100 变量, <1秒
- Small: <100 variables, <1 second
- 中规模: 100-1000 变量, 数秒
- Medium: 100-1000 variables, few seconds
- 大规模: 1000-10000 变量, 数十秒到分钟
- Large: 1000-10000 variables, tens of seconds to minutes

---

## 🔬 算法验证 | Algorithm Validation

### 可行性检验 | Feasibility Check

优化结果必须满足:

Optimization results must satisfy:

1. **需求满足**: Σ x[i,j,p] = D[j,p]
   ```python
   # 验证代码
   for each demand:
       assert abs(sum(allocated) - demand) < tolerance
   ```

2. **容量限制**: Σ x[i,j,p] ≤ Cap[i]
   ```python
   # 验证代码
   for each warehouse:
       assert sum(allocated) <= capacity + tolerance
   ```

3. **非负性**: x[i,j,p] ≥ 0
   ```python
   # 验证代码
   assert all(allocation_df['Allocated_Units'] >= -tolerance)
   ```

### 最优性验证 | Optimality Verification

**对偶理论 | Duality Theory**:

线性规划的对偶问题可以验证最优性

The dual problem of LP can verify optimality

```
如果原问题和对偶问题都可行，且目标值相等，则达到最优
If primal and dual are both feasible and objective values equal, optimal reached
```

SciPy的 `linprog` 自动检查最优性条件

SciPy's `linprog` automatically checks optimality conditions

---

## 🎯 优化技巧 | Optimization Tips

### 1. 预处理 | Preprocessing

**消除不可行配对**:
```python
# 如果某仓库到某DC距离过远(>1000 miles)，可以预先排除
if distance > 1000:
    continue  # 不添加到决策变量
```

**好处 | Benefits**:
- 减少变量数量
- 加快求解速度
- 避免不实际的分配

### 2. 热启动 | Warm Start

如果有历史解或初步解:
```python
# 某些求解器支持提供初始解
x0 = previous_solution
result = linprog(..., x0=x0)
```

### 3. 稀疏矩阵 | Sparse Matrices

对于大规模问题，使用稀疏矩阵:
```python
from scipy.sparse import csr_matrix

A_eq_sparse = csr_matrix(A_eq)
# 节省内存，加快计算
```

### 4. 参数调优 | Parameter Tuning

```python
result = linprog(
    c, A_ub, b_ub, A_eq, b_eq,
    method='highs',
    options={
        'presolve': True,      # 预处理
        'disp': False,         # 不显示迭代信息
        'maxiter': 10000,      # 最大迭代次数
        'tol': 1e-6           # 容差
    }
)
```

---

## 📊 案例分析 | Case Study

### 案例: 3仓库-4DC问题 | Case: 3-Warehouse-4-DC Problem

**输入数据 | Input Data**:

**仓库 | Warehouses**:
```
A: Los Angeles (34.05°N, 118.24°W), Capacity: 10,000
B: Chicago (41.88°N, 87.63°W), Capacity: 8,000
C: New York (40.71°N, 74.01°W), Capacity: 12,000
```

**配送中心 | Distribution Centers**:
```
1: Amazon-CA (San Francisco)
2: Walmart-TX (Dallas)
3: Target-IL (Chicago)
4: Amazon-NY (New York)
```

**需求 | Demand**:
```
Product A to DC1: 5,000 units
Product A to DC2: 3,000 units
Product A to DC3: 2,500 units
Product A to DC4: 4,000 units
Total: 14,500 units
```

**运费率 | Shipping Rate**: $0.15/unit/100 miles

### 距离矩阵 (英里) | Distance Matrix (miles)

```
        DC1(CA)  DC2(TX)  DC3(IL)  DC4(NY)
WH-A(LA)   347     1,237    1,745    2,451
WH-B(CHI) 1,858    921       8       713
WH-C(NY)  2,574   1,374     711       0
```

### 成本矩阵 ($/unit) | Cost Matrix ($/unit)

```
        DC1(CA)  DC2(TX)  DC3(IL)  DC4(NY)
WH-A    0.52     1.86     2.62     3.68
WH-B    2.79     1.38     0.01     1.07
WH-C    3.86     2.06     1.07     0.00
```

### 客户方案 (就近发货) | Customer Approach (Nearest)

```
DC1 (5000) ← WH-A (最近)
DC2 (3000) ← WH-B (最近)
DC3 (2500) ← WH-B (最近)
DC4 (4000) ← WH-C (最近)

总成本 = 5000×0.52 + 3000×1.38 + 2500×0.01 + 4000×0.00
      = 2,600 + 4,140 + 25 + 0
      = $6,765
```

### 优化方案 | Optimized Solution

```
DC1 (5000) ← WH-A: 5,000 (成本: $2,600)
DC2 (3000) ← WH-B: 3,000 (成本: $4,140)
DC3 (2500) ← WH-B: 2,500 (成本: $25)
DC4 (4000) ← WH-C: 4,000 (成本: $0)

总成本 = $6,765
```

在这个特例中，就近策略碰巧是最优的！

In this specific case, the nearest strategy happens to be optimal!

**但是**，如果容量受限或需求分布变化，优化方案会显著不同。

**However**, if capacity is constrained or demand distribution changes, the optimized solution would be significantly different.

### 容量受限场景 | Capacity-Constrained Scenario

假设 WH-B 容量只有 4,000:

Assume WH-B capacity is only 4,000:

**客户方案** (超出容量，不可行)
**Customer approach** (exceeds capacity, infeasible)

**优化方案**:
```
DC1 (5000) ← WH-A: 5,000
DC2 (3000) ← WH-B: 1,000 + WH-A: 2,000
DC3 (2500) ← WH-B: 2,500
DC4 (4000) ← WH-C: 4,000

WH-A: 5,000 + 2,000 = 7,000 < 10,000 ✓
WH-B: 1,000 + 2,500 = 3,500 < 4,000 ✓
WH-C: 4,000 < 12,000 ✓

总成本 = 5000×0.52 + (1000×1.38 + 2000×1.86) + 2500×0.01 + 4000×0.00
      = 2,600 + 5,100 + 25 + 0
      = $7,725
```

虽然比无约束情况贵，但这是满足容量约束的最优解。

While more expensive than unconstrained, this is the optimal solution satisfying capacity constraints.

---

## 🚀 性能优化建议 | Performance Optimization Suggestions

### 1. 并行计算 | Parallel Computing

对于多产品场景，可以分产品并行优化:

For multi-product scenarios, can optimize per product in parallel:

```python
from concurrent.futures import ProcessPoolExecutor

def optimize_single_product(product_data):
    # 单产品优化
    pass

with ProcessPoolExecutor() as executor:
    results = executor.map(optimize_single_product, product_list)
```

### 2. 缓存距离矩阵 | Cache Distance Matrix

```python
@st.cache_data
def calculate_distance_matrix():
    # 距离计算较慢，缓存结果
    pass
```

### 3. 增量更新 | Incremental Updates

如果只改变需求，不需要重算距离:

If only demand changes, no need to recalculate distances:

```python
if demand_changed and not location_changed:
    # 使用缓存的距离矩阵
    use_cached_distances()
```

---

## 📚 参考文献 | References

1. **Dantzig, G. B.** (1951). "Application of the Simplex Method to a Transportation Problem". In Activity Analysis of Production and Allocation.

2. **Hitchcock, F. L.** (1941). "The Distribution of a Product from Several Sources to Numerous Localities". Journal of Mathematics and Physics, 20(1-4), 224-230.

3. **Schrijver, A.** (1998). "Theory of Linear and Integer Programming". Wiley.

4. **Vanderbei, R. J.** (2020). "Linear Programming: Foundations and Extensions". Springer.

5. **SciPy Documentation**: https://docs.scipy.org/doc/scipy/reference/optimize.linprog-highs.html

---

**文档版本 | Document Version**: 1.0

**最后更新 | Last Updated**: 2024
