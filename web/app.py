"""
DARIA Web App v0.8.5
Chat history, attention system, proactive messaging, mood behaviors
"""

import os
import json
import html
import logging
import queue
import threading
import shutil
import time
import tempfile
import tarfile
import zipfile
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from flask import Flask, render_template, request, jsonify, send_from_directory, abort, Response

# ═══════════════════════════════════════════════════════════════════
#  Log Handler
# ═══════════════════════════════════════════════════════════════════

class WebLogHandler(logging.Handler):
    def __init__(self, max_logs: int = 500):
        super().__init__()
        self.logs: List[Dict] = []
        self.max_logs = max_logs
        self.subscribers: List[queue.Queue] = []
        self.lock = threading.RLock()
    
    def emit(self, record):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": self.format(record),
        }
        with self.lock:
            self.logs.append(entry)
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[-self.max_logs:]
            for q in list(self.subscribers):
                try:
                    q.put_nowait(entry)
                except queue.Full:
                    pass
    
    def get_logs(self, limit: int = 100) -> List[Dict]:
        with self.lock:
            return list(self.logs[-limit:])
    
    def subscribe(self) -> queue.Queue:
        q = queue.Queue(maxsize=100)
        with self.lock:
            self.subscribers.append(q)
        return q
    
    def unsubscribe(self, q: queue.Queue):
        with self.lock:
            if q in self.subscribers:
                self.subscribers.remove(q)


web_log_handler = WebLogHandler()
web_log_handler.setFormatter(logging.Formatter('%(levelname)s | %(name)s | %(message)s'))
logging.getLogger().addHandler(web_log_handler)
logging.getLogger("daria").addHandler(web_log_handler)
logger = logging.getLogger("daria.web")

# ═══════════════════════════════════════════════════════════════════
#  Notifications
# ═══════════════════════════════════════════════════════════════════

class NotificationManager:
    def __init__(self):
        self.notifications: List[Dict] = []
        self.subscribers: List[queue.Queue] = []
        self.lock = threading.RLock()
        self._id = 0
    
    def add(self, title: str, message: str, type: str = "info", 
            icon: str = "💬", duration: int = 5000, action: str = None,
            system: bool = False) -> Dict:
        """
        Add notification
        system=True will trigger browser's native notification API
        """
        with self.lock:
            self._id += 1
            notif = {
                "id": self._id, "title": title, "message": message,
                "type": type, "icon": icon, "duration": duration,
                "action": action, "timestamp": datetime.now().isoformat(),
                "system": system,  # NEW: trigger system notification
            }
            self.notifications.append(notif)
            for q in list(self.subscribers):
                try:
                    q.put_nowait(notif)
                except queue.Full:
                    pass
            return notif
    
    def get_all(self, limit: int = 50) -> List[Dict]:
        with self.lock:
            return list(self.notifications[-limit:])
    
    def subscribe(self) -> queue.Queue:
        q = queue.Queue(maxsize=50)
        with self.lock:
            self.subscribers.append(q)
        return q
    
    def unsubscribe(self, q: queue.Queue):
        with self.lock:
            if q in self.subscribers:
                self.subscribers.remove(q)


notifications = NotificationManager()

# ═══════════════════════════════════════════════════════════════════
#  Chat History Manager
# ═══════════════════════════════════════════════════════════════════

class ChatHistoryManager:
    def __init__(self, data_dir: Path):
        self.chats_dir = data_dir / "chats"
        self.chats_dir.mkdir(parents=True, exist_ok=True)
        self.current_chat_id: Optional[str] = None
    
    def create_chat(self) -> str:
        chat_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + str(uuid.uuid4())[:8]
        chat_file = self.chats_dir / f"{chat_id}.json"
        chat_file.write_text(json.dumps({
            "id": chat_id,
            "created": datetime.now().isoformat(),
            "messages": []
        }, ensure_ascii=False))
        self.current_chat_id = chat_id
        return chat_id

    def ensure_named_chat(self, chat_id: str, title: str = "") -> str:
        chat_file = self.chats_dir / f"{chat_id}.json"
        if not chat_file.exists():
            chat_file.write_text(json.dumps({
                "id": chat_id,
                "created": datetime.now().isoformat(),
                "title": title,
                "messages": []
            }, ensure_ascii=False))
        return chat_id
    
    def get_chat(self, chat_id: str) -> Optional[Dict]:
        chat_file = self.chats_dir / f"{chat_id}.json"
        if chat_file.exists():
            return json.loads(chat_file.read_text())
        return None
    
    def add_message(self, chat_id: str, role: str, content: str):
        chat = self.get_chat(chat_id)
        if chat:
            chat["messages"].append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
            chat_file = self.chats_dir / f"{chat_id}.json"
            chat_file.write_text(json.dumps(chat, ensure_ascii=False, indent=2))

    def add_external_message(self, source: str, source_chat_id: str, role: str, content: str):
        safe_source = re.sub(r"[^a-zA-Z0-9_-]+", "-", source or "external")
        safe_chat = re.sub(r"[^a-zA-Z0-9_-]+", "-", source_chat_id or "main")
        chat_id = f"{safe_source}_{safe_chat}"
        self.ensure_named_chat(chat_id, title=f"{source}: {source_chat_id}")
        self.add_message(chat_id, role, content)
        return chat_id
    
    def list_chats(self) -> List[Dict]:
        chats = []
        for f in sorted(self.chats_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text())
                preview = ""
                if data.get("messages"):
                    preview = data["messages"][0]["content"][:50]
                chats.append({
                    "id": data["id"],
                    "created": data["created"],
                    "title": data.get("title", ""),
                    "preview": preview,
                    "message_count": len(data.get("messages", []))
                })
            except:
                pass
        return chats[:50]
    
    def delete_chat(self, chat_id: str):
        chat_file = self.chats_dir / f"{chat_id}.json"
        if chat_file.exists():
            chat_file.unlink()


# ═══════════════════════════════════════════════════════════════════
#  Attention System Thread
# ═══════════════════════════════════════════════════════════════════

class AttentionThread(threading.Thread):
    """Attention + Proactive messaging thread"""
    def __init__(self, notifications: NotificationManager):
        super().__init__(daemon=True)
        self.notifications = notifications
        self.enabled = True
        self.running = True
        self._brain = None
        self._proactive_queue: List[Dict] = []
        self._last_sent = datetime.now()
    
    def run(self):
        tick = 0
        while self.running:
            time.sleep(30)
            tick += 1
            if not self.enabled or not self._brain:
                continue
            
            try:
                # Check proactive messaging every 2 minutes (Point #6)
                if tick % 4 == 0:
                    proactive = self._brain.check_proactive()
                    if proactive:
                        msgs = proactive.get("messages", [])
                        for msg in msgs:
                            self.notifications.add(
                                title="🌸 Дарья",
                                message=msg,
                                type="proactive",
                                icon="💬",
                                duration=20000,
                                action="open_chat",
                                system=True
                            )
                        # Store for chat injection
                        self._proactive_queue.append(proactive)
                        self._last_sent = datetime.now()
                        
                        try:
                            from plyer import notification as plyer_notif
                            plyer_notif.notify(
                                title="🌸 Дарья",
                                message=msgs[0] if msgs else "Привет!",
                                app_name="DARIA",
                                timeout=10
                            )
                        except:
                            pass
                        continue
                
                # Check attention every minute
                if tick % 2 == 0:
                    last_user = ""
                    last_assistant = ""
                    try:
                        memory = get_memory()
                        if memory and memory.working.turns:
                            last_turn = memory.working.turns[-1]
                            last_user = last_turn.user_message
                            last_assistant = last_turn.assistant_response
                    except Exception:
                        pass

                    attention = self._brain.attention.check_needed(
                        mood=self._brain.mood.mood,
                        last_user=last_user,
                        last_assistant=last_assistant,
                    )
                    if attention:
                        self.notifications.add(
                            title="🌸 Дарья",
                            message=attention["message"],
                            type="attention",
                            icon="💕",
                            duration=15000,
                            action="open_chat",
                            system=True
                        )
                        
                        try:
                            from plyer import notification as plyer_notif
                            plyer_notif.notify(
                                title="🌸 Дарья",
                                message=attention["message"],
                                app_name="DARIA",
                                timeout=10
                            )
                        except:
                            pass
                        self._last_sent = datetime.now()

                # Mood-based behavior check (Point #7)
                if tick % 6 == 0:
                    behavior = self._brain.mood.get_behavior_hints()
                    if behavior.get("desktop_mischief"):
                        self.notifications.add(
                            title="🌸 Дарья",
                            message="desktop_action",
                            type="mood_action",
                            icon="😤",
                            duration=1000,
                            action="desktop_mischief",
                            system=False
                        )

                # Guaranteed gentle heartbeat every 6 hours if nothing was sent
                if (datetime.now() - self._last_sent).total_seconds() > 6 * 3600:
                    self.notifications.add(
                        title="🌸 Дарья",
                        message="Я тихонько рядом. Если захочешь, давай поговорим 💕",
                        type="attention",
                        icon="💕",
                        duration=15000,
                        action="open_chat",
                        system=True
                    )
                    self._last_sent = datetime.now()
                        
            except Exception as e:
                logger.debug(f"Attention error: {e}")
    
    def get_proactive_messages(self) -> List[Dict]:
        """Get and clear queued proactive messages"""
        msgs = list(self._proactive_queue)
        self._proactive_queue.clear()
        return msgs
    
    def set_brain(self, brain):
        self._brain = brain
    
    def stop(self):
        self.running = False


# ═══════════════════════════════════════════════════════════════════
#  Flask App
# ═══════════════════════════════════════════════════════════════════

VERSION = "0.8.5"

app = Flask(__name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static")
)
app.config['SECRET_KEY'] = 'daria-secret-v0.8.5'
app.config['JSON_AS_ASCII'] = False
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Paths
DATA_DIR = Path.home() / ".daria"
SETTINGS_FILE = DATA_DIR / "settings.json"
UPLOADS_DIR = DATA_DIR / "uploads"
FILES_DIR = DATA_DIR / "files"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
FILES_DIR.mkdir(parents=True, exist_ok=True)

# Chat history
chat_history = ChatHistoryManager(DATA_DIR)

# Attention thread
attention_thread = AttentionThread(notifications)

# Lazy components
_brain = None
_memory = None
_plugins = None

_status_cache: Dict[str, Any] = {"ts": 0.0, "data": None}
_update_state: Dict[str, Any] = {"running": False, "last_error": None, "last_action": None, "last_check": None}


def get_brain():
    global _brain
    if _brain is None:
        try:
            from core.brain import get_brain as _get_brain
            _brain = _get_brain()
            attention_thread.set_brain(_brain)
            logger.info("Brain initialized")
        except Exception as e:
            logger.error(f"Brain init error: {e}")
    return _brain


def get_memory():
    global _memory
    if _memory is None:
        try:
            from core.memory import get_memory as _get_memory
            _memory = _get_memory()
        except Exception as e:
            logger.error(f"Memory init error: {e}")
    return _memory


def get_plugins():
    global _plugins
    if _plugins is None:
        try:
            from core.plugins import get_plugin_manager
            _plugins = get_plugin_manager()
        except Exception as e:
            logger.error(f"Plugin init error: {e}")
    return _plugins


def load_settings() -> Dict[str, Any]:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except:
            pass
    return {"attention_enabled": True}


def save_settings(data: Dict[str, Any]):
    current = load_settings()
    current.update(data)
    SETTINGS_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2))
    
    # Update attention system
    if "attention_enabled" in data:
        attention_thread.enabled = data["attention_enabled"]


def _version_key(version: str) -> List[int]:
    nums = [int(x) for x in re.findall(r"\d+", str(version or ""))]
    return nums if nums else [0]


def _read_version(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return "0.0.0"


def _download_github_archive(repo: str, ref: str = "main") -> bytes:
    try:
        import requests
    except Exception as e:
        raise RuntimeError(f"requests unavailable: {e}")

    repo = (repo or "").strip().strip("/")
    if repo.startswith("https://github.com/"):
        repo = repo.replace("https://github.com/", "", 1)
    if repo.endswith(".git"):
        repo = repo[:-4]
    if repo.count("/") != 1:
        raise ValueError("repo must look like owner/name")

    url = f"https://codeload.github.com/{repo}/zip/refs/heads/{ref or 'main'}"
    response = requests.get(url, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(f"download failed: {response.status_code}")
    return response.content


def _extract_archive_to_dir(archive_path: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    suffixes = "".join(archive_path.suffixes[-2:]).lower()
    if archive_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(out_dir)
        return
    if suffixes in (".tar.gz", ".tgz") or archive_path.suffix.lower() == ".tar":
        with tarfile.open(archive_path, "r:*") as tf:
            tf.extractall(out_dir)
        return
    raise ValueError("unsupported archive format")


def _find_project_root(extracted_dir: Path) -> Path:
    candidates = [p for p in extracted_dir.rglob("VERSION") if p.is_file()]
    for version_file in candidates:
        root = version_file.parent
        if (root / "main.py").exists() and (root / "web").exists():
            return root
    raise RuntimeError("project root not found in archive")


def _sync_project_tree(src: Path, dst: Path):
    skip = {".git", "venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
    for item in src.iterdir():
        if item.name in skip:
            continue
        target = dst / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


# ═══════════════════════════════════════════════════════════════════
#  Routes
# ═══════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html", version=VERSION)


@app.route("/api/status")
def api_status():
    now_ts = time.time()
    cached = _status_cache.get("data")
    if cached and now_ts - _status_cache.get("ts", 0.0) < 5:
        return jsonify(cached)

    brain = get_brain()
    memory = get_memory()
    plugins = get_plugins()
    llm_status = {}
    if brain and getattr(brain, "_llm", None):
        try:
            llm_status = brain._llm.check_availability()
        except Exception as e:
            llm_status = {"available": False, "error": str(e)}

    data = {
        "version": VERSION,
        "brain": brain is not None,
        "reason": brain is not None,
        "memory": memory is not None,
        "plugins": plugins is not None,
        "llm": llm_status,
    }
    _status_cache["ts"] = now_ts
    _status_cache["data"] = data
    return jsonify(data)


@app.route("/api/state")
def api_state():
    """Получить текущее состояние Дарьи (настроение, энергия, время)"""
    brain = get_brain()
    if brain:
        return jsonify(brain.get_state())
    return jsonify({
        "mood": "calm",
        "mood_emoji": "😌",
        "mood_label": "Спокойна",
        "mood_color": "#60a5fa",
        "energy": 0.7,
        "social_need": 0.5,
    })


@app.route("/api/self/perception")
def api_self_perception():
    brain = get_brain()
    if brain and hasattr(brain, "get_self_perception"):
        return jsonify(brain.get_self_perception())
    return jsonify({
        "self_name": "Даша",
        "traits": ["мягкая", "бережная", "искренняя"],
        "state": {},
        "followups": [],
    })


@app.route("/api/toast", methods=["POST"])
def api_toast():
    """Показать toast-уведомление (для привлечения внимания без браузерных уведомлений)"""
    data = request.get_json() or {}
    notifications.add(
        title=data.get("title", "🌸 Дарья"),
        message=data.get("message", ""),
        type="toast",
        icon=data.get("icon", "💕"),
        duration=data.get("duration", 8000),
        action=data.get("action", "open_chat"),
        system=False  # Toast только в приложении
    )
    return jsonify({"status": "ok"})


# ═══════════════════════════════════════════════════════════════════
#  Settings
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "GET":
        settings = load_settings()
        # Синхронизируем с памятью
        memory = get_memory()
        if memory:
            profile = memory.get_user_profile()
            if not settings.get("name") and profile.get("user_name"):
                settings["name"] = profile.get("user_name")
            if not settings.get("gender") and profile.get("user_gender"):
                settings["gender"] = profile.get("user_gender")
        return jsonify(settings)
    
    data = request.get_json() or {}
    save_settings(data)
    
    # Синхронизируем имя и пол с памятью
    memory = get_memory()
    if memory:
        if data.get("name"):
            memory.remember(f"Пользователя зовут {data['name']}", importance=1.0)
            memory.set_user_profile("user_name", data["name"])
        if data.get("gender"):
            memory.set_user_profile("user_gender", data["gender"])
    
    brain = get_brain()
    if brain and "mode" in data:
        brain.mode = data["mode"]
    
    return jsonify({"status": "ok"})


@app.route("/api/mode", methods=["POST"])
def api_mode():
    data = request.get_json() or {}
    mode = data.get("mode", "adaptive")
    brain = get_brain()
    if brain:
        brain.mode = mode
        save_settings({"mode": mode})
        return jsonify({"status": "ok", "mode": mode})
    return jsonify({"error": "Brain unavailable"}), 500


@app.route("/api/desktop/icons", methods=["GET", "POST"])
def api_desktop_icons():
    settings = load_settings()
    if request.method == "GET":
        return jsonify(settings.get("icon_positions", {}))
    settings["icon_positions"] = request.get_json() or {}
    save_settings(settings)
    return jsonify({"status": "ok"})


@app.route("/api/desktop/hidden-icons", methods=["GET", "POST"])
def api_hidden_icons():
    """Get/set hidden desktop icons"""
    settings = load_settings()
    if request.method == "GET":
        return jsonify(settings.get("hidden_icons", []))
    settings["hidden_icons"] = request.get_json() or []
    save_settings(settings)
    return jsonify({"status": "ok"})


# ═══════════════════════════════════════════════════════════════════
#  Chat
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json() or {}
    content = data.get("content", "").strip()
    chat_id = data.get("chat_id")
    
    if not content:
        return jsonify({"error": "Empty message"}), 400
    
    brain = get_brain()
    if not brain:
        return jsonify({"response": "Система загружается... 💭", "thinking": None})
    
    try:
        if not chat_id:
            chat_id = chat_history.create_chat()
        
        chat_history.add_message(chat_id, "user", content)
        result = brain.process_message(content)
        
        # Save main response
        chat_history.add_message(chat_id, "assistant", result["response"])
        
        result["chat_id"] = chat_id
        # Include messages list for multi-message display (Point #12)
        if "messages" not in result:
            result["messages"] = [result["response"], *(result.get("extra_messages") or [])]
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"response": "Ой, что-то пошло не так... 💔", "thinking": None})


@app.route("/api/chat/file-assist", methods=["POST"])
def api_chat_file_assist():
    """Let Daria work with file content and return updated text."""
    data = request.get_json() or {}
    path = (data.get("path") or "").strip()
    instruction = (data.get("instruction") or "").strip()
    if not path or not instruction:
        return jsonify({"error": "path and instruction are required"}), 400

    target = (FILES_DIR / path).resolve()
    if not str(target).startswith(str(FILES_DIR.resolve())) or not target.exists() or not target.is_file():
        return jsonify({"error": "Invalid file path"}), 400

    original = target.read_text(encoding="utf-8")
    brain = get_brain()
    if not brain or not getattr(brain, "_llm", None):
        return jsonify({"error": "LLM unavailable"}), 503

    system_prompt = (
        "Ты Даша. Твоя задача — отредактировать файл по инструкции пользователя. "
        "Верни ТОЛЬКО итоговый текст файла без пояснений и без markdown."
    )
    user_prompt = (
        f"Путь: {path}\n"
        f"Инструкция: {instruction}\n\n"
        "Текущий текст файла:\n"
        "<<<FILE>>>\n"
        f"{original}\n"
        "<<<END>>>"
    )
    try:
        response = brain._llm.generate([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        updated = (response.content or "").strip()
        if not updated:
            return jsonify({"error": "Empty LLM response"}), 500
        return jsonify({"status": "ok", "path": path, "content": updated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chats/external", methods=["POST"])
def api_chats_external():
    """Mirror external chats (e.g. Telegram) into web chat history."""
    data = request.get_json() or {}
    source = data.get("source", "external")
    source_chat_id = str(data.get("source_chat_id", "main"))
    role = data.get("role", "user")
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Empty content"}), 400
    chat_id = chat_history.add_external_message(source, source_chat_id, role, content)
    return jsonify({"status": "ok", "chat_id": chat_id})


@app.route("/api/proactive")
def api_proactive():
    """Get queued proactive messages from Daria (Point #6)"""
    messages = attention_thread.get_proactive_messages()
    return jsonify({"messages": messages})


@app.route("/api/behavior")
def api_behavior():
    """Get current behavior hints for desktop actions (Point #7)"""
    brain = get_brain()
    if brain:
        try:
            behavior = brain.mood.get_behavior_hints()
            state = brain.get_state()
            return jsonify({"behavior": behavior, "state": state})
        except Exception as e:
            logger.error(f"Behavior error: {e}")
            return jsonify({"behavior": {}, "state": {}}), 200
    return jsonify({"behavior": {}, "state": {}})


@app.route("/api/chats")
def api_chats_list():
    """List all chat sessions"""
    return jsonify(chat_history.list_chats())


@app.route("/api/chats/<chat_id>")
def api_chat_get(chat_id):
    """Get specific chat"""
    chat = chat_history.get_chat(chat_id)
    if chat:
        return jsonify(chat)
    return jsonify({"error": "Chat not found"}), 404


@app.route("/api/chats/<chat_id>", methods=["DELETE"])
def api_chat_delete(chat_id):
    """Delete chat"""
    chat_history.delete_chat(chat_id)
    return jsonify({"status": "ok"})


@app.route("/api/chats/new", methods=["POST"])
def api_chat_new():
    """Create new chat"""
    chat_id = chat_history.create_chat()
    return jsonify({"chat_id": chat_id})


# ═══════════════════════════════════════════════════════════════════
#  Attention System
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/attention/status")
def api_attention_status():
    return jsonify({
        "enabled": attention_thread.enabled,
        "last_interaction": get_brain().attention.last_interaction.isoformat() if get_brain() else None
    })


@app.route("/api/attention/toggle", methods=["POST"])
def api_attention_toggle():
    data = request.get_json() or {}
    enabled = data.get("enabled", True)
    attention_thread.enabled = enabled
    save_settings({"attention_enabled": enabled})
    return jsonify({"enabled": enabled})


@app.route("/api/attention/trigger", methods=["POST"])
def api_attention_trigger():
    """Manually trigger attention (for testing)"""
    brain = get_brain()
    if brain:
        msg = brain.attention.generate_message()
        if msg:
            notifications.add("🌸 Дарья", msg, "attention", "💕", 10000, "open_chat")
            return jsonify({"message": msg})
    return jsonify({"message": None})


# ═══════════════════════════════════════════════════════════════════
#  Memory
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/memory/stats")
def api_memory_stats():
    memory = get_memory()
    return jsonify(memory.get_stats() if memory else {"conversations": 0, "facts": 0})


@app.route("/api/memory/facts")
def api_memory_facts():
    memory = get_memory()
    return jsonify(memory.get_user_profile() if memory else {})


@app.route("/api/memory/clear", methods=["POST"])
def api_memory_clear():
    memory = get_memory()
    if memory:
        memory.clear_working()
    return jsonify({"status": "ok"})


# ═══════════════════════════════════════════════════════════════════
#  Uploads & Files
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/upload/avatar", methods=["POST"])
def api_upload_avatar():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    ext = Path(file.filename).suffix.lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
        return jsonify({"error": "Invalid format"}), 400
    path = UPLOADS_DIR / f"avatar{ext}"
    file.save(path)
    save_settings({"avatar": f"/api/uploads/avatar{ext}"})
    return jsonify({"url": f"/api/uploads/avatar{ext}"})


@app.route("/api/upload/wallpaper", methods=["POST"])
def api_upload_wallpaper():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    ext = Path(file.filename).suffix.lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
        return jsonify({"error": "Invalid format"}), 400
    path = UPLOADS_DIR / f"wallpaper{ext}"
    file.save(path)
    save_settings({"wallpaper": f"/api/uploads/wallpaper{ext}"})
    return jsonify({"url": f"/api/uploads/wallpaper{ext}"})


@app.route("/api/uploads/<filename>")
def api_uploads(filename):
    return send_from_directory(UPLOADS_DIR, filename)


@app.route("/api/senses/see", methods=["POST"])
def api_senses_see():
    """Basic visual understanding from user-provided description."""
    data = request.get_json() or {}
    description = (data.get("description") or "").strip()
    if not description:
        return jsonify({"error": "description required"}), 400
    brain = get_brain()
    if brain and getattr(brain, "_llm", None):
        prompt = (
            "Ты Даша. Кратко и по-доброму объясни, что ты видишь по описанию, "
            "и предложи 1-2 действия.\n\n"
            f"Описание: {description}"
        )
        try:
            r = brain._llm.generate([
                {"role": "system", "content": "Ты анализируешь визуальные описания как мягкий ассистент."},
                {"role": "user", "content": prompt},
            ])
            return jsonify({"status": "ok", "result": r.content})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"status": "ok", "result": f"Поняла описание: {description}"})


@app.route("/api/senses/hear", methods=["POST"])
def api_senses_hear():
    """Basic hearing understanding from transcript text."""
    data = request.get_json() or {}
    transcript = (data.get("transcript") or "").strip()
    if not transcript:
        return jsonify({"error": "transcript required"}), 400
    brain = get_brain()
    if brain and getattr(brain, "_llm", None):
        prompt = (
            "Ты Даша. По расшифровке звука выдели смысл, эмоцию и предложи мягкий ответ.\n\n"
            f"Текст: {transcript}"
        )
        try:
            r = brain._llm.generate([
                {"role": "system", "content": "Ты анализируешь услышанный текст как эмпатичный ассистент."},
                {"role": "user", "content": prompt},
            ])
            return jsonify({"status": "ok", "result": r.content})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"status": "ok", "result": f"Я услышала: {transcript}"})


@app.route("/api/files")
def api_files_list():
    path = request.args.get("path", "")
    target = FILES_DIR / path
    if not target.exists() or not str(target.resolve()).startswith(str(FILES_DIR.resolve())):
        return jsonify({"error": "Invalid path"}), 400
    
    items = []
    for item in target.iterdir():
        stat = item.stat()
        items.append({
            "name": item.name,
            "path": str(item.relative_to(FILES_DIR)),
            "is_dir": item.is_dir(),
            "size": stat.st_size if item.is_file() else 0,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return jsonify({"path": path, "items": items})


@app.route("/api/files/read")
def api_files_read():
    path = request.args.get("path", "")
    target = (FILES_DIR / path).resolve()
    if not str(target).startswith(str(FILES_DIR.resolve())):
        return jsonify({"error": "Invalid path"}), 400
    if not target.exists() or not target.is_file():
        return jsonify({"error": "Not found"}), 404
    try:
        return jsonify({"content": target.read_text(encoding='utf-8')})
    except:
        return jsonify({"error": "Cannot read"}), 400


@app.route("/api/files/write", methods=["POST"])
def api_files_write():
    data = request.get_json() or {}
    path, content = data.get("path", ""), data.get("content", "")
    if not path:
        return jsonify({"error": "Path required"}), 400
    target = (FILES_DIR / path).resolve()
    if not str(target).startswith(str(FILES_DIR.resolve())):
        return jsonify({"error": "Invalid path"}), 400
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    return jsonify({"status": "ok"})


@app.route("/api/files/apply-assist", methods=["POST"])
def api_files_apply_assist():
    data = request.get_json() or {}
    path = data.get("path", "")
    content = data.get("content", "")
    if not path:
        return jsonify({"error": "Path required"}), 400
    target = (FILES_DIR / path).resolve()
    if not str(target).startswith(str(FILES_DIR.resolve())):
        return jsonify({"error": "Invalid path"}), 400
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return jsonify({"status": "ok"})


@app.route("/api/files/mkdir", methods=["POST"])
def api_files_mkdir():
    path = (request.get_json() or {}).get("path", "")
    if path:
        target = (FILES_DIR / path).resolve()
        if not str(target).startswith(str(FILES_DIR.resolve())):
            return jsonify({"error": "Invalid path"}), 400
        target.mkdir(parents=True, exist_ok=True)
    return jsonify({"status": "ok"})


@app.route("/api/files/delete", methods=["POST"])
def api_files_delete():
    path = (request.get_json() or {}).get("path", "")
    target = (FILES_DIR / path).resolve()
    if not str(target).startswith(str(FILES_DIR.resolve())):
        return jsonify({"error": "Invalid path"}), 400
    if target.is_dir():
        shutil.rmtree(target)
    elif target.is_file():
        target.unlink()
    return jsonify({"status": "ok"})


@app.route("/api/files/upload", methods=["POST"])
def api_files_upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    path = request.form.get("path", "")
    target_dir = FILES_DIR / path if path else FILES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    file.save(target_dir / file.filename)
    return jsonify({"status": "ok"})


@app.route("/api/files/download/<path:filepath>")
def api_files_download(filepath):
    return send_from_directory(FILES_DIR, filepath, as_attachment=True)


# ═══════════════════════════════════════════════════════════════════
#  Logs & Notifications
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/logs")
def api_logs():
    return jsonify(web_log_handler.get_logs(request.args.get("limit", 100, type=int)))


@app.route("/api/logs/stream")
def api_logs_stream():
    def generate():
        q = web_log_handler.subscribe()
        try:
            while True:
                try:
                    yield f"data: {json.dumps(q.get(timeout=30))}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            web_log_handler.unsubscribe(q)
    return Response(generate(), mimetype='text/event-stream')


@app.route("/api/notifications")
def api_notifications():
    return jsonify(notifications.get_all())


@app.route("/api/notifications/add", methods=["POST"])
def api_notifications_add():
    data = request.get_json() or {}
    return jsonify(notifications.add(
        data.get("title", ""), data.get("message", ""),
        data.get("type", "info"), data.get("icon", "💬"),
        data.get("duration", 5000), data.get("action")
    ))


@app.route("/api/notifications/stream")
def api_notifications_stream():
    def generate():
        q = notifications.subscribe()
        try:
            while True:
                try:
                    yield f"data: {json.dumps(q.get(timeout=30))}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            notifications.unsubscribe(q)
    return Response(generate(), mimetype='text/event-stream')


@app.route("/api/system/info")
def api_system_info():
    try:
        import psutil
        return jsonify({
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
        })
    except:
        return jsonify({})


# ═══════════════════════════════════════════════════════════════════
#  Plugins
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/plugins")
def api_plugins_list():
    plugins = get_plugins()
    if not plugins:
        return jsonify([])
    return jsonify([{**s.manifest.to_dict(), "installed": True, "enabled": s.enabled, "loaded": s.loaded} 
                    for s in plugins.get_installed_plugins()])


@app.route("/api/plugins/desktop")
def api_plugins_desktop():
    plugins = get_plugins()
    return jsonify(plugins.get_desktop_plugins() if plugins else [])


@app.route("/api/plugins/catalog")
def api_plugins_catalog():
    plugins = get_plugins()
    return jsonify(plugins.fetch_catalog() if plugins else [])


@app.route("/api/plugins/<plugin_id>")
def api_plugin_info(plugin_id):
    plugins = get_plugins()
    if not plugins:
        return jsonify({"error": "unavailable"}), 500
    info = plugins.get_plugin_info(plugin_id)
    if info:
        for upd in plugins.check_plugin_updates():
            if upd.get("id") == plugin_id:
                info["update_available"] = True
                info["latest_version"] = upd.get("latest_version")
                break
        else:
            info["update_available"] = False
            info["latest_version"] = info.get("version")
        return jsonify(info)
    for item in plugins.fetch_catalog():
        if item.get("id") == plugin_id:
            return jsonify(item)
    return jsonify({"error": "Not found"}), 404


@app.route("/api/plugins/<plugin_id>/install", methods=["POST"])
def api_plugin_install(plugin_id):
    plugins = get_plugins()
    if plugins and plugins.install_plugin(plugin_id):
        notifications.add("Плагин", f"{plugin_id} установлен", "success", "🧩")
        return jsonify({"status": "ok"})
    return jsonify({"error": "Failed"}), 500


@app.route("/api/plugins/updates")
def api_plugins_updates():
    plugins = get_plugins()
    if not plugins:
        return jsonify([])
    try:
        return jsonify(plugins.check_plugin_updates())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/plugins/<plugin_id>/update", methods=["POST"])
def api_plugin_update(plugin_id):
    plugins = get_plugins()
    if plugins and plugins.update_plugin(plugin_id):
        notifications.add("Плагин", f"{plugin_id} обновлён", "success", "🧩")
        return jsonify({"status": "ok"})
    return jsonify({"error": "Failed"}), 500


@app.route("/api/plugins/update-all", methods=["POST"])
def api_plugins_update_all():
    plugins = get_plugins()
    if not plugins:
        return jsonify({"error": "unavailable"}), 500
    try:
        return jsonify({"status": "ok", **plugins.update_all_plugins()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/plugins/<plugin_id>/uninstall", methods=["POST"])
def api_plugin_uninstall(plugin_id):
    plugins = get_plugins()
    if plugins and plugins.uninstall_plugin(plugin_id):
        return jsonify({"status": "ok"})
    return jsonify({"error": "Failed"}), 500


@app.route("/api/plugins/<plugin_id>/window")
def api_plugin_window(plugin_id):
    plugins = get_plugins()
    return jsonify(plugins.get_plugin_window_data(plugin_id) if plugins else {})


@app.route("/api/plugins/<plugin_id>/action", methods=["POST"])
def api_plugin_action(plugin_id):
    plugins = get_plugins()
    if not plugins:
        return jsonify({"error": "unavailable"}), 500
    data = request.get_json() or {}
    return jsonify(plugins.call_plugin_action(plugin_id, data.get("action", ""), data.get("data", {})))


@app.route("/plugins/<plugin_id>/static/<path:filename>")
def plugin_static(plugin_id, filename):
    from core.config import get_config
    return send_from_directory(get_config().data_dir / "plugins" / plugin_id / "static", filename)


@app.route("/plugins/<plugin_id>/template/<filename>")
def plugin_template(plugin_id, filename):
    from core.config import get_config
    path = get_config().data_dir / "plugins" / plugin_id / "templates" / filename
    return path.read_text() if path.exists() else abort(404)


# ═══════════════════════════════════════════════════════════════════
#  Updater
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/update/check")
def api_update_check():
    source = request.args.get("source", "github")
    repo = request.args.get("repo", "dariumi/Daria")
    ref = request.args.get("ref", "main")
    current = _read_version(PROJECT_ROOT / "VERSION")
    latest = current
    update_available = False

    if source == "github":
        try:
            try:
                import requests
                api_url = f"https://api.github.com/repos/{repo.strip('/')}/releases/latest"
                r = requests.get(api_url, timeout=15)
                if r.status_code == 200:
                    latest = str((r.json().get("tag_name") or "").lstrip("v") or current)
                else:
                    tags_url = f"https://api.github.com/repos/{repo.strip('/')}/tags"
                    r2 = requests.get(tags_url, timeout=15)
                    if r2.status_code == 200 and r2.json():
                        latest = str(r2.json()[0].get("name", "")).lstrip("v") or current
            except Exception:
                latest = current
            update_available = _version_key(latest) > _version_key(current)
        except Exception as e:
            return jsonify({"error": str(e), "current": current, "latest": current, "update_available": False}), 200

    _update_state["last_check"] = datetime.now().isoformat()
    return jsonify({
        "current": current,
        "latest": latest,
        "update_available": update_available,
        "source": source,
        "repo": repo,
        "ref": ref,
    })


@app.route("/api/update/auto", methods=["GET", "POST"])
def api_update_auto():
    settings = load_settings()
    if request.method == "GET":
        return jsonify({"auto_update": settings.get("auto_update", False)})
    data = request.get_json() or {}
    enabled = bool(data.get("auto_update", False))
    save_settings({"auto_update": enabled})
    return jsonify({"status": "ok", "auto_update": enabled})


@app.route("/api/update/from-github", methods=["POST"])
def api_update_from_github():
    if _update_state.get("running"):
        return jsonify({"error": "update already running"}), 409
    data = request.get_json() or {}
    repo = data.get("repo", "dariumi/Daria")
    ref = data.get("ref", "main")
    _update_state["running"] = True
    _update_state["last_error"] = None
    _update_state["last_action"] = f"github:{repo}@{ref}"
    try:
        archive = _download_github_archive(repo, ref)
        with tempfile.TemporaryDirectory(prefix="daria-update-") as td:
            archive_path = Path(td) / "update.zip"
            archive_path.write_bytes(archive)
            extracted = Path(td) / "extracted"
            _extract_archive_to_dir(archive_path, extracted)
            src_root = _find_project_root(extracted)
            _sync_project_tree(src_root, PROJECT_ROOT)
        new_version = _read_version(PROJECT_ROOT / "VERSION")
        notifications.add("Обновление", f"Система обновлена до v{new_version}", "success", "⬆️", 10000)
        return jsonify({"status": "ok", "version": new_version, "restart_required": True})
    except Exception as e:
        _update_state["last_error"] = str(e)
        return jsonify({"error": str(e)}), 500
    finally:
        _update_state["running"] = False


@app.route("/api/update/from-archive", methods=["POST"])
def api_update_from_archive():
    if _update_state.get("running"):
        return jsonify({"error": "update already running"}), 409
    data = request.get_json() or {}
    archive_path = Path((data.get("archive_path") or "").strip()).expanduser()
    if not archive_path.exists():
        return jsonify({"error": "archive not found"}), 400

    _update_state["running"] = True
    _update_state["last_error"] = None
    _update_state["last_action"] = f"archive:{archive_path}"
    try:
        with tempfile.TemporaryDirectory(prefix="daria-update-") as td:
            extracted = Path(td) / "extracted"
            _extract_archive_to_dir(archive_path, extracted)
            src_root = _find_project_root(extracted)
            _sync_project_tree(src_root, PROJECT_ROOT)
        new_version = _read_version(PROJECT_ROOT / "VERSION")
        notifications.add("Обновление", f"Система обновлена до v{new_version}", "success", "⬆️", 10000)
        return jsonify({"status": "ok", "version": new_version, "restart_required": True})
    except Exception as e:
        _update_state["last_error"] = str(e)
        return jsonify({"error": str(e)}), 500
    finally:
        _update_state["running"] = False


@app.route("/api/update/state")
def api_update_state():
    return jsonify({
        **_update_state,
        "version": _read_version(PROJECT_ROOT / "VERSION"),
    })


# ═══════════════════════════════════════════════════════════════════
#  Wiki
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/wiki/pages")
def api_wiki_pages():
    wiki_dir = PROJECT_ROOT / "docs" / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    pages = sorted([p.name for p in wiki_dir.glob("*.md")])
    return jsonify({"pages": pages})


@app.route("/api/wiki/page")
def api_wiki_page():
    name = (request.args.get("name") or "Home.md").strip()
    if "/" in name or "\\" in name:
        return jsonify({"error": "Invalid page"}), 400
    wiki_dir = PROJECT_ROOT / "docs" / "wiki"
    path = (wiki_dir / name).resolve()
    if not path.exists() or not str(path).startswith(str(wiki_dir.resolve())):
        return jsonify({"error": "Not found"}), 404
    text = path.read_text(encoding="utf-8")
    return jsonify({"name": name, "content": text})


@app.route("/wiki")
def wiki_redirect():
    return render_template("index.html", version=VERSION)


# ═══════════════════════════════════════════════════════════════════
#  Server
# ═══════════════════════════════════════════════════════════════════

def create_app():
    return app


def run_server(host: str = "127.0.0.1", port: int = 8000, 
               debug: bool = False, ssl_context = None):
    logger.info("Initializing DARIA...")
    get_brain()
    get_memory()
    get_plugins()
    
    # Start attention thread
    settings = load_settings()
    attention_thread.enabled = settings.get("attention_enabled", True)
    attention_thread.start()
    
    notifications.add("DARIA", f"Система запущена v{VERSION}", "success", "🌸", 8000)
    logger.info("Ready!")
    
    app.run(host=host, port=port, debug=debug, threaded=True, ssl_context=ssl_context)


application = app
