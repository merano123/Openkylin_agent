from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

# 导入多个 Agent 模块
from agents.chat_agent import ChatAgent
from agents.test_planner_agent import PlannerAgent
from agents.test_executor_agent import ExecutorAgent
from agents.test_memory_agent import MemoryAgent
from agents.test_collaborate_agent import CollaborateAgent

# 初始化应用
app = FastAPI(title="openKylin Multi-Agent Backend")

# 允许跨域访问（前端可直接请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 Agent 实例

# 先初始化子agent
planner_agent = PlannerAgent()
executor_agent = ExecutorAgent()
memory_agent = MemoryAgent()
collaborate_agent = CollaborateAgent()
# 主agent注入子agent
chat_agent = ChatAgent(
    planner_agent=planner_agent,
    executor_agent=executor_agent,
    memory_agent=memory_agent,
    collaborate_agent=collaborate_agent
)


# 定义请求体模型
class ChatRequest(BaseModel):
    message: str


class PlanRequest(BaseModel):
    goal: str


class ExecuteRequest(BaseModel):
    action: str
    params: dict = {}


class MemoryRequest(BaseModel):
    mode: str  # "save" 或 "query"
    data: dict = {}


class CollaborateRequest(BaseModel):
    sender: str
    receiver: str
    task: str


# 接口定义区域

@app.get("/")
async def root():
    """测试接口"""
    return {"status": "ok", "message": "openKylin Multi-Agent backend running"}

# 只保留 chat agent 统一入口
@app.post("/api/agent")
async def chat_entry(request: Request, response: Response):
    data = await request.json()
    message = data.get("message") or data.get("content") or data.get("text")
    incoming_sid = data.get("session_id")
    cookie_sid = request.cookies.get("ok_session_id")
    session_id = incoming_sid or cookie_sid or uuid.uuid4().hex
    if cookie_sid is None:
        response.set_cookie(key="ok_session_id", value=session_id, max_age=31536000, path="/", samesite="lax")
    if not message:
        return {"error": "缺少 message 字段"}
    reply = chat_agent.reply(message, session_id)
    return {"agent": "chat", "reply": reply, "session_id": session_id}

@app.post("/api/memory")
async def memory_entry(req: MemoryRequest, request: Request, response: Response):
    cookie_sid = request.cookies.get("ok_session_id")
    data = dict(req.data or {})
    session_id = data.get("session_id") or cookie_sid or uuid.uuid4().hex
    if cookie_sid is None:
        response.set_cookie(key="ok_session_id", value=session_id, max_age=31536000, path="/", samesite="lax")
    data["session_id"] = session_id
    return chat_agent.memory_entry(req.mode, data)
