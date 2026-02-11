"""
DARIA Web App v0.7.4
Chat history, attention system, improved UI
"""

import os
import json
import logging
import queue
import threading
import shutil
import time
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
    def __init__(self, notifications: NotificationManager):
        super().__init__(daemon=True)
        self.notifications = notifications
        self.enabled = True
        self.running = True
        self._brain = None
    
    def run(self):
        while self.running:
            time.sleep(60)
            if self.enabled and self._brain:
                try:
                    attention = self._brain.attention.check_attention_needed()
                    if attention:
                        # Send in-app notification
                        self.notifications.add(
                            title="🌸 Дарья",
                            message=attention["message"],
                            type="attention",
                            icon="💕",
                            duration=15000,
                            action="open_chat",
                            system=True
                        )
                        
                        # Send OS notification via plyer
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
                            
                except Exception as e:
                    logger.debug(f"Attention error: {e}")
    
    def set_brain(self, brain):
        self._brain = brain
    
    def stop(self):
        self.running = False


# ═══════════════════════════════════════════════════════════════════
#  Flask App
# ═══════════════════════════════════════════════════════════════════

VERSION = "0.7.4"

app = Flask(__name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static")
)
app.config['SECRET_KEY'] = 'daria-secret-v0.7.4'
app.config['JSON_AS_ASCII'] = False
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Paths
DATA_DIR = Path.home() / ".daria"
SETTINGS_FILE = DATA_DIR / "settings.json"
UPLOADS_DIR = DATA_DIR / "uploads"
FILES_DIR = DATA_DIR / "files"
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


# ═══════════════════════════════════════════════════════════════════
#  Routes
# ═══════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html", version=VERSION)


@app.route("/api/status")
def api_status():
    return jsonify({
        "version": VERSION,
        "brain": get_brain() is not None,
        "memory": get_memory() is not None,
        "plugins": get_plugins() is not None,
        "llm": get_brain()._llm.check_availability() if get_brain() and get_brain()._llm else {}
    })


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
            memory._user_profile["user_name"] = data["name"]
        if data.get("gender"):
            memory._user_profile["user_gender"] = data["gender"]
        memory._save_profiles()
    
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
        # Create chat if needed
        if not chat_id:
            chat_id = chat_history.create_chat()
        
        # Save user message
        chat_history.add_message(chat_id, "user", content)
        
        # Get response
        result = brain.process_message(content)
        
        # Save assistant message
        chat_history.add_message(chat_id, "assistant", result["response"])
        
        result["chat_id"] = chat_id
        return jsonify(result)
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"response": "Ой, что-то пошло не так... 💔", "thinking": None})


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
        msg = brain.generate_attention_message()
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
    target = FILES_DIR / path
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
    target = FILES_DIR / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    return jsonify({"status": "ok"})


@app.route("/api/files/mkdir", methods=["POST"])
def api_files_mkdir():
    path = (request.get_json() or {}).get("path", "")
    if path:
        (FILES_DIR / path).mkdir(parents=True, exist_ok=True)
    return jsonify({"status": "ok"})


@app.route("/api/files/delete", methods=["POST"])
def api_files_delete():
    path = (request.get_json() or {}).get("path", "")
    target = FILES_DIR / path
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
