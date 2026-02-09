"""
DARIA Pomodoro Timer v1.0.0
"""

from typing import Dict, Any

from core.plugins import DariaPlugin, PluginAPI, PluginManifest


class PomodoroPlugin(DariaPlugin):
    """Pomodoro timer plugin"""
    
    WORK_MESSAGES = [
        "Время работать! Ты справишься! 💪",
        "Начинаем! Сосредоточься и вперёд! 🎯",
        "25 минут фокуса. Я верю в тебя! 🌸",
    ]
    
    BREAK_MESSAGES = [
        "Отличная работа! Отдохни немного 🌸",
        "Перерыв! Потянись и расслабься 💕",
        "Молодец! Сделай паузу, ты заслужил! ✨",
    ]
    
    COMPLETE_MESSAGES = [
        "Потрясающе! Ты завершил сессию! 🎉",
        "Супер! Так держать! 💖",
        "Ты молодец! Продолжай в том же духе! 🌸",
    ]
    
    def on_load(self):
        self.api.log("Pomodoro plugin loaded")
        self.stats = self.api.load_data("stats", {
            "completed_pomodoros": 0,
            "total_work_minutes": 0,
        })
    
    def on_window_open(self) -> Dict[str, Any]:
        settings = self.api.load_data("settings", {
            "work_duration": 25,
            "short_break": 5,
            "long_break": 15,
            "pomodoros_until_long": 4,
        })
        return {
            "settings": settings,
            "stats": self.stats,
        }
    
    def on_window_action(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        import random
        
        if action == "save_settings":
            self.api.save_data("settings", data)
            return {"status": "ok"}
        
        elif action == "pomodoro_complete":
            self.stats["completed_pomodoros"] += 1
            self.stats["total_work_minutes"] += data.get("minutes", 25)
            self.api.save_data("stats", self.stats)
            
            message = random.choice(self.COMPLETE_MESSAGES)
            self.api.send_notification("🍅 Помодоро", message, "success")
            
            return {"status": "ok", "stats": self.stats, "message": message}
        
        elif action == "get_message":
            msg_type = data.get("type", "work")
            if msg_type == "work":
                return {"message": random.choice(self.WORK_MESSAGES)}
            elif msg_type == "break":
                return {"message": random.choice(self.BREAK_MESSAGES)}
            return {"message": ""}
        
        elif action == "get_stats":
            return {"stats": self.stats}
        
        return {"error": "Unknown action"}
