import os
import json
import sqlite3
import time
from typing import List, Dict, Any, Optional


class MemoryAgent:
    """
    记忆智能体（MemoryAgent）：
    - 存储会话上下文（按 `session_id` 分组）。
    - 记录与检索历史操作（类型、摘要、附加元数据）。
    - 提供简单的关键词检索（会话消息与操作摘要/元数据）。

    存储介质：SQLite（默认在本文件同目录的 `memory.sqlite`）。

    统一入口：`handle(mode, data)` 与 `run(**kwargs)`。
    - `mode='save'`：保存会话消息 / 操作 / 键值。
    - `mode='query'`：查询上下文 / 操作 / 关键词检索 / 键值。
    """

    def __init__(self, db_path: Optional[str] = None):
        base_dir = os.path.dirname(__file__)
        self.db_path = db_path or os.path.join(base_dir, "memory.sqlite")
        # 使用 check_same_thread=False 允许在简单场景下跨线程访问
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        """初始化三张表：会话、操作、键值。"""
        cur = self.conn.cursor()
        # 会话消息表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                ts REAL
            )
            """
        )
        # 操作日志表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                op_type TEXT,
                summary TEXT,
                metadata TEXT,
                ts REAL
            )
            """
        )
        # 键值存储表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS kv_store (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                key TEXT,
                value TEXT,
                ts REAL
            )
            """
        )
        self.conn.commit()

    # ---------- 会话记忆 ----------
    def add_message(self, session_id: str, role: str, content: str, ts: Optional[float] = None) -> None:
        ts = ts or time.time()
        self.conn.execute(
            "INSERT INTO conversations (session_id, role, content, ts) VALUES (?, ?, ?, ?)",
            (session_id, role, content, ts),
        )
        self.conn.commit()

    def get_context(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """返回最近的 `limit` 条消息，按时间正序（从旧到新）。"""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT role, content, ts FROM (
                SELECT role, content, ts FROM conversations
                WHERE session_id = ?
                ORDER BY ts DESC
                LIMIT ?
            ) sub ORDER BY ts ASC
            """,
            (session_id, limit),
        )
        rows = cur.fetchall()
        return [{"role": r[0], "content": r[1], "ts": r[2]} for r in rows]

    def search_context(self, session_id: str, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """按关键词检索会话消息，返回最新匹配（按时间倒序）。"""
        cur = self.conn.cursor()
        like = f"%{keyword}%"
        cur.execute(
            """
            SELECT role, content, ts
            FROM conversations
            WHERE session_id = ? AND content LIKE ?
            ORDER BY ts DESC
            LIMIT ?
            """,
            (session_id, like, limit),
        )
        rows = cur.fetchall()
        return [{"role": r[0], "content": r[1], "ts": r[2]} for r in rows]

    # ---------- 操作记忆 ----------
    def record_operation(
        self,
        session_id: str,
        op_type: str,
        summary: str,
        metadata: Optional[Dict[str, Any]] = None,
        ts: Optional[float] = None,
    ) -> None:
        ts = ts or time.time()
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
        self.conn.execute(
            "INSERT INTO operations (session_id, op_type, summary, metadata, ts) VALUES (?, ?, ?, ?, ?)",
            (session_id, op_type, summary, metadata_json, ts),
        )
        self.conn.commit()

    def get_operations(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT op_type, summary, metadata, ts FROM operations WHERE session_id = ? ORDER BY ts DESC LIMIT ?",
            (session_id, limit),
        )
        rows = cur.fetchall()
        return [
            {
                "op_type": r[0],
                "summary": r[1],
                "metadata": json.loads(r[2] or "{}"),
                "ts": r[3],
            }
            for r in rows
        ]

    def search_operations(self, session_id: str, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        like = f"%{keyword}%"
        cur.execute(
            """
            SELECT op_type, summary, metadata, ts
            FROM operations
            WHERE session_id = ? AND (summary LIKE ? OR metadata LIKE ?)
            ORDER BY ts DESC
            LIMIT ?
            """,
            (session_id, like, like, limit),
        )
        rows = cur.fetchall()
        return [
            {
                "op_type": r[0],
                "summary": r[1],
                "metadata": json.loads(r[2] or "{}"),
                "ts": r[3],
            }
            for r in rows
        ]

    # ---------- 键值记忆 ----------
    def save_kv(self, session_id: str, key: str, value: Any, ts: Optional[float] = None) -> None:
        ts = ts or time.time()
        value_json = json.dumps(value, ensure_ascii=False)
        self.conn.execute(
            "INSERT INTO kv_store (session_id, key, value, ts) VALUES (?, ?, ?, ?)",
            (session_id, key, value_json, ts),
        )
        self.conn.commit()

    def get_kv(self, session_id: str, key: str) -> Optional[Any]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT value FROM kv_store WHERE session_id = ? AND key = ? ORDER BY ts DESC LIMIT 1",
            (session_id, key),
        )
        row = cur.fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except Exception:
            return row[0]

    # ---------- 兼容入口（供路由或其他 Agent 调用） ----------
    def handle(self, mode: str, data: Dict[str, Any]):
        """
        与既有调用方式保持兼容的统一入口。

        模式：
        - 'save'（保存）：
            * 当提供 'content' 时保存会话消息。
              字段：session_id（可选，默认 'default'）、role（可选，默认 'user'）、content（必填）
            * 当提供 'op_type' 与 'summary' 时记录一次操作。
              字段：session_id（可选）、op_type（必填）、summary（必填）、metadata（可选）
            * 当提供 'key' 与 'value' 时保存通用键值记忆。
        - 'query'（查询）：
            * 当 {'type': 'context', 'session_id', 'limit'} 时返回最近会话上下文。
            * 当 {'type': 'operations', 'session_id', 'limit'} 时返回最近操作列表。
            * 当 {'type': 'search_context'|'search_operations', 'keyword', 'session_id', 'limit'} 时执行关键字检索。
            * 当仅提供 {'key', 'session_id'} 时返回对应键值。
        """
        # 按您的需求：每次调用前先输出一句话
        print("我是memory")

        session_id = data.get("session_id", "default")

        if mode == "save":
            if "content" in data:  # 保存会话消息
                role = data.get("role", "user")
                self.add_message(session_id=session_id, role=role, content=data["content"]) 
                return {"status": "ok", "msg": "context_saved"}
            elif "op_type" in data and "summary" in data:  # 记录一次操作
                self.record_operation(
                    session_id=session_id,
                    op_type=data["op_type"],
                    summary=data["summary"],
                    metadata=data.get("metadata"),
                )
                return {"status": "ok", "msg": "operation_recorded"}
            elif "key" in data and "value" in data:  # 保存键值记忆
                self.save_kv(session_id=session_id, key=data["key"], value=data["value"]) 
                return {"status": "ok", "msg": "kv_saved"}
            else:
                return {"status": "error", "msg": "invalid_save_payload"}

        elif mode == "query":
            qtype = data.get("type")
            limit = int(data.get("limit", 20))
            if qtype == "context":
                return {"status": "ok", "data": self.get_context(session_id, limit)}
            elif qtype == "operations":
                return {"status": "ok", "data": self.get_operations(session_id, limit)}
            elif qtype == "search_context":
                keyword = data.get("keyword", "")
                return {"status": "ok", "data": self.search_context(session_id, keyword, limit)}
            elif qtype == "search_operations":
                keyword = data.get("keyword", "")
                return {"status": "ok", "data": self.search_operations(session_id, keyword, limit)}
            elif "key" in data:  # 查询键值
                val = self.get_kv(session_id=session_id, key=data["key"]) 
                if val is None:
                    return {"status": "miss", "msg": "not_found"}
                return {"status": "ok", "data": val}
            else:
                return {"status": "error", "msg": "invalid_query_payload"}

        return {"status": "error", "msg": "unknown_mode"}

    def run(self, **kwargs):
        """统一入口的轻量封装：`run(mode=..., data=...)`。"""
        mode = kwargs.get("mode")
        data = kwargs.get("data", {})
        return self.handle(mode, data)