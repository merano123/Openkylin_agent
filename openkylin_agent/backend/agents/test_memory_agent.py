class MemoryAgent:
    memory_db = {}

    def handle(self, mode: str, data: dict):
        if mode == "save":
            self.memory_db.update(data)
            return "已保存记忆"
        elif mode == "query":
            key = list(data.keys())[0]
            return self.memory_db.get(key, "未找到相关记忆")
        return "未知模式"
