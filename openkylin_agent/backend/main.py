from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from agents.chat_agent import ChatAgent

# 初始化应用
app = FastAPI(title="openKylin AI Agent")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化一个全局 Agent 实例
agent = ChatAgent()

# 定义请求体
class ChatRequest(BaseModel):
    message: str

# 定义聊天接口
@app.post("/chat")
async def chat(req: ChatRequest):
    reply = agent.reply(req.message)
    return {"reply": reply}
