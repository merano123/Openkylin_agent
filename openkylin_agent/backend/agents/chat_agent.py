from openai import OpenAI
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()


class ChatAgent:
    """
    主控制 Agent：
    1. 接收用户输入
    2. 使用 LLM 分析用户意图
    3. 根据意图调用相应的子 Agent (Planner/Executor/Memory)
    4. 整合结果并返回给用户
    """

    def __init__(self, planner_agent=None, executor_agent=None, memory_agent=None, collaborate_agent=None):
        api_key = os.getenv("QWEN_API_KEY")
        base_url = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv("QWEN_MODEL", "qwen-turbo")

        # 支持多会话：{session_id: [history]}
        self.sessions = {}

        # 子 Agent
        self.planner_agent = planner_agent
        self.executor_agent = executor_agent
        self.memory_agent = memory_agent
        self.collaborate_agent = collaborate_agent

        # 确保存在可用的 MemoryAgent
        if self.memory_agent is None:
            try:
                from agents.test_memory_agent import MemoryAgent as DefaultMemoryAgent
                self.memory_agent = DefaultMemoryAgent()
            except Exception:
                self.memory_agent = None

    def memory_entry(self, mode: str, data: dict):
        return self.memory_agent.handle(mode, data)

    def _analyze_intent(self, user_input: str, history: list) -> dict:
        """
        使用 LLM 分析用户意图

        返回:
        {
            "intent": "execute_action" | "plan_task" | "query_memory" | "chat",
            "action": "open_app" | "create_file" | ...,  # 当 intent="execute_action" 时
            "params": {...},  # 操作参数
            "goal": "...",  # 当 intent="plan_task" 时
            "query": "..."  # 当 intent="query_memory" 时
        }
        """
        system_prompt = """你是 openKylin 系统的智能助手。分析用户的意图并返回 JSON 格式的结果。

意图类型：
1. execute_action - 执行具体的系统操作（打开应用、文件操作、查看系统信息等）
2. plan_task - 制定复杂任务的执行计划
3. query_memory - 查询历史对话或操作记录
4. chat - 普通对话（问候、闲聊、咨询等）

可执行的操作（execute_action）：
- open_app: 打开应用，params: {"name": "应用名"}
- create_file: 创建文件，params: {"path": "路径", "content": "内容"}
- create_directory: 创建目录，params: {"path": "路径"}
- read_file: 读取文件，params: {"path": "路径"}
- write_file: 写入文件，params: {"path": "路径", "content": "内容"}
- list_directory: 列出目录，params: {"path": "路径"}
- delete_file: 删除文件，params: {"path": "路径"}
- open_url: 打开网页，params: {"url": "网址"}
- search_web: 搜索网页，params: {"query": "关键词"}
- get_system_info: 获取系统信息，params: {}
- get_disk_usage: 获取磁盘使用，params: {"path": "/"}
- get_current_time: 获取当前时间，params: {}
- get_process_list: 获取进程列表，params: {"limit": 10}
- search_package: 搜索软件包，params: {"keyword": "关键词"}
- install_package: 安装软件，params: {"package": "包名"}

路径规则（重要 - openKylin 中文系统）：
- 桌面文件用: "桌面/文件名" 或 "Desktop/文件名" 或 "~/桌面/文件名"
- 文档目录用: "文档/文件名" 或 "Documents/文件名"
- 下载目录用: "下载/文件名" 或 "Downloads/文件名"
- 图片目录用: "图片/文件名" 或 "Pictures/文件名"
- 用户主目录: "~/文件名" 或 "文件名"
- 绝对路径: "/home/用户名/文件名"
- 注意：openKylin 中文系统的用户目录通常是中文名（桌面、文档、下载等）

示例：
用户："打开火狐浏览器" -> {"intent": "execute_action", "action": "open_app", "params": {"name": "firefox"}}
用户："在桌面上创建一个test.txt" -> {"intent": "execute_action", "action": "create_file", "params": {"path": "桌面/test.txt", "content": ""}}
用户："帮我在桌面创建一个叫 hello.txt 的文件" -> {"intent": "execute_action", "action": "create_file", "params": {"path": "桌面/hello.txt", "content": ""}}
用户："在文档目录创建readme.md" -> {"intent": "execute_action", "action": "create_file", "params": {"path": "文档/readme.md", "content": ""}}
用户："帮我制定一个学习Python的计划" -> {"intent": "plan_task", "goal": "学习Python"}
用户："我刚才问了什么" -> {"intent": "query_memory", "query": "recent"}
用户："你好" -> {"intent": "chat"}

只返回 JSON，不要其他文字。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"分析这句话的意图：{user_input}"}
                ],
                temperature=0.3,
            )

            content = response.choices[0].message.content.strip()

            # 移除可能的 markdown 代码块标记
            if content.startswith("```"):
                content = re.sub(r"```json\n?|```\n?", "", content).strip()

            intent_data = json.loads(content)
            return intent_data

        except Exception as e:
            print(f"意图分析失败: {e}")
            # 降级：使用关键词匹配
            return self._fallback_intent_analysis(user_input)

    def _fallback_intent_analysis(self, user_input: str) -> dict:
        """当 LLM 分析失败时的后备方案"""
        text = user_input.lower()

        # 系统操作关键词
        if any(word in text for word in ["打开", "启动", "运行"]):
            # 提取应用名
            app_name = "firefox"  # 默认
            if "火狐" in text or "firefox" in text:
                app_name = "firefox"
            elif "浏览器" in text:
                app_name = "浏览器"
            elif "文件" in text and "管理" in text:
                app_name = "文件管理器"
            elif "终端" in text:
                app_name = "终端"
            elif "计算器" in text:
                app_name = "计算器"

            return {"intent": "execute_action", "action": "open_app", "params": {"name": app_name}}

        if any(word in text for word in ["创建文件", "新建文件", "创建", "新建"]):
            # 默认在桌面创建
            return {"intent": "execute_action", "action": "create_file",
                    "params": {"path": "桌面/new_file.txt", "content": ""}}

        if any(word in text for word in ["系统信息", "系统状态"]):
            return {"intent": "execute_action", "action": "get_system_info", "params": {}}

        if any(word in text for word in ["磁盘", "硬盘", "存储空间"]):
            return {"intent": "execute_action", "action": "get_disk_usage", "params": {"path": "/"}}

        if any(word in text for word in ["进程", "任务"]):
            return {"intent": "execute_action", "action": "get_process_list", "params": {"limit": 10}}

        if any(word in text for word in ["搜索软件", "查找软件", "搜索包"]):
            return {"intent": "execute_action", "action": "search_package", "params": {"keyword": "firefox"}}

        if any(word in text for word in ["计划", "规划", "方案"]):
            return {"intent": "plan_task", "goal": user_input}

        if any(word in text for word in ["历史", "之前", "刚才", "记录"]):
            return {"intent": "query_memory", "query": "recent"}

        # 默认为普通对话
        return {"intent": "chat"}

    def reply(self, user_input: str, session_id: str = "default") -> str:
        """接收用户输入，智能分发到相应的 Agent 执行任务"""
        # 获取或创建会话历史
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        history = self.sessions[session_id]

        history.append({"role": "user", "content": user_input})

        try:
            # 1. 分析用户意图
            intent_data = self._analyze_intent(user_input, history)
            intent = intent_data.get("intent", "chat")

            print(f"[ChatAgent] 意图分析结果: {intent_data}")  # 调试信息

            # 2. 根据意图调用相应的 Agent
            if intent == "execute_action":
                # 调用 ExecutorAgent 执行系统操作
                action = intent_data.get("action")
                params = intent_data.get("params", {})

                print(f"[ChatAgent] 调用 ExecutorAgent: {action}, {params}")
                result = self.executor_agent.execute(action, params)

                # 3. 格式化执行结果
                if result.get("success"):
                    reply_text = f"✅ {result.get('message')}"

                    # 根据不同的操作类型，格式化数据展示
                    data = result.get("data")
                    if data:
                        if action == "list_directory":
                            reply_text += f"\n\n📁 目录内容（共 {data.get('count', 0)} 项）："
                            for item in data.get("items", [])[:15]:
                                icon = "📁" if item.get("type") == "dir" else "📄"
                                reply_text += f"\n{icon} {item.get('name')}"

                        elif action == "get_system_info":
                            reply_text += "\n\n💻 系统信息："
                            for key, value in data.items():
                                reply_text += f"\n• {key}: {value}"

                        elif action == "get_disk_usage":
                            total_gb = data.get("total", 0) / (1024 ** 3)
                            used_gb = data.get("used", 0) / (1024 ** 3)
                            free_gb = data.get("free", 0) / (1024 ** 3)
                            percent = data.get("percent", 0)
                            reply_text += f"\n\n💾 磁盘使用情况："
                            reply_text += f"\n• 总容量: {total_gb:.2f} GB"
                            reply_text += f"\n• 已使用: {used_gb:.2f} GB ({percent}%)"
                            reply_text += f"\n• 可用: {free_gb:.2f} GB"

                        elif action == "get_process_list":
                            reply_text += f"\n\n⚙️ 进程列表（共 {data.get('count', 0)} 个）："
                            for proc in data.get("processes", [])[:10]:
                                cmd = proc.get("command", "")[:60]
                                reply_text += f"\n• PID {proc['pid']}: {cmd}"

                        elif action == "search_package":
                            reply_text += f"\n\n🔍 找到 {data.get('count', 0)} 个软件包："
                            for pkg in data.get("packages", [])[:10]:
                                reply_text += f"\n• {pkg}"

                        elif action == "read_file":
                            content = data.get("content", "")
                            if len(content) > 500:
                                content = content[:500] + "\n...(内容过长，已截断)"
                            reply_text += f"\n\n📄 文件内容：\n{content}"

                        elif action == "get_current_time":
                            reply_text += f"\n\n🕒 {data.get('datetime')}"
                else:
                    reply_text = f"❌ {result.get('message', '操作失败')}"

            elif intent == "plan_task":
                # 调用 PlannerAgent 制定任务计划
                goal = intent_data.get("goal", user_input)

                print(f"[ChatAgent] 调用 PlannerAgent: {goal}")
                steps = self.planner_agent.plan(goal)

                # 格式化计划输出
                reply_text = f"📋 已为您制定执行计划：{goal}\n"
                for step in steps:
                    step_num = step.get("step", "?")
                    desc = step.get("description", "")
                    action = step.get("action", "")
                    time_est = step.get("estimated_time", 0)

                    reply_text += f"\n{step_num}. {desc}"
                    if action:
                        reply_text += f" [{action}]"
                    if time_est > 0:
                        reply_text += f" (约 {time_est}秒)"

                reply_text += "\n\n💡 提示：您可以让我逐步执行这些操作"

            elif intent == "query_memory":
                # 调用 MemoryAgent 查询历史记录
                query_type = intent_data.get("query", "recent")

                print(f"[ChatAgent] 调用 MemoryAgent: {query_type}")

                if query_type == "recent" or query_type == "conversation":
                    records = self.memory_agent.get_context(None, limit=10)
                    reply_text = f"📜 最近的对话记录（共 {len(records)} 条）：\n"
                    for record in records[-5:]:  # 只显示最近5条
                        role = "我" if record["role"] == "user" else "助手"
                        content = record["content"][:80]
                        if len(record["content"]) > 80:
                            content += "..."
                        reply_text += f"\n{role}: {content}"
                else:
                    # 关键词搜索
                    records = self.memory_agent.search_context(None, query_type, limit=5)
                    if records:
                        reply_text = f"🔍 搜索「{query_type}」的结果（共 {len(records)} 条）：\n"
                        for record in records:
                            role = "我" if record["role"] == "user" else "助手"
                            content = record["content"][:80]
                            reply_text += f"\n{role}: {content}"
                    else:
                        reply_text = f"没有找到关于「{query_type}」的记录"

            else:
                # 普通对话，直接使用 LLM 回复
                print(f"[ChatAgent] 普通对话模式")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": """你是 openKylin 系统的智能助手，友好、专业、有帮助。

你可以帮助用户：
- 执行系统操作（打开应用、文件管理、查看系统信息等）
- 制定任务计划
- 查询历史记录
- 回答关于 openKylin 的问题

请用简洁、友好的语气回复用户。"""
                        },
                        *history
                    ],
                    temperature=0.7,
                )
                reply_text = response.choices[0].message.content.strip()

        except Exception as e:
            print(f"[ChatAgent] 处理失败: {e}")
            import traceback
            traceback.print_exc()

            # 降级到简单对话模式
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是 openKylin 桌面助手。"},
                        *history
                    ],
                    temperature=0.7,
                )
                reply_text = response.choices[0].message.content.strip()
            except:
                reply_text = f"抱歉，处理您的请求时出现了问题：{str(e)}"

        # 4. 保存对话到 MemoryAgent
        try:
            if self.memory_agent is not None:
                self.memory_agent.add_message(session_id, "user", user_input)
                self.memory_agent.add_message(session_id, "assistant", reply_text)
        except Exception as e:
            print(f"[ChatAgent] 保存记忆失败: {e}")

        history.append({"role": "assistant", "content": reply_text})
        return reply_text