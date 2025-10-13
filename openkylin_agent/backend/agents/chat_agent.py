from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()  
class ChatAgent:
    """
    一个最小可运行的智能体类。
    后续可以添加：记忆、工具调用、系统接口、A2A协作 等功能。
    """
    def __init__(self):
        api_key = os.getenv("QWEN_API_KEY")
        base_url = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.history = []

    def reply(self, user_input: str) -> str:
        """接收用户输入，生成模型回复"""
        self.history.append({"role": "user", "content": user_input})
        response = self.client.chat.completions.create(
            model="qwen-turbo",
            messages=[
                {"role": "system", "content": "你是 openKylin 桌面助手。"},
                *self.history
            ]
        )
        reply_text = response.choices[0].message.content.strip()
        self.history.append({"role": "assistant", "content": reply_text})
        return reply_text
