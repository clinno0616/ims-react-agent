"""
生成大量樣本數據的資料庫初始化程式
- 至少 100 個料件品號
- 至少 20 筆訂單
- 至少 20 筆採購單
"""
import sqlite3
import os
import random
import argparse
from datetime import datetime, timedelta

def generate_product_code(index):
    """生成料件品號"""
    categories = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    category = categories[index % len(categories)]
    number = str(index + 1).zfill(4)
    return f"{category}{number}"

def generate_product_name(code):
    """根據品號生成產品名稱"""
    category_names = {
        'A': '電子零件',
        'B': '機械零件',
        'C': '塑膠製品',
        'D': '金屬材料',
        'E': '化工原料',
        'F': '包裝材料',
        'G': '工具配件',
        'H': '辦公用品'
    }
    category = code[0]
    number = code[1:]
    return f"{category_names.get(category, '其他')}-{number}"

def random_date(start_date, end_date):
    """生成隨機日期"""
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randint(0, days_between)
    return start_date + timedelta(days=random_days)

def init_sample_database(db_path="erp_inventory_sample.db", num_products=100, num_orders=20, num_purchases=20):
    """初始化包含大量樣本數據的 ERP 資料庫"""
    
    # 如果資料庫已存在，詢問是否覆蓋
    if os.path.exists(db_path):
        response = input(f"資料庫 {db_path} 已存在，是否覆蓋？(y/n): ")
        if response.lower() != 'y':
            print("操作已取消")
            return
        os.remove(db_path)
    
    print(f"\n{'='*60}")
    print(f"開始生成樣本資料庫")
    print(f"{'='*60}")
    print(f"料件數量: {num_products}")
    print(f"訂單數量: {num_orders}")
    print(f"採購單數量: {num_purchases}")
    print(f"{'='*60}\n")
    
    # 連接資料庫
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ==================== 創建資料表 ====================
    print("📋 創建資料表...")
    
    # 1. 庫存表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_code TEXT NOT NULL UNIQUE,
        product_name TEXT NOT NULL,
        current_stock INTEGER DEFAULT 0,
        safety_stock INTEGER DEFAULT 0,
        reorder_point INTEGER DEFAULT 0,
        max_stock INTEGER DEFAULT 0,
        avg_daily_sales REAL DEFAULT 0,
        avg_monthly_sales REAL DEFAULT 0,
        max_daily_sales REAL DEFAULT 0,
        lead_time_days INTEGER DEFAULT 0,
        last_purchase_date TEXT,
        unit_price REAL DEFAULT 0,
        category TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 2. 訂單主檔表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sales_orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no TEXT NOT NULL UNIQUE,
        customer_name TEXT NOT NULL,
        order_date TEXT NOT NULL,
        delivery_date TEXT,
        total_amount REAL DEFAULT 0,
        status TEXT DEFAULT 'pending',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 3. 訂單明細表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sales_order_details (
        detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_code TEXT NOT NULL,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES sales_orders(order_id)
    )
    ''')
    
    # 4. 採購單主檔表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS purchase_orders (
        purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_no TEXT NOT NULL UNIQUE,
        supplier_name TEXT NOT NULL,
        order_date TEXT NOT NULL,
        expected_date TEXT,
        total_amount REAL DEFAULT 0,
        status TEXT DEFAULT 'pending',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 5. 採購單明細表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS purchase_order_details (
        detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_id INTEGER NOT NULL,
        product_code TEXT NOT NULL,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (purchase_id) REFERENCES purchase_orders(purchase_id)
    )
    ''')
    
    # 6. 銷貨記錄表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sales_records (
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no TEXT,
        product_code TEXT NOT NULL,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL,
        total_amount REAL,
        sale_date TEXT NOT NULL,
        customer TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 7. 進貨記錄表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS purchase_records (
        purchase_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_no TEXT,
        product_code TEXT NOT NULL,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL,
        total_amount REAL,
        purchase_date TEXT NOT NULL,
        supplier TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 8. 月度統計表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS monthly_summary (
        summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
        month TEXT NOT NULL UNIQUE,
        opening_stock INTEGER DEFAULT 0,
        closing_stock INTEGER DEFAULT 0,
        total_sales INTEGER DEFAULT 0,
        total_purchases INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    print("✅ 資料表創建完成\n")
    
    # ==================== 生成產品數據 ====================
    print(f"📦 生成 {num_products} 個產品...")
    
    products = []
    for i in range(num_products):
        product_code = generate_product_code(i)
        product_name = generate_product_name(product_code)
        category = product_code[0]
        
        # 隨機生成庫存相關數據
        avg_daily_sales = random.uniform(1, 50)
        avg_monthly_sales = avg_daily_sales * 30
        max_daily_sales = avg_daily_sales * random.uniform(1.5, 3.0)
        lead_time_days = random.randint(3, 30)
        
        safety_stock = int((max_daily_sales - avg_daily_sales) * lead_time_days)
        reorder_point = int(avg_daily_sales * lead_time_days + safety_stock)
        max_stock = int(reorder_point + avg_monthly_sales)
        current_stock = random.randint(int(safety_stock * 0.5), int(max_stock * 1.2))
        
        unit_price = random.uniform(10, 1000)
        
        # 隨機生成最後進貨日期（過去 90 天內）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        last_purchase_date = random_date(start_date, end_date).strftime('%Y-%m-%d')
        
        products.append((
            product_code, product_name, current_stock, safety_stock,
            reorder_point, max_stock, avg_daily_sales, avg_monthly_sales,
            max_daily_sales, lead_time_days, last_purchase_date, unit_price, category
        ))
    
    cursor.executemany('''
    INSERT INTO inventory (product_code, product_name, current_stock, safety_stock,
                          reorder_point, max_stock, avg_daily_sales, avg_monthly_sales,
                          max_daily_sales, lead_time_days, last_purchase_date, unit_price, category)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', products)
    
    print(f"✅ 已生成 {num_products} 個產品\n")
    
    # ==================== 生成訂單數據 ====================
    print(f"📋 生成 {num_orders} 筆訂單...")
    
    customers = [f"客戶{chr(65+i)}" for i in range(20)]  # 客戶A到客戶T
    statuses = ['pending', 'confirmed', 'shipped', 'completed', 'cancelled']
    
    # 獲取所有產品代碼
    cursor.execute("SELECT product_code, product_name, unit_price FROM inventory")
    all_products = cursor.fetchall()
    
    for i in range(num_orders):
        order_no = f"SO{datetime.now().year}{str(i+1).zfill(5)}"
        customer_name = random.choice(customers)
        
        # 訂單日期在過去 60 天內
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        order_date = random_date(start_date, end_date)
        delivery_date = order_date + timedelta(days=random.randint(3, 14))
        
        status = random.choice(statuses)
        
        # 插入訂單主檔
        cursor.execute('''
        INSERT INTO sales_orders (order_no, customer_name, order_date, delivery_date, status)
        VALUES (?, ?, ?, ?, ?)
        ''', (order_no, customer_name, order_date.strftime('%Y-%m-%d'), 
              delivery_date.strftime('%Y-%m-%d'), status))
        
        order_id = cursor.lastrowid
        
        # 每筆訂單包含 1-5 個產品
        num_items = random.randint(1, 5)
        selected_products = random.sample(all_products, num_items)
        
        total_amount = 0
        for product_code, product_name, unit_price in selected_products:
            quantity = random.randint(10, 200)
            subtotal = quantity * unit_price
            total_amount += subtotal
            
            # 插入訂單明細
            cursor.execute('''
            INSERT INTO sales_order_details (order_id, product_code, product_name, quantity, unit_price, subtotal)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (order_id, product_code, product_name, quantity, unit_price, subtotal))
            
            # 如果訂單已完成，記錄到銷貨記錄
            if status in ['shipped', 'completed']:
                cursor.execute('''
                INSERT INTO sales_records (order_no, product_code, product_name, quantity, 
                                          unit_price, total_amount, sale_date, customer)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (order_no, product_code, product_name, quantity, unit_price, 
                      subtotal, order_date.strftime('%Y-%m-%d'), customer_name))
        
        # 更新訂單總金額
        cursor.execute('UPDATE sales_orders SET total_amount = ? WHERE order_id = ?', 
                      (total_amount, order_id))
    
    print(f"✅ 已生成 {num_orders} 筆訂單\n")
    
    # ==================== 生成採購單數據 ====================
    print(f"📋 生成 {num_purchases} 筆採購單...")
    
    suppliers = [f"供應商{chr(65+i)}" for i in range(15)]  # 供應商A到供應商O
    
    for i in range(num_purchases):
        purchase_no = f"PO{datetime.now().year}{str(i+1).zfill(5)}"
        supplier_name = random.choice(suppliers)
        
        # 採購日期在過去 90 天內
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        order_date = random_date(start_date, end_date)
        expected_date = order_date + timedelta(days=random.randint(7, 30))
        
        status = random.choice(statuses)
        
        # 插入採購單主檔
        cursor.execute('''
        INSERT INTO purchase_orders (purchase_no, supplier_name, order_date, expected_date, status)
        VALUES (?, ?, ?, ?, ?)
        ''', (purchase_no, supplier_name, order_date.strftime('%Y-%m-%d'), 
              expected_date.strftime('%Y-%m-%d'), status))
        
        purchase_id = cursor.lastrowid
        
        # 每筆採購單包含 1-8 個產品
        num_items = random.randint(1, 8)
        selected_products = random.sample(all_products, num_items)
        
        total_amount = 0
        for product_code, product_name, unit_price in selected_products:
            quantity = random.randint(50, 500)
            # 採購價格通常比售價低 20-40%
            purchase_price = unit_price * random.uniform(0.6, 0.8)
            subtotal = quantity * purchase_price
            total_amount += subtotal
            
            # 插入採購單明細
            cursor.execute('''
            INSERT INTO purchase_order_details (purchase_id, product_code, product_name, 
                                               quantity, unit_price, subtotal)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (purchase_id, product_code, product_name, quantity, purchase_price, subtotal))
            
            # 如果採購單已完成，記錄到進貨記錄
            if status in ['shipped', 'completed']:
                cursor.execute('''
                INSERT INTO purchase_records (purchase_no, product_code, product_name, quantity, 
                                             unit_price, total_amount, purchase_date, supplier)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (purchase_no, product_code, product_name, quantity, purchase_price, 
                      subtotal, order_date.strftime('%Y-%m-%d'), supplier_name))
        
        # 更新採購單總金額
        cursor.execute('UPDATE purchase_orders SET total_amount = ? WHERE purchase_id = ?', 
                      (total_amount, purchase_id))
    
    print(f"✅ 已生成 {num_purchases} 筆採購單\n")
    
    # ==================== 生成月度統計 ====================
    print("📊 生成月度統計...")
    
    # 生成過去 6 個月的統計
    for i in range(6):
        month_date = datetime.now() - timedelta(days=30*i)
        month_str = month_date.strftime('%Y-%m')
        
        opening_stock = random.randint(8000, 12000)
        closing_stock = random.randint(7000, 11000)
        total_sales = random.randint(15000, 25000)
        total_purchases = random.randint(14000, 24000)
        
        cursor.execute('''
        INSERT INTO monthly_summary (month, opening_stock, closing_stock, total_sales, total_purchases)
        VALUES (?, ?, ?, ?, ?)
        ''', (month_str, opening_stock, closing_stock, total_sales, total_purchases))
    
    print("✅ 已生成月度統計\n")
    
    # 提交更改
    conn.commit()
    
    # ==================== 顯示統計信息 ====================
    print(f"\n{'='*60}")
    print("資料庫生成完成！")
    print(f"{'='*60}\n")
    
    print("📊 資料統計：")
    print("-" * 60)
    
    cursor.execute("SELECT COUNT(*) FROM inventory")
    print(f"  產品數量: {cursor.fetchone()[0]} 個")
    
    cursor.execute("SELECT COUNT(*) FROM sales_orders")
    print(f"  訂單數量: {cursor.fetchone()[0]} 筆")
    
    cursor.execute("SELECT COUNT(*) FROM sales_order_details")
    print(f"  訂單明細: {cursor.fetchone()[0]} 筆")
    
    cursor.execute("SELECT COUNT(*) FROM purchase_orders")
    print(f"  採購單數量: {cursor.fetchone()[0]} 筆")
    
    cursor.execute("SELECT COUNT(*) FROM purchase_order_details")
    print(f"  採購單明細: {cursor.fetchone()[0]} 筆")
    
    cursor.execute("SELECT COUNT(*) FROM sales_records")
    print(f"  銷貨記錄: {cursor.fetchone()[0]} 筆")
    
    cursor.execute("SELECT COUNT(*) FROM purchase_records")
    print(f"  進貨記錄: {cursor.fetchone()[0]} 筆")
    
    cursor.execute("SELECT COUNT(*) FROM monthly_summary")
    print(f"  月度統計: {cursor.fetchone()[0]} 筆")
    
    print("\n📦 產品分類統計：")
    print("-" * 60)
    cursor.execute("""
        SELECT category, COUNT(*) as count, 
               SUM(current_stock) as total_stock,
               AVG(unit_price) as avg_price
        FROM inventory 
        GROUP BY category 
        ORDER BY category
    """)
    for row in cursor.fetchall():
        print(f"  類別 {row[0]}: {row[1]} 個產品, 總庫存 {row[2]:.0f}, 平均單價 ${row[3]:.2f}")
    
    print("\n💰 訂單統計：")
    print("-" * 60)
    cursor.execute("""
        SELECT status, COUNT(*) as count, SUM(total_amount) as total
        FROM sales_orders 
        GROUP BY status
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} 筆, 總金額 ${row[2]:,.2f}")
    
    print("\n💰 採購單統計：")
    print("-" * 60)
    cursor.execute("""
        SELECT status, COUNT(*) as count, SUM(total_amount) as total
        FROM purchase_orders 
        GROUP BY status
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} 筆, 總金額 ${row[2]:,.2f}")
    
    print("\n🔍 庫存警示：")
    print("-" * 60)
    cursor.execute("""
        SELECT product_code, product_name, current_stock, safety_stock
        FROM inventory 
        WHERE current_stock < safety_stock
        LIMIT 5
    """)
    low_stock = cursor.fetchall()
    if low_stock:
        print("  低於安全庫存的產品（前5個）：")
        for row in low_stock:
            print(f"    {row[0]} - {row[1]}: 當前 {row[2]}, 安全庫存 {row[3]}")
    else:
        print("  ✅ 所有產品庫存充足")
    
    # 關閉連接
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"✅ 資料庫已創建: {os.path.abspath(db_path)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='ERP 進銷存樣本資料庫生成器')
    parser.add_argument('--products', type=int, default=100, help='產品數量 (預設: 100)')
    parser.add_argument('--orders', type=int, default=50, help='訂單數量 (預設: 50)')
    parser.add_argument('--purchases', type=int, default=50, help='採購單數量 (預設: 50)')
    parser.add_argument('--db', type=str, default='erp_inventory_sample.db', help='資料庫檔名 (預設: erp_inventory_sample.db)')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("ERP 進銷存樣本資料庫生成器")
    print("="*60 + "\n")
    
    init_sample_database(
        db_path=args.db,
        num_products=args.products,
        num_orders=args.orders,
        num_purchases=args.purchases
    )

