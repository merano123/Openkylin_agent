import os
import sys
import subprocess
import webbrowser
import json
from pathlib import Path
from typing import Dict, Any, Optional
import platform


class ExecutorAgent:
    """
    执行器智能体（ExecutorAgent）：
    - 打开应用程序
    - 文件操作（创建、删除、移动、复制）
    - 浏览器操作（打开网页、搜索）
    - 系统信息查询
    """

    def __init__(self):
        self.system = platform.system()
        # 检测是否为 openKylin 系统
        self.is_openkylin = self._detect_openkylin()

        # 仅支持 Linux 系统
        if self.system != "Linux":
            raise RuntimeError("ExecutorAgent 仅支持 Linux/openKylin 系统")

        # 定义支持的操作类型
        self.actions = {
            # 应用程序操作
            "open_app": self._open_app,

            # 文件操作
            "create_file": self._create_file,
            "delete_file": self._delete_file,
            "move_file": self._move_file,
            "copy_file": self._copy_file,
            "read_file": self._read_file,
            "write_file": self._write_file,

            # 浏览器操作
            "open_url": self._open_url,
            "search_web": self._search_web,

            # 系统操作
            "get_system_info": self._get_system_info,
            "get_disk_usage": self._get_disk_usage,
            "get_current_time": self._get_current_time,
        }

    def _detect_openkylin(self) -> bool:
        """检测是否为 openKylin 系统"""
        if self.system != "Linux":
            return False
        try:
            # 检查 /etc/os-release 文件
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    content = f.read().lower()
                    return "openkylin" in content or "kylin" in content
        except:
            pass
        return False

    def _normalize_path(self, filepath: str) -> Path:
        """
        规范化文件路径：
        1. 如果是绝对路径，直接使用
        2. 如果是 ~/xxx，展开为用户目录
        3. 处理中英文目录名映射（桌面/Desktop、文档/Documents 等）
        4. 如果是其他相对路径，使用用户主目录
        """
        if not filepath:
            return Path.home()

        # 展开用户目录符号 ~
        if filepath.startswith("~"):
            return Path(filepath).expanduser()

        # 如果是绝对路径，直接使用(不要修改)
        path = Path(filepath)
        if path.is_absolute():
            return path

        # openKylin 中文系统的目录映射
        # 用户界面显示的是中文，但实际文件夹可能是英文或中文
        # 需要检测实际存在的目录名
        home = Path.home()

        # 中英文目录对应关系
        dir_mappings = [
            # (用户可能输入的名称, 实际目录名候选列表)
            (["桌面", "Desktop", "desktop"], ["桌面", "Desktop"]),
            (["文档", "Documents", "documents"], ["文档", "Documents"]),
            (["下载", "Downloads", "downloads"], ["下载", "Downloads"]),
            (["图片", "Pictures", "pictures"], ["图片", "Pictures"]),
            (["音乐", "Music", "music"], ["音乐", "Music"]),
            (["视频", "Videos", "videos"], ["视频", "Videos"]),
            (["公共", "Public", "public"], ["公共", "Public"]),
            (["模板", "Templates", "templates"], ["模板", "Templates"]),
        ]

        # 相对路径处理：不要移除开头的 /
        clean_path = filepath

        # 检查是否匹配某个特殊目录
        for input_names, actual_names in dir_mappings:
            for input_name in input_names:
                # 完全匹配目录名
                if clean_path == input_name:
                    # 尝试找到实际存在的目录
                    for actual_name in actual_names:
                        actual_dir = home / actual_name
                        if actual_dir.exists():
                            return actual_dir
                    # 如果都不存在，使用第一个（中文名）
                    return home / actual_names[0]

                # 以 "目录名/" 开头
                if clean_path.startswith(input_name + "/"):
                    # 提取目录名后面的部分
                    rest_path = clean_path[len(input_name) + 1:]
                    # 尝试找到实际存在的目录
                    for actual_name in actual_names:
                        actual_dir = home / actual_name
                        if actual_dir.exists():
                            return actual_dir / rest_path
                    # 如果都不存在，使用第一个（中文名）
                    return home / actual_names[0] / rest_path

        # 其他相对路径，使用用户主目录
        return home / clean_path

    def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行指定的操作

        Args:
            action: 操作类型（如 'open_app', 'create_file' 等）
            params: 操作参数

        Returns:
            包含执行结果的字典 {"success": bool, "message": str, "data": Any}
        """
        params = params or {}

        if action not in self.actions:
            return {
                "success": False,
                "message": f"不支持的操作: {action}",
                "data": {"available_actions": list(self.actions.keys())}
            }

        try:
            result = self.actions[action](params)
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"执行失败: {str(e)}",
                "data": None
            }

    # ========== 应用程序操作 ==========

    def _open_app(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """打开应用程序（openKylin/Linux）"""
        app_name = params.get("name", "")
        if not app_name:
            return {"success": False, "message": "缺少应用程序名称", "data": None}

        try:
            # openKylin / Linux 常见应用
            # 格式：显示名: [(命令1, 参数1), (命令2, 参数2), ...] - 按优先级尝试
            app_map = {
                # 浏览器
                "firefox": [("firefox", ["--new-window"])],
                "火狐": [("firefox", ["--new-window"])],
                "浏览器": [("firefox", ["--new-window"]), ("google-chrome", ["--new-window"])],
                "chrome": [("google-chrome", ["--new-window"]), ("chromium-browser", ["--new-window"])],
                "chromium": [("chromium-browser", ["--new-window"])],
                "谷歌浏览器": [("google-chrome", ["--new-window"])],

                # 文件管理
                "文件管理器": [("nautilus", ["--new-window"]), ("peony", []), ("dolphin", ["--new-window"])],
                "文件": [("nautilus", ["--new-window"]), ("peony", [])],
                "peony": [("peony", [])],
                "dolphin": [("dolphin", ["--new-window"])],

                # 终端 - 尝试多个终端模拟器
                "终端": [
                    ("mate-terminal", ["--working-directory=" + str(Path.home())]),
                    ("gnome-terminal", ["--working-directory=" + str(Path.home())]),
                    ("xfce4-terminal", ["--working-directory=" + str(Path.home())]),
                    ("konsole", ["--workdir", str(Path.home())]),
                    ("xterm", []),
                    ("uxterm", []),
                ],
                "konsole": [("konsole", ["--workdir", str(Path.home())])],
                "terminal": [
                    ("mate-terminal", ["--working-directory=" + str(Path.home())]),
                    ("gnome-terminal", ["--working-directory=" + str(Path.home())]),
                    ("xterm", []),
                ],

                # 文本编辑器
                "文本编辑器": [("gedit", []), ("kate", []), ("pluma", [])],
                "gedit": [("gedit", [])],
                "kate": [("kate", [])],
                "vim": [("vim", [])],
                "nano": [("nano", [])],
                "记事本": [("gedit", []), ("pluma", [])],

                # 办公软件
                "wps": [("wps", [])],
                "libreoffice": [("libreoffice", [])],
                "writer": [("libreoffice", ["--writer"])],
                "calc": [("libreoffice", ["--calc"])],
                "文字处理": [("libreoffice", ["--writer"])],
                "表格": [("libreoffice", ["--calc"])],

                # 系统工具
                "计算器": [("gnome-calculator", []), ("kcalc", []), ("mate-calc", [])],
                "calculator": [("gnome-calculator", []), ("kcalc", [])],
                "系统监视器": [("gnome-system-monitor", []), ("mate-system-monitor", [])],
                "任务管理器": [("gnome-system-monitor", []), ("mate-system-monitor", [])],
                "设置": [("gnome-control-center", []), ("mate-control-center", [])],
                "控制中心": [("gnome-control-center", []), ("ukui-control-center", [])],

                # 多媒体
                "音乐": [("rhythmbox", [])],
                "视频": [("totem", []), ("vlc", [])],
                "vlc": [("vlc", [])],
                "截图": [("gnome-screenshot", []), ("mate-screenshot", [])],

                # openKylin 特有应用
                "应用商店": [("kylin-software-center", [])],
                "软件中心": [("kylin-software-center", [])],
                "ukui控制面板": [("ukui-control-center", [])],
            }

            # 获取命令列表
            cmd_list = app_map.get(app_name.lower(), [(app_name, [])])

            # 尝试每个命令，直到成功
            last_error = None
            for cmd, args in cmd_list:
                try:
                    # 检查命令是否存在
                    check_result = subprocess.run(
                        ["which", cmd],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )

                    if check_result.returncode == 0:
                        # 命令存在，启动应用
                        full_cmd = [cmd] + args
                        subprocess.Popen(
                            full_cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )

                        return {
                            "success": True,
                            "message": f"已打开应用: {app_name} (使用 {cmd})",
                            "data": {"app": app_name, "command": cmd, "system": "openKylin/Linux"}
                        }
                except Exception as e:
                    last_error = str(e)
                    continue

            # 所有命令都失败
            return {
                "success": False,
                "message": f"无法打开应用 {app_name}：命令不存在或未安装",
                "data": {"tried_commands": [c[0] for c in cmd_list], "last_error": last_error}
            }
        except Exception as e:
            return {"success": False, "message": f"打开应用失败: {str(e)}", "data": None}

    # ========== 文件操作 ==========

    def _create_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建文件"""
        filepath = params.get("path", "")
        content = params.get("content", "")

        if not filepath:
            return {"success": False, "message": "缺少文件路径", "data": None}

        try:
            # 规范化路径
            path = self._normalize_path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return {
                "success": True,
                "message": f"已创建文件: {path}",
                "data": {"path": str(path.absolute())}
            }
        except Exception as e:
            return {"success": False, "message": f"创建文件失败: {str(e)}", "data": None}

    def _delete_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除文件"""
        filepath = params.get("path", "")

        if not filepath:
            return {"success": False, "message": "缺少文件路径", "data": None}

        try:
            # 规范化路径
            path = self._normalize_path(filepath)
            if path.is_file():
                path.unlink()
                return {"success": True, "message": f"已删除文件: {path}", "data": None}
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)
                return {"success": True, "message": f"已删除目录: {path}", "data": None}
            else:
                return {"success": False, "message": "文件或目录不存在", "data": None}
        except Exception as e:
            return {"success": False, "message": f"删除失败: {str(e)}", "data": None}

    def _move_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """移动文件"""
        source = params.get("source", "")
        destination = params.get("destination", "")

        if not source or not destination:
            return {"success": False, "message": "缺少源路径或目标路径", "data": None}

        try:
            import shutil
            # 规范化路径
            src_path = self._normalize_path(source)
            dst_path = self._normalize_path(destination)
            shutil.move(str(src_path), str(dst_path))
            return {
                "success": True,
                "message": f"已移动: {src_path} -> {dst_path}",
                "data": None
            }
        except Exception as e:
            return {"success": False, "message": f"移动失败: {str(e)}", "data": None}

    def _copy_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """复制文件"""
        source = params.get("source", "")
        destination = params.get("destination", "")

        if not source or not destination:
            return {"success": False, "message": "缺少源路径或目标路径", "data": None}

        try:
            import shutil
            # 规范化路径
            src_path = self._normalize_path(source)
            dst_path = self._normalize_path(destination)

            if src_path.is_dir():
                shutil.copytree(str(src_path), str(dst_path))
            else:
                shutil.copy2(str(src_path), str(dst_path))
            return {
                "success": True,
                "message": f"已复制: {src_path} -> {dst_path}",
                "data": None
            }
        except Exception as e:
            return {"success": False, "message": f"复制失败: {str(e)}", "data": None}

    def _read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """读取文件内容"""
        filepath = params.get("path", "")
        max_size = params.get("max_size", 1024 * 1024)  # 默认最大 1MB

        if not filepath:
            return {"success": False, "message": "缺少文件路径", "data": None}

        try:
            # 规范化路径
            path = self._normalize_path(filepath)
            if not path.is_file():
                return {"success": False, "message": "文件不存在", "data": None}

            if path.stat().st_size > max_size:
                return {"success": False, "message": f"文件过大（超过 {max_size} 字节）", "data": None}

            content = path.read_text(encoding="utf-8")
            return {
                "success": True,
                "message": f"已读取文件: {path}",
                "data": {"content": content}
            }
        except Exception as e:
            return {"success": False, "message": f"读取失败: {str(e)}", "data": None}

    def _write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """写入文件内容"""
        filepath = params.get("path", "")
        content = params.get("content", "")
        mode = params.get("mode", "w")  # 'w' 覆盖, 'a' 追加

        if not filepath:
            return {"success": False, "message": "缺少文件路径", "data": None}

        try:
            # 规范化路径
            path = self._normalize_path(filepath)
            if mode == "a":
                with open(path, "a", encoding="utf-8") as f:
                    f.write(content)
            else:
                path.write_text(content, encoding="utf-8")

            return {
                "success": True,
                "message": f"已写入文件: {path}",
                "data": None
            }
        except Exception as e:
            return {"success": False, "message": f"写入失败: {str(e)}", "data": None}

    # ========== 浏览器操作 ==========
    def _open_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """打开网页"""
        url = params.get("url", "")

        if not url:
            return {"success": False, "message": "缺少 URL", "data": None}

        try:
            webbrowser.open(url)
            return {
                "success": True,
                "message": f"已打开网页: {url}",
                "data": None
            }
        except Exception as e:
            return {"success": False, "message": f"打开网页失败: {str(e)}", "data": None}

    def _search_web(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """网页搜索"""
        query = params.get("query", "")
        engine = params.get("engine", "baidu")  # baidu, google, bing

        if not query:
            return {"success": False, "message": "缺少搜索关键词", "data": None}

        try:
            engines = {
                "baidu": f"https://www.baidu.com/s?wd={query}",
                "google": f"https://www.google.com/search?q={query}",
                "bing": f"https://www.bing.com/search?q={query}",
            }
            url = engines.get(engine, engines["baidu"])
            webbrowser.open(url)
            return {
                "success": True,
                "message": f"已搜索: {query}（使用 {engine}）",
                "data": {"url": url}
            }
        except Exception as e:
            return {"success": False, "message": f"搜索失败: {str(e)}", "data": None}

    # ========== 系统操作 ==========

    def _get_system_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            info = {
                "system": platform.system(),
                "platform": platform.platform(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "hostname": platform.node(),
            }
            return {
                "success": True,
                "message": "系统信息",
                "data": info
            }
        except Exception as e:
            return {"success": False, "message": f"获取系统信息失败: {str(e)}", "data": None}

    def _get_disk_usage(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取磁盘使用情况"""
        path = params.get("path", "/")

        try:
            import shutil
            usage = shutil.disk_usage(path)
            return {
                "success": True,
                "message": f"磁盘使用情况: {path}",
                "data": {
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": round(usage.used / usage.total * 100, 2)
                }
            }
        except Exception as e:
            return {"success": False, "message": f"获取磁盘信息失败: {str(e)}", "data": None}

    def _get_current_time(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取当前时间"""
        try:
            from datetime import datetime
            now = datetime.now()
            return {
                "success": True,
                "message": "当前时间",
                "data": {
                    "timestamp": now.timestamp(),
                    "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "date": now.strftime("%Y-%m-%d"),
                    "time": now.strftime("%H:%M:%S")
                }
            }
        except Exception as e:
            return {"success": False, "message": f"获取时间失败: {str(e)}", "data": None}