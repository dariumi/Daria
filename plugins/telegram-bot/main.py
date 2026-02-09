"""
DARIA Telegram Bot Plugin v1.0.0
Chat with Daria via Telegram
"""

import asyncio
import threading
import logging
from typing import Dict, Any, Optional

from core.plugins import DariaPlugin, PluginAPI, PluginManifest

logger = logging.getLogger("daria.plugins.telegram")

# Try to import telegram
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False
    logger.warning("python-telegram-bot not installed")


class TelegramBotPlugin(DariaPlugin):
    """Telegram Bot integration for DARIA"""
    
    def on_load(self):
        self.api.log("Telegram Bot plugin loaded")
        
        self.bot_token: Optional[str] = None
        self.allowed_users: list = []
        self.running = False
        self.app: Optional[Application] = None
        self._thread: Optional[threading.Thread] = None
        
        # Load settings
        settings = self.api.load_data("settings", {})
        self.bot_token = settings.get("bot_token")
        self.allowed_users = settings.get("allowed_users", [])
        
        # Auto-start if configured
        if self.bot_token and settings.get("auto_start", False):
            self.start_bot()
    
    def on_unload(self):
        self.stop_bot()
        self.api.log("Telegram Bot plugin unloaded")
    
    # ─── Window Events ─────────────────────────────────────────────
    
    def on_window_open(self) -> Dict[str, Any]:
        return {
            "has_telegram": HAS_TELEGRAM,
            "bot_token": self.bot_token[:10] + "..." if self.bot_token else None,
            "running": self.running,
            "allowed_users": self.allowed_users,
        }
    
    def on_window_action(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if action == "save_settings":
            self.bot_token = data.get("bot_token")
            self.allowed_users = data.get("allowed_users", [])
            
            self.api.save_data("settings", {
                "bot_token": self.bot_token,
                "allowed_users": self.allowed_users,
                "auto_start": data.get("auto_start", False),
            })
            
            return {"status": "ok"}
        
        elif action == "start_bot":
            if self.start_bot():
                return {"status": "ok", "running": True}
            return {"status": "error", "message": "Failed to start bot"}
        
        elif action == "stop_bot":
            self.stop_bot()
            return {"status": "ok", "running": False}
        
        elif action == "get_status":
            return {
                "running": self.running,
                "has_telegram": HAS_TELEGRAM,
            }
        
        return {"error": "Unknown action"}
    
    # ─── Bot Management ────────────────────────────────────────────
    
    def start_bot(self) -> bool:
        if not HAS_TELEGRAM:
            self.api.log("Telegram library not installed", "error")
            return False
        
        if not self.bot_token:
            self.api.log("Bot token not configured", "error")
            return False
        
        if self.running:
            return True
        
        try:
            self._thread = threading.Thread(target=self._run_bot, daemon=True)
            self._thread.start()
            self.running = True
            self.api.log("Telegram bot started")
            return True
        except Exception as e:
            self.api.log(f"Failed to start bot: {e}", "error")
            return False
    
    def stop_bot(self):
        if not self.running:
            return
        
        self.running = False
        
        if self.app:
            try:
                asyncio.run(self.app.stop())
            except:
                pass
        
        self.api.log("Telegram bot stopped")
    
    def _run_bot(self):
        """Run bot in separate thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            self.app = Application.builder().token(self.bot_token).build()
            
            # Handlers
            self.app.add_handler(CommandHandler("start", self._cmd_start))
            self.app.add_handler(CommandHandler("help", self._cmd_help))
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message))
            
            # Run
            self.app.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            self.api.log(f"Bot error: {e}", "error")
            self.running = False
    
    # ─── Telegram Handlers ─────────────────────────────────────────
    
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text("❌ У тебя нет доступа к боту")
            return
        
        await update.message.reply_text(
            "🌸 Привет! Я Дарья!\n\n"
            "Напиши мне что-нибудь, и я отвечу! 💕\n\n"
            "Команды:\n"
            "/help - помощь\n"
        )
    
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📚 Помощь\n\n"
            "Просто напиши мне сообщение, и я отвечу!\n\n"
            "Я помню наши разговоры и могу:\n"
            "• Отвечать на вопросы\n"
            "• Поддержать в трудную минуту\n"
            "• Просто поболтать 💕"
        )
    
    async def _on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if self.allowed_users and user_id not in self.allowed_users:
            return
        
        text = update.message.text
        
        try:
            # Get response from Daria
            result = self.api.send_message(text)
            response = result.get("response", "Ой, что-то пошло не так... 💔")
            
            await update.message.reply_text(response)
        except Exception as e:
            self.api.log(f"Message error: {e}", "error")
            await update.message.reply_text("Извини, у меня сейчас небольшие проблемы... 💭")
