"""
DARIA Telegram Bot Plugin v2.0.0
- Fixed: set_wakeup_fd thread error (use asyncio properly)
- Added: attention system in telegram
- Added: proactive messaging
- Multi-message support
"""

import asyncio
import threading
import logging
import random
import time as time_module
from typing import Dict, Any, Optional, List

from core.plugins import DariaPlugin, PluginAPI, PluginManifest

logger = logging.getLogger("daria.plugins.telegram")

try:
    from telegram import Update, Bot
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False
    logger.warning("python-telegram-bot not installed")


class TelegramBotPlugin(DariaPlugin):
    """Telegram Bot integration for DARIA v2.0"""

    def on_load(self):
        self.api.log("Telegram Bot plugin v2.0 loaded")

        self.bot_token: Optional[str] = None
        self.allowed_users: list = []
        self.running = False
        self.app: Optional[Application] = None
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._attention_thread: Optional[threading.Thread] = None
        self._attention_enabled = True
        self._chat_ids: List[int] = []

        settings = self.api.load_data("settings", {})
        self.bot_token = settings.get("bot_token")
        self.allowed_users = settings.get("allowed_users", [])
        self._chat_ids = settings.get("chat_ids", [])
        self._attention_enabled = settings.get("attention_enabled", True)

        if self.bot_token and settings.get("auto_start", False):
            self.start_bot()

    def on_unload(self):
        self.stop_bot()
        self.api.log("Telegram Bot plugin unloaded")

    def on_window_open(self) -> Dict[str, Any]:
        return {
            "has_telegram": HAS_TELEGRAM,
            "bot_token": self.bot_token[:10] + "..." if self.bot_token else None,
            "running": self.running,
            "allowed_users": self.allowed_users,
            "attention_enabled": self._attention_enabled,
            "chat_ids_count": len(self._chat_ids),
        }

    def on_window_action(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if action == "save_settings":
            self.bot_token = data.get("bot_token")
            self.allowed_users = data.get("allowed_users", [])
            self._attention_enabled = data.get("attention_enabled", True)
            self._save_settings()
            return {"status": "ok"}

        elif action == "start_bot":
            if self.start_bot():
                return {"status": "ok", "running": True}
            return {"status": "error", "message": "Failed to start bot"}

        elif action == "stop_bot":
            self.stop_bot()
            return {"status": "ok", "running": False}

        elif action == "toggle_attention":
            self._attention_enabled = data.get("enabled", True)
            self._save_settings()
            return {"status": "ok", "attention_enabled": self._attention_enabled}

        elif action == "get_status":
            return {"running": self.running, "has_telegram": HAS_TELEGRAM, "attention_enabled": self._attention_enabled}

        return {"error": "Unknown action"}

    def _save_settings(self):
        self.api.save_data("settings", {
            "bot_token": self.bot_token,
            "allowed_users": self.allowed_users,
            "auto_start": True,
            "attention_enabled": self._attention_enabled,
            "chat_ids": self._chat_ids,
        })

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

            self._attention_thread = threading.Thread(target=self._attention_loop, daemon=True)
            self._attention_thread.start()
            return True
        except Exception as e:
            self.api.log(f"Failed to start bot: {e}", "error")
            return False

    def stop_bot(self):
        if not self.running:
            return
        self.running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.api.log("Telegram bot stopped")

    def _run_bot(self):
        """Run bot in separate thread with its own event loop - NO signal handlers"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._start_polling())
            self._loop.run_forever()
        except Exception as e:
            self.api.log(f"Bot error: {e}", "error")
            self.running = False
        finally:
            try:
                self._loop.run_until_complete(self._cleanup())
            except:
                pass
            self._loop.close()

    async def _start_polling(self):
        """Start bot without signal handlers (fixes set_wakeup_fd error)"""
        self.app = Application.builder().token(self.bot_token).build()

        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("help", self._cmd_help))
        self.app.add_handler(CommandHandler("mood", self._cmd_mood))
        self.app.add_handler(CommandHandler("play", self._cmd_play))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message))

        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

    async def _cleanup(self):
        if self.app:
            try:
                await self.app.updater.stop()
                await self.app.stop()
                await self.app.shutdown()
            except:
                pass

    def _attention_loop(self):
        """Attention and proactive messaging loop for Telegram"""
        while self.running:
            time_module.sleep(60)
            if not self._attention_enabled or not self._chat_ids or not self._loop:
                continue

            try:
                brain = self.api.get_brain()
                if not brain:
                    continue

                proactive = brain.check_proactive()
                if proactive:
                    for chat_id in self._chat_ids:
                        for msg in proactive.get("messages", []):
                            asyncio.run_coroutine_threadsafe(
                                self._send_to_chat(chat_id, msg), self._loop
                            )
                            time_module.sleep(1.5)
                    continue

                attention = brain.attention.check_attention_needed()
                if attention:
                    for chat_id in self._chat_ids:
                        asyncio.run_coroutine_threadsafe(
                            self._send_to_chat(chat_id, attention["message"]), self._loop
                        )
            except Exception as e:
                logger.debug(f"Telegram attention error: {e}")

    async def _send_to_chat(self, chat_id: int, text: str):
        try:
            if self.app and self.app.bot:
                await self.app.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            logger.debug(f"Failed to send to {chat_id}: {e}")

    def _remember_chat_id(self, chat_id: int):
        if chat_id not in self._chat_ids:
            self._chat_ids.append(chat_id)
            self._save_settings()

    # ─── Telegram Handlers ─────────────────────────────────────────

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text("❌ У тебя нет доступа к боту")
            return
        self._remember_chat_id(update.effective_chat.id)
        await update.message.reply_text(
            "🌸 Привет! Я Дарья!\n\n"
            "Напиши мне что-нибудь, и я отвечу! 💕\n\n"
            "/help - помощь\n/mood - моё настроение\n/play - поиграем!\n"
        )

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📚 Помощь\n\nПросто напиши мне сообщение!\n\n"
            "/mood - моё настроение\n/play - предложить игру"
        )

    async def _cmd_mood(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            brain = self.api.get_brain()
            if brain:
                state = brain.get_state()
                await update.message.reply_text(
                    f"{state.get('mood_emoji', '😌')} Сейчас я {state.get('mood_label', 'спокойна')}\n"
                    f"⚡ Энергия: {int(state.get('energy', 0.7) * 100)}%"
                )
            else:
                await update.message.reply_text("Не могу определить настроение... 💭")
        except:
            await update.message.reply_text("Ой, что-то пошло не так... 💔")

    async def _cmd_play(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        games = [
            "Давай поиграем в слова! Я говорю слово, ты — следующее на последнюю букву 🔤\nМоё слово: Солнце",
            "Хочешь загадку? 🤔\nЧто можно увидеть с закрытыми глазами?",
            "Давай в ассоциации! Я говорю слово, а ты — первое что придёт в голову 💭\nМоё слово: Звёзды",
            "Правда или ложь? 🎯\nСлоны умеют прыгать. Правда или ложь?",
        ]
        await update.message.reply_text(random.choice(games))

    async def _on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if self.allowed_users and user_id not in self.allowed_users:
            return

        self._remember_chat_id(update.effective_chat.id)
        text = update.message.text

        try:
            result = self.api.send_message(text)

            # Multi-message support
            messages = result.get("messages", [result.get("response", "Ой, что-то пошло не так... 💔")])

            for i, msg in enumerate(messages):
                if i > 0:
                    await update.effective_chat.send_action("typing")
                    await asyncio.sleep(0.8 + len(msg) * 0.015)
                await update.message.reply_text(msg)

        except Exception as e:
            self.api.log(f"Message error: {e}", "error")
            await update.message.reply_text("Извини, у меня сейчас небольшие проблемы... 💭")
