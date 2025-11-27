# ERP 進銷存 AI 查詢系統

基於 Streamlit 和 Ollama 的智能 ERP 進銷存管理系統，使用 ReAct Agent 架構實現自然語言查詢和分析。

## 📋 目錄

- [系統特色](#系統特色)
- [技術架構](#技術架構)
- [系統需求](#系統需求)
- [安裝步驟](#安裝步驟)
- [使用方法](#使用方法)
- [資料庫結構](#資料庫結構)
- [專案結構](#專案結構)
- [功能說明](#功能說明)

## ✨ 系統特色

### 🤖 AI 智能對話
- 使用自然語言查詢庫存、訂單、採購數據
- 自動生成並執行 SQL 查詢
- 支援複雜的多步驟分析
- 提供專業的庫存管理建議

### 📊 資料庫瀏覽
- 直接查看所有資料表內容
- 支援資料排序和篩選
- 顯示資料表結構和統計信息
- 可調整顯示筆數

### 🔍 系統日誌
- 完整記錄 AI 思考過程
- 顯示執行的 SQL 語句
- 追蹤每次查詢的詳細步驟
- 展示可用工具列表

### 🎯 模型自動偵測
- 自動偵測 Ollama 可用模型
- 支援多種 LLM 模型切換
- 智能預設模型選擇

## 🏗️ 技術架構

### 核心技術
- **前端框架**: Streamlit
- **AI 模型**: Ollama (支援 qwen3:14b, qwen3:8b 等)
- **資料庫**: SQLite
- **Agent 架構**: ReAct (Reasoning + Acting)

### 系統組件
```
┌─────────────────────────────────────────┐
│         Streamlit Web UI                │
│  (對話界面 + 資料庫瀏覽 + 系統日誌)      │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         ReAct Agent                     │
│  (思考 → 行動 → 觀察 → 最終答案)        │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         Tools (工具集)                  │
│  • execute_sql (SQL 查詢)               │
│  • run_terminal_command (終端命令)      │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│    SQLite Database (ERP 資料庫)         │
│  • inventory (庫存)                     │
│  • sales_orders (銷售訂單)              │
│  • purchase_orders (採購訂單)           │
│  • monthly_summary (月度統計)           │
└─────────────────────────────────────────┘
```

## 💻 系統需求

### 必要環境
- Python 3.8+
- Ollama (本地 LLM 服務)
- 至少 8GB RAM (建議 16GB)

### 推薦配置
- Python 3.11
- Ollama 最新版本
- qwen3:14b 或 qwen3:8b 模型

## 🚀 安裝步驟

### 1. 安裝 Ollama

**Windows:**
```bash
# 下載並安裝 Ollama
# https://ollama.ai/download

# 下載模型
ollama pull qwen3:14b
```

**Linux/Mac:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen3:14b
```

### 2. 啟動 Ollama 服務

```bash
ollama serve
```

### 3. 安裝 Python 依賴

```bash
# 克隆或下載專案後
cd tiptop

# 安裝依賴
pip install -r requirements.txt
```

### 4. 生成樣本資料庫

```bash
# 生成預設資料庫 (120 個產品)
python generate_sample_data.py

# 或自訂數量
python generate_sample_data.py --products 200 --orders 50 --purchases 50 --db custom.db
```

## 📖 使用方法

### 啟動系統

```bash
streamlit run streamlit_app.py
```

系統將在瀏覽器中自動開啟 (預設: http://localhost:8501)

### 基本操作流程

1. **連接系統**
   - 在左側邊欄選擇資料庫 (建議使用「樣本資料庫」)
   - 確認 Ollama URL (預設: http://localhost:11434)
   - 選擇 AI 模型
   - 點擊「🔌 連接系統」

2. **AI 對話查詢**
   - 在主畫面輸入自然語言問題
   - 例如: "請查詢當前庫存低於安全庫存的產品"
   - AI 會自動分析、查詢並提供答案

3. **資料庫瀏覽**
   - 切換到「📊 資料庫瀏覽」頁面
   - 選擇要查看的資料表
   - 調整顯示筆數
   - 查看欄位結構

4. **查看系統日誌**
   - 在右側欄展開「🔍 系統日誌」
   - 查看 AI 的思考過程
   - 檢視執行的 SQL 語句
   - 了解每個步驟的結果

## 🗄️ 資料庫結構

### 主要資料表

#### 1. inventory (庫存表)
```sql
- product_id: 產品 ID (主鍵)
- product_code: 料件品號 (唯一)
- product_name: 產品名稱
- current_stock: 當前庫存
- safety_stock: 安全庫存
- reorder_point: 再訂購點
- max_stock: 最高庫存
- avg_daily_sales: 平均日銷量
- avg_monthly_sales: 平均月銷量
- lead_time_days: 前置時間(天)
- category: 產品類別
```

#### 2. sales_orders (銷售訂單主檔)
```sql
- order_id: 訂單 ID (主鍵)
- order_no: 訂單編號 (唯一)
- customer_name: 客戶名稱
- order_date: 訂單日期
- total_amount: 訂單總金額
- status: 訂單狀態
```

#### 3. sales_order_details (銷售訂單明細)
```sql
- detail_id: 明細 ID (主鍵)
- order_id: 訂單 ID (外鍵 → sales_orders)
- product_code: 料件品號
- product_name: 產品名稱
- quantity: 數量
- unit_price: 單價
- subtotal: 小計
```

#### 4. purchase_orders (採購訂單主檔)
```sql
- purchase_id: 採購 ID (主鍵)
- purchase_no: 採購單號 (唯一)
- supplier_name: 供應商名稱
- order_date: 訂單日期
- total_amount: 採購總金額
- status: 採購狀態
```

#### 5. purchase_order_details (採購訂單明細)
```sql
- detail_id: 明細 ID (主鍵)
- purchase_id: 採購 ID (外鍵 → purchase_orders)
- product_code: 料件品號
- product_name: 產品名稱
- quantity: 數量
- unit_price: 單價
- subtotal: 小計
```

#### 6. monthly_summary (月度統計表)
```sql
- summary_id: 統計 ID (主鍵)
- month: 月份 (YYYY-MM)
- opening_stock: 期初庫存
- closing_stock: 期末庫存
- total_sales: 總銷售量
- total_purchases: 總採購量
```

### 資料表關聯
```
sales_orders (1) ──< (N) sales_order_details
purchase_orders (1) ──< (N) purchase_order_details
```

## 📁 專案結構

```
tiptop/
├── agent.py                    # ReAct Agent 核心邏輯
├── streamlit_app.py            # Streamlit 前端應用
├── prompt_template.py          # AI 系統提示詞模板
├── generate_sample_data.py     # 樣本資料庫生成器
├── requirements.txt            # Python 依賴清單
├── erp_inventory_sample.db     # 樣本資料庫 (自動生成)
└── README.md                   # 本文件
```

### 核心檔案說明

#### agent.py
- **ReActAgent 類別**: 實現 ReAct 架構的 AI Agent
- **工具函數**: `execute_sql`, `run_terminal_command`
- **模型調用**: 與 Ollama 服務通訊
- **錯誤處理**: 完善的異常處理機制

#### streamlit_app.py
- **頁面導航**: AI 對話 / 資料庫瀏覽
- **對話界面**: 聊天歷史、輸入框、快速查詢範例
- **日誌顯示**: 詳細的執行過程記錄
- **模型管理**: 自動偵測和選擇 Ollama 模型

#### prompt_template.py
- **系統提示詞**: 定義 AI 的角色和行為規範
- **查詢範例**: 提供標準的查詢模式
- **公式參考**: ERP 進銷存管理公式
- **資料表參考**: 列出所有可用資料表

#### generate_sample_data.py
- **資料庫初始化**: 創建完整的資料表結構
- **樣本數據生成**: 自動生成測試數據
- **命令列參數**: 支援自訂數據量
- **統計報告**: 顯示生成的數據統計

## 🎯 功能說明

### AI 查詢範例

#### 📦 庫存查詢
```
請查詢當前庫存低於安全庫存的產品
請列出所有電子零件(A類)的庫存情況
請查詢庫存最多的前10個產品
```

#### 📋 訂單分析
```
請統計各狀態的訂單數量和金額
請查詢最近的10筆訂單
請分析哪些客戶的訂單金額最高
```

#### 🏭 採購分析
```
請統計各供應商的採購金額
請查詢待處理的採購單
請分析最常採購的產品
```

#### 📈 趨勢分析
```
請分析最近6個月的進銷存趨勢
請計算庫存周轉率
請找出滯銷產品
```

### 進階功能

#### 1. 自訂查詢
系統支援任何自然語言查詢，AI 會自動:
- 理解查詢意圖
- 生成對應的 SQL 語句
- 執行查詢並分析結果
- 提供專業建議

#### 2. 多步驟分析
AI 可以執行複雜的多步驟分析:
- 先查詢基礎數據
- 再進行計算和統計
- 最後提供綜合建議

#### 3. 資料更新
支援透過自然語言更新資料:
```
請將產品A的安全庫存更新為200件
請記錄今天收到的採購單PO-001
```

## 🔧 進階設定

### 自訂 Ollama 模型

1. 下載其他模型:
```bash
ollama pull llama3
ollama pull mistral
```

2. 在 Streamlit 界面選擇模型

### 調整系統參數

編輯 `agent.py` 中的參數:
```python
max_iterations = 20  # 最大迭代次數
timeout = 300        # 模型請求超時時間(秒)
```

### 自訂提示詞

編輯 `prompt_template.py` 來調整 AI 的行為:
- 修改角色定義
- 添加新的查詢範例
- 調整輸出格式

## 📄 授權

本專案僅供學習和研究使用。
