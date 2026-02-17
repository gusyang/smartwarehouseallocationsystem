import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import linprog
import plotly.express as px
import plotly.graph_objects as go
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import json
from io import BytesIO
import time

# Page configuration
st.set_page_config(
    page_title="Smart Warehouse Allocation System", 
    layout="wide", 
    page_icon="🏭",
    initial_sidebar_state="expanded"  # 默认展开侧边栏
)

# Custom CSS for Modern UI
st.markdown("""
<style>
    /* Import modern font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #1E293B;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    /* Metric Cards Styling */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
        transition: box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    div[data-testid="stMetric"] label {
        color: #64748B;
        font-size: 0.875rem;
        font-weight: 500;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #0F172A;
        font-weight: 700;
    }
    
    /* Buttons */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        border: none;
        transition: all 0.2s;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
    }
    div.stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 8px -1px rgba(37, 99, 235, 0.3);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #e2e8f0;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        border-radius: 6px 6px 0 0;
        font-weight: 500;
        color: #64748B;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #2563EB;
        background-color: #EFF6FF;
        border-bottom: 2px solid #2563EB;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
    }
    
    /* Dataframes */
    div[data-testid="stDataFrame"] {
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state with new structure
if 'warehouses' not in st.session_state:
    st.session_state.warehouses = pd.DataFrame({
        'Name': ['EL PASO', 'Valley View', 'Seabrook', 'Cesanek'],
        'Address': [
            '12100 Emerald Pass Drive, El Paso, TX 79936',
            '6800 Valley View St, Buena Park, CA 90620',
            '300 Seabrook Parkway, Pooler, GA 31322',
            '175 Cesanek Rd., Northampton, PA 18067'
        ],
        'Current_Inventory': [500, 600, 400, 300],          # Low current inventory
        'Incoming_Week3': [200, 300, 150, 200],             # Small incoming Week 3
        'Incoming_Week4': [250, 350, 200, 250],             # Small incoming Week 4
        'Outgoing_Week1': [300, 400, 200, 150],             # Week 1 outgoing
        'Outgoing_Week2': [350, 450, 250, 200],             # Week 2 outgoing
        'Capacity': [10000, 12000, 9000, 11000],            # High capacity for shipping
    })

if 'distribution_centers' not in st.session_state:
    st.session_state.distribution_centers = pd.DataFrame({
        'Channel': ['Amazon', 'Walmart', 'Target', 'Amazon'],
        'State': ['CA', 'TX', 'GA', 'PA'],
        'Address': ['San Francisco, CA', 'Dallas, TX', 'Atlanta, GA', 'Philadelphia, PA']
    })

if 'demand_forecast' not in st.session_state:
    st.session_state.demand_forecast = pd.DataFrame({
        'Product': ['32Q21K', '32Q21K', '32Q21K', '32Q21K'],
        'Channel': ['Amazon', 'Walmart', 'Target', 'Amazon'],
        'State': ['CA', 'TX', 'GA', 'PA'],
        'Demand_Week3': [2200, 1800, 1600, 1900],           # Total: 7,500
        'Demand_Week4': [2300, 1900, 1700, 2000]            # Total: 7,900
    })

# Shipping rates - Market (customer current) vs TMS (smart suggestion)
if 'market_shipping_rate' not in st.session_state:
    st.session_state.market_shipping_rate = 0.18  # $/unit/100miles

if 'tms_shipping_rate' not in st.session_state:
    st.session_state.tms_shipping_rate = 0.12  # $/unit/100miles (better rate)

if 'customer_allocation_plan' not in st.session_state:
    # Initialize with customer default warehouses
    st.session_state.customer_allocation_plan = pd.DataFrame({
        'Product': ['32Q21K', '32Q21K', '32Q21K', '32Q21K'],
        'Warehouse': ['Valley View', 'EL PASO', 'EL PASO', 'Cesanek'],
        'Channel': ['Amazon', 'Walmart', 'Target', 'Amazon'],
        'State': ['CA', 'TX', 'GA', 'PA'],
        'Allocated_Units_Week3': [2200, 1800, 1600, 1900],
        'Allocated_Units_Week4': [2300, 1900, 1700, 2000]
    })

if 'customer_plan_mode' not in st.session_state:
    st.session_state.customer_plan_mode = 'auto'  # 'auto' or 'manual'

if 'customer_selected_warehouses' not in st.session_state:
    st.session_state.customer_selected_warehouses = st.session_state.warehouses['Name'].tolist()


@st.cache_data
def geocode_address(address):
    """Convert address to coordinates (中文: 将地址转换为坐标)"""
    # Respect Nominatim usage policy (max 1 request/sec) to avoid 429 errors
    time.sleep(1.1)
    try:
        geolocator = Nominatim(user_agent="smart_warehouse_optimizer_app_v2_cloud")
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except Exception as e:
        st.warning(f"Geocoding failed (地址解析失败): {address} - {e}")
        return None, None


def calculate_distance_from_addresses(address1, address2, cache={}):
    """Calculate distance between two addresses with caching (中文: 计算两地址间距离，带缓存)"""
    cache_key = f"{address1}|{address2}"
    
    if cache_key in cache:
        return cache[cache_key]
    
    lat1, lon1 = geocode_address(address1)
    lat2, lon2 = geocode_address(address2)
    
    if lat1 is None or lat2 is None:
        cache[cache_key] = 500.0
        return 500.0
    
    distance = geodesic((lat1, lon1), (lat2, lon2)).miles
    cache[cache_key] = distance
    
    return distance


def calculate_distance_matrix():
    """Calculate distance matrix from warehouses to DCs (中文: 计算仓库到DC的距离矩阵)"""
    warehouses = st.session_state.warehouses
    dcs = st.session_state.distribution_centers
    
    distances = []
    distance_cache = {}
    
    total_pairs = len(warehouses) * len(dcs)
    progress_text = "Calculating distances (计算距离中)..."
    
    if total_pairs > 10:
        progress_bar = st.progress(0, text=progress_text)
    else:
        progress_bar = None
    
    current_pair = 0
    
    for _, wh in warehouses.iterrows():
        wh_address = wh['Address']
        
        for _, dc in dcs.iterrows():
            dc_address = dc['Address']
            
            dist = calculate_distance_from_addresses(wh_address, dc_address, distance_cache)
            
            distances.append({
                'Warehouse': wh['Name'],
                'Warehouse_Address': wh_address,
                'DC_Channel': dc['Channel'],
                'DC_State': dc['State'],
                'DC_Address': dc_address,
                'Distance_Miles': dist
            })
            
            current_pair += 1
            if progress_bar:
                progress_bar.progress(current_pair / total_pairs, text=progress_text)
    
    if progress_bar:
        progress_bar.empty()
    
    return pd.DataFrame(distances)


def calculate_shipping_costs(distance_matrix, rate_per_unit_per_100miles):
    """Calculate shipping costs (中文: 计算运输成本)"""
    costs = distance_matrix.copy()
    costs['Cost_Per_Unit'] = costs['Distance_Miles'] * rate_per_unit_per_100miles / 100
    return costs


def calculate_available_inventory(week):
    """
    Calculate available inventory for a specific week (中文: 计算特定周的可用库存)
    Week 3 or Week 4
    """
    warehouses = st.session_state.warehouses
    
    inventory = warehouses[['Name', 'Current_Inventory']].copy()
    
    if week == 3:
        # Week 3: Current + Incoming_Week3 - Outgoing_Week1 - Outgoing_Week2
        inventory['Available'] = (
            warehouses['Current_Inventory'] +
            warehouses['Incoming_Week3'] -
            warehouses['Outgoing_Week1'] -
            warehouses['Outgoing_Week2']
        )
    elif week == 4:
        # Week 4: Current + Incoming_Week3 + Incoming_Week4 - Outgoing_Week1 - Outgoing_Week2
        inventory['Available'] = (
            warehouses['Current_Inventory'] +
            warehouses['Incoming_Week3'] +
            warehouses['Incoming_Week4'] -
            warehouses['Outgoing_Week1'] -
            warehouses['Outgoing_Week2']
        )
    else:
        inventory['Available'] = warehouses['Current_Inventory']
    
    return inventory


def optimize_allocation_multi_week():
    """
    Optimize allocation for both Week 3 and Week 4
    Logic: Calculate how much to ship TO each warehouse to meet demand
    (中文: 优化第3周和第4周的分配 - 计算需要发货到每个仓库的量来满足需求)
    """
    warehouses = st.session_state.warehouses
    demand = st.session_state.demand_forecast
    distance_matrix = calculate_distance_matrix()
    
    rate = st.session_state.tms_shipping_rate
    shipping_costs = calculate_shipping_costs(distance_matrix, rate)
    
    results = {}
    
    for week in [3, 4]:
        demand_col = f'Demand_Week{week}'
        
        # Get available inventory for this week (what's already in warehouse)
        inventory = calculate_available_inventory(week)
        
        allocation_data = []
        
        for _, d in demand.iterrows():
            channel = d['Channel']
            state = d['State']
            demand_units = d[demand_col]
            product = d['Product']
            
            # Find all warehouse-DC pairs for this demand
            relevant_costs = shipping_costs[
                (shipping_costs['DC_Channel'] == channel) & 
                (shipping_costs['DC_State'] == state)
            ]
            
            for _, cost in relevant_costs.iterrows():
                wh_name = cost['Warehouse']
                
                # Get current available inventory for this warehouse
                wh_inventory = inventory[inventory['Name'] == wh_name]['Available'].values
                if len(wh_inventory) > 0:
                    current_available = wh_inventory[0]
                else:
                    current_available = 0
                
                allocation_data.append({
                    'Product': product,
                    'Warehouse': wh_name,
                    'Channel': channel,
                    'State': state,
                    'Demand': demand_units,
                    'Cost_Per_Unit': cost['Cost_Per_Unit'],
                    'Distance_Miles': cost['Distance_Miles'],
                    'Current_Available': current_available
                })
        
        allocation_df = pd.DataFrame(allocation_data)
        
        if allocation_df.empty:
            results[week] = (None, None)
            continue
        
        n_vars = len(allocation_df)
        c = allocation_df['Cost_Per_Unit'].values
        
        # Demand constraints - MUST meet all demand
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
        
        # Warehouse capacity constraints - can ship UP TO capacity
        # (but we want to minimize shipping, so optimizer will choose minimum needed)
        capacity_constraints = []
        capacity_bounds = []
        
        for wh_name in warehouses['Name']:
            constraint = np.zeros(n_vars)
            mask = allocation_df['Warehouse'] == wh_name
            constraint[mask] = 1
            capacity_constraints.append(constraint)
            
            # Max capacity for shipping TO this warehouse
            wh_capacity = warehouses[warehouses['Name'] == wh_name]['Capacity'].values
            if len(wh_capacity) > 0:
                capacity_bounds.append(wh_capacity[0])
            else:
                capacity_bounds.append(100000)  # Large number if not found
        
        A_eq = np.array(demand_constraints) if demand_constraints else None
        b_eq = np.array(demand_bounds) if demand_bounds else None
        
        A_ub = np.array(capacity_constraints) if capacity_constraints else None
        b_ub = np.array(capacity_bounds) if capacity_bounds else None
        
        bounds = [(0, None) for _ in range(n_vars)]
        
        # Solve the optimization
        try:
            if A_eq is not None and A_ub is not None:
                result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, 
                                bounds=bounds, method='highs')
            elif A_eq is not None:
                result = linprog(c, A_eq=A_eq, b_eq=b_eq, 
                                bounds=bounds, method='highs')
            else:
                result = None
            
            if result and result.success:
                allocation_df['Allocated_Units'] = result.x
                allocation_df['Total_Cost'] = allocation_df['Allocated_Units'] * allocation_df['Cost_Per_Unit']
                
                # Filter out very small allocations
                allocation_df = allocation_df[allocation_df['Allocated_Units'] > 0.01].copy()
                
                # Add "Ship Required" column - how much needs to be shipped TO warehouse
                allocation_df['Ship_Required'] = allocation_df.apply(
                    lambda row: max(0, row['Allocated_Units'] - row['Current_Available']), 
                    axis=1
                )
                
                total_cost = result.fun
                results[week] = (allocation_df, total_cost)
            else:
                results[week] = (None, None)
        except Exception as e:
            st.error(f"Optimization error for Week {week}: {str(e)}")
            results[week] = (None, None)
    
    return results


def calculate_customer_cost_multi_week():
    """
    Calculate customer current cost for both weeks
    Supports two modes:
    - Auto: Optimize allocation from customer default warehouses to all DCs
    - Manual: Use pre-configured allocation plan
    (中文: 计算客户当前方案成本 - 支持自动和手动两种模式)
    """
    return calculate_customer_cost_manual()


def calculate_customer_cost_manual():
    """Use manually configured customer allocation plan (使用手动配置的方案)"""
    customer_plan = st.session_state.customer_allocation_plan
    distance_matrix = calculate_distance_matrix()
    
    rate = st.session_state.market_shipping_rate
    shipping_costs = calculate_shipping_costs(distance_matrix, rate)
    
    # Get customer default warehouses for validation
    customer_default_warehouses = st.session_state.get('customer_selected_warehouses', [])
    
    results = {}
    
    for week in [3, 4]:
        alloc_col = f'Allocated_Units_Week{week}'
        
        customer_allocation = []
        
        for _, plan in customer_plan.iterrows():
            product = plan['Product']
            warehouse = plan['Warehouse']
            channel = plan['Channel']
            state = plan['State']
            allocated_units = plan[alloc_col]
            
            # Warning if using non-default warehouse
            if warehouse not in customer_default_warehouses:
                st.warning(f"⚠️ {warehouse} for {channel}-{state} is not a Customer Default warehouse")
            
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
        
        customer_df = pd.DataFrame(customer_allocation)
        total_cost = customer_df['Total_Cost'].sum() if not customer_df.empty else 0
        
        results[week] = (customer_df, total_cost)
    
    return results


def calculate_customer_cost_auto(selected_warehouses=None):
    """
    Auto-optimize allocation from selected customer warehouses to all DCs
    (自动优化从选定的客户仓库到所有DC的分配)
    
    NOTE: For Customer Plan, we IGNORE capacity constraints.
    We assume the customer forces shipment from these locations (implying replenishment if needed),
    which highlights the high cost of suboptimal warehouse selection.
    """
    warehouses = st.session_state.warehouses
    demand = st.session_state.demand_forecast
    distance_matrix = calculate_distance_matrix()
    
    rate = st.session_state.market_shipping_rate
    shipping_costs = calculate_shipping_costs(distance_matrix, rate)
    
    # Use provided selection or fallback to all defaults
    if selected_warehouses is None:
        target_warehouses = st.session_state.get('customer_selected_warehouses', warehouses['Name'].tolist())
    else:
        target_warehouses = selected_warehouses
    
    if not target_warehouses:
        st.warning("⚠️ No Customer Default warehouses selected.")
        return {3: (None, 0), 4: (None, 0)}
    
    results = {}
    
    for week in [3, 4]:
        demand_col = f'Demand_Week{week}'
        
        # Get available inventory (just for reference in result, not for constraint)
        inventory = calculate_available_inventory(week)
        
        allocation_data = []
        
        # For each demand (DC), consider only the selected warehouses
        for _, d in demand.iterrows():
            channel = d['Channel']
            state = d['State']
            demand_units = d[demand_col]
            product = d['Product']
            
            # Find shipping costs from target warehouses to this DC
            relevant_costs = shipping_costs[
                (shipping_costs['DC_Channel'] == channel) & 
                (shipping_costs['DC_State'] == state) &
                (shipping_costs['Warehouse'].isin(target_warehouses))
            ]
            
            for _, cost in relevant_costs.iterrows():
                wh_name = cost['Warehouse']
                
                # Get current available inventory
                wh_inventory = inventory[inventory['Name'] == wh_name]['Available'].values
                if len(wh_inventory) > 0:
                    current_available = wh_inventory[0]
                else:
                    current_available = 0
                
                allocation_data.append({
                    'Product': product,
                    'Warehouse': wh_name,
                    'Channel': channel,
                    'State': state,
                    'Demand': demand_units,
                    'Cost_Per_Unit': cost['Cost_Per_Unit'],
                    'Distance_Miles': cost['Distance_Miles'],
                    'Current_Available': current_available
                })
        
        allocation_df = pd.DataFrame(allocation_data)
        
        if allocation_df.empty:
            results[week] = (None, 0)
            continue
        
        n_vars = len(allocation_df)
        c = allocation_df['Cost_Per_Unit'].values
        
        # Demand constraints - MUST meet all demand
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
        
        # NO CAPACITY CONSTRAINTS for Customer Plan
        # We assume customer forces shipment regardless of inventory
        
        A_eq = np.array(demand_constraints) if demand_constraints else None
        b_eq = np.array(demand_bounds) if demand_bounds else None
        
        bounds = [(0, None) for _ in range(n_vars)]
        
        # Solve optimization for customer's warehouses
        try:
            # Use highs method
            result = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
            
            if result and result.success:
                allocation_df['Allocated_Units'] = result.x
                allocation_df['Total_Cost'] = allocation_df['Allocated_Units'] * allocation_df['Cost_Per_Unit']
                
                # Filter out very small allocations
                allocation_df = allocation_df[allocation_df['Allocated_Units'] > 0.01].copy()
                
                total_cost = result.fun
                results[week] = (allocation_df, total_cost)
            else:
                st.error(f"Failed to optimize customer allocation for Week {week}. Check if selected warehouses can reach all DCs.")
                results[week] = (None, 0)
        except Exception as e:
            st.error(f"Customer allocation error for Week {week}: {str(e)}")
            results[week] = (None, 0)
    
    return results


# UI Layout
st.markdown("""
    <div style='text-align: center; padding-bottom: 20px; padding-top: 10px;'>
        <h1 style='color: #1E293B; margin-bottom: 0.5rem;'>🏭 Smart Warehouse Allocation System</h1>
        <p style='color: #64748B; font-size: 1.1em; font-weight: 500;'>Intelligent 3PL Planning Solution - Optimize Costs, Improve Efficiency</p>
        <p style='color: #94A3B8; font-size: 0.9em;'>智能3PL规划方案 - 优化成本，提升效率</p>
    </div>
""", unsafe_allow_html=True)

# Sidebar navigation - 默认展开
st.sidebar.title("Navigation (导航)")
page = st.sidebar.radio(
    "Select Page (选择页面)",
    ["📊 Configuration", "🤖 Run Scenarios", "📈 Cost Comparison", "📁 Data Management"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.info("""
**Quick Guide (快速指南)**

1. Configure warehouses & DCs
2. Set demand forecast
3. Run optimization
4. Compare costs
""")

# Configuration Page
if page == "📊 Configuration":
    st.header("📊 System Configuration")
    st.markdown("*系统配置*")
    
    # Display persistent success message (显示持久化成功消息)
    if 'success_msg' in st.session_state:
        st.success(st.session_state.success_msg)
        del st.session_state.success_msg
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Warehouses (仓库)", 
        "Distribution Centers (配送中心)", 
        "Demand Forecast (需求预测)", 
        "Shipping Rates (运费)",
        "Customer Current Plan (客户当前方案)"
    ])
    
    with tab1:
        st.subheader("Warehouse Management (仓库管理)")
        
        # Display current warehouses
        st.markdown("**Current Warehouses (当前仓库列表)**")
        display_wh = st.session_state.warehouses.copy()
        
        # Add summary row
        summary_row = pd.DataFrame({
            'Name': ['** TOTAL **'],
            'Address': ['All Warehouses'],
            'Current_Inventory': [st.session_state.warehouses['Current_Inventory'].sum()],
            'Incoming_Week3': [st.session_state.warehouses['Incoming_Week3'].sum()],
            'Incoming_Week4': [st.session_state.warehouses['Incoming_Week4'].sum()],
            'Outgoing_Week1': [st.session_state.warehouses['Outgoing_Week1'].sum()],
            'Outgoing_Week2': [st.session_state.warehouses['Outgoing_Week2'].sum()],
            'Capacity': [st.session_state.warehouses['Capacity'].sum()]
        })
        display_wh_with_summary = pd.concat([display_wh, summary_row], ignore_index=True)
        
        st.dataframe(display_wh_with_summary, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        with st.expander("✏️ Edit Warehouses (编辑仓库)", expanded=False):
            st.markdown("""
            **Instructions (操作说明)**:
            - Edit inventory levels (编辑库存水平)
            - Week 1 & 2: Outgoing inventory (第1-2周: 出库)
            - Week 3 & 4: Incoming inventory (第3-4周: 入库)
            """)
            
            edited_wh = st.data_editor(
                st.session_state.warehouses,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Name": st.column_config.TextColumn("Warehouse Name (仓库名)", required=True),
                    "Address": st.column_config.TextColumn("Address (地址)", required=True),
                    "Current_Inventory": st.column_config.NumberColumn("Current Inventory (当前库存)", min_value=0, step=100),
                    "Incoming_Week3": st.column_config.NumberColumn("Incoming Week 3 (第3周入库)", min_value=0, step=50),
                    "Incoming_Week4": st.column_config.NumberColumn("Incoming Week 4 (第4周入库)", min_value=0, step=50),
                    "Outgoing_Week1": st.column_config.NumberColumn("Outgoing Week 1 (第1周出库)", min_value=0, step=50),
                    "Outgoing_Week2": st.column_config.NumberColumn("Outgoing Week 2 (第2周出库)", min_value=0, step=50),
                    "Capacity": st.column_config.NumberColumn("Max Capacity (最大容量)", min_value=0, step=100)
                }
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save Changes (保存更改)", type="primary", use_container_width=True):
                    st.session_state.warehouses = edited_wh
                    st.session_state.success_msg = "✅ Warehouses saved successfully! (仓库已保存!)"
                    st.rerun()
            
            with col2:
                if st.button("🔄 Reset to Default (恢复默认)", use_container_width=True):
                    st.session_state.warehouses = pd.DataFrame({
                        'Name': ['EL PASO', 'Valley View', 'Seabrook', 'Cesanek'],
                        'Address': [
                            '12100 Emerald Pass Drive, El Paso, TX 79936',
                            '6800 Valley View St, Buena Park, CA 90620',
                            '300 Seabrook Parkway, Pooler, GA 31322',
                            '175 Cesanek Rd., Northampton, PA 18067'
                        ],
                        'Current_Inventory': [500, 600, 400, 300],
                        'Incoming_Week3': [200, 300, 150, 200],
                        'Incoming_Week4': [250, 350, 200, 250],
                        'Outgoing_Week1': [300, 400, 200, 150],
                        'Outgoing_Week2': [350, 450, 250, 200],
                        'Capacity': [10000, 12000, 9000, 11000]
                    })
                    st.session_state.success_msg = "✅ Warehouses reset to default! (仓库已恢复默认!)"
                    st.rerun()
        
        # Inventory projection
        st.markdown("---")
        st.markdown("**📊 Inventory Projection (库存预测)**")
        
        # Show Selected Customer warehouses
        selected_whs = st.session_state.get('customer_selected_warehouses', [])
        
        if selected_whs:
            st.info(f"**Selected Customer Warehouses (选定的客户仓库)**: {', '.join(selected_whs)}")
        else:
            st.warning("⚠️ **No Customer warehouses selected!** Please configure in 'Customer Current Plan' tab. (请在'客户当前方案'标签页选择仓库)")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Week 3 Available (第3周可用库存)**")
            inv3 = calculate_available_inventory(3)
            
            # Add summary row
            summary_row = pd.DataFrame({
                'Name': ['** TOTAL **'],
                'Current_Inventory': [st.session_state.warehouses['Current_Inventory'].sum()],
                'Available': [inv3['Available'].sum()]
            })
            inv3_display = pd.concat([inv3, summary_row], ignore_index=True)
            
            st.dataframe(inv3_display, use_container_width=True, hide_index=True)
            
            # Additional metrics
            total_available_w3 = inv3['Available'].sum()
            total_demand_w3 = st.session_state.demand_forecast['Demand_Week3'].sum() if not st.session_state.demand_forecast.empty else 0
            coverage_w3 = (total_available_w3 / total_demand_w3 * 100) if total_demand_w3 > 0 else 0
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Total Available (总可用)", f"{total_available_w3:,}")
            with col_b:
                if total_demand_w3 > 0:
                    diff_w3 = total_available_w3 - total_demand_w3
                    st.metric("vs Demand (vs 需求)", f"{diff_w3:+,}", 
                             delta=f"{coverage_w3:.0f}% coverage",
                             delta_color="normal" if diff_w3 >= 0 else "inverse")
        
        with col2:
            st.markdown("**Week 4 Available (第4周可用库存)**")
            inv4 = calculate_available_inventory(4)
            
            # Add summary row
            summary_row = pd.DataFrame({
                'Name': ['** TOTAL **'],
                'Current_Inventory': [st.session_state.warehouses['Current_Inventory'].sum()],
                'Available': [inv4['Available'].sum()]
            })
            inv4_display = pd.concat([inv4, summary_row], ignore_index=True)
            
            st.dataframe(inv4_display, use_container_width=True, hide_index=True)
            
            # Additional metrics
            total_available_w4 = inv4['Available'].sum()
            total_demand_w4 = st.session_state.demand_forecast['Demand_Week4'].sum() if not st.session_state.demand_forecast.empty else 0
            coverage_w4 = (total_available_w4 / total_demand_w4 * 100) if total_demand_w4 > 0 else 0
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Total Available (总可用)", f"{total_available_w4:,}")
            with col_b:
                if total_demand_w4 > 0:
                    diff_w4 = total_available_w4 - total_demand_w4
                    st.metric("vs Demand (vs 需求)", f"{diff_w4:+,}", 
                             delta=f"{coverage_w4:.0f}% coverage",
                             delta_color="normal" if diff_w4 >= 0 else "inverse")
    
    with tab2:
        st.subheader("Distribution Center Management (配送中心管理)")
        
        # Display current DCs
        st.markdown("**Current Distribution Centers (当前配送中心列表)**")
        
        dc_display = st.session_state.distribution_centers.copy()
        summary_row = pd.DataFrame({
            'Channel': [f'** TOTAL: {len(dc_display)} DCs **'],
            'State': [f'{dc_display["State"].nunique()} States'],
            'Address': ['Multiple Locations']
        })
        dc_with_summary = pd.concat([dc_display, summary_row], ignore_index=True)
        
        st.dataframe(dc_with_summary, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        with st.expander("✏️ Edit Distribution Centers (编辑配送中心)", expanded=False):
            edited_dc = st.data_editor(
                st.session_state.distribution_centers,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Channel": st.column_config.TextColumn("Channel (渠道)"),
                    "State": st.column_config.TextColumn("State (州)"),
                    "Address": st.column_config.TextColumn("Address (地址)", required=True)
                }
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save DC Changes (保存DC更改)", type="primary", use_container_width=True):
                    st.session_state.distribution_centers = edited_dc
                    st.session_state.success_msg = "✅ Distribution Centers saved! (配送中心已保存!)"
                    st.rerun()
            
            with col2:
                if st.button("🔄 Reset DCs (恢复默认DC)", use_container_width=True):
                    st.session_state.distribution_centers = pd.DataFrame({
                        'Channel': ['Amazon', 'Walmart', 'Target', 'Amazon'],
                        'State': ['CA', 'TX', 'GA', 'PA'],
                        'Address': ['San Francisco, CA', 'Dallas, TX', 'Atlanta, GA', 'Philadelphia, PA']
                    })
                    st.session_state.success_msg = "✅ Distribution Centers reset! (配送中心已恢复默认!)"
                    st.rerun()
    
    with tab3:
        st.subheader("Demand Forecast (需求预测)")
        
        # Display current demand
        st.markdown("**Current Demand Forecast (当前需求预测)**")
        
        # Add summary row to demand display
        demand_display = st.session_state.demand_forecast.copy()
        summary_row = pd.DataFrame({
            'Product': ['** TOTAL **'],
            'Channel': ['All Channels'],
            'State': ['All States'],
            'Demand_Week3': [demand_display['Demand_Week3'].sum()],
            'Demand_Week4': [demand_display['Demand_Week4'].sum()]
        })
        demand_with_summary = pd.concat([demand_display, summary_row], ignore_index=True)
        
        st.dataframe(demand_with_summary, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        with st.expander("✏️ Edit Demand Forecast (编辑需求预测)", expanded=False):
            st.info("💡 Enter demand for Week 3 and Week 4 only (仅输入第3周和第4周的需求)")
            
            edited_demand = st.data_editor(
                st.session_state.demand_forecast,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Product": st.column_config.TextColumn("Product (产品)"),
                    "Channel": st.column_config.TextColumn("Channel (渠道)"),
                    "State": st.column_config.TextColumn("State (州)"),
                    "Demand_Week3": st.column_config.NumberColumn("Week 3 Demand (第3周需求)", min_value=0, step=100),
                    "Demand_Week4": st.column_config.NumberColumn("Week 4 Demand (第4周需求)", min_value=0, step=100)
                }
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save Demand (保存需求)", type="primary", use_container_width=True):
                    st.session_state.demand_forecast = edited_demand
                    st.session_state.success_msg = "✅ Demand forecast saved! (需求预测已保存!)"
                    st.rerun()
            
            with col2:
                if st.button("🔄 Reset Demand (恢复默认)", use_container_width=True, key="reset_demand"):
                    st.session_state.demand_forecast = pd.DataFrame({
                        'Product': ['32Q21K', '32Q21K', '32Q21K', '32Q21K'],
                        'Channel': ['Amazon', 'Walmart', 'Target', 'Amazon'],
                        'State': ['CA', 'TX', 'GA', 'PA'],
                        'Demand_Week3': [2200, 1800, 1600, 1900],
                        'Demand_Week4': [2300, 1900, 1700, 2000]
                    })
                    st.session_state.success_msg = "✅ Demand forecast reset! (需求预测已恢复默认!)"
                    st.rerun()
        
        # Show total demand
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            total_w3 = st.session_state.demand_forecast['Demand_Week3'].sum()
            st.metric("Total Week 3 Demand (第3周总需求)", f"{total_w3:,}")
        with col2:
            total_w4 = st.session_state.demand_forecast['Demand_Week4'].sum()
            st.metric("Total Week 4 Demand (第4周总需求)", f"{total_w4:,}")
    
    with tab4:
        st.subheader("Shipping Rates Configuration (运费配置)")
        
        st.markdown("""
        **Two Rate Types (两种费率类型)**:
        - **Market Rates**: Used for customer current plan (客户当前方案使用的市场费率)
        - **TMS Rates**: Used for smart suggestion (智能方案使用的TMS优惠费率)
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📦 Market Shipping Rates (市场运费)**")
            market_rate = st.number_input(
                "Market Rate ($/unit/100 miles) - 市场费率",
                min_value=0.01,
                max_value=1.0,
                value=st.session_state.market_shipping_rate,
                step=0.01,
                key="market_rate_input",
                help="Used for customer current cost calculation (用于客户当前成本计算)"
            )
            st.session_state.market_shipping_rate = market_rate
            st.info(f"Current: ${market_rate}/unit/100mi")
        
        with col2:
            st.markdown("**🚚 TMS Shipping Rates (TMS运费)**")
            tms_rate = st.number_input(
                "TMS Rate ($/unit/100 miles) - TMS费率",
                min_value=0.01,
                max_value=1.0,
                value=st.session_state.tms_shipping_rate,
                step=0.01,
                key="tms_rate_input",
                help="Used for smart suggestion calculation (用于智能方案成本计算)"
            )
            st.session_state.tms_shipping_rate = tms_rate
            st.info(f"Current: ${tms_rate}/unit/100mi")
        
        st.markdown("---")
        
        rate_diff = market_rate - tms_rate
        rate_diff_pct = (rate_diff / market_rate * 100) if market_rate > 0 else 0
        
        if rate_diff > 0:
            st.success(f"""
            ✅ **TMS Rate Advantage (TMS费率优势)**
            
            TMS rate is **${rate_diff:.3f}** ({rate_diff_pct:.1f}%) lower than market rate
            
            TMS费率比市场费率低 **${rate_diff:.3f}** ({rate_diff_pct:.1f}%)
            """)
        elif rate_diff < 0:
            st.warning(f"⚠️ TMS rate is higher than market rate (TMS费率高于市场费率)")
        else:
            st.info("ℹ️ TMS rate equals market rate (TMS费率等于市场费率)")
    
    with tab5:
        st.subheader("Customer Current Plan Configuration (客户当前方案配置)")
        
        # Get all available warehouses
        all_warehouses = st.session_state.warehouses['Name'].tolist()
        
        # 1. Select Warehouses for Plan
        st.markdown("**1. Select Customer Warehouses (选择客户仓库)**")
        
        # Get current saved selection, defaulting to all if not set
        current_selection = st.session_state.get('customer_selected_warehouses', all_warehouses)
        valid_defaults = [w for w in current_selection if w in all_warehouses]
        
        selected_plan_whs = st.multiselect(
            "Choose warehouses to use (选择要使用的仓库):",
            options=all_warehouses,
            default=valid_defaults,
            key="customer_selected_warehouses_widget",
            help="Select warehouses to fulfill demand. (选择用于满足需求的仓库)"
        )
        
        # Update the persistent state
        st.session_state.customer_selected_warehouses = selected_plan_whs
        
        if selected_plan_whs:
            st.caption(f"**Selected for Plan:** {', '.join(selected_plan_whs)}")
        else:
            st.warning("⚠️ No warehouses selected!")
        
        if st.button("⚡ Generate Plan (生成方案)", type="primary", help="Assign demand to nearest selected warehouse (将需求分配给最近的选定仓库)"):
            if not selected_plan_whs:
                st.error("⚠️ Please select at least one warehouse first. (请先选择至少一个仓库)")
            else:
                # Auto-allocate logic (Nearest Neighbor)
                demand = st.session_state.demand_forecast
                distance_matrix = calculate_distance_matrix()
                rate = st.session_state.market_shipping_rate
                shipping_costs = calculate_shipping_costs(distance_matrix, rate)
                
                new_plan_rows = []
                
                for _, d in demand.iterrows():
                    channel = d['Channel']
                    state = d['State']
                    product = d['Product']
                    
                    # Find nearest selected warehouse
                    relevant_costs = shipping_costs[
                        (shipping_costs['DC_Channel'] == channel) & 
                        (shipping_costs['DC_State'] == state) &
                        (shipping_costs['Warehouse'].isin(selected_plan_whs))
                    ].sort_values('Distance_Miles')
                    
                    if not relevant_costs.empty:
                        nearest_wh = relevant_costs.iloc[0]['Warehouse']
                        
                        new_plan_rows.append({
                            'Product': product,
                            'Warehouse': nearest_wh,
                            'Channel': channel,
                            'State': state,
                            'Allocated_Units_Week3': d['Demand_Week3'],
                            'Allocated_Units_Week4': d['Demand_Week4']
                        })
                
                st.session_state.customer_allocation_plan = pd.DataFrame(new_plan_rows)
                st.session_state.success_msg = f"✅ Plan generated using {len(selected_plan_whs)} warehouses. (方案已生成!)"
                st.rerun()
        
        # 3. Editor
        st.markdown("---")
        st.markdown("**2. Edit Allocation Plan (编辑分配方案)**")
        
        # Show warehouses actually used in the plan
        if not st.session_state.customer_allocation_plan.empty:
            used_whs = sorted(st.session_state.customer_allocation_plan['Warehouse'].unique().tolist())
            st.info(f"**Warehouses in Current Plan (当前方案使用的仓库):** {', '.join(used_whs)}")
            
        st.info("Adjust the quantities below. Total allocated must meet demand. (调整下方数量。总分配量必须满足需求。)")
        
        edited_plan = st.data_editor(
            st.session_state.customer_allocation_plan,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Product": st.column_config.TextColumn("Product"),
                "Warehouse": st.column_config.TextColumn("Warehouse"),
                "Channel": st.column_config.TextColumn("Channel"),
                "State": st.column_config.TextColumn("State"),
                "Allocated_Units_Week3": st.column_config.NumberColumn("Week 3 Qty", min_value=0, step=100),
                "Allocated_Units_Week4": st.column_config.NumberColumn("Week 4 Qty", min_value=0, step=100)
            }
        )
        
        # Save button for manual edits
        if st.button("💾 Save Changes (保存更改)", type="primary"):
            st.session_state.customer_allocation_plan = edited_plan
            st.session_state.success_msg = "✅ Allocation plan saved! (分配方案已保存!)"
            st.rerun()
        
        # 4. Validation Display
        st.markdown("---")
        st.markdown("**3. Validation (验证)**")
        
        demand = st.session_state.demand_forecast
        plan = st.session_state.customer_allocation_plan
        
        validation_data = []
        all_valid = True
        
        for _, d in demand.iterrows():
            channel = d['Channel']
            state = d['State']
            
            # Filter plan for this DC
            dc_plan = plan[
                (plan['Channel'] == channel) & 
                (plan['State'] == state)
            ]
            
            for week in [3, 4]:
                req = d[f'Demand_Week{week}']
                alloc = dc_plan[f'Allocated_Units_Week{week}'].sum()
                
                status = "✅ OK"
                if alloc < req:
                    status = f"❌ Low ({alloc-req:+.0f})"
                    all_valid = False
                elif alloc > req:
                    status = f"⚠️ High ({alloc-req:+.0f})"
                
                validation_data.append({
                    'DC': f"{channel}-{state}",
                    'Week': f"Week {week}",
                    'Demand': req,
                    'Allocated': alloc,
                    'Status': status
                })
        
        val_df = pd.DataFrame(validation_data)
        
        # Display validation table with styling
        st.dataframe(
            val_df.style.map(lambda x: 'color: red' if '❌' in str(x) else ('color: orange' if '⚠️' in str(x) else 'color: green'), subset=['Status']),
            use_container_width=True,
            hide_index=True
        )
        
        if not all_valid:
            st.error("❌ Some demands are not fully met! Please adjust allocation above. (部分需求未满足，请调整分配)")
        else:
            st.success("✅ All demands met! (所有需求已满足)")



# Run Scenarios Page (Renamed from Smart Suggestion)
elif page == "🤖 Run Scenarios":
    st.header("🤖 Run Scenarios & Calculations")
    st.markdown("*运行场景与计算*")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Customer Current Plan")
        st.markdown("Calculate cost based on your configuration in 'Customer Current Plan' tab.")
        
        if st.button("💼 Calculate Customer Cost (计算客户成本)", type="primary", use_container_width=True):
            with st.spinner("Calculating customer cost..."):
                results = calculate_customer_cost_multi_week()
                st.session_state.customer_results = results
                
                total = sum(cost for _, cost in results.values())
                st.success(f"✅ Customer Total Cost: ${total:,.2f}")
                
    with col2:
        st.subheader("2. Smart Optimization")
        st.markdown("Run AI optimization to find the best allocation using all warehouses.")
        
        if st.button("🚀 Run Smart Optimization (运行智能优化)", type="primary", use_container_width=True):
            with st.spinner("Optimizing allocation..."):
                results = optimize_allocation_multi_week()
                st.session_state.smart_results = results
                
                total = sum(cost for _, cost in results.values() if cost is not None)
                st.success(f"✅ Smart Solution Total Cost: ${total:,.2f}")
    
    st.markdown("---")
    
    # Display Results Summary if available
    if 'customer_results' in st.session_state or 'smart_results' in st.session_state:
        st.subheader("📊 Calculation Results Summary")
        
        c1, c2 = st.columns(2)
        
        with c1:
            if 'customer_results' in st.session_state:
                st.markdown("**Customer Plan Results**")
                cust_total = sum(cost for _, cost in st.session_state.customer_results.values())
                st.info(f"Total Cost: **${cust_total:,.2f}**")
                
                # Show brief breakdown
                for week in [3, 4]:
                    _, cost = st.session_state.customer_results.get(week, (None, 0))
                    st.caption(f"Week {week}: ${cost:,.2f}")
            else:
                st.warning("Customer cost not calculated yet.")

        with c2:
            if 'smart_results' in st.session_state:
                st.markdown("**Smart Optimization Results**")
                smart_total = sum(cost for _, cost in st.session_state.smart_results.values() if cost is not None)
                st.success(f"Total Cost: **${smart_total:,.2f}**")
                
                # Show brief breakdown
                for week in [3, 4]:
                    _, cost = st.session_state.smart_results.get(week, (None, 0))
                    st.caption(f"Week {week}: ${cost:,.2f}")
            else:
                st.warning("Smart optimization not run yet.")
                
        if 'customer_results' in st.session_state and 'smart_results' in st.session_state:
            st.markdown("---")
            st.info("👉 Go to **Cost Comparison** page for detailed analysis.")

    # Display Customer Allocation Details
    if 'customer_results' in st.session_state:
        st.markdown("---")
        st.subheader("📋 Customer Allocation Details")
        
        tab1, tab2 = st.tabs(["Week 3 Results (第3周结果)", "Week 4 Results (第4周结果)"])
        
        for idx, week in enumerate([3, 4]):
            with [tab1, tab2][idx]:
                allocation_df, total_cost = st.session_state.customer_results.get(week, (None, None))
                
                if allocation_df is not None:
                    st.subheader(f"Week {week} Customer Allocation (第{week}周客户分配)")
                    
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.metric("Total Cost (总成本)", f"${total_cost:,.2f}", help="Using Market rates (使用市场费率)")
                    with col2:
                        st.metric("Total Units (总数量)", f"{allocation_df['Allocated_Units'].sum():,.0f}")
                    
                    st.markdown("**Allocation Details (分配详情)**")
                    display_alloc = allocation_df[['Product', 'Warehouse', 'Channel', 'State', 'Allocated_Units', 'Cost_Per_Unit', 'Total_Cost']].copy()
                    display_alloc['Allocated_Units'] = display_alloc['Allocated_Units'].round(0)
                    display_alloc['Cost_Per_Unit'] = display_alloc['Cost_Per_Unit'].round(3)
                    display_alloc['Total_Cost'] = display_alloc['Total_Cost'].round(2)
                    st.dataframe(display_alloc, use_container_width=True, hide_index=True)
                    
                    # By warehouse summary
                    st.markdown("**By Warehouse (按仓库汇总)**")
                    wh_summary = allocation_df.groupby('Warehouse').agg({
                        'Allocated_Units': 'sum',
                        'Total_Cost': 'sum'
                    }).reset_index()
                    wh_summary.columns = ['Warehouse', 'Total Units', 'Total Cost ($)']
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.dataframe(wh_summary, use_container_width=True, hide_index=True)
                    with col2:
                        fig = px.pie(wh_summary, values='Total Units', names='Warehouse',
                                    title=f'Week {week} Customer Allocation Distribution')
                        fig.update_layout(template='plotly_white', margin=dict(t=40, b=20, l=20, r=20))
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning(f"⚠️ No results for Week {week}. Calculate customer cost first. (第{week}周无结果，请先计算客户成本)")

    # Display Smart Allocation Details (Moved from old Smart Suggestion page)
    if 'smart_results' in st.session_state:
        st.markdown("---")
        st.subheader("📋 Smart Allocation Details")
        
        tab1, tab2 = st.tabs(["Week 3 Results (第3周结果)", "Week 4 Results (第4周结果)"])
        
        for idx, week in enumerate([3, 4]):
            with [tab1, tab2][idx]:
                allocation_df, total_cost = st.session_state.smart_results.get(week, (None, None))
                
                if allocation_df is not None:
                    st.subheader(f"Week {week} Smart Allocation (第{week}周智能分配)")
                    
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.metric("Total Cost (总成本)", f"${total_cost:,.2f}", help="Using TMS rates (使用TMS费率)")
                    with col2:
                        st.metric("Total Units (总数量)", f"{allocation_df['Allocated_Units'].sum():,.0f}")
                    
                    st.markdown("**Allocation Details (分配详情)**")
                    display_alloc = allocation_df[['Product', 'Warehouse', 'Channel', 'State', 'Allocated_Units', 'Cost_Per_Unit', 'Total_Cost']].copy()
                    display_alloc['Allocated_Units'] = display_alloc['Allocated_Units'].round(0)
                    display_alloc['Cost_Per_Unit'] = display_alloc['Cost_Per_Unit'].round(3)
                    display_alloc['Total_Cost'] = display_alloc['Total_Cost'].round(2)
                    st.dataframe(display_alloc, use_container_width=True, hide_index=True)
                    
                    # By warehouse summary
                    st.markdown("**By Warehouse (按仓库汇总)**")
                    wh_summary = allocation_df.groupby('Warehouse').agg({
                        'Allocated_Units': 'sum',
                        'Total_Cost': 'sum'
                    }).reset_index()
                    wh_summary.columns = ['Warehouse', 'Total Units', 'Total Cost ($)']
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.dataframe(wh_summary, use_container_width=True, hide_index=True)
                    with col2:
                        fig = px.pie(wh_summary, values='Total Units', names='Warehouse',
                                    title=f'Week {week} Allocation Distribution')
                        fig.update_layout(template='plotly_white', margin=dict(t=40, b=20, l=20, r=20))
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning(f"⚠️ No results for Week {week}. Run optimization first. (第{week}周无结果，请先运行优化)")


# Cost Comparison Page
elif page == "📈 Cost Comparison":
    st.header("📈 Cost Comparison Analysis")
    st.markdown("*成本对比分析*")
    
    if 'customer_results' not in st.session_state or 'smart_results' not in st.session_state:
        st.warning("⚠️ Please run calculations in '🤖 Run Scenarios' page first.")
        st.info("👉 Go to **Run Scenarios** page to calculate costs.")
    
    
    # Show comparison if both calculated
    if 'customer_results' in st.session_state and 'smart_results' in st.session_state:
        st.markdown("---")
        st.markdown("### 💰 Cost Comparison Results (成本对比结果)")
        
        # Calculate totals
        customer_total = sum(cost for _, cost in st.session_state.customer_results.values())
        smart_total = sum(cost for _, cost in st.session_state.smart_results.values() if cost is not None)
        
        savings = customer_total - smart_total
        savings_pct = (savings / customer_total * 100) if customer_total > 0 else 0
        
        # Overall metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Customer Current (客户当前)", f"${customer_total:,.2f}", help="Using Market rates")
        
        with col2:
            st.metric("Smart Solution (智能方案)", f"${smart_total:,.2f}", help="Using TMS rates")
        
        with col3:
            st.metric("💵 Savings (节省)", f"${savings:,.2f}", 
                     delta=f"-${savings:,.2f}" if savings > 0 else f"+${abs(savings):,.2f}")
        
        with col4:
            st.metric("📊 Savings % (节省比例)", f"{savings_pct:.1f}%",
                     delta=f"{savings_pct:.1f}%")
        
        if savings > 0:
            st.success(f"""
            ### 🎉 Significant Optimization! (优化效果显著!)
            
            Smart solution saves **${savings:,.2f}** ({savings_pct:.1f}%) compared to customer current plan.
            
            智能方案相比客户当前方案节省 **${savings:,.2f}** ({savings_pct:.1f}%)
            """)
        
        # Week by week comparison
        st.markdown("---")
        st.markdown("### 📊 Week-by-Week Summary (逐周汇总)")
        
        comparison_data = []
        for week in [3, 4]:
            _, cust_cost = st.session_state.customer_results.get(week, (None, 0))
            _, smart_cost = st.session_state.smart_results.get(week, (None, 0))
            
            comparison_data.append({
                'Week': f'Week {week}',
                'Customer Current ($)': cust_cost,
                'Smart Solution ($)': smart_cost,
                'Savings ($)': cust_cost - smart_cost,
                'Savings %': ((cust_cost - smart_cost) / cust_cost * 100) if cust_cost > 0 else 0
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        
        # Visual comparison
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Customer Current', x=['Week 3', 'Week 4'], 
                            y=[comparison_data[0]['Customer Current ($)'], comparison_data[1]['Customer Current ($)']],
                            marker_color='#FF6B6B'))
        fig.add_trace(go.Bar(name='Smart Solution', x=['Week 3', 'Week 4'],
                            y=[comparison_data[0]['Smart Solution ($)'], comparison_data[1]['Smart Solution ($)']],
                            marker_color='#4ECDC4'))
        fig.update_layout(title='Cost Comparison by Week (按周成本对比)', 
                         barmode='group',
                         yaxis_title='Cost ($)',
                         height=400,
                         template='plotly_white',
                         font=dict(family="Inter, sans-serif"))
        st.plotly_chart(fig, use_container_width=True)
        
        # DETAILED COMPARISON BY WEEK
        st.markdown("---")
        st.markdown("### 📋 Detailed Comparison by Week (详细对比)")
        
        tab1, tab2 = st.tabs(["Week 3 Details (第3周明细)", "Week 4 Details (第4周明细)"])
        
        for tab_idx, week in enumerate([3, 4]):
            with [tab1, tab2][tab_idx]:
                st.subheader(f"Week {week} Detailed Comparison (第{week}周详细对比)")
                
                customer_df, cust_cost = st.session_state.customer_results.get(week, (None, 0))
                smart_df, smart_cost = st.session_state.smart_results.get(week, (None, 0))
                
                if customer_df is not None and smart_df is not None:
                    # Create side-by-side comparison
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**🏢 Customer Current Plan (客户当前方案)**")
                        st.info(f"Total Cost: ${cust_cost:,.2f} | Market Rate: ${st.session_state.market_shipping_rate:.3f}/unit/100mi")
                        
                        # Prepare customer data for display
                        cust_display = customer_df[['Product', 'Warehouse', 'Channel', 'State', 'Allocated_Units', 'Cost_Per_Unit', 'Distance_Miles', 'Total_Cost']].copy()
                        cust_display['Allocated_Units'] = cust_display['Allocated_Units'].round(0).astype(int)
                        cust_display['Cost_Per_Unit'] = cust_display['Cost_Per_Unit'].apply(lambda x: f"${x:.4f}")
                        cust_display['Distance_Miles'] = cust_display['Distance_Miles'].round(1)
                        cust_display['Total_Cost'] = cust_display['Total_Cost'].apply(lambda x: f"${x:,.2f}")
                        
                        cust_display.columns = ['Product', 'Warehouse', 'Channel', 'State', 'Units', 'Rate ($/unit)', 'Distance (mi)', 'Cost']
                        
                        st.dataframe(cust_display, use_container_width=True, hide_index=True)
                        
                        # Customer summary by warehouse
                        cust_wh_summary = customer_df.groupby('Warehouse').agg({
                            'Allocated_Units': 'sum',
                            'Total_Cost': 'sum'
                        }).reset_index()
                        cust_wh_summary.columns = ['Warehouse', 'Total Units', 'Total Cost ($)']
                        cust_wh_summary['Total Units'] = cust_wh_summary['Total Units'].round(0).astype(int)
                        cust_wh_summary['Total Cost ($)'] = cust_wh_summary['Total Cost ($)'].round(2)
                        
                        st.markdown("**Summary by Warehouse (按仓库汇总)**")
                        st.dataframe(cust_wh_summary, use_container_width=True, hide_index=True)
                    
                    with col2:
                        st.markdown("**💡 Smart Suggestion (智能建议)**")
                        st.info(f"Total Cost: ${smart_cost:,.2f} | TMS Rate: ${st.session_state.tms_shipping_rate:.3f}/unit/100mi")
                        
                        # Prepare smart data for display
                        smart_display = smart_df[['Product', 'Warehouse', 'Channel', 'State', 'Allocated_Units', 'Cost_Per_Unit', 'Distance_Miles', 'Total_Cost']].copy()
                        smart_display['Allocated_Units'] = smart_display['Allocated_Units'].round(0).astype(int)
                        smart_display['Cost_Per_Unit'] = smart_display['Cost_Per_Unit'].apply(lambda x: f"${x:.4f}")
                        smart_display['Distance_Miles'] = smart_display['Distance_Miles'].round(1)
                        smart_display['Total_Cost'] = smart_display['Total_Cost'].apply(lambda x: f"${x:,.2f}")
                        
                        smart_display.columns = ['Product', 'Warehouse', 'Channel', 'State', 'Units', 'Rate ($/unit)', 'Distance (mi)', 'Cost']
                        
                        st.dataframe(smart_display, use_container_width=True, hide_index=True)
                        
                        # Smart summary by warehouse
                        smart_wh_summary = smart_df.groupby('Warehouse').agg({
                            'Allocated_Units': 'sum',
                            'Total_Cost': 'sum'
                        }).reset_index()
                        smart_wh_summary.columns = ['Warehouse', 'Total Units', 'Total Cost ($)']
                        smart_wh_summary['Total Units'] = smart_wh_summary['Total Units'].round(0).astype(int)
                        smart_wh_summary['Total Cost ($)'] = smart_wh_summary['Total Cost ($)'].round(2)
                        
                        st.markdown("**Summary by Warehouse (按仓库汇总)**")
                        st.dataframe(smart_wh_summary, use_container_width=True, hide_index=True)
                    
                    # Difference Analysis
                    st.markdown("---")
                    st.markdown(f"**🔍 Week {week} Difference Analysis (差异分析)**")
                    
                    week_savings = cust_cost - smart_cost
                    week_savings_pct = (week_savings / cust_cost * 100) if cust_cost > 0 else 0
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Cost Difference (成本差异)", f"${week_savings:,.2f}")
                    with col2:
                        st.metric("Percentage Saved (节省比例)", f"{week_savings_pct:.1f}%")
                    with col3:
                        rate_diff = st.session_state.market_shipping_rate - st.session_state.tms_shipping_rate
                        st.metric("Rate Advantage (费率优势)", f"${rate_diff:.3f}/unit/100mi")
                    
                    # Compare warehouse usage
                    st.markdown("**Warehouse Usage Comparison (仓库使用对比)**")
                    
                    # Merge customer and smart warehouse summaries
                    cust_wh_summary['Plan'] = 'Customer'
                    smart_wh_summary['Plan'] = 'Smart'
                    
                    combined = pd.concat([
                        cust_wh_summary[['Warehouse', 'Total Units', 'Plan']],
                        smart_wh_summary[['Warehouse', 'Total Units', 'Plan']]
                    ])
                    
                    fig_wh = px.bar(combined, x='Warehouse', y='Total Units', color='Plan',
                                   barmode='group',
                                   title=f'Week {week} - Warehouse Usage Comparison',
                                   color_discrete_map={'Customer': '#EF4444', 'Smart': '#10B981'})
                    fig_wh.update_layout(template='plotly_white', font=dict(family="Inter, sans-serif"))
                    st.plotly_chart(fig_wh, use_container_width=True)
                    
                    # Key Insights
                    st.markdown("**💡 Key Insights (关键洞察)**")
                    
                    insights = []
                    
                    # Compare warehouse counts
                    cust_wh_count = len(cust_wh_summary)
                    smart_wh_count = len(smart_wh_summary)
                    
                    if smart_wh_count < cust_wh_count:
                        insights.append(f"✅ Smart solution uses **{smart_wh_count} warehouses** vs customer's {cust_wh_count}, improving efficiency (智能方案使用更少仓库，提升效率)")
                    elif smart_wh_count > cust_wh_count:
                        insights.append(f"📊 Smart solution leverages **{smart_wh_count} warehouses** for better distribution (智能方案使用更多仓库优化配送)")
                    
                    # Rate advantage
                    if rate_diff > 0:
                        insights.append(f"💰 TMS rate is **${rate_diff:.3f} ({(rate_diff/st.session_state.market_shipping_rate*100):.1f}%)** lower than market rate (TMS费率优势)")
                    
                    # Distance optimization
                    cust_avg_dist = customer_df['Distance_Miles'].mean()
                    smart_avg_dist = smart_df['Distance_Miles'].mean()
                    dist_diff = cust_avg_dist - smart_avg_dist
                    
                    if dist_diff > 0:
                        insights.append(f"🚚 Smart solution reduces average distance by **{dist_diff:.1f} miles** ({(dist_diff/cust_avg_dist*100):.1f}%) (平均距离缩短)")
                    
                    for insight in insights:
                        st.markdown(f"- {insight}")
                    
                    if not insights:
                        st.info("Both plans have similar efficiency patterns (两方案效率相近)")
                
                else:
                    st.warning(f"⚠️ Missing data for Week {week}. Please run both calculations. (第{week}周数据缺失，请运行两个计算)")
    



# Data Management Page  
elif page == "📁 Data Management":
    st.header("📁 Data Management")
    st.markdown("*数据管理*")
    
    # Export
    st.subheader("💾 Export Configuration (导出配置)")
    
    if st.button("Export All Configuration as JSON (导出全部配置为JSON)"):
        config = {
            'warehouses': st.session_state.warehouses.to_dict('records'),
            'distribution_centers': st.session_state.distribution_centers.to_dict('records'),
            'demand_forecast': st.session_state.demand_forecast.to_dict('records'),
            'market_shipping_rate': st.session_state.market_shipping_rate,
            'tms_shipping_rate': st.session_state.tms_shipping_rate,
            'customer_allocation_plan': st.session_state.customer_allocation_plan.to_dict('records')
        }
        
        json_str = json.dumps(config, indent=2)
        st.download_button(
            label="⬇️ Download Configuration File (下载配置文件)",
            data=json_str,
            file_name="warehouse_config.json",
            mime="application/json"
        )
    
    # Import
    st.markdown("---")
    st.subheader("📤 Import Configuration (导入配置)")
    
    uploaded_config = st.file_uploader("Upload Configuration JSON (上传配置JSON)", type=['json'])
    if uploaded_config:
        try:
            config = json.load(uploaded_config)
            
            st.session_state.warehouses = pd.DataFrame(config['warehouses'])
            st.session_state.distribution_centers = pd.DataFrame(config['distribution_centers'])
            st.session_state.demand_forecast = pd.DataFrame(config['demand_forecast'])
            st.session_state.market_shipping_rate = config.get('market_shipping_rate', 0.18)
            st.session_state.tms_shipping_rate = config.get('tms_shipping_rate', 0.12)
            
            if 'customer_allocation_plan' in config:
                st.session_state.customer_allocation_plan = pd.DataFrame(config['customer_allocation_plan'])
            
            st.success("✅ Configuration imported successfully! (配置导入成功!)")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Import failed (导入失败): {e}")

# Footer
st.markdown("---")
st.markdown("**© 2024 Smart Warehouse Allocation System | Optimize logistics, reduce costs, improve efficiency**")
st.markdown("*优化物流，降低成本，提升效率*")
