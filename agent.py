import ast
import inspect
import os
import re
import sqlite3
from string import Template
from typing import List, Callable, Tuple

import click
import requests
import platform

from prompt_template import react_system_prompt_template


class ReActAgent:
    def __init__(self, tools: List[Callable], model: str, project_directory: str, db_path: str = None, ollama_url: str = "http://localhost:11434"):
        self.tools = { func.__name__: func for func in tools }
        self.model = model
        self.project_directory = project_directory
        self.db_path = db_path or os.path.join(project_directory, "erp_inventory.db")
        self.ollama_url = ollama_url
        
        # 檢查 Ollama 服務是否運行
        self.check_ollama_server()
        # 檢查模型是否存在
        self.check_model_available()
    
    def check_ollama_server(self):
        """檢查 Ollama 服務器是否正在運行"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            response.raise_for_status()
            print(f"✅ Ollama 服務器運行正常 ({self.ollama_url})")
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"❌ 無法連接到 Ollama 服務器 ({self.ollama_url})\n"
                f"請確保:\n"
                f"1. Ollama 已安裝\n"
                f"2. 運行命令: ollama serve\n"
                f"3. 服務器地址正確"
            )
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"❌ Ollama 服務器檢查失敗: {str(e)}")
    
    def check_model_available(self):
        """檢查指定的模型是否可用"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            response.raise_for_status()
            models_data = response.json()
            
            available_models = [model['name'] for model in models_data.get('models', [])]
            
            if not available_models:
                raise RuntimeError(
                    f"❌ 沒有可用的模型\n"
                    f"請先下載模型，例如: ollama pull {self.model}"
                )
            
            # 檢查指定模型是否存在（支持帶標籤和不帶標籤的匹配）
            model_exists = any(
                self.model == m or 
                self.model == m.split(':')[0] or 
                m.startswith(self.model + ':')
                for m in available_models
            )
            
            if model_exists:
                print(f"✅ 模型 '{self.model}' 可用")
            else:
                print(f"⚠️  警告: 模型 '{self.model}' 未找到")
                print(f"可用的模型: {', '.join(available_models)}")
                print(f"如需下載模型，請運行: ollama pull {self.model}")
                
                user_input = input("\n是否繼續? (Y/N): ")
                if user_input.lower() != 'y':
                    raise RuntimeError("用戶取消操作")
                    
        except requests.exceptions.RequestException as e:
            print(f"⚠️  無法檢查模型列表: {str(e)}")
            print(f"將嘗試使用模型 '{self.model}'...")

    def run(self, user_input: str):
        messages = [
            {"role": "system", "content": self.render_system_prompt(react_system_prompt_template)},
            {"role": "user", "content": f"<question>{user_input}</question>"}
        ]

        max_iterations = 20  # 防止無限循環
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            print(f"\n{'='*60}")
            print(f"迭代 {iteration}/{max_iterations}")
            print(f"{'='*60}")

            # 請求模型
            try:
                content = self.call_model(messages)
            except Exception as e:
                print(f"❌ 模型調用失敗: {str(e)}")
                raise

            # 檢測 Thought
            thought_match = re.search(r"<thought>(.*?)</thought>", content, re.DOTALL)
            if thought_match:
                thought = thought_match.group(1).strip()
                print(f"\n\n💭 Thought: {thought}")

            # 檢測模型是否輸出 Final Answer，如果是的話，直接返回
            if "<final_answer>" in content:
                final_answer = re.search(r"<final_answer>(.*?)</final_answer>", content, re.DOTALL)
                if final_answer:
                    return final_answer.group(1).strip()
                else:
                    # 如果標籤不完整，嘗試提取 <final_answer> 之後的內容
                    match = re.search(r"<final_answer>(.*)", content, re.DOTALL)
                    if match:
                        return match.group(1).strip()
                    else:
                        print("⚠️  警告: 檢測到 <final_answer> 但無法解析內容")
                        return content.strip()

            # 檢測 Action
            action_match = re.search(r"<action>(.*?)</action>", content, re.DOTALL)
            if not action_match:
                # 如果沒有找到完整的 action 標籤，但找到了開始標籤
                if "<action>" in content:
                    incomplete_match = re.search(r"<action>(.*)", content, re.DOTALL)
                    if incomplete_match:
                        print("⚠️  警告: 檢測到不完整的 <action> 標籤")
                        action = incomplete_match.group(1).strip()
                    else:
                        print("❌ 錯誤: 模型輸出了 <action> 但內容為空")
                        print(f"模型輸出: {content}")
                        raise RuntimeError("模型未正確輸出 <action>，請檢查模型輸出")
                else:
                    print("❌ 錯誤: 模型未輸出 <action> 標籤")
                    print(f"模型完整輸出:\n{content}")
                    raise RuntimeError("模型未輸出 <action>，可能是模型理解錯誤或提示詞問題")
            else:
                action = action_match.group(1).strip()
            
            # 解析 action
            try:
                tool_name, args = self.parse_action(action)
            except Exception as e:
                print(f"❌ 錯誤: 無法解析 action: {action}")
                print(f"解析錯誤: {str(e)}")
                raise RuntimeError(f"Action 解析失敗: {str(e)}")

            print(f"\n\n🔧 Action: {tool_name}({', '.join(str(a)[:50] for a in args)})")
            
            # 只有終端命令才需要詢問用戶，其他的工具直接執行
            should_continue = input(f"\n\n是否繼續?(Y/N)") if tool_name == "run_terminal_command" else "y"
            if should_continue.lower() != 'y':
                print("\n\n操作已取消。")
                return "操作被用戶取消"

            try:
                # 對於資料庫操作，傳遞資料庫路徑
                if tool_name == "execute_sql":
                    observation = self.tools[tool_name](self.db_path, *args)
                else:
                    observation = self.tools[tool_name](*args)
            except Exception as e:
                observation = f"工具執行錯誤:{str(e)}"
            print(f"\n\n🔍 Observation:{observation}")
            obs_msg = f"<observation>{observation}</observation>"
            messages.append({"role": "user", "content": obs_msg})
        
        # 達到最大迭代次數
        print(f"\n⚠️  警告: 達到最大迭代次數 ({max_iterations})，任務未完成")
        return f"任務未完成: 達到最大迭代次數 {max_iterations}"


    def get_tool_list(self) -> str:
        """生成工具列表字符串,包含函數簽名和簡要說明"""
        tool_descriptions = []
        for func in self.tools.values():
            name = func.__name__
            signature = str(inspect.signature(func))
            doc = inspect.getdoc(func)
            
            # 為資料庫操作添加額外說明
            if name == "execute_sql":
                doc += f"\n  注意: 資料庫位於 {self.db_path}"
                doc += f"\n  支援 SELECT, INSERT, UPDATE, DELETE 等 SQL 語句"
                doc += f"\n  查詢前請先確認與檢查{self.db_path}所有表格與欄位"
                doc += f"\n  查詢結果以 JSON 格式返回"
            
            tool_descriptions.append(f"- {name}{signature}: {doc}")
        return "\n".join(tool_descriptions)

    def render_system_prompt(self, system_prompt_template: str) -> str:
        """渲染系統提示模板,替換變量"""
        tool_list = self.get_tool_list()
        print(f"\n\n工具列表:\n{tool_list}")
        
        return Template(system_prompt_template).substitute(
            tool_list=tool_list
        )

    def call_model(self, messages):
        """調用本地 Ollama 模型"""
        print("\n\n正在請求模型,請稍等...")
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False
                },
                timeout=300  # 5分鐘超時
            )
            
            # 詳細的錯誤處理
            if response.status_code == 404:
                raise RuntimeError(
                    f"❌ API 端點不存在 (404)\n"
                    f"請求的 URL: {self.ollama_url}/api/chat\n"
                    f"請確保:\n"
                    f"1. Ollama 版本是最新的 (ollama --version)\n"
                    f"2. 服務正在運行 (ollama serve)\n"
                    f"3. URL 地址正確"
                )
            elif response.status_code == 400:
                error_detail = response.json().get('error', '未知錯誤')
                raise RuntimeError(
                    f"❌ 請求參數錯誤 (400)\n"
                    f"錯誤詳情: {error_detail}\n"
                    f"可能原因: 模型 '{self.model}' 不存在\n"
                    f"請運行: ollama pull {self.model}"
                )
            
            response.raise_for_status()
            
            result = response.json()
            content = result["message"]["content"]
            messages.append({"role": "assistant", "content": content})
            return content
            
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"❌ 無法連接到 Ollama 服務器\n"
                f"請確保 Ollama 服務正在運行: ollama serve"
            )
        except requests.exceptions.Timeout:
            raise RuntimeError("❌ 請求超時，模型響應時間過長")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"❌ Ollama API 請求失敗: {str(e)}")

    def parse_action(self, code_str: str) -> Tuple[str, List[str]]:
        match = re.match(r'(\w+)\((.*)\)', code_str, re.DOTALL)
        if not match:
            raise ValueError("Invalid function call syntax")

        func_name = match.group(1)
        args_str = match.group(2).strip()

        # 手動解析參數,特別處理包含多行內容的字符串
        args = []
        current_arg = ""
        in_string = False
        string_char = None
        i = 0
        paren_depth = 0
        
        while i < len(args_str):
            char = args_str[i]
            
            if not in_string:
                if char in ['"', "'"]:
                    in_string = True
                    string_char = char
                    current_arg += char
                elif char == '(':
                    paren_depth += 1
                    current_arg += char
                elif char == ')':
                    paren_depth -= 1
                    current_arg += char
                elif char == ',' and paren_depth == 0:
                    # 遇到頂層逗號,結束當前參數
                    args.append(self._parse_single_arg(current_arg.strip()))
                    current_arg = ""
                else:
                    current_arg += char
            else:
                current_arg += char
                if char == string_char and (i == 0 or args_str[i-1] != '\\'):
                    in_string = False
                    string_char = None
            
            i += 1
        
        # 添加最後一個參數
        if current_arg.strip():
            args.append(self._parse_single_arg(current_arg.strip()))
        
        return func_name, args
    
    def _parse_single_arg(self, arg_str: str):
        """解析單個參數"""
        arg_str = arg_str.strip()
        
        # 如果是字符串字面量
        if (arg_str.startswith('"') and arg_str.endswith('"')) or \
           (arg_str.startswith("'") and arg_str.endswith("'")):
            # 移除外層引號並處理轉義字符
            inner_str = arg_str[1:-1]
            # 處理常見的轉義字符
            inner_str = inner_str.replace('\\"', '"').replace("\\'", "'")
            inner_str = inner_str.replace('\\n', '\n').replace('\\t', '\t')
            inner_str = inner_str.replace('\\r', '\r').replace('\\\\', '\\')
            return inner_str
        
        # 嘗試使用 ast.literal_eval 解析其他類型
        try:
            return ast.literal_eval(arg_str)
        except (SyntaxError, ValueError):
            # 如果解析失敗,返回原始字符串
            return arg_str

    def get_operating_system_name(self):
        os_map = {
            "Darwin": "macOS",
            "Windows": "Windows",
            "Linux": "Linux"
        }

        return os_map.get(platform.system(), "Unknown")


def execute_sql(db_path, sql_query):
    """執行 SQL 查詢並返回結果"""
    try:
        print(f"  [DEBUG] 連接資料庫: {db_path}")
        print(f"  [DEBUG] 執行 SQL: {sql_query}")
        
        # 連接到 SQLite 資料庫
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # 使結果可以像字典一樣訪問
        cursor = conn.cursor()
        
        # 執行 SQL 語句
        cursor.execute(sql_query)
        
        # 判斷是查詢還是修改操作
        sql_upper = sql_query.strip().upper()
        if sql_upper.startswith('SELECT'):
            # 查詢操作
            rows = cursor.fetchall()
            # 將結果轉換為字典列表
            result = [dict(row) for row in rows]
            conn.close()
            print(f"  [DEBUG] 查詢成功，返回 {len(result)} 筆記錄")
            return result
        else:
            # 修改操作 (INSERT, UPDATE, DELETE)
            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()
            print(f"  [DEBUG] 執行成功，影響 {affected_rows} 筆記錄")
            return f"✅ 資料庫更新成功，影響{affected_rows}筆記錄"
            
    except sqlite3.Error as e:
        return f"❌ SQL 錯誤: {str(e)}"
    except Exception as e:
        return f"❌ 資料庫操作錯誤: {str(e)}"

def run_terminal_command(command):
    """用於執行終端命令"""
    import subprocess
    run_result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return "執行成功" if run_result.returncode == 0 else run_result.stderr

@click.command()
@click.argument('project_directory',
                type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--model', default='qwen3:14b', help='Ollama 模型名稱')
@click.option('--ollama-url', default='http://localhost:11434', help='Ollama 服務地址')
def main(project_directory, model, ollama_url):
    project_dir = os.path.abspath(project_directory)
    
    # 切換到項目目錄，這樣相對路徑就能正確工作
    original_cwd = os.getcwd()
    os.chdir(project_dir)
    
    print("=" * 60)
    print("ReActAgent with Ollama")
    print("=" * 60)
    print(f"📁 工作目錄: {project_dir}")
    print(f"📁 當前工作路徑: {os.getcwd()}")
    print(f"\n當前目錄文件:")
    try:
        for item in sorted(os.listdir(project_dir)):
            item_path = os.path.join(project_dir, item)
            if os.path.isfile(item_path):
                size = os.path.getsize(item_path)
                print(f"  📄 {item} ({size} bytes)")
            else:
                print(f"  📁 {item}/")
    except Exception as e:
        print(f"  無法列出文件: {e}")
    print("=" * 60)

    try:
        # 設定資料庫路徑
        db_path = os.path.join(project_dir, "erp_inventory.db")
        print(f"🗄️  資料庫路徑: {db_path}")
        
        tools = [execute_sql, run_terminal_command]
        agent = ReActAgent(tools=tools, model=model, project_directory=project_dir, db_path=db_path, ollama_url=ollama_url)

        task = input("\n請輸入任務:")

        final_answer = agent.run(task)

        print(f"\n\n✅ Final Answer:{final_answer}")
        
        # 任務完成後，顯示目錄內容的變化
        print("\n" + "=" * 60)
        print("任務完成後的目錄內容:")
        try:
            for item in sorted(os.listdir(project_dir)):
                item_path = os.path.join(project_dir, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path)
                    print(f"  📄 {item} ({size} bytes)")
                else:
                    print(f"  📁 {item}/")
        except Exception as e:
            print(f"  無法列出文件: {e}")
        print("=" * 60)
        
    except RuntimeError as e:
        print(f"\n{str(e)}")
        print("\n" + "=" * 60)
        print("故障排除步驟:")
        print("1. 檢查 Ollama 是否安裝: ollama --version")
        print("2. 啟動 Ollama 服務: ollama serve")
        print("3. 查看可用模型: ollama list")
        print("4. 下載需要的模型: ollama pull qwen2.5:14b")
        print("=" * 60)
        exit(1)
    except KeyboardInterrupt:
        print("\n\n用戶中斷操作")
        exit(0)
    finally:
        # 恢復原始工作目錄
        os.chdir(original_cwd)

if __name__ == "__main__":
    main()