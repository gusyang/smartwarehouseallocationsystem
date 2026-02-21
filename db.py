import sqlite3
import pandas as pd
import os
from datetime import datetime
import streamlit as st

DB_FILE = "warehouse_v5.db"

def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_database():
    """初始化数据库表"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Carriers表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS carriers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mode TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, mode)
        )
    """)
    
    # Rates表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            carrier_id INTEGER REFERENCES carriers(id),
            min_distance REAL,
            max_distance REAL,
            rate_per_mile REAL,
            minimum_charge REAL,
            fixed_cost REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # SKU表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sku (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku_code TEXT NOT NULL UNIQUE,
            name TEXT,
            length_in REAL,
            width_in REAL,
            height_in REAL,
            weight_lbs REAL,
            unit_type TEXT DEFAULT 'each',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Warehouse Inventory表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warehouse_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            warehouse_name TEXT NOT NULL,
            sku_code TEXT REFERENCES sku(sku_code),
            quantity_on_hand INTEGER DEFAULT 0,
            quantity_in_transit INTEGER DEFAULT 0,
            UNIQUE(warehouse_name, sku_code)
        )
    """)
    
    # Vehicles表 (车辆类型)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            length_inches REAL,
            width_inches REAL,
            height_inches REAL,
            max_weight_lbs REAL,
            description TEXT
        )
    """)
    
    # Warehouses表 (只包含基本信息)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warehouses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            address TEXT,
            capacity INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Distribution Centers表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS distribution_centers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT,
            state TEXT,
            address TEXT
        )
    """)
    
    # Demand Forecast表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS demand_forecast (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT,
            channel TEXT,
            state TEXT,
            demand_week3 INTEGER,
            demand_week4 INTEGER
        )
    """)
    
    # Customer Allocation Plan表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_allocation_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT,
            warehouse TEXT,
            channel TEXT,
            state TEXT,
            allocated_units_week3 INTEGER,
            allocated_units_week4 INTEGER
        )
    """)
    
    # Settings表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # Warehouse Schedule表 (入库/出库计划)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warehouse_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            warehouse_name TEXT NOT NULL,
            sku_code TEXT,
            incoming_week3 INTEGER DEFAULT 0,
            incoming_week4 INTEGER DEFAULT 0,
            outgoing_week1 INTEGER DEFAULT 0,
            outgoing_week2 INTEGER DEFAULT 0,
            UNIQUE(warehouse_name, sku_code)
        )
    """)
    
    # Customer Settings表 (客户选择的carrier等)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_carrier_id INTEGER REFERENCES carriers(id),
            tms_carrier_id INTEGER REFERENCES carriers(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def seed_default_data():
    """插入默认数据（如果表为空）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 检查是否已有数据
    cursor.execute("SELECT COUNT(*) FROM carriers")
    if cursor.fetchone()[0] == 0:
        # 插入默认Carriers
        carriers = [
            ('UPS', 'LTL', 'Less Than Truckload'),
            ('FedEx', 'LTL', 'Less Than Truckload'),
            ('XPO', 'FTL', 'Full Truckload'),
            ('Old Dominion', 'LTL', 'Less Than Truckload'),
            ('TMS', 'LTL', 'Our own fleet - Less Than Truckload'),
            ('TMS', 'FTL', 'Our own fleet - Full Truckload')
        ]
        cursor.executemany("INSERT INTO carriers (name, mode, description) VALUES (?, ?, ?)", carriers)
        
        # 插入默认Rates
        cursor.execute("SELECT id FROM carriers WHERE name = 'UPS'")
        ups_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM carriers WHERE name = 'XPO'")
        xpo_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM carriers WHERE name = 'FedEx'")
        fedex_id = cursor.fetchone()[0]
        
        rates = [
            (ups_id, 0, 500, 2.5, 25, 15),
            (ups_id, 500, 1000, 2.2, 35, 15),
            (ups_id, 1000, 99999, 1.8, 50, 15),
            (xpo_id, 0, 2000, 4.5, 200, 100),
            (xpo_id, 2000, 99999, 3.8, 300, 100),
            (fedex_id, 0, 500, 2.8, 30, 20),
            (fedex_id, 500, 1000, 2.4, 40, 20),
        ]
        cursor.executemany("""
            INSERT INTO rates (carrier_id, min_distance, max_distance, rate_per_mile, minimum_charge, fixed_cost) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, rates)
        
        # 添加TMS费率
        cursor.execute("SELECT id FROM carriers WHERE name = 'TMS' AND mode = 'LTL'")
        result = cursor.fetchone()
        tms_ltl_id = result[0] if result else None
        cursor.execute("SELECT id FROM carriers WHERE name = 'TMS' AND mode = 'FTL'")
        result = cursor.fetchone()
        tms_ftl_id = result[0] if result else None
        
        if tms_ltl_id:
            tms_rates = [
                (tms_ltl_id, 0, 500, 2.0, 20, 10),
                (tms_ltl_id, 500, 1000, 1.8, 25, 10),
                (tms_ltl_id, 1000, 99999, 1.5, 30, 10),
            ]
            cursor.executemany("""
                INSERT INTO rates (carrier_id, min_distance, max_distance, rate_per_mile, minimum_charge, fixed_cost) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, tms_rates)
        
        if tms_ftl_id:
            tms_ftl_rates = [
                (tms_ftl_id, 0, 2000, 3.5, 150, 80),
                (tms_ftl_id, 2000, 99999, 3.0, 200, 80),
            ]
            cursor.executemany("""
                INSERT INTO rates (carrier_id, min_distance, max_distance, rate_per_mile, minimum_charge, fixed_cost) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, tms_ftl_rates)
        
    # 检查Vehicles (车辆类型)
    cursor.execute("SELECT COUNT(*) FROM vehicles")
    if cursor.fetchone()[0] == 0:
        vehicles = [
            ('53\' Trailer', 636, 96, 108, 45000, 'Standard 53 foot trailer'),
            ('40\' Trailer', 480, 96, 108, 40000, 'Standard 40 foot trailer'),
        ]
        cursor.executemany("""
            INSERT INTO vehicles (name, length_inches, width_inches, height_inches, max_weight_lbs, description) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, vehicles)
    
    # 检查SKU
    cursor.execute("SELECT COUNT(*) FROM sku")
    if cursor.fetchone()[0] == 0:
        sku_data = [
            ('32Q21K', 'Product A', 12, 8, 6, 5, 'each'),
            ('SKU-B001', 'Product B', 24, 18, 12, 15, 'case'),
            ('SKU-C002', 'Product C', 48, 40, 36, 45, 'pallet'),
        ]
        cursor.executemany("""
            INSERT INTO sku (sku_code, name, length_in, width_in, height_in, weight_lbs, unit_type) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, sku_data)
        
    # 检查Warehouses
    cursor.execute("SELECT COUNT(*) FROM warehouses")
    if cursor.fetchone()[0] == 0:
        warehouses = [
            ('EL PASO', '12100 Emerald Pass Drive, El Paso, TX 79936', 10000),
            ('Valley View', '6800 Valley View St, Buena Park, CA 90620', 12000),
            ('Seabrook', '300 Seabrook Parkway, Pooler, GA 31322', 9000),
            ('Cesanek', '175 Cesanek Rd., Northampton, PA 18067', 11000),
        ]
        cursor.executemany("""
            INSERT INTO warehouses (name, address, capacity) 
            VALUES (?, ?, ?)
        """, warehouses)
        
    # 检查Distribution Centers
    cursor.execute("SELECT COUNT(*) FROM distribution_centers")
    if cursor.fetchone()[0] == 0:
        dcs = [
            ('Amazon', 'CA', 'San Francisco, CA'),
            ('Walmart', 'TX', 'Dallas, TX'),
            ('Target', 'GA', 'Atlanta, GA'),
            ('Amazon', 'PA', 'Philadelphia, PA'),
        ]
        cursor.executemany("INSERT INTO distribution_centers (channel, state, address) VALUES (?, ?, ?)", dcs)
        
    # 检查Demand Forecast
    cursor.execute("SELECT COUNT(*) FROM demand_forecast")
    if cursor.fetchone()[0] == 0:
        demand = [
            ('32Q21K', 'Amazon', 'CA', 2200, 2300),
            ('32Q21K', 'Walmart', 'TX', 1800, 1900),
            ('32Q21K', 'Target', 'GA', 1600, 1700),
            ('32Q21K', 'Amazon', 'PA', 1900, 2000),
        ]
        cursor.executemany("INSERT INTO demand_forecast (product, channel, state, demand_week3, demand_week4) VALUES (?, ?, ?, ?, ?)", demand)
        
    # 检查Customer Allocation Plan
    cursor.execute("SELECT COUNT(*) FROM customer_allocation_plan")
    if cursor.fetchone()[0] == 0:
        plan = [
            ('32Q21K', 'Valley View', 'Amazon', 'CA', 2200, 2300),
            ('32Q21K', 'EL PASO', 'Walmart', 'TX', 1800, 1900),
            ('32Q21K', 'EL PASO', 'Target', 'GA', 1600, 1700),
            ('32Q21K', 'Cesanek', 'Amazon', 'PA', 1900, 2000),
        ]
        cursor.executemany("""
            INSERT INTO customer_allocation_plan (product, warehouse, channel, state, allocated_units_week3, allocated_units_week4) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, plan)
    
    # 检查Warehouse Schedule
    cursor.execute("SELECT COUNT(*) FROM warehouse_schedule")
    if cursor.fetchone()[0] == 0:
        schedule = [
            ('EL PASO', '32Q21K', 200, 250, 300, 350),
            ('Valley View', '32Q21K', 300, 350, 400, 450),
            ('Seabrook', '32Q21K', 150, 200, 200, 250),
            ('Cesanek', '32Q21K', 200, 250, 150, 200),
        ]
        cursor.executemany("""
            INSERT INTO warehouse_schedule (warehouse_name, sku_code, incoming_week3, incoming_week4, outgoing_week1, outgoing_week2) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, schedule)
    
    # 检查Customer Settings (默认选择UPS作为customer carrier, TMS用TMS LTL)
    cursor.execute("SELECT COUNT(*) FROM customer_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id FROM carriers WHERE name = 'UPS'")
        result = cursor.fetchone()
        customer_carrier = result[0] if result else None
        
        cursor.execute("SELECT id FROM carriers WHERE name = 'TMS' AND mode = 'LTL'")
        result = cursor.fetchone()
        tms_carrier = result[0] if result else None
        
        if customer_carrier and tms_carrier:
            cursor.execute("INSERT INTO customer_settings (customer_carrier_id, tms_carrier_id) VALUES (?, ?)",
                         (customer_carrier, tms_carrier))
    
    conn.commit()
    conn.close()

# ============ CRUD Operations ============

def get_all_carriers():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM carriers", conn)
    conn.close()
    return df

def add_carrier(name, mode, description=""):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO carriers (name, mode, description) VALUES (?, ?, ?)", (name, mode, description))
        conn.commit()
        return True, "Carrier added successfully"
    except sqlite3.IntegrityError:
        return False, "Carrier already exists"
    finally:
        conn.close()

def delete_carrier(carrier_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rates WHERE carrier_id = ?", (carrier_id,))
    cursor.execute("DELETE FROM carriers WHERE id = ?", (carrier_id,))
    conn.commit()
    conn.close()

def get_rates_with_carrier():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT r.id, r.carrier_id, c.name as carrier_name, c.mode, 
               r.min_distance, r.max_distance, r.rate_per_mile, r.minimum_charge, r.fixed_cost
        FROM rates r
        JOIN carriers c ON r.carrier_id = c.id
    """, conn)
    conn.close()
    return df

def add_rate(carrier_id, min_dist, max_dist, rate_per_mile, minimum, fixed_cost):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO rates (carrier_id, min_distance, max_distance, rate_per_mile, minimum_charge, fixed_cost) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (carrier_id, min_dist, max_dist, rate_per_mile, minimum, fixed_cost))
    conn.commit()
    conn.close()

def delete_rate(rate_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rates WHERE id = ?", (rate_id,))
    conn.commit()
    conn.close()

def get_all_sku():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM sku", conn)
    conn.close()
    return df

def add_sku(sku_code, name, length, width, height, weight, unit_type):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO sku (sku_code, name, length_in, width_in, height_in, weight_lbs, unit_type) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sku_code, name, length, width, height, weight, unit_type))
        conn.commit()
        return True, "SKU added successfully"
    except sqlite3.IntegrityError:
        return False, "SKU code already exists"
    finally:
        conn.close()

def update_sku(sku_id, sku_code, name, length, width, height, weight, unit_type):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE sku SET sku_code=?, name=?, length_in=?, width_in=?, height_in=?, weight_lbs=?, unit_type=?
        WHERE id=?
    """, (sku_code, name, length, width, height, weight, unit_type, sku_id))
    conn.commit()
    conn.close()

def delete_sku(sku_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sku WHERE id = ?", (sku_id,))
    conn.commit()
    conn.close()

def get_warehouse_inventory():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT wi.id, wi.warehouse_name, wi.sku_code, s.name as sku_name, 
               s.length_in, s.width_in, s.height_in, s.weight_lbs,
               wi.quantity_on_hand, wi.quantity_in_transit
        FROM warehouse_inventory wi
        LEFT JOIN sku s ON wi.sku_code = s.sku_code
    """, conn)
    conn.close()
    return df

def get_warehouse_inventory_by_warehouse(warehouse_name):
    conn = get_connection()
    df = pd.read_sql("""
        SELECT wi.*, s.name as sku_name, s.length_in, s.width_in, s.height_in, s.weight_lbs
        FROM warehouse_inventory wi
        LEFT JOIN sku s ON wi.sku_code = s.sku_code
        WHERE wi.warehouse_name = ?
    """, conn, params=(warehouse_name,))
    conn.close()
    return df

def update_warehouse_inventory(warehouse_name, sku_code, qty_on_hand, qty_in_transit):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO warehouse_inventory (warehouse_name, sku_code, quantity_on_hand, quantity_in_transit)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(warehouse_name, sku_code) DO UPDATE SET
            quantity_on_hand = excluded.quantity_on_hand,
            quantity_in_transit = excluded.quantity_in_transit
    """, (warehouse_name, sku_code, qty_on_hand, qty_in_transit))
    conn.commit()
    conn.close()

# ============ Warehouse Schedule ============

def get_warehouse_schedule():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT ws.*, w.capacity
        FROM warehouse_schedule ws
        JOIN warehouses w ON ws.warehouse_name = w.name
    """, conn)
    conn.close()
    df = df.rename(columns={
        'warehouse_name': 'Warehouse',
        'sku_code': 'SKU',
        'incoming_week3': 'Incoming_Week3',
        'incoming_week4': 'Incoming_Week4',
        'outgoing_week1': 'Outgoing_Week1',
        'outgoing_week2': 'Outgoing_Week2'
    })
    return df

def get_warehouse_schedule_by_warehouse(warehouse_name):
    conn = get_connection()
    df = pd.read_sql("""
        SELECT ws.*, w.capacity
        FROM warehouse_schedule ws
        JOIN warehouses w ON ws.warehouse_name = w.name
        WHERE ws.warehouse_name = ?
    """, conn, params=(warehouse_name,))
    conn.close()
    return df

def save_warehouse_schedule(warehouse_name, sku_code, in_w3, in_w4, out_w1, out_w2):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO warehouse_schedule (warehouse_name, sku_code, incoming_week3, incoming_week4, outgoing_week1, outgoing_week2)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(warehouse_name, sku_code) DO UPDATE SET
            incoming_week3 = excluded.incoming_week3,
            incoming_week4 = excluded.incoming_week4,
            outgoing_week1 = excluded.outgoing_week1,
            outgoing_week2 = excluded.outgoing_week2
    """, (warehouse_name, sku_code, in_w3, in_w4, out_w1, out_w2))
    conn.commit()
    conn.close()

def calculate_available_inventory(warehouse_name, sku_code, week):
    """计算特定仓库、SKU在某周的可用库存"""
    schedule = get_warehouse_schedule_by_warehouse(warehouse_name)
    
    if schedule.empty or sku_code not in schedule['sku_code'].values:
        return 0
    
    sku_row = schedule[schedule['sku_code'] == sku_code]
    if sku_row.empty:
        return 0
    
    inv = sku_row.iloc[0]
    current = inv.get('quantity_on_hand', 0)
    in_w3 = inv.get('incoming_week3', 0)
    in_w4 = inv.get('incoming_week4', 0)
    out_w1 = inv.get('outgoing_week1', 0)
    out_w2 = inv.get('outgoing_week2', 0)
    
    if week == 3:
        available = current + in_w3 - out_w1 - out_w2
    elif week == 4:
        available = current + in_w3 + in_w4 - out_w1 - out_w2
    else:
        available = current
    
    return max(0, available)

# ============ Vehicles ============

def get_vehicles():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM vehicles", conn)
    conn.close()
    return df

def add_vehicle(name, length, width, height, max_weight, description=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO vehicles (name, length_inches, width_inches, height_inches, max_weight_lbs, description) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, length, width, height, max_weight, description))
    conn.commit()
    conn.close()

def calculate_max_units_per_vehicle(sku_code, vehicle_id=None):
    """
    计算每辆车能装多少单位
    使用 0.85 markup factor
    """
    conn = get_connection()
    
    # Get SKU info
    sku_df = pd.read_sql("SELECT * FROM sku WHERE sku_code = ?", conn, params=(sku_code,))
    if sku_df.empty:
        conn.close()
        return 0, "SKU not found"
    
    sku = sku_df.iloc[0]
    sku_volume = sku['length_in'] * sku['width_in'] * sku['height_in']  # cubic inches
    sku_weight = sku['weight_lbs']
    
    # Get vehicles
    if vehicle_id:
        vehicles_df = pd.read_sql("SELECT * FROM vehicles WHERE id = ?", conn, params=(vehicle_id,))
    else:
        vehicles_df = pd.read_sql("SELECT * FROM vehicles", conn)
    
    conn.close()
    
    if vehicles_df.empty:
        return 0, "No vehicles found"
    
    results = []
    for _, vehicle in vehicles_df.iterrows():
        vehicle_volume = vehicle['length_inches'] * vehicle['width_inches'] * vehicle['height_inches']
        max_weight = vehicle['max_weight_lbs']
        
        # Apply 0.85 markup factor
        usable_volume = vehicle_volume * 0.85
        usable_weight = max_weight * 0.85
        
        # Calculate max units by volume and weight
        max_units_by_volume = usable_volume / sku_volume if sku_volume > 0 else 0
        max_units_by_weight = usable_weight / sku_weight if sku_weight > 0 else 0
        
        # Use the smaller value (limiting factor)
        max_units = min(max_units_by_volume, max_units_by_weight)
        
        results.append({
            'vehicle': vehicle['name'],
            'max_units': int(max_units),
            'by_volume': int(max_units_by_volume),
            'by_weight': int(max_units_by_weight),
            'usable_volume': usable_volume,
            'usable_weight': usable_weight
        })
    
    return results, None

# ============ Customer Settings ============

def get_customer_settings():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT cs.*, 
               c1.name as customer_carrier_name, c1.mode as customer_carrier_mode,
               c2.name as tms_carrier_name, c2.mode as tms_carrier_mode
        FROM customer_settings cs
        LEFT JOIN carriers c1 ON cs.customer_carrier_id = c1.id
        LEFT JOIN carriers c2 ON cs.tms_carrier_id = c2.id
    """, conn)
    conn.close()
    return df

def save_customer_settings(customer_carrier_id, tms_carrier_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM customer_settings")
    cursor.execute("INSERT INTO customer_settings (customer_carrier_id, tms_carrier_id) VALUES (?, ?)",
                 (customer_carrier_id, tms_carrier_id))
    conn.commit()
    conn.close()

# ============ Shipping Rate Calculation ============

def calculate_unit_shipping_rate(sku_code, distance_miles, carrier_id, vehicle_id=None):
    """
    计算单位运费 ($/unit)
    基于SKU dimension、carrier rate和vehicle capacity
    """
    conn = get_connection()
    
    # 获取SKU信息
    sku_df = pd.read_sql("SELECT * FROM sku WHERE sku_code = ?", conn, params=(sku_code,))
    if sku_df.empty:
        conn.close()
        return 0, 0, "SKU not found"
    
    sku = sku_df.iloc[0]
    actual_weight = sku['weight_lbs']
    dim_weight = (sku['length_in'] * sku['width_in'] * sku['height_in']) / 139
    chargeable_weight = max(actual_weight, dim_weight)
    
    # 获取carrier信息
    carrier_df = pd.read_sql("SELECT * FROM carriers WHERE id = ?", conn, params=(carrier_id,))
    if carrier_df.empty:
        conn.close()
        return 0, 0, "Carrier not found"
    
    carrier_mode = carrier_df.iloc[0]['mode']
    
    # 获取carrier的rate
    rate_df = pd.read_sql("""
        SELECT * FROM rates 
        WHERE carrier_id = ? AND min_distance <= ? AND max_distance >= ?
    """, conn, params=(carrier_id, distance_miles, distance_miles))
    
    if rate_df.empty:
        conn.close()
        return 0, 0, "No rate found for this distance"
    
    rate = rate_df.iloc[0]
    
    # 计算车辆容量
    # 车辆容量 - FTL和LTL都使用车辆容量
    max_units_per_vehicle = 1
    if carrier_mode in ['FTL', 'LTL']:
        # 使用车辆容量
        results, err = calculate_max_units_per_vehicle(sku_code, vehicle_id)
        if err or not results:
            max_units_per_vehicle = 1
        else:
            # 使用最大的车辆容量
            max_units_per_vehicle = max([r['max_units'] for r in results])
    
    # 计算总成本
    variable_cost = chargeable_weight * rate['rate_per_mile'] * distance_miles / 100
    total_cost = max(rate['minimum_charge'], variable_cost + rate['fixed_cost'])
    
    # 单位成本 = 总成本 / 车辆容量
    cost_per_unit = total_cost / max_units_per_vehicle if max_units_per_vehicle > 0 else total_cost
    
    conn.close()
    
    return cost_per_unit, max_units_per_vehicle, None

def get_warehouses():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM warehouses", conn)
    conn.close()
    # Convert column names to match app expectations (capitalize)
    df = df.rename(columns={
        'name': 'Name',
        'address': 'Address',
        'capacity': 'Capacity'
    })
    return df

def add_warehouse(name, address, capacity):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO warehouses (name, address, capacity) 
        VALUES (?, ?, ?)
    """, (name, address, capacity))
    conn.commit()
    conn.close()

def save_warehouses_df(df):
    """Save warehouses DataFrame to database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Clear existing warehouses
    cursor.execute("DELETE FROM warehouses")
    
    # Insert all rows
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO warehouses (name, address, capacity) 
            VALUES (?, ?, ?)
        """, (
            row['Name'], row['Address'], int(row['Capacity'])
        ))
    
    conn.commit()
    conn.close()

def get_distribution_centers():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM distribution_centers", conn)
    conn.close()
    # Capitalize column names
    df = df.rename(columns={
        'channel': 'Channel',
        'state': 'State',
        'address': 'Address'
    })
    return df

def add_dc(channel, state, address):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO distribution_centers (channel, state, address) VALUES (?, ?, ?)", (channel, state, address))
    conn.commit()
    conn.close()

def get_demand_forecast():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM demand_forecast", conn)
    conn.close()
    # Capitalize column names
    df = df.rename(columns={
        'product': 'Product',
        'channel': 'Channel',
        'state': 'State',
        'demand_week3': 'Demand_Week3',
        'demand_week4': 'Demand_Week4'
    })
    return df

def add_demand(product, channel, state, week3, week4):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO demand_forecast (product, channel, state, demand_week3, demand_week4) 
        VALUES (?, ?, ?, ?, ?)
    """, (product, channel, state, week3, week4))
    conn.commit()
    conn.close()

def get_customer_allocation_plan():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM customer_allocation_plan", conn)
    conn.close()
    # Capitalize column names
    df = df.rename(columns={
        'product': 'Product',
        'warehouse': 'Warehouse',
        'channel': 'Channel',
        'state': 'State',
        'allocated_units_week3': 'Allocated_Units_Week3',
        'allocated_units_week4': 'Allocated_Units_Week4'
    })
    return df

def save_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

# ============ Shipping Cost Calculation ============

def calculate_dim_weight(length, width, height, dim_factor=139):
    """计算体积重"""
    return (length * width * height) / dim_factor

def calculate_shipping_cost(sku_code, distance_miles):
    """
    计算运费 - 基于SKU维度和配置的carrier费率
    返回: (carrier_name, mode, cost_per_unit, error_msg)
    """
    conn = get_connection()
    
    # 获取SKU信息
    sku_df = pd.read_sql("SELECT * FROM sku WHERE sku_code = ?", conn, params=(sku_code,))
    if sku_df.empty:
        conn.close()
        return None, None, 0, f"SKU {sku_code} not found"
    
    sku = sku_df.iloc[0]
    actual_weight = sku['weight_lbs']
    dim_weight = calculate_dim_weight(sku['length_in'], sku['width_in'], sku['height_in'])
    chargeable_weight = max(actual_weight, dim_weight)
    
    # 获取所有carrier的费率
    rates_df = pd.read_sql("""
        SELECT c.name, c.mode, r.rate_per_mile, r.minimum_charge, r.fixed_cost
        FROM rates r
        JOIN carriers c ON r.carrier_id = c.id
        WHERE r.min_distance <= ? AND r.max_distance >= ?
    """, conn, params=(distance_miles, distance_miles))
    
    conn.close()
    
    if rates_df.empty:
        # 使用默认费率
        return "Default", "LTL", 0.15, "No rate found, using default"
    
    # 找到最便宜的carrier
    best_rate = None
    best_cost = float('inf')
    
    for _, rate in rates_df.iterrows():
        variable_cost = chargeable_weight * rate['rate_per_mile'] * distance_miles / 100
        total_cost = max(rate['minimum_charge'], variable_cost + rate['fixed_cost'])
        cost_per_unit = total_cost / 1 if total_cost > 0 else 0  # 假设每单位
        
        if cost_per_unit < best_cost:
            best_cost = cost_per_unit
            best_rate = rate
    
    if best_rate is None:
        return "Default", "LTL", 0.15, "No rate found, using default"
    
    return best_rate['name'], best_rate['mode'], best_cost, None

# ============ Data Loading for App ============

def load_all_data():
    """加载所有数据到session_state"""
    data = {}
    
    data['carriers'] = get_all_carriers()
    data['rates'] = get_rates_with_carrier()
    data['sku'] = get_all_sku()
    data['warehouses'] = get_warehouses()
    data['distribution_centers'] = get_distribution_centers()
    data['demand_forecast'] = get_demand_forecast()
    data['customer_allocation_plan'] = get_customer_allocation_plan()
    data['warehouse_inventory'] = get_warehouse_inventory()
    data['warehouse_schedule'] = get_warehouse_schedule()
    data['customer_settings'] = get_customer_settings()
    data['vehicles'] = get_vehicles()
    
    # Load settings
    data['market_shipping_rate'] = float(get_setting('market_shipping_rate', '0.18'))
    data['tms_shipping_rate'] = float(get_setting('tms_shipping_rate', '0.12'))
    
    return data

# 初始化数据库
init_database()
seed_default_data()

def reload_session_state():
    """重新加载所有数据到session_state"""
    data = load_all_data()
    
    st.session_state.warehouses = data['warehouses'].copy()
    st.session_state.distribution_centers = data['distribution_centers'].copy()
    st.session_state.demand_forecast = data['demand_forecast'].copy()
    st.session_state.customer_allocation_plan = data['customer_allocation_plan'].copy()
    st.session_state.carriers = data['carriers'].copy()
    st.session_state.rates = data['rates'].copy()
    st.session_state.sku = data['sku'].copy()
    st.session_state.warehouse_inventory = data['warehouse_inventory'].copy()
    st.session_state.market_shipping_rate = data['market_shipping_rate']
    st.session_state.tms_shipping_rate = data['tms_shipping_rate']
