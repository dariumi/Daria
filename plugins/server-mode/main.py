"""
DARIA Server Mode Plugin v1.0.0
Multi-user support with accounts
"""

import hashlib
import secrets
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.plugins import DariaPlugin, PluginAPI, PluginManifest


class ServerModePlugin(DariaPlugin):
    """Multi-user server mode"""
    
    def on_load(self):
        self.api.log("Server Mode plugin loaded")
        
        self.users = self.api.load_data("users", {})
        self.sessions = {}
        self.settings = self.api.load_data("settings", {
            "enabled": False,
            "registration_open": True,
            "max_users": 10,
            "require_approval": False,
        })
    
    def on_unload(self):
        self.api.save_data("users", self.users)
        self.api.save_data("settings", self.settings)
    
    def on_window_open(self) -> Dict[str, Any]:
        return {
            "enabled": self.settings.get("enabled", False),
            "user_count": len(self.users),
            "settings": self.settings,
            "users": [
                {"username": u, "created": self.users[u].get("created"), "approved": self.users[u].get("approved", True)}
                for u in self.users
            ],
        }
    
    def on_window_action(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if action == "toggle_server":
            self.settings["enabled"] = data.get("enabled", False)
            self._save()
            return {"status": "ok", "enabled": self.settings["enabled"]}
        
        elif action == "save_settings":
            self.settings.update({
                "registration_open": data.get("registration_open", True),
                "max_users": data.get("max_users", 10),
                "require_approval": data.get("require_approval", False),
            })
            self._save()
            return {"status": "ok"}
        
        elif action == "create_user":
            username = data.get("username", "").strip().lower()
            password = data.get("password", "")
            
            if not username or not password:
                return {"error": "Заполни все поля"}
            
            if username in self.users:
                return {"error": "Пользователь уже существует"}
            
            if len(self.users) >= self.settings.get("max_users", 10):
                return {"error": "Достигнут лимит пользователей"}
            
            self.users[username] = {
                "password_hash": self._hash_password(password),
                "created": datetime.now().isoformat(),
                "approved": not self.settings.get("require_approval", False),
                "settings": {},
            }
            self._save()
            return {"status": "ok", "user": username}
        
        elif action == "delete_user":
            username = data.get("username", "")
            if username in self.users:
                del self.users[username]
                self._save()
                return {"status": "ok"}
            return {"error": "User not found"}
        
        elif action == "approve_user":
            username = data.get("username", "")
            if username in self.users:
                self.users[username]["approved"] = True
                self._save()
                return {"status": "ok"}
            return {"error": "User not found"}
        
        elif action == "get_users":
            return {"users": [
                {"username": u, "created": self.users[u].get("created"), "approved": self.users[u].get("approved", True)}
                for u in self.users
            ]}
        
        elif action == "login":
            username = data.get("username", "").strip().lower()
            password = data.get("password", "")
            
            if username not in self.users:
                return {"error": "Неверный логин или пароль"}
            
            user = self.users[username]
            if not user.get("approved", True):
                return {"error": "Аккаунт ожидает одобрения"}
            
            if user.get("password_hash") != self._hash_password(password):
                return {"error": "Неверный логин или пароль"}
            
            # Create session
            token = secrets.token_hex(32)
            self.sessions[token] = {
                "username": username,
                "created": datetime.now().isoformat(),
            }
            
            return {"status": "ok", "token": token, "username": username}
        
        elif action == "register":
            if not self.settings.get("registration_open", True):
                return {"error": "Регистрация закрыта"}
            
            return self.on_window_action("create_user", data)
        
        return {"error": "Unknown action"}
    
    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _save(self):
        self.api.save_data("users", self.users)
        self.api.save_data("settings", self.settings)
    
    def authenticate(self, token: str) -> Optional[str]:
        """Check if token is valid, return username"""
        session = self.sessions.get(token)
        if session:
            return session.get("username")
        return None
