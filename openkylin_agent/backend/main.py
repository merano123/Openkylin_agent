from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
chat_agent = ChatAgent()
planner_agent = PlannerAgent()
executor_agent = ExecutorAgent()
memory_agent = MemoryAgent()
collaborate_agent = CollaborateAgent()


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


@app.post("/agent/chat")
async def chat(req: ChatRequest):
    """聊天接口"""
    reply = chat_agent.reply(req.message)
    return {"agent": "chat", "reply": reply}


@app.post("/agent/plan")
async def plan(req: PlanRequest):
    """任务规划接口"""
    plan_steps = planner_agent.plan(req.goal)
    return {"agent": "planner", "goal": req.goal, "steps": plan_steps}


@app.post("/agent/execute")
async def execute(req: ExecuteRequest):
    """执行系统任务接口"""
    result = executor_agent.execute(req.action, req.params)
    return {"agent": "executor", "result": result}


@app.post("/agent/memory")
async def memory(req: MemoryRequest):
    """记忆接口"""
    result = memory_agent.handle(req.mode, req.data)
    return {"agent": "memory", "mode": req.mode, "result": result}


@app.post("/agent/collaborate")
async def collaborate(req: CollaborateRequest):
    """多智能体协作接口"""
    result = collaborate_agent.communicate(req.sender, req.receiver, req.task)
    return {"agent": "collaborate", "task": req.task, "result": result}
