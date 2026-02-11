"""
DARIA Actions v0.7.4
System actions and tool execution
"""

import subprocess
import platform
import os
import re
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger("daria")


class ActionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class ActionResult:
    status: ActionStatus
    data: Any = None
    message: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "status": self.status.value,
            "data": self.data,
            "message": self.message,
            "error": self.error
        }


class SystemDetector:
    """Detect system information"""
    
    @staticmethod
    def get_os() -> str:
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        return system
    
    @staticmethod
    def get_desktop_path() -> Path:
        return Path.home() / "Desktop"
    
    @staticmethod
    def get_documents_path() -> Path:
        return Path.home() / "Documents"


class BrowserAction:
    """Browser control actions"""
    
    SEARCH_ENGINES = {
        "google": "https://www.google.com/search?q=",
        "yandex": "https://yandex.ru/search/?text=",
        "youtube": "https://www.youtube.com/results?search_query=",
        "duckduckgo": "https://duckduckgo.com/?q="
    }
    
    def __init__(self):
        self.system = SystemDetector.get_os()
    
    def search(self, query: str, engine: str = "google") -> ActionResult:
        """Search in browser"""
        base_url = self.SEARCH_ENGINES.get(engine, self.SEARCH_ENGINES["google"])
        url = base_url + query.replace(" ", "+")
        return self.open_url(url)
    
    def open_url(self, url: str) -> ActionResult:
        """Open URL in default browser"""
        try:
            if self.system == "windows":
                os.startfile(url)
            elif self.system == "macos":
                subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:  # Linux
                subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            return ActionResult(
                status=ActionStatus.SUCCESS,
                data={"url": url},
                message=f"Открыла: {url[:50]}..."
            )
        except Exception as e:
            logger.error(f"Browser error: {e}")
            return ActionResult(
                status=ActionStatus.FAILED,
                error=str(e)
            )


class NotificationAction:
    """System notification actions"""
    
    def __init__(self):
        self.system = SystemDetector.get_os()
    
    def show(self, title: str, message: str) -> ActionResult:
        """Show system notification"""
        try:
            if self.system == "linux":
                subprocess.run(
                    ["notify-send", title, message],
                    capture_output=True,
                    timeout=5
                )
            elif self.system == "macos":
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    timeout=5
                )
            elif self.system == "windows":
                try:
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast(title, message, duration=5)
                except ImportError:
                    pass
            
            return ActionResult(
                status=ActionStatus.SUCCESS,
                message=f"Показала уведомление: {title}"
            )
        except Exception as e:
            logger.error(f"Notification error: {e}")
            return ActionResult(
                status=ActionStatus.FAILED,
                error=str(e)
            )


class FileAction:
    """File system actions"""
    
    def __init__(self):
        self.desktop = SystemDetector.get_desktop_path()
        self.documents = SystemDetector.get_documents_path()
    
    def create_note(self, title: str, content: str, location: str = "desktop") -> ActionResult:
        """Create a note file"""
        try:
            base_path = self.desktop if location == "desktop" else self.documents
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = re.sub(r'[^\w\s\-]', '', title)[:30]
            filename = f"Daria_{safe_title}_{timestamp}.txt"
            filepath = base_path / filename
            
            note_content = f"""╔══════════════════════════════════════════╗
║  💕 Заметка от Дарьи                     ║
╚══════════════════════════════════════════╝

📝 {title}

{content}

───────────────────────────────────────────
Создано: {datetime.now().strftime("%d.%m.%Y %H:%M")}
"""
            filepath.write_text(note_content, encoding='utf-8')
            
            return ActionResult(
                status=ActionStatus.SUCCESS,
                data={"path": str(filepath), "filename": filename},
                message=f"Создала файл: {filename}"
            )
        except Exception as e:
            logger.error(f"File creation error: {e}")
            return ActionResult(
                status=ActionStatus.FAILED,
                error=str(e)
            )


class ActionExecutor:
    """Execute tools/actions - Main executor class"""
    
    def __init__(self):
        self.browser = BrowserAction()
        self.notification = NotificationAction()
        self.file = FileAction()
    
    def execute(self, tool_name: str, params: Dict[str, Any] = None) -> ActionResult:
        """Execute a tool by name"""
        params = params or {}
        
        handlers = {
            "datetime": self._handle_datetime,
            "calculator": self._handle_calculator,
            "open_browser": self._handle_browser,
            "search": self._handle_browser,
            "system_notify": self._handle_notify,
            "notify": self._handle_notify,
            "file_create": self._handle_file,
            "create_note": self._handle_file,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return ActionResult(
                status=ActionStatus.FAILED,
                error=f"Unknown tool: {tool_name}"
            )
        
        try:
            return handler(params)
        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {e}")
            return ActionResult(
                status=ActionStatus.FAILED,
                error=str(e)
            )
    
    def _handle_datetime(self, params: Dict) -> ActionResult:
        now = datetime.now()
        weekdays = ["понедельник", "вторник", "среда", "четверг", 
                    "пятница", "суббота", "воскресенье"]
        return ActionResult(
            status=ActionStatus.SUCCESS,
            data={
                "date": now.strftime("%d.%m.%Y"),
                "time": now.strftime("%H:%M:%S"),
                "datetime": now.isoformat(),
                "weekday": weekdays[now.weekday()]
            },
            message=now.strftime("Сейчас %d.%m.%Y, %H:%M")
        )
    
    def _handle_calculator(self, params: Dict) -> ActionResult:
        expr = params.get("expression") or params.get("query", "")
        
        math_match = re.search(r'[\d\+\-\*\/\.\(\)\s]+', expr)
        if not math_match:
            return ActionResult(
                status=ActionStatus.FAILED,
                error="No valid expression found"
            )
        
        clean_expr = math_match.group().strip()
        
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in clean_expr):
            return ActionResult(
                status=ActionStatus.FAILED,
                error="Invalid characters in expression"
            )
        
        try:
            result = eval(clean_expr)
            return ActionResult(
                status=ActionStatus.SUCCESS,
                data={"expression": clean_expr, "result": result},
                message=f"{clean_expr} = {result}"
            )
        except Exception as e:
            return ActionResult(
                status=ActionStatus.FAILED,
                error=f"Calculation error: {e}"
            )
    
    def _handle_browser(self, params: Dict) -> ActionResult:
        query = params.get("query") or params.get("url", "")
        engine = params.get("engine", "google")
        
        if query.startswith("http://") or query.startswith("https://"):
            return self.browser.open_url(query)
        
        return self.browser.search(query, engine)
    
    def _handle_notify(self, params: Dict) -> ActionResult:
        title = params.get("title", "Дарья")
        message = params.get("message") or params.get("text", "")
        return self.notification.show(title, message)
    
    def _handle_file(self, params: Dict) -> ActionResult:
        title = params.get("title", "Заметка")
        content = params.get("content") or params.get("text", "")
        location = params.get("location", "desktop")
        return self.file.create_note(title, content, location)


# Singleton accessor
_executor: Optional[ActionExecutor] = None


def get_executor() -> ActionExecutor:
    global _executor
    if _executor is None:
        _executor = ActionExecutor()
    return _executor
