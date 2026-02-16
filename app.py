import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import linprog
import plotly.express as px
import plotly.graph_objects as go
from geopy.distance import geodesic
import json
from io import BytesIO

# Page configuration
st.set_page_config(page_title="智能仓库分配系统 | Smart Warehouse Allocation", layout="wide", page_icon="🏭")

# Initialize session state
if 'warehouses' not in st.session_state:
    st.session_state.warehouses = pd.DataFrame({
        'Name': ['Warehouse A', 'Warehouse B', 'Warehouse C'],
        'Address': ['Los Angeles, CA', 'Chicago, IL', 'New York, NY'],
        'Capacity': [10000, 8000, 12000]
    })

if 'distribution_centers' not in st.session_state:
    st.session_state.distribution_centers = pd.DataFrame({
        'Channel': ['Amazon', 'Walmart', 'Target', 'Amazon'],
        'State': ['CA', 'TX', 'IL', 'NY'],
        'Address': ['San Francisco, CA', 'Dallas, TX', 'Chicago, IL', 'New York, NY']
    })

if 'demand_forecast' not in st.session_state:
    st.session_state.demand_forecast = pd.DataFrame({
        'Product': ['Product A', 'Product A', 'Product A', 'Product A'],
        'Channel': ['Amazon', 'Walmart', 'Target', 'Amazon'],
        'State': ['CA', 'TX', 'IL', 'NY'],
        'Demand_Units': [5000, 3000, 2500, 4000]
    })

if 'shipping_rates' not in st.session_state:
    # Default shipping rate: $0.15 per unit per 100 miles
    st.session_state.shipping_rates = None

if 'customer_current_cost' not in st.session_state:
    st.session_state.customer_current_cost = None

if 'customer_allocation_plan' not in st.session_state:
    # 初始化客户当前分配方案（示例数据）
    st.session_state.customer_allocation_plan = pd.DataFrame({
        'Product': ['Product A', 'Product A', 'Product A', 'Product A'],
        'Warehouse': ['Warehouse A', 'Warehouse B', 'Warehouse B', 'Warehouse C'],
        'Channel': ['Amazon', 'Walmart', 'Target', 'Amazon'],
        'State': ['CA', 'TX', 'IL', 'NY'],
        'Allocated_Units': [5000, 3000, 2500, 4000]
    })


def geocode_address(address):
    """将地址转换为经纬度坐标"""
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="warehouse_optimizer")
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        else:
            # 如果地理编码失败，返回None
            return None, None
    except Exception as e:
        st.warning(f"地址解析失败 | Geocoding failed: {address} - {e}")
        return None, None


def calculate_distance_from_addresses(address1, address2, cache={}):
    """根据两个地址计算距离（带缓存）"""
    # 创建缓存键
    cache_key = f"{address1}|{address2}"
    
    # 检查缓存
    if cache_key in cache:
        return cache[cache_key]
    
    # 地理编码
    lat1, lon1 = geocode_address(address1)
    lat2, lon2 = geocode_address(address2)
    
    if lat1 is None or lat2 is None:
        # 如果地理编码失败，返回一个默认值（例如500英里）
        cache[cache_key] = 500.0
        return 500.0
    
    # 计算距离
    distance = geodesic((lat1, lon1), (lat2, lon2)).miles
    
    # 缓存结果
    cache[cache_key] = distance
    
    return distance


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate geodesic distance between two points"""
    return geodesic((lat1, lon1), (lat2, lon2)).miles


def calculate_distance_matrix():
    """Calculate distance matrix from warehouses to DCs using addresses"""
    warehouses = st.session_state.warehouses
    dcs = st.session_state.distribution_centers
    
    distances = []
    distance_cache = {}  # 缓存以避免重复地理编码
    
    # 显示进度
    total_pairs = len(warehouses) * len(dcs)
    progress_text = "计算距离中... | Calculating distances..."
    
    if total_pairs > 10:  # 只在有很多配对时显示进度条
        progress_bar = st.progress(0, text=progress_text)
    else:
        progress_bar = None
    
    current_pair = 0
    
    for _, wh in warehouses.iterrows():
        wh_address = wh['Address']
        
        for _, dc in dcs.iterrows():
            dc_address = dc['Address']
            
            # 计算距离
            dist = calculate_distance_from_addresses(wh_address, dc_address, distance_cache)
            
            distances.append({
                'Warehouse': wh['Name'],
                'Warehouse_Address': wh_address,
                'DC_Channel': dc['Channel'],
                'DC_State': dc['State'],
                'DC_Address': dc_address,
                'Distance_Miles': dist
            })
            
            # 更新进度
            current_pair += 1
            if progress_bar:
                progress_bar.progress(current_pair / total_pairs, text=progress_text)
    
    if progress_bar:
        progress_bar.empty()
    
    return pd.DataFrame(distances)


def calculate_shipping_costs(distance_matrix, rate_per_unit_per_100miles=0.15):
    """Calculate shipping costs based on distance"""
    costs = distance_matrix.copy()
    costs['Cost_Per_Unit'] = costs['Distance_Miles'] * rate_per_unit_per_100miles / 100
    return costs


def optimize_allocation():
    """
    Optimize warehouse allocation using linear programming
    Objective: Minimize total shipping cost
    Constraints: Meet all demand, respect warehouse capacity
    """
    warehouses = st.session_state.warehouses
    demand = st.session_state.demand_forecast
    distance_matrix = calculate_distance_matrix()
    
    # Get shipping costs
    rate = st.session_state.get('shipping_rate_per_100miles', 0.15)
    shipping_costs = calculate_shipping_costs(distance_matrix, rate)
    
    # Merge demand with shipping costs
    allocation_data = []
    
    for _, d in demand.iterrows():
        channel = d['Channel']
        state = d['State']
        demand_units = d['Demand_Units']
        product = d['Product']
        
        # Find shipping costs for this channel-state combination
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
    
    allocation_df = pd.DataFrame(allocation_data)
    
    if allocation_df.empty:
        return None, None
    
    # Create decision variables: allocation[warehouse][channel][state][product]
    # Simplified: allocation per row in allocation_df
    n_vars = len(allocation_df)
    
    # Objective: minimize total cost
    c = allocation_df['Cost_Per_Unit'].values
    
    # Constraints:
    # 1. Meet demand for each channel-state-product combination
    demand_constraints = []
    demand_bounds = []
    
    unique_demands = allocation_df.groupby(['Product', 'Channel', 'State'])['Demand'].first()
    
    for (product, channel, state), demand_val in unique_demands.items():
        constraint = np.zeros(n_vars)
        mask = (
            (allocation_df['Product'] == product) & 
            (allocation_df['Channel'] == channel) & 
            (allocation_df['State'] == state)
        )
        constraint[mask] = 1
        demand_constraints.append(constraint)
        demand_bounds.append(demand_val)
    
    # 2. Warehouse capacity constraints
    capacity_constraints = []
    capacity_bounds = []
    
    for wh_name in warehouses['Name']:
        constraint = np.zeros(n_vars)
        mask = allocation_df['Warehouse'] == wh_name
        constraint[mask] = 1
        capacity_constraints.append(constraint)
        capacity_idx = warehouses[warehouses['Name'] == wh_name].index[0]
        capacity_bounds.append(warehouses.loc[capacity_idx, 'Capacity'])
    
    # Combine constraints
    A_eq = np.array(demand_constraints)
    b_eq = np.array(demand_bounds)
    
    A_ub = np.array(capacity_constraints)
    b_ub = np.array(capacity_bounds)
    
    # Bounds: all allocations >= 0
    bounds = [(0, None) for _ in range(n_vars)]
    
    # Solve
    result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, 
                     bounds=bounds, method='highs')
    
    if result.success:
        allocation_df['Allocated_Units'] = result.x
        allocation_df['Total_Cost'] = allocation_df['Allocated_Units'] * allocation_df['Cost_Per_Unit']
        
        # Filter out zero allocations
        allocation_df = allocation_df[allocation_df['Allocated_Units'] > 0.01].copy()
        
        total_cost = result.fun
        
        return allocation_df, total_cost
    else:
        return None, None


def calculate_customer_allocation_cost():
    """根据客户配置的分配方案计算成本"""
    warehouses = st.session_state.warehouses
    customer_plan = st.session_state.customer_allocation_plan
    distance_matrix = calculate_distance_matrix()
    
    rate = st.session_state.get('shipping_rate_per_100miles', 0.15)
    shipping_costs = calculate_shipping_costs(distance_matrix, rate)
    
    customer_allocation = []
    
    for _, plan in customer_plan.iterrows():
        product = plan['Product']
        warehouse = plan['Warehouse']
        channel = plan['Channel']
        state = plan['State']
        allocated_units = plan['Allocated_Units']
        
        # 查找对应的运输成本
        cost_info = shipping_costs[
            (shipping_costs['Warehouse'] == warehouse) &
            (shipping_costs['DC_Channel'] == channel) &
            (shipping_costs['DC_State'] == state)
        ]
        
        if not cost_info.empty:
            cost_per_unit = cost_info.iloc[0]['Cost_Per_Unit']
            distance = cost_info.iloc[0]['Distance_Miles']
            
            customer_allocation.append({
                'Product': product,
                'Warehouse': warehouse,
                'Channel': channel,
                'State': state,
                'Allocated_Units': allocated_units,
                'Cost_Per_Unit': cost_per_unit,
                'Distance_Miles': distance,
                'Total_Cost': allocated_units * cost_per_unit
            })
        else:
            # 如果找不到对应的成本信息，返回警告
            st.warning(f"警告: 无法找到 {warehouse} → {channel}-{state} 的运输成本信息")
    
    customer_df = pd.DataFrame(customer_allocation)
    total_cost = customer_df['Total_Cost'].sum() if not customer_df.empty else 0
    
    return customer_df, total_cost


# UI Layout
st.title("🏭 智能仓库分配系统 | Smart Warehouse Allocation System")
st.markdown("**3PL智能规划方案 - 优化成本，提升效率**")

# Sidebar navigation
page = st.sidebar.selectbox(
    "导航 | Navigation",
    ["📊 配置 | Configuration", "🎯 智能方案 | Smart Allocation", "📈 成本对比 | Cost Comparison", "📁 数据管理 | Data Management"]
)

# Configuration Page
if page == "📊 配置 | Configuration":
    st.header("📊 系统配置 | System Configuration")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "仓库 | Warehouses", 
        "配送中心 | Distribution Centers", 
        "需求预测 | Demand Forecast", 
        "运费设置 | Shipping Rates",
        "客户当前方案 | Customer Current Plan"
    ])
    
    with tab1:
        st.subheader("仓库管理 | Warehouse Management")
        
        st.info("💡 **删除方法**: (1) 在下方选择框中勾选要删除的仓库，点击删除按钮  (2) 或在编辑器中通过 '+' 添加、直接修改内容")
        
        # 简易删除界面
        if not st.session_state.warehouses.empty:
            st.markdown("**🗑️ 选择要删除的仓库 | Select Warehouses to Delete**")
            
            # 创建带索引的选择列表
            warehouse_options = {}
            for i, row in st.session_state.warehouses.iterrows():
                label = f"{row['Name']} ({row['Address']})"
                warehouse_options[label] = i
            
            selected_to_delete = st.multiselect(
                "勾选要删除的仓库 | Check warehouses to delete:",
                options=list(warehouse_options.keys()),
                help="可以选择多个仓库一次性删除",
                key="wh_delete_select"
            )
            
            if selected_to_delete:
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("🗑️ 删除选中 | Delete Selected", type="secondary", use_container_width=True):
                        # 获取选中的索引
                        indices_to_delete = [warehouse_options[item] for item in selected_to_delete]
                        # 删除选中的行
                        st.session_state.warehouses = st.session_state.warehouses.drop(indices_to_delete).reset_index(drop=True)
                        st.success(f"✅ 已删除 {len(indices_to_delete)} 个仓库！")
                        st.rerun()
                with col2:
                    st.warning(f"⚠️ 将删除 {len(selected_to_delete)} 个仓库")
        
        st.markdown("---")
        
        # Allow editing
        with st.expander("✏️ 编辑/添加仓库 | Edit/Add Warehouses", expanded=False):
            st.markdown("""
            **操作说明 | Instructions**:
            - ➕ **添加行**: 点击表格底部的 "+" 按钮
            - ✏️ **编辑**: 直接点击单元格修改内容
            - ➖ **删除行**: 将鼠标移到行号左侧，点击出现的 "−" 按钮
            """)
            
            edited_wh = st.data_editor(
                st.session_state.warehouses, 
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Name": st.column_config.TextColumn("仓库名称 | Name", required=True, help="仓库的唯一标识名称"),
                    "Address": st.column_config.TextColumn("地址 | Address", required=True, help="完整地址，如: Los Angeles, CA 或 1234 Main St, Chicago, IL"),
                    "Capacity": st.column_config.NumberColumn("容量 | Capacity", min_value=0, step=100, help="仓库最大容量（单位数）")
                }
            )
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("💾 保存仓库更改 | Save Changes", type="primary", use_container_width=True):
                    st.session_state.warehouses = edited_wh
                    st.success("✅ 已保存！| Saved!")
                    st.rerun()
            
            with col2:
                if st.button("🔄 恢复默认 | Reset to Default", use_container_width=True):
                    st.session_state.warehouses = pd.DataFrame({
                        'Name': ['Warehouse A', 'Warehouse B', 'Warehouse C'],
                        'Address': ['Los Angeles, CA', 'Chicago, IL', 'New York, NY'],
                        'Capacity': [10000, 8000, 12000]
                    })
                    st.success("✅ 已恢复默认仓库！")
                    st.rerun()
            
            with col3:
                if st.button("❌ 清空所有 | Clear All", use_container_width=True):
                    if st.session_state.get('confirm_clear_warehouses', False):
                        st.session_state.warehouses = pd.DataFrame(columns=['Name', 'Address', 'Capacity'])
                        st.session_state.confirm_clear_warehouses = False
                        st.warning("⚠️ 已清空所有仓库！")
                        st.rerun()
                    else:
                        st.session_state.confirm_clear_warehouses = True
                        st.warning("⚠️ 再次点击确认清空所有仓库")
        
        # 显示当前仓库汇总
        st.markdown("---")
        st.markdown("**📊 当前仓库汇总 | Current Warehouse Summary**")
        
        if not st.session_state.warehouses.empty:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("仓库数量 | Total Warehouses", len(st.session_state.warehouses))
            with col2:
                total_cap = st.session_state.warehouses['Capacity'].sum()
                st.metric("总容量 | Total Capacity", f"{total_cap:,}")
            with col3:
                avg_capacity = st.session_state.warehouses['Capacity'].mean()
                st.metric("平均容量 | Avg Capacity", f"{avg_capacity:,.0f}")
        else:
            st.warning("⚠️ 当前没有仓库，请添加至少一个仓库！")

    
    with tab2:
        st.subheader("配送中心管理 | Distribution Center Management")
        
        st.dataframe(st.session_state.distribution_centers, use_container_width=True, hide_index=True)
        
        with st.expander("✏️ 编辑配送中心 | Edit DCs", expanded=False):
            st.markdown("**操作**: 直接编辑地址，点击底部 '+' 添加新行")
            
            edited_dc = st.data_editor(
                st.session_state.distribution_centers, 
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Channel": st.column_config.TextColumn("渠道 | Channel", help="如 Amazon, Walmart, Target"),
                    "State": st.column_config.TextColumn("州 | State", help="州代码，如 CA, TX"),
                    "Address": st.column_config.TextColumn("地址 | Address", required=True, help="完整地址，如: Dallas, TX 或 1234 Main St, Dallas, TX")
                }
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 保存DC更改 | Save DC Changes", type="primary", use_container_width=True):
                    st.session_state.distribution_centers = edited_dc
                    st.success("✅ 已保存！| Saved!")
                    st.rerun()
            with col2:
                if st.button("🔄 恢复默认 | Reset", use_container_width=True, key="reset_dc"):
                    st.session_state.distribution_centers = pd.DataFrame({
                        'Channel': ['Amazon', 'Walmart', 'Target', 'Amazon'],
                        'State': ['CA', 'TX', 'IL', 'NY'],
                        'Address': ['San Francisco, CA', 'Dallas, TX', 'Chicago, IL', 'New York, NY']
                    })
                    st.success("✅ 已恢复！")
                    st.rerun()
        
        st.markdown("---")
        if not st.session_state.distribution_centers.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("配送中心数量 | Total DCs", len(st.session_state.distribution_centers))
            with col2:
                st.metric("渠道数量 | Channels", st.session_state.distribution_centers['Channel'].nunique())

    
    with tab3:
        st.subheader("需求预测 | Demand Forecast")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.dataframe(st.session_state.demand_forecast, use_container_width=True)
        
        with col2:
            if st.button("➕ 添加需求 | Add Demand"):
                new_row = pd.DataFrame({
                    'Product': ['Product X'],
                    'Channel': ['Channel'],
                    'State': [''],
                    'Demand_Units': [1000]
                })
                st.session_state.demand_forecast = pd.concat([st.session_state.demand_forecast, new_row], ignore_index=True)
                st.rerun()
        
        with st.expander("编辑需求预测 | Edit Demand"):
            edited_demand = st.data_editor(st.session_state.demand_forecast, num_rows="dynamic")
            if st.button("保存需求更改 | Save Demand Changes"):
                st.session_state.demand_forecast = edited_demand
                st.success("已保存 | Saved!")
        
        # Upload CSV
        st.markdown("---")
        uploaded_file = st.file_uploader("上传需求预测CSV | Upload Demand Forecast CSV", type=['csv'])
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                required_cols = ['Product', 'Channel', 'State', 'Demand_Units']
                if all(col in df.columns for col in required_cols):
                    st.session_state.demand_forecast = df
                    st.success("成功上传! | Successfully uploaded!")
                    st.rerun()
                else:
                    st.error(f"CSV必须包含这些列 | CSV must contain columns: {required_cols}")
            except Exception as e:
                st.error(f"上传错误 | Upload error: {e}")
    
    with tab4:
        st.subheader("运费设置 | Shipping Rate Settings")
        
        st.markdown("**基础运费率 | Base Shipping Rate**")
        rate = st.number_input(
            "每单位每100英里费用 ($) | Cost per unit per 100 miles ($)",
            min_value=0.01,
            max_value=10.0,
            value=0.15,
            step=0.01,
            help="默认运费计算: 距离 × 单位数 × 费率 / 100"
        )
        st.session_state.shipping_rate_per_100miles = rate
        
        st.info(f"当前费率: ${rate}/单位/100英里 | Current rate: ${rate} per unit per 100 miles")
        
        # Distance matrix preview
        if st.checkbox("查看距离矩阵 | View Distance Matrix"):
            dist_matrix = calculate_distance_matrix()
            st.dataframe(dist_matrix, use_container_width=True)
        
        # Shipping cost preview
        if st.checkbox("查看运费矩阵 | View Shipping Cost Matrix"):
            shipping_costs = calculate_shipping_costs(calculate_distance_matrix(), rate)
            st.dataframe(shipping_costs, use_container_width=True)
    
    with tab5:
        st.subheader("客户当前分配方案 | Customer Current Allocation Plan")
        
        st.info("💡 **配置说明**: 在这里设置客户目前的产品分配方案，用于与智能优化方案对比。")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.dataframe(st.session_state.customer_allocation_plan, use_container_width=True)
        
        with col2:
            if st.button("➕ 添加分配 | Add Allocation"):
                new_row = pd.DataFrame({
                    'Product': ['Product X'],
                    'Warehouse': ['Warehouse A'],
                    'Channel': ['Channel'],
                    'State': [''],
                    'Allocated_Units': [1000]
                })
                st.session_state.customer_allocation_plan = pd.concat([
                    st.session_state.customer_allocation_plan, new_row
                ], ignore_index=True)
                st.rerun()
        
        with st.expander("✏️ 编辑客户方案 | Edit Customer Plan"):
            st.markdown("""
            **使用提示 | Usage Tips**:
            - 确保Product、Channel、State与需求预测匹配
            - Warehouse必须在仓库列表中存在
            - Allocated_Units总和应等于对应的需求
            """)
            
            # 显示可用选项
            col1, col2, col3 = st.columns(3)
            with col1:
                if not st.session_state.warehouses.empty:
                    st.info(f"**可用仓库 | Available Warehouses**:\n\n" + 
                           ", ".join(st.session_state.warehouses['Name'].tolist()))
            with col2:
                if not st.session_state.demand_forecast.empty:
                    unique_products = st.session_state.demand_forecast['Product'].unique().tolist()
                    st.info(f"**可用产品 | Available Products**:\n\n" + 
                           ", ".join(unique_products))
            with col3:
                if not st.session_state.demand_forecast.empty:
                    unique_channels = st.session_state.demand_forecast['Channel'].unique().tolist()
                    st.info(f"**可用渠道 | Available Channels**:\n\n" + 
                           ", ".join(unique_channels))
            
            edited_plan = st.data_editor(
                st.session_state.customer_allocation_plan, 
                num_rows="dynamic",
                column_config={
                    "Product": st.column_config.TextColumn("Product"),
                    "Warehouse": st.column_config.TextColumn("Warehouse"),
                    "Channel": st.column_config.TextColumn("Channel"),
                    "State": st.column_config.TextColumn("State"),
                    "Allocated_Units": st.column_config.NumberColumn(
                        "Allocated Units",
                        min_value=0,
                        step=1
                    )
                }
            )
            
            if st.button("💾 保存客户方案 | Save Customer Plan"):
                st.session_state.customer_allocation_plan = edited_plan
                st.success("✅ 已保存客户方案！| Customer plan saved!")
                st.rerun()
        
        # 快速生成客户方案的选项
        st.markdown("---")
        st.markdown("**🚀 快速生成方案 | Quick Generate Plan**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📍 基于就近仓库生成 | Generate Based on Nearest Warehouse"):
                # 使用就近仓库策略生成
                warehouses = st.session_state.warehouses
                demand = st.session_state.demand_forecast
                distance_matrix = calculate_distance_matrix()
                rate = st.session_state.get('shipping_rate_per_100miles', 0.15)
                shipping_costs = calculate_shipping_costs(distance_matrix, rate)
                
                nearest_plan = []
                for _, d in demand.iterrows():
                    channel = d['Channel']
                    state = d['State']
                    demand_units = d['Demand_Units']
                    product = d['Product']
                    
                    relevant_costs = shipping_costs[
                        (shipping_costs['DC_Channel'] == channel) & 
                        (shipping_costs['DC_State'] == state)
                    ].sort_values('Distance_Miles')
                    
                    if not relevant_costs.empty:
                        nearest = relevant_costs.iloc[0]
                        nearest_plan.append({
                            'Product': product,
                            'Warehouse': nearest['Warehouse'],
                            'Channel': channel,
                            'State': state,
                            'Allocated_Units': demand_units
                        })
                
                if nearest_plan:
                    st.session_state.customer_allocation_plan = pd.DataFrame(nearest_plan)
                    st.success("✅ 已基于就近仓库生成方案！")
                    st.rerun()
        
        with col2:
            if st.button("🎲 平均分配生成 | Generate with Even Distribution"):
                # 平均分配策略
                warehouses = st.session_state.warehouses
                demand = st.session_state.demand_forecast
                
                even_plan = []
                for _, d in demand.iterrows():
                    product = d['Product']
                    channel = d['Channel']
                    state = d['State']
                    demand_units = d['Demand_Units']
                    
                    # 平均分配到所有仓库
                    n_warehouses = len(warehouses)
                    units_per_warehouse = demand_units / n_warehouses
                    
                    for _, wh in warehouses.iterrows():
                        even_plan.append({
                            'Product': product,
                            'Warehouse': wh['Name'],
                            'Channel': channel,
                            'State': state,
                            'Allocated_Units': round(units_per_warehouse, 2)
                        })
                
                if even_plan:
                    st.session_state.customer_allocation_plan = pd.DataFrame(even_plan)
                    st.success("✅ 已生成平均分配方案！")
                    st.rerun()
        
        # 验证分配方案
        st.markdown("---")
        if st.button("🔍 验证分配方案 | Validate Allocation Plan"):
            demand = st.session_state.demand_forecast
            customer_plan = st.session_state.customer_allocation_plan
            
            validation_results = []
            all_valid = True
            
            for _, d in demand.iterrows():
                product = d['Product']
                channel = d['Channel']
                state = d['State']
                required_demand = d['Demand_Units']
                
                # 计算该需求的总分配
                allocated = customer_plan[
                    (customer_plan['Product'] == product) &
                    (customer_plan['Channel'] == channel) &
                    (customer_plan['State'] == state)
                ]['Allocated_Units'].sum()
                
                diff = allocated - required_demand
                is_valid = abs(diff) < 0.01
                
                validation_results.append({
                    'Product': product,
                    'Channel-State': f"{channel}-{state}",
                    'Required': required_demand,
                    'Allocated': allocated,
                    'Difference': diff,
                    'Status': '✅ 匹配' if is_valid else '❌ 不匹配'
                })
                
                if not is_valid:
                    all_valid = False
            
            validation_df = pd.DataFrame(validation_results)
            st.dataframe(validation_df, use_container_width=True)
            
            if all_valid:
                st.success("✅ 所有分配都与需求匹配！| All allocations match demand!")
            else:
                st.error("❌ 部分分配与需求不匹配，请检查！| Some allocations don't match demand!")



elif page == "🎯 智能方案 | Smart Allocation":
    st.header("🎯 智能分配方案 | Smart Allocation Solution")
    
    if st.button("🚀 运行优化算法 | Run Optimization", type="primary"):
        with st.spinner("正在计算最优方案... | Calculating optimal solution..."):
            allocation_result, optimal_cost = optimize_allocation()
            
            if allocation_result is not None:
                st.session_state.smart_allocation = allocation_result
                st.session_state.smart_cost = optimal_cost
                st.success(f"✅ 优化完成! 总成本: ${optimal_cost:,.2f} | Optimization complete! Total cost: ${optimal_cost:,.2f}")
            else:
                st.error("❌ 优化失败，请检查配置 | Optimization failed, please check configuration")
    
    if 'smart_allocation' in st.session_state:
        st.markdown("---")
        
        # Display allocation details
        st.subheader("📋 分配详情 | Allocation Details")
        
        allocation = st.session_state.smart_allocation
        
        # Summary by warehouse
        warehouse_summary = allocation.groupby('Warehouse').agg({
            'Allocated_Units': 'sum',
            'Total_Cost': 'sum'
        }).reset_index()
        warehouse_summary.columns = ['Warehouse', 'Total Units Allocated', 'Total Cost ($)']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**仓库分配汇总 | Warehouse Allocation Summary**")
            st.dataframe(warehouse_summary, use_container_width=True)
        
        with col2:
            # Pie chart
            fig = px.pie(warehouse_summary, values='Total Units Allocated', names='Warehouse',
                        title='仓库分配比例 | Warehouse Allocation Distribution')
            st.plotly_chart(fig, use_container_width=True)
        
        # Detailed allocation table
        st.markdown("**详细分配表 | Detailed Allocation Table**")
        display_allocation = allocation.copy()
        display_allocation['Allocated_Units'] = display_allocation['Allocated_Units'].round(2)
        display_allocation['Total_Cost'] = display_allocation['Total_Cost'].round(2)
        st.dataframe(display_allocation, use_container_width=True)
        
        # Visualization: Map
        st.markdown("---")
        st.subheader("🗺️ 分配路线图 | Allocation Route Map")
        
        st.info("💡 地图功能需要地理编码所有地址，可能需要一些时间...")
        
        if st.button("🗺️ 生成地图 | Generate Map"):
            with st.spinner("正在解析地址并生成地图... | Geocoding addresses and generating map..."):
                # Create map data
                map_data = []
                
                # Add warehouses
                for _, wh in st.session_state.warehouses.iterrows():
                    lat, lon = geocode_address(wh['Address'])
                    if lat and lon:
                        map_data.append({
                            'Latitude': lat,
                            'Longitude': lon,
                            'Name': wh['Name'],
                            'Address': wh['Address'],
                            'Type': 'Warehouse',
                            'Size': 20
                        })
                
                # Add DCs
                for _, dc in st.session_state.distribution_centers.iterrows():
                    lat, lon = geocode_address(dc['Address'])
                    if lat and lon:
                        map_data.append({
                            'Latitude': lat,
                            'Longitude': lon,
                            'Name': f"{dc['Channel']} - {dc['State']}",
                            'Address': dc['Address'],
                            'Type': 'DC',
                            'Size': 15
                        })
                
                if map_data:
                    map_df = pd.DataFrame(map_data)
                    
                    fig = px.scatter_mapbox(
                        map_df, 
                        lat='Latitude', 
                        lon='Longitude', 
                        color='Type', 
                        size='Size',
                        hover_name='Name',
                        hover_data={'Address': True, 'Latitude': False, 'Longitude': False, 'Size': False},
                        title='仓库和配送中心分布 | Warehouse and DC Distribution',
                        mapbox_style='open-street-map',
                        zoom=3, 
                        height=500
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.success(f"✅ 成功显示 {len(map_data)} 个位置")
                else:
                    st.warning("⚠️ 无法解析任何地址，请检查地址格式")



# Cost Comparison Page
elif page == "📈 成本对比 | Cost Comparison":
    st.header("📈 成本对比分析 | Cost Comparison Analysis")
    
    st.info("💡 请先在 **配置页面** 的 **客户当前方案** 标签中设置客户的分配方案")
    
    # Calculate both scenarios
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💼 计算客户当前成本 | Calculate Customer Current Cost", type="primary"):
            with st.spinner("计算中... | Calculating..."):
                customer_allocation, customer_cost = calculate_customer_allocation_cost()
                st.session_state.customer_allocation = customer_allocation
                st.session_state.customer_cost = customer_cost
                
                if customer_cost > 0:
                    st.success(f"✅ 客户当前成本: ${customer_cost:,.2f}")
                else:
                    st.warning("⚠️ 请检查客户分配方案配置")
    
    with col2:
        if st.button("🎯 计算智能方案成本 | Calculate Smart Solution Cost", type="primary"):
            with st.spinner("计算中... | Calculating..."):
                allocation_result, optimal_cost = optimize_allocation()
                if allocation_result is not None:
                    st.session_state.smart_allocation = allocation_result
                    st.session_state.smart_cost = optimal_cost
                    st.success(f"✅ 智能方案成本: ${optimal_cost:,.2f}")
                else:
                    st.error("❌ 优化失败，请检查配置")
    
    # Display comparison
    if 'customer_cost' in st.session_state and 'smart_cost' in st.session_state:
        st.markdown("---")
        
        customer_cost = st.session_state.customer_cost
        smart_cost = st.session_state.smart_cost
        savings = customer_cost - smart_cost
        savings_pct = (savings / customer_cost * 100) if customer_cost > 0 else 0
        
        # Metrics with larger display
        st.markdown("### 💰 成本对比结果 | Cost Comparison Results")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "客户当前成本 | Current Cost", 
                f"${customer_cost:,.2f}",
                help="基于客户配置的分配方案"
            )
        
        with col2:
            st.metric(
                "智能方案成本 | Smart Cost", 
                f"${smart_cost:,.2f}",
                help="基于线性规划优化的最优方案"
            )
        
        with col3:
            st.metric(
                "💵 节省金额 | Savings", 
                f"${savings:,.2f}",
                delta=f"-${savings:,.2f}" if savings > 0 else f"+${abs(savings):,.2f}",
                delta_color="normal" if savings > 0 else "inverse",
                help="客户当前成本 - 智能方案成本"
            )
        
        with col4:
            st.metric(
                "📊 节省比例 | Savings %", 
                f"{savings_pct:.1f}%",
                delta=f"{savings_pct:.1f}%",
                delta_color="normal" if savings > 0 else "inverse",
                help="节省金额 / 客户当前成本 × 100%"
            )
        
        # Highlight savings
        if savings > 0:
            st.success(f"""
            ### 🎉 优化效果显著！
            
            使用智能优化方案，可以为客户节省 **${savings:,.2f}** ({savings_pct:.1f}%)
            
            **Using smart optimization, save ${savings:,.2f} ({savings_pct:.1f}%) for the customer**
            """)
        elif savings < 0:
            st.warning(f"""
            ### ⚠️ 当前方案已接近最优
            
            客户当前方案比智能方案便宜 **${abs(savings):,.2f}** ({abs(savings_pct):.1f}%)
            
            这可能意味着客户已经有较好的分配策略。
            """)
        else:
            st.info("### ℹ️ 两方案成本相同")
        
        # Visual comparison
        st.markdown("---")
        st.subheader("📊 可视化对比 | Visual Comparison")
        
        # Create comparison chart
        comparison_df = pd.DataFrame({
            'Scenario': ['客户当前方案\nCurrent Plan', '智能优化方案\nSmart Plan'],
            'Total Cost ($)': [customer_cost, smart_cost],
            'Type': ['Customer', 'Smart']
        })
        
        fig = px.bar(
            comparison_df, 
            x='Scenario', 
            y='Total Cost ($)',
            title='总成本对比 | Total Cost Comparison',
            color='Type',
            color_discrete_map={'Customer': '#FF6B6B', 'Smart': '#4ECDC4'},
            text='Total Cost ($)'
        )
        fig.update_traces(
            texttemplate='$%{text:,.2f}', 
            textposition='outside',
            textfont_size=14
        )
        fig.update_layout(
            showlegend=False,
            height=400,
            yaxis_title="总成本 | Total Cost ($)",
            xaxis_title=""
        )
        
        # Add savings annotation
        if savings != 0:
            fig.add_annotation(
                x=0.5,
                y=max(customer_cost, smart_cost) * 0.8,
                text=f"节省 Savings<br>${savings:,.2f} ({savings_pct:.1f}%)",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="#2ECC71" if savings > 0 else "#E74C3C",
                font=dict(size=16, color="#2ECC71" if savings > 0 else "#E74C3C", family="Arial Black"),
                bgcolor="white",
                bordercolor="#2ECC71" if savings > 0 else "#E74C3C",
                borderwidth=2
            )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed breakdown
        st.markdown("---")
        st.subheader("🔍 详细成本分解 | Detailed Cost Breakdown")
        
        tab1, tab2 = st.tabs(["📋 按仓库分解 | By Warehouse", "📋 按渠道分解 | By Channel"])
        
        with tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**客户当前方案 - 按仓库 | Customer Plan - By Warehouse**")
                if 'customer_allocation' in st.session_state and not st.session_state.customer_allocation.empty:
                    customer_by_wh = st.session_state.customer_allocation.groupby('Warehouse').agg({
                        'Allocated_Units': 'sum',
                        'Total_Cost': 'sum'
                    }).reset_index()
                    customer_by_wh.columns = ['Warehouse', 'Units', 'Cost ($)']
                    customer_by_wh['Cost ($)'] = customer_by_wh['Cost ($)'].round(2)
                    st.dataframe(customer_by_wh, use_container_width=True)
                    
                    # Pie chart
                    fig1 = px.pie(
                        customer_by_wh, 
                        values='Cost ($)', 
                        names='Warehouse',
                        title='客户方案成本分布',
                        color_discrete_sequence=px.colors.sequential.RdBu
                    )
                    st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                st.markdown("**智能优化方案 - 按仓库 | Smart Plan - By Warehouse**")
                if 'smart_allocation' in st.session_state and not st.session_state.smart_allocation.empty:
                    smart_by_wh = st.session_state.smart_allocation.groupby('Warehouse').agg({
                        'Allocated_Units': 'sum',
                        'Total_Cost': 'sum'
                    }).reset_index()
                    smart_by_wh.columns = ['Warehouse', 'Units', 'Cost ($)']
                    smart_by_wh['Cost ($)'] = smart_by_wh['Cost ($)'].round(2)
                    st.dataframe(smart_by_wh, use_container_width=True)
                    
                    # Pie chart
                    fig2 = px.pie(
                        smart_by_wh, 
                        values='Cost ($)', 
                        names='Warehouse',
                        title='智能方案成本分布',
                        color_discrete_sequence=px.colors.sequential.Tealgrn
                    )
                    st.plotly_chart(fig2, use_container_width=True)
        
        with tab2:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**客户当前方案 - 按渠道 | Customer Plan - By Channel**")
                if 'customer_allocation' in st.session_state and not st.session_state.customer_allocation.empty:
                    customer_by_ch = st.session_state.customer_allocation.groupby('Channel').agg({
                        'Allocated_Units': 'sum',
                        'Total_Cost': 'sum'
                    }).reset_index()
                    customer_by_ch.columns = ['Channel', 'Units', 'Cost ($)']
                    customer_by_ch['Cost ($)'] = customer_by_ch['Cost ($)'].round(2)
                    st.dataframe(customer_by_ch, use_container_width=True)
            
            with col2:
                st.markdown("**智能优化方案 - 按渠道 | Smart Plan - By Channel**")
                if 'smart_allocation' in st.session_state and not st.session_state.smart_allocation.empty:
                    smart_by_ch = st.session_state.smart_allocation.groupby('Channel').agg({
                        'Allocated_Units': 'sum',
                        'Total_Cost': 'sum'
                    }).reset_index()
                    smart_by_ch.columns = ['Channel', 'Units', 'Cost ($)']
                    smart_by_ch['Cost ($)'] = smart_by_ch['Cost ($)'].round(2)
                    st.dataframe(smart_by_ch, use_container_width=True)
        
        # Detailed allocation tables
        st.markdown("---")
        st.subheader("📄 完整分配明细 | Complete Allocation Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**客户当前分配明细 | Customer Current Allocation Details**")
            if 'customer_allocation' in st.session_state:
                display_customer = st.session_state.customer_allocation.copy()
                display_customer['Total_Cost'] = display_customer['Total_Cost'].round(2)
                display_customer['Cost_Per_Unit'] = display_customer['Cost_Per_Unit'].round(4)
                st.dataframe(display_customer, use_container_width=True)
        
        with col2:
            st.markdown("**智能优化分配明细 | Smart Optimized Allocation Details**")
            if 'smart_allocation' in st.session_state:
                display_smart = st.session_state.smart_allocation[
                    ['Product', 'Warehouse', 'Channel', 'State', 'Allocated_Units', 'Cost_Per_Unit', 'Total_Cost']
                ].copy()
                display_smart['Allocated_Units'] = display_smart['Allocated_Units'].round(2)
                display_smart['Cost_Per_Unit'] = display_smart['Cost_Per_Unit'].round(4)
                display_smart['Total_Cost'] = display_smart['Total_Cost'].round(2)
                st.dataframe(display_smart, use_container_width=True)
    
    else:
        st.warning("⚠️ 请先计算客户当前成本和智能方案成本")
        st.markdown("""
        **操作步骤 | Steps**:
        1. 在 **配置** 页面设置客户当前分配方案
        2. 点击上方 **"计算客户当前成本"** 按钮
        3. 点击 **"计算智能方案成本"** 按钮
        4. 查看对比结果
        """)


# Data Management Page
elif page == "📁 数据管理 | Data Management":
    st.header("📁 数据管理 | Data Management")
    
    # Export configuration
    st.subheader("💾 导出配置 | Export Configuration")
    
    if st.button("导出全部配置为JSON | Export All Configuration as JSON"):
        config = {
            'warehouses': st.session_state.warehouses.to_dict('records'),
            'distribution_centers': st.session_state.distribution_centers.to_dict('records'),
            'demand_forecast': st.session_state.demand_forecast.to_dict('records'),
            'customer_allocation_plan': st.session_state.customer_allocation_plan.to_dict('records'),
            'shipping_rate': st.session_state.get('shipping_rate_per_100miles', 0.15)
        }
        
        json_str = json.dumps(config, indent=2)
        st.download_button(
            label="⬇️ 下载配置文件 | Download Configuration File",
            data=json_str,
            file_name="warehouse_config.json",
            mime="application/json"
        )
    
    # Import configuration
    st.markdown("---")
    st.subheader("📤 导入配置 | Import Configuration")
    
    uploaded_config = st.file_uploader("上传配置JSON文件 | Upload Configuration JSON", type=['json'])
    if uploaded_config:
        try:
            config = json.load(uploaded_config)
            
            st.session_state.warehouses = pd.DataFrame(config['warehouses'])
            st.session_state.distribution_centers = pd.DataFrame(config['distribution_centers'])
            st.session_state.demand_forecast = pd.DataFrame(config['demand_forecast'])
            
            # Import customer allocation plan if exists
            if 'customer_allocation_plan' in config:
                st.session_state.customer_allocation_plan = pd.DataFrame(config['customer_allocation_plan'])
            
            st.session_state.shipping_rate_per_100miles = config.get('shipping_rate', 0.15)
            
            st.success("✅ 配置导入成功! | Configuration imported successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ 导入失败 | Import failed: {e}")
    
    # Export results
    if 'smart_allocation' in st.session_state:
        st.markdown("---")
        st.subheader("📊 导出分析结果 | Export Analysis Results")
        
        # Prepare Excel export
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Smart allocation
            st.session_state.smart_allocation.to_excel(writer, sheet_name='Smart Allocation', index=False)
            
            # Customer allocation
            if 'customer_allocation' in st.session_state:
                st.session_state.customer_allocation.to_excel(writer, sheet_name='Customer Allocation', index=False)
            
            # Customer plan (configured by user)
            st.session_state.customer_allocation_plan.to_excel(writer, sheet_name='Customer Plan Config', index=False)
            
            # Summary sheet
            summary_data = {
                'Metric': ['Customer Current Cost', 'Smart Solution Cost', 'Savings Amount', 'Savings Percentage'],
                'Value': [
                    f"${st.session_state.get('customer_cost', 0):,.2f}",
                    f"${st.session_state.get('smart_cost', 0):,.2f}",
                    f"${st.session_state.get('customer_cost', 0) - st.session_state.get('smart_cost', 0):,.2f}",
                    f"{((st.session_state.get('customer_cost', 0) - st.session_state.get('smart_cost', 0)) / st.session_state.get('customer_cost', 1) * 100):.1f}%"
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
        
        excel_data = output.getvalue()
        
        st.download_button(
            label="⬇️ 下载Excel报告 | Download Excel Report",
            data=excel_data,
            file_name="warehouse_optimization_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Footer
st.markdown("---")
st.markdown("**© 2024 Smart Warehouse Allocation System | 智能仓库分配系统**")
st.markdown("*优化物流，降低成本，提升效率 | Optimize logistics, reduce costs, improve efficiency*")