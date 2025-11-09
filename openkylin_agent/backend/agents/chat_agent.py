from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()  
class ChatAgent:
    """
    主Agent，可根据用户输入自动调用其他Agent。
    """
    def __init__(self, planner_agent=None, executor_agent=None, memory_agent=None, collaborate_agent=None):
        api_key = os.getenv("QWEN_API_KEY")
        base_url = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.history = []
        self.planner_agent = planner_agent
        self.executor_agent = executor_agent
        self.memory_agent = memory_agent
        self.collaborate_agent = collaborate_agent

        # 确保存在可用的 MemoryAgent（若上层未注入则使用默认实现）
        if self.memory_agent is None:
            try:
                from agents.test_memory_agent import MemoryAgent as DefaultMemoryAgent
                self.memory_agent = DefaultMemoryAgent()
            except Exception:
                self.memory_agent = None

    def reply(self, user_input: str) -> str:
        """接收用户输入，自动分发到其他Agent或直接回复"""
        self.history.append({"role": "user", "content": user_input})

        # 简单关键词触发调用其他agent（可扩展为更智能的意图识别）
        if user_input.startswith("记忆:") or user_input.lower().startswith("memory:"):
            # 例：记忆: save {"key": "value"}
            try:
                rest = user_input.split(":", 1)[1].strip()
                if rest.startswith("save"):
                    import json
                    data = json.loads(rest[4:].strip())
                    result = self.memory_agent.handle("save", data)
                    reply_text = f"[MemoryAgent] {result}"
                elif rest.startswith("query"):
                    import json
                    data = json.loads(rest[5:].strip())
                    result = self.memory_agent.handle("query", data)
                    reply_text = f"[MemoryAgent] {result}"
                else:
                    reply_text = "[MemoryAgent] 用法: 记忆: save/query {json}"
            except Exception as e:
                reply_text = f"[MemoryAgent] 输入格式错误: {e}"
        elif user_input.startswith("计划:") or user_input.lower().startswith("plan:"):
            # 例：计划: 实现一个记事本
            goal = user_input.split(":", 1)[1].strip()
            steps = self.planner_agent.plan(goal)
            reply_text = f"[PlannerAgent] 任务拆解:\n" + "\n".join(steps)
        elif user_input.startswith("执行:") or user_input.lower().startswith("exec:"):
            # 例：执行: {"action": "open_app", "params": {"name": "计算器"}}
            import json
            try:
                data = json.loads(user_input.split(":", 1)[1].strip())
                action = data.get("action", "")
                params = data.get("params", {})
                result = self.executor_agent.execute(action, params)
                reply_text = f"[ExecutorAgent] {result}"
            except Exception as e:
                reply_text = f"[ExecutorAgent] 输入格式错误: {e}"
        elif user_input.startswith("协作:") or user_input.lower().startswith("collab:"):
            # 例：协作: {"sender": "A", "receiver": "B", "task": "测试"}
            import json
            try:
                data = json.loads(user_input.split(":", 1)[1].strip())
                sender = data.get("sender", "")
                receiver = data.get("receiver", "")
                task = data.get("task", "")
                result = self.collaborate_agent.communicate(sender, receiver, task)
                reply_text = f"[CollaborateAgent] {result}"
            except Exception as e:
                reply_text = f"[CollaborateAgent] 输入格式错误: {e}"
        else:
            # 默认走大模型回复
            response = self.client.chat.completions.create(
                model="qwen-turbo",
                messages=[
                    {"role": "system", "content": "你是 openKylin 桌面助手。"},
                    *self.history
                ]
            )
            reply_text = response.choices[0].message.content.strip()

        # 自动保存本轮对话到 MemoryAgent（满足“每段对话都记忆存储”的需求）
        try:
            if self.memory_agent is not None:
                self.memory_agent.handle("save", {"session_id": "default", "role": "user", "content": user_input})
                self.memory_agent.handle("save", {"session_id": "default", "role": "assistant", "content": reply_text})
        except Exception:
            # 自动保存失败不影响正常回复
            pass

        self.history.append({"role": "assistant", "content": reply_text})
        return reply_text
