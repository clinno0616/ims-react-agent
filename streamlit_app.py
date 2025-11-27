"""
Streamlit 前端 ERP 進銷存 AI 查詢系統
使用 Ollama qwen3:14b 模型和 ReAct Agent
"""
import streamlit as st
import os
import sys
import sqlite3
import requests
from datetime import datetime

# 添加當前目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import ReActAgent, execute_sql, run_terminal_command
from prompt_template import react_system_prompt_template

def get_ollama_models(base_url):
    """獲取 Ollama 可用模型列表"""
    try:
        # 確保 URL 格式正確
        if not base_url.startswith('http'):
            base_url = f"http://{base_url}"
        
        response = requests.get(f"{base_url}/api/tags", timeout=2)
        if response.status_code == 200:
            data = response.json()
            models = [model['name'] for model in data['models']]
            return models
        return []
    except Exception:
        return []

# 頁面配置
st.set_page_config(
    page_title="ERP 進銷存 AI 查詢系統",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定義 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #1f77b4;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
        font-weight: bold;
        border-radius: 5px;
        padding: 0.5rem 1rem;
    }
    .stButton>button:hover {
        background-color: #145a8c;
    }
    .info-box {
        background-color: #e7f3ff;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #ffc107;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 初始化 Session State
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'db_connected' not in st.session_state:
    st.session_state.db_connected = False
if 'execution_logs' not in st.session_state:
    st.session_state.execution_logs = []
if 'current_iteration' not in st.session_state:
    st.session_state.current_iteration = 0

def init_agent(db_path, model, ollama_url):
    """初始化 Agent"""
    try:
        project_dir = os.path.dirname(os.path.abspath(__file__))
        tools = [execute_sql, run_terminal_command]
        agent = ReActAgent(
            tools=tools,
            model=model,
            project_directory=project_dir,
            db_path=db_path,
            ollama_url=ollama_url
        )
        return agent, None
    except Exception as e:
        return None, str(e)

def check_database(db_path):
    """檢查資料庫連接和內容"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 獲取資料表列表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # 獲取基本統計
        stats = {}
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        
        conn.close()
        return True, tables, stats
    except Exception as e:
        return False, [], {}

def format_agent_response(response):
    """格式化 Agent 回應"""
    # 移除 XML 標籤
    import re
    response = re.sub(r'<[^>]+>', '', response)
    return response.strip()

def run_agent_with_logs(agent, user_input, max_iterations=20):
    """執行 Agent 並捕獲詳細日誌"""
    import re
    from datetime import datetime
    
    logs = []
    messages = [
        {"role": "system", "content": agent.render_system_prompt(react_system_prompt_template)},
        {"role": "user", "content": f"<question>{user_input}</question>"}
    ]
    
    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        
        log_entry = {
            "iteration": iteration,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "thought": "",
            "action": "",
            "observation": "",
            "final_answer": ""
        }
        
        try:
            # 調用模型
            content = agent.call_model(messages)
            
            # 提取 Thought
            thought_match = re.search(r"<thought>(.*?)</thought>", content, re.DOTALL)
            if thought_match:
                log_entry["thought"] = thought_match.group(1).strip()
            
            # 檢測 Final Answer
            if "<final_answer>" in content:
                final_answer = re.search(r"<final_answer>(.*?)</final_answer>", content, re.DOTALL)
                if final_answer:
                    log_entry["final_answer"] = final_answer.group(1).strip()
                    logs.append(log_entry)
                    full_logs = {
                        "question": user_input,
                        "tool_list": agent.get_tool_list(),
                        "iterations": logs
                    }
                    return log_entry["final_answer"], full_logs
                else:
                    match = re.search(r"<final_answer>(.*)", content, re.DOTALL)
                    if match:
                        log_entry["final_answer"] = match.group(1).strip()
                        logs.append(log_entry)
                        full_logs = {
                            "question": user_input,
                            "tool_list": agent.get_tool_list(),
                            "iterations": logs
                        }
                        return log_entry["final_answer"], full_logs
            
            # 提取 Action
            action_match = re.search(r"<action>(.*?)</action>", content, re.DOTALL)
            if not action_match:
                if "<action>" in content:
                    incomplete_match = re.search(r"<action>(.*)", content, re.DOTALL)
                    if incomplete_match:
                        action = incomplete_match.group(1).strip()
                    else:
                        # 模型輸出了 action 標籤但沒有內容
                        log_entry["observation"] = "模型輸出了 <action> 但內容為空，提示繼續"
                        logs.append(log_entry)
                        messages.append({"role": "user", "content": "請繼續你的操作，確保 <action> 標籤內有內容。"})
                        continue
                else:
                    # 完全沒有 action 標籤
                    # 可能是模型忘記了，或者它認為它已經回答了但沒有用 final_answer 標籤
                    log_entry["observation"] = "模型未輸出 <action> 標籤，提示繼續或給出最終答案"
                    logs.append(log_entry)
                    messages.append({"role": "user", "content": "請執行下一步操作 (使用 <action> 標籤) 或給出最終答案 (使用 <final_answer> 標籤)。"})
                    continue
            else:
                action = action_match.group(1).strip()
            
            log_entry["action"] = action
            
            # 解析並執行 action
            try:
                tool_name, args = agent.parse_action(action)
                
                # 執行工具
                if tool_name == "execute_sql":
                    observation = agent.tools[tool_name](agent.db_path, *args)
                else:
                    observation = agent.tools[tool_name](*args)
                
                log_entry["observation"] = str(observation)
                
            except Exception as e:
                observation = f"工具執行錯誤: {str(e)}"
                log_entry["observation"] = observation
            
            logs.append(log_entry)
            
            # 添加 observation 到消息
            obs_msg = f"<observation>{observation}</observation>"
            messages.append({"role": "user", "content": obs_msg})
            
        except Exception as e:
            log_entry["observation"] = f"錯誤: {str(e)}"
            logs.append(log_entry)
            full_logs = {
                "question": user_input,
                "tool_list": agent.get_tool_list(),
                "iterations": logs
            }
            return f"處理過程中發生錯誤: {str(e)}", full_logs
    
    full_logs = {
        "question": user_input,
        "tool_list": agent.get_tool_list(),
        "iterations": logs
    }
    return f"任務未完成: 達到最大迭代次數 {max_iterations}", full_logs

# ==================== 側邊欄配置 ====================
with st.sidebar:
    st.markdown("### ⚙️ 系統配置")
    
    # 頁面導航
    st.markdown("#### 🧭 頁面導航")
    page = st.radio("選擇功能", ["💬 AI 對話", "📊 資料庫瀏覽"])
    st.markdown("---")
    
    # 資料庫設定
    st.markdown("#### 📁 資料庫設定")
    db_options = {
        "樣本資料庫 (120 產品)": "erp_inventory_sample.db",
        "基本資料庫 (4 產品)": "erp_inventory.db",
        "自定義": "custom"
    }
    db_choice = st.selectbox("選擇資料庫", list(db_options.keys()))
    
    if db_choice == "自定義":
        db_path = st.text_input("資料庫路徑", "erp_inventory.db")
    else:
        db_path = db_options[db_choice]
    
    # 模型設定
    st.markdown("#### 🤖 模型設定")
    ollama_url = st.text_input("Ollama URL", "http://localhost:11434")
    
    # 自動獲取模型列表
    available_models = get_ollama_models(ollama_url)
    
    if available_models:
        # 嘗試預設選中 qwen3:14b 或 qwen3:8b
        default_index = 0
        if "qwen3:14b" in available_models:
            default_index = available_models.index("qwen3:14b")
        elif "qwen3:8b" in available_models:
            default_index = available_models.index("qwen3:8b")
            
        model = st.selectbox("選擇 Ollama 模型", available_models, index=default_index)
        st.caption(f"✅ 偵測到 {len(available_models)} 個模型")
    else:
        st.warning("⚠️ 無法連接 Ollama 或未找到模型")
        model = st.text_input("手動輸入模型名稱", "qwen3:14b")
        st.caption("請確保 Ollama 正在運行 (預設端口 11434)")
    
    # 連接按鈕
    if st.button("🔌 連接系統", type="primary"):
        with st.spinner("正在連接..."):
            # 檢查資料庫
            db_exists = os.path.exists(db_path)
            if not db_exists:
                st.error(f"❌ 資料庫不存在: {db_path}")
            else:
                is_valid, tables, stats = check_database(db_path)
                if is_valid:
                    # 初始化 Agent
                    agent, error = init_agent(db_path, model, ollama_url)
                    if agent:
                        st.session_state.agent = agent
                        st.session_state.db_connected = True
                        st.session_state.db_path = db_path
                        st.session_state.db_tables = tables
                        st.session_state.db_stats = stats
                        st.success("✅ 系統連接成功！")
                    else:
                        st.error(f"❌ Agent 初始化失敗: {error}")
                else:
                    st.error("❌ 資料庫格式錯誤")
    
    # 顯示連接狀態
    st.markdown("---")
    st.markdown("#### 📊 連接狀態")
    if st.session_state.db_connected:
        st.markdown('<div class="success-box">✅ 已連接</div>', unsafe_allow_html=True)
        st.markdown(f"**資料庫**: `{st.session_state.db_path}`")
        st.markdown(f"**模型**: `{model}`")
        
        # 顯示資料庫統計
        if 'db_stats' in st.session_state:
            st.markdown("**資料表統計**:")
            for table, count in st.session_state.db_stats.items():
                if table != 'sqlite_sequence':
                    st.markdown(f"- {table}: {count} 筆")
    else:
        st.markdown('<div class="warning-box">⚠️ 未連接</div>', unsafe_allow_html=True)
    
    # 清除對話歷史
    st.markdown("---")
    if st.button("🗑️ 清除對話歷史"):
        st.session_state.chat_history = []
        st.rerun()



# ==================== 主要內容區 ====================
if page == "💬 AI 對話":
    st.markdown('<div class="main-header">📊 ERP 進銷存 AI 查詢系統</div>', unsafe_allow_html=True)
    
    # 檢查是否已連接
    if not st.session_state.db_connected:
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.markdown("""
        ### 👋 歡迎使用 ERP 進銷存 AI 查詢系統
        
        **開始使用前，請先在左側設定並連接系統：**
        
        1. 選擇資料庫（建議使用樣本資料庫）
        2. 確認 Ollama 模型設定
        3. 點擊「連接系統」按鈕
        
        **系統功能：**
        - 📊 智能查詢庫存、訂單、採購數據
        - 📈 自動分析進銷存趨勢
        - 💡 提供庫存管理建議
        - 🔍 多維度數據統計
        
        **提示：** 如果還沒有資料庫，請先運行：
        ```bash
        python generate_sample_data.py
        ```
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # 創建兩欄布局
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 💬 AI 對話")
            
            # 顯示對話歷史
            chat_container = st.container()
            with chat_container:
                for i, (role, message) in enumerate(st.session_state.chat_history):
                    if role == "user":
                        st.markdown(f"""
                        <div style="background-color: #e3f2fd; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;">
                            <strong>👤 您:</strong><br>{message}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="background-color: #f5f5f5; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;">
                            <strong>🤖 AI 助手:</strong><br>{message}
                        </div>
                        """, unsafe_allow_html=True)
            
            # 輸入區域
            st.markdown("---")
            user_input = st.text_area(
                "請輸入您的問題",
                height=100,
                placeholder="例如：請查詢當前庫存低於安全庫存的產品\n或：請分析上個月的進銷存情況"
            )
            
            col_btn1, col_btn2 = st.columns([1, 5])
            with col_btn1:
                submit_button = st.button("🚀 發送", type="primary")
            
            if submit_button and user_input:
                # 添加用戶消息到歷史
                st.session_state.chat_history.append(("user", user_input))
                
                # 顯示處理中
                with st.spinner("🤔 AI 正在思考..."):
                    try:
                        # 調用 Agent 並捕獲日誌
                        response, full_logs = run_agent_with_logs(st.session_state.agent, user_input)
                        
                        # 保存執行日誌
                        st.session_state.execution_logs = full_logs
                        st.session_state.current_iteration = len(full_logs['iterations'])
                        
                        # 格式化回應
                        formatted_response = format_agent_response(response)
                        
                        # 添加 AI 回應到歷史
                        st.session_state.chat_history.append(("assistant", formatted_response))
                        
                        # 重新載入頁面以顯示新消息
                        st.rerun()
                        
                    except Exception as e:
                        error_msg = f"❌ 處理錯誤: {str(e)}"
                        st.session_state.chat_history.append(("assistant", error_msg))
                        st.error(error_msg)
        
        with col2:
            st.markdown("### 📚 快速查詢範例")
            
            # 預設查詢範例
            examples = {
                "📦 庫存查詢": [
                    "請查詢當前庫存低於安全庫存的產品",
                    "請列出所有電子零件(A類)的庫存情況",
                    "請查詢庫存最多的前10個產品"
                ],
                "📋 訂單分析": [
                    "請統計各狀態的訂單數量和金額",
                    "請查詢最近的10筆訂單",
                    "請分析哪些客戶的訂單金額最高"
                ],
                "🏭 採購分析": [
                    "請統計各供應商的採購金額",
                    "請查詢待處理的採購單",
                    "請分析最常採購的產品"
                ],
                "📈 趨勢分析": [
                    "請分析最近6個月的進銷存趨勢",
                    "請計算庫存周轉率",
                    "請找出滯銷產品"
                ]
            }
            
            for category, queries in examples.items():
                with st.expander(category):
                    for query in queries:
                        if st.button(query, key=f"example_{query}"):
                            st.session_state.chat_history.append(("user", query))
                            with st.spinner("🤔 AI 正在思考..."):
                                try:
                                    response, full_logs = run_agent_with_logs(st.session_state.agent, query)
                                    st.session_state.execution_logs = full_logs
                                    st.session_state.current_iteration = len(full_logs['iterations'])
                                    formatted_response = format_agent_response(response)
                                    st.session_state.chat_history.append(("assistant", formatted_response))
                                    st.rerun()
                                except Exception as e:
                                    error_msg = f"❌ 處理錯誤: {str(e)}"
                                    st.session_state.chat_history.append(("assistant", error_msg))
                                    st.error(error_msg)
            
            # 系統信息
            st.markdown("---")
            st.markdown("### ℹ️ 系統信息")
            st.markdown(f"""
            - **當前時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            - **對話輪數**: {len(st.session_state.chat_history) // 2}
            - **資料表數**: {len(st.session_state.db_tables) if 'db_tables' in st.session_state else 0}
            """)
            
            # 使用提示
            st.markdown("---")
            st.markdown("### 💡 使用提示")
            st.markdown("""
            - 使用自然語言描述您的需求
            - AI 會自動生成並執行 SQL 查詢
            - 支援複雜的多步驟分析
            - 可以要求計算、統計、排序等操作
            """)
            
            # 系統日誌
            st.markdown("---")
            st.markdown("### 🔍 系統日誌")
            
            if st.session_state.execution_logs:
                # 兼容舊格式（如果是列表則轉換）
                logs_data = st.session_state.execution_logs
                if isinstance(logs_data, list):
                    logs_data = {"question": "未知", "tool_list": "未知", "iterations": logs_data}
                
                iterations = logs_data.get("iterations", [])
                question = logs_data.get("question", "未知")
                tool_list = logs_data.get("tool_list", "未知")
                
                with st.expander(f"📋 查看執行日誌 ({len(iterations)} 次迭代)", expanded=False):
                    st.markdown(f"**❓ 用戶問題:**")
                    st.info(question)
                    
                    # 使用 HTML details 標籤來避免嵌套 expander 錯誤
                    st.markdown(f"""
                    <details>
                    <summary><strong>🛠️ 可用工具列表 (點擊展開)</strong></summary>
                    <pre>{tool_list}</pre>
                    </details>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    for log in iterations:
                        st.markdown(f"**⏱️ 迭代 {log['iteration']} ({log['timestamp']})**")
                        
                        if log['thought']:
                            st.markdown(f"**💭 思考過程 (<thought>):**")
                            st.text(log['thought'])
                        
                        if log['action']:
                            st.markdown(f"**🔧 執行動作 (<action>):**")
                            st.code(log['action'], language="python")
                        
                        if log['observation']:
                            st.markdown(f"**🔍 執行結果 (<observation>):**")
                            # 限制顯示長度
                            obs_text = str(log['observation'])
                            if len(obs_text) > 1000:
                                st.text(obs_text[:1000] + "...\n(內容過長已截斷)")
                            else:
                                st.text(obs_text)
                        
                        if log['final_answer']:
                            st.markdown(f"**✅ 最終答案 (<final_answer>):**")
                            st.success(log['final_answer'])
                        
                        st.markdown("---")
            else:
                st.info("尚無執行日誌，請先進行查詢")

elif page == "📊 資料庫瀏覽":
        try:
            conn = sqlite3.connect(st.session_state.db_path)
            
            # 獲取所有資料表
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # 選擇資料表
            selected_table = st.selectbox("選擇資料表", tables)
            
            if selected_table:
                # 獲取資料表結構
                cursor.execute(f"PRAGMA table_info({selected_table})")
                columns_info = cursor.fetchall()
                columns = [col[1] for col in columns_info]
                
                # 獲取數據
                # 添加分頁或限制
                limit = st.number_input("顯示筆數", min_value=10, max_value=1000, value=100, step=10)
                
                cursor.execute(f"SELECT * FROM {selected_table} LIMIT {limit}")
                rows = cursor.fetchall()
                
                # 顯示統計信息
                cursor.execute(f"SELECT COUNT(*) FROM {selected_table}")
                total_count = cursor.fetchone()[0]
                
                st.markdown(f"### 📋 {selected_table}")
                st.markdown(f"**總筆數**: {total_count} | **顯示**: {len(rows)} 筆")
                
                # 轉換為 DataFrame 顯示
                import pandas as pd
                if rows:
                    df = pd.DataFrame(rows, columns=columns)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("此資料表尚無數據")
                
                # 顯示欄位信息
                with st.expander("查看欄位結構"):
                    st.markdown("| 欄位名稱 | 類型 | 允許空值 | 預設值 | 主鍵 |")
                    st.markdown("|---|---|---|---|---|")
                    for col in columns_info:
                        cid, name, type_, notnull, dflt_value, pk = col
                        st.markdown(f"| {name} | {type_} | {'否' if notnull else '是'} | {dflt_value} | {'是' if pk else '否'} |")
            
            conn.close()
            
        except Exception as e:
            st.error(f"讀取資料庫失敗: {str(e)}")

# ==================== 頁腳 ====================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <small>ERP 進銷存 AI 查詢系統 | Powered by Ollama & Streamlit | v1.0</small>
</div>
""", unsafe_allow_html=True)
