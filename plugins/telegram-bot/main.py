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
import re
from datetime import datetime
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

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    requests = None
    HAS_REQUESTS = False


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
        self._mirror_to_web = True
        self._group_mode = False
        self._auto_start = True
        self._private_mode = True
        self._allowed_groups: List[int] = []
        self._group_histories: Dict[str, List[Dict[str, str]]] = {}
        self._chat_meta: Dict[str, Dict[str, Any]] = {}
        self._bot_message_ids: Dict[str, List[int]] = {}
        self._bot_id: Optional[int] = None
        self._bot_username: str = ""

        settings = self.api.load_data("settings", {})
        self.bot_token = settings.get("bot_token")
        self.allowed_users = self._normalize_int_list(settings.get("allowed_users", []))
        self._chat_ids = settings.get("chat_ids", [])
        self._attention_enabled = settings.get("attention_enabled", True)
        self._mirror_to_web = settings.get("mirror_to_web", True)
        self._group_mode = settings.get("group_mode", False)
        self._auto_start = settings.get("auto_start", True)
        self._private_mode = settings.get("private_mode", True)
        self._allowed_groups = self._normalize_int_list(settings.get("allowed_groups", []))
        self._group_histories = self.api.load_data("group_histories", {})
        self._chat_meta = self.api.load_data("chat_meta", {})

        if self.bot_token and self._auto_start:
            self.start_bot()

    def on_unload(self):
        self.stop_bot()
        self.api.log("Telegram Bot plugin unloaded")

    def on_window_open(self) -> Dict[str, Any]:
        return {
            "has_telegram": HAS_TELEGRAM,
            "bot_token": "",
            "token_configured": bool(self.bot_token),
            "running": self.running,
            "allowed_users": self.allowed_users,
            "attention_enabled": self._attention_enabled,
            "chat_ids_count": len(self._chat_ids),
            "mirror_to_web": self._mirror_to_web,
            "group_mode": self._group_mode,
            "auto_start": self._auto_start,
            "private_mode": self._private_mode,
            "allowed_groups": self._allowed_groups,
            "chats": self._get_chats_for_ui(),
        }

    def on_window_action(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if action == "save_settings":
            token = (data.get("bot_token") or "").strip()
            if token and "..." not in token:
                self.bot_token = token
            self.allowed_users = self._normalize_int_list(data.get("allowed_users", []))
            self._attention_enabled = data.get("attention_enabled", True)
            self._mirror_to_web = data.get("mirror_to_web", True)
            self._group_mode = data.get("group_mode", False)
            self._auto_start = data.get("auto_start", True)
            self._private_mode = data.get("private_mode", True)
            self._allowed_groups = self._normalize_int_list(data.get("allowed_groups", []))
            self._save_settings()
            return {"status": "ok", "token_configured": bool(self.bot_token)}

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
            return {
                "running": self.running,
                "has_telegram": HAS_TELEGRAM,
                "attention_enabled": self._attention_enabled,
                "private_mode": self._private_mode,
                "group_mode": self._group_mode,
            }

        elif action == "get_chats":
            return {"status": "ok", "chats": self._get_chats_for_ui()}

        elif action == "check_access":
            return {"status": "ok", "checks": self._check_access_for_known_chats()}

        return {"error": "Unknown action"}

    def _save_settings(self):
        self.api.save_data("settings", {
            "bot_token": self.bot_token,
            "allowed_users": self.allowed_users,
            "auto_start": self._auto_start,
            "attention_enabled": self._attention_enabled,
            "chat_ids": self._chat_ids,
            "mirror_to_web": self._mirror_to_web,
            "group_mode": self._group_mode,
            "private_mode": self._private_mode,
            "allowed_groups": self._allowed_groups,
        })
        self.api.save_data("group_histories", self._group_histories)
        self.api.save_data("chat_meta", self._chat_meta)

    @staticmethod
    def _normalize_int_list(values: Any) -> List[int]:
        if not values:
            return []
        result: List[int] = []
        for value in values:
            try:
                parsed = int(value)
            except Exception:
                continue
            if parsed not in result:
                result.append(parsed)
        return result

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
        me = await self.app.bot.get_me()
        self._bot_id = me.id
        self._bot_username = (me.username or "").lower()

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
                        chat_meta = self._chat_meta.get(str(chat_id), {})
                        if chat_meta.get("type") != "private":
                            continue
                        if not self._private_mode:
                            continue
                        for msg in proactive.get("messages", []):
                            asyncio.run_coroutine_threadsafe(
                                self._send_to_chat(chat_id, msg), self._loop
                            )
                            time_module.sleep(1.5)
                    continue

                attention = brain.attention.check_attention_needed()
                if attention:
                    for chat_id in self._chat_ids:
                        chat_meta = self._chat_meta.get(str(chat_id), {})
                        if chat_meta.get("type") != "private":
                            continue
                        if not self._private_mode:
                            continue
                        asyncio.run_coroutine_threadsafe(
                            self._send_to_chat(chat_id, attention["message"]), self._loop
                        )
            except Exception as e:
                logger.debug(f"Telegram attention error: {e}")

    async def _send_to_chat(self, chat_id: int, text: str):
        try:
            if self.app and self.app.bot:
                sent = await self.app.bot.send_message(chat_id=chat_id, text=text)
                self._remember_bot_message(chat_id, getattr(sent, "message_id", None))
        except Exception as e:
            logger.debug(f"Failed to send to {chat_id}: {e}")

    def _remember_chat_id(self, chat_id: int):
        if chat_id not in self._chat_ids:
            self._chat_ids.append(chat_id)
            self._save_settings()

    def _remember_chat_meta(self, update: Update, role: str, content: str):
        chat = update.effective_chat
        user = update.effective_user
        if not chat:
            return
        cid = str(chat.id)
        ctype = str(chat.type)
        title = chat.title or chat.full_name or chat.username or f"chat {chat.id}"
        author = "Даша" if role == "assistant" else (user.full_name if user else "Пользователь")
        avatar = "👤" if ctype == "private" else "👥"
        self._chat_meta[cid] = {
            "id": chat.id,
            "type": ctype,
            "title": title,
            "avatar": avatar,
            "last_message": (content or "")[:240],
            "last_author": author,
            "last_ts": datetime.now().isoformat(),
        }
        self._save_settings()

    def _get_chats_for_ui(self) -> List[Dict[str, Any]]:
        chats = list(self._chat_meta.values())
        chats.sort(key=lambda x: x.get("last_ts", ""), reverse=True)
        return chats

    def _looks_like_group_trigger(self, text: str) -> bool:
        tl = (text or "").lower().strip()
        if not tl:
            return False
        if self._bot_username and f"@{self._bot_username}" in tl:
            return True
        triggers = [
            "даша", "даш", "дарья",
            "все тут", "все тута", "кто тут", "кто здесь", "есть кто",
            "привет всем", "всем привет",
        ]
        if any(t in tl for t in triggers):
            return True
        return bool(re.search(r"\b(даша|дарья)\b", tl))

    def _group_allowed(self, chat_id: int) -> bool:
        if not self._allowed_groups:
            return False
        return chat_id in self._allowed_groups

    async def _can_write_chat_async(self, chat_id: int, chat_type: str) -> Dict[str, Any]:
        if not self.app or not self.app.bot:
            return {"ok": False, "reason": "bot_unavailable"}
        try:
            if chat_type == "private":
                await self.app.bot.send_chat_action(chat_id=chat_id, action="typing")
                return {"ok": True, "reason": "ok"}
            member = await self.app.bot.get_chat_member(chat_id=chat_id, user_id=self._bot_id)
            can_send = getattr(member, "can_send_messages", True)
            return {"ok": bool(can_send), "reason": "ok" if can_send else "cannot_send_messages"}
        except Exception as e:
            return {"ok": False, "reason": str(e)}

    def _check_access_for_known_chats(self) -> List[Dict[str, Any]]:
        results = []
        for chat in self._get_chats_for_ui():
            cid = int(chat["id"])
            ctype = chat.get("type", "private")
            status = {"ok": False, "reason": "loop_unavailable"}
            if self._loop:
                try:
                    fut = asyncio.run_coroutine_threadsafe(self._can_write_chat_async(cid, ctype), self._loop)
                    status = fut.result(timeout=5)
                except Exception as e:
                    status = {"ok": False, "reason": str(e)}
            results.append({
                "id": cid,
                "title": chat.get("title", str(cid)),
                "type": ctype,
                "access": status,
            })
        return results

    def _remember_bot_message(self, chat_id: int, message_id: Any):
        try:
            mid = int(message_id)
        except Exception:
            return
        key = str(chat_id)
        ids = self._bot_message_ids.get(key, [])
        ids.append(mid)
        self._bot_message_ids[key] = ids[-200:]

    def _is_reply_to_bot(self, update: Update) -> bool:
        msg = update.message
        replied = msg.reply_to_message if msg else None
        if not replied:
            return False

        chat_id = update.effective_chat.id if update.effective_chat else None
        replied_mid = getattr(replied, "message_id", None)
        if chat_id is not None and replied_mid is not None:
            known = self._bot_message_ids.get(str(chat_id), [])
            try:
                if int(replied_mid) in known:
                    return True
            except Exception:
                pass

        from_user = replied.from_user
        if from_user and self._bot_id and from_user.id == self._bot_id:
            return True
        if from_user and self._bot_username and (from_user.username or "").lower() == self._bot_username:
            return True
        return False

    def _reply_info(self, update: Update) -> Dict[str, Any]:
        msg = update.message
        replied = msg.reply_to_message if msg else None
        if not replied:
            return {"is_reply": False, "to_bot": False, "text": ""}

        to_bot = self._is_reply_to_bot(update)
        replied_text = (replied.text or replied.caption or "").strip()
        return {
            "is_reply": True,
            "to_bot": to_bot,
            "text": replied_text[:800],
        }

    @staticmethod
    def _compose_user_input(text: str, reply_info: Dict[str, Any]) -> str:
        if not reply_info.get("to_bot"):
            return text
        replied_text = (reply_info.get("text") or "").strip()
        if not replied_text:
            return text
        return (
            "Пользователь отвечает на твое предыдущее сообщение.\n"
            f"Твое сообщение: {replied_text}\n"
            f"Ответ пользователя: {text}"
        )

    # ─── Telegram Handlers ─────────────────────────────────────────

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text("❌ У тебя нет доступа к боту")
            return
        self._remember_chat_id(update.effective_chat.id)
        self._remember_chat_meta(update, "user", "/start")
        sent = await update.message.reply_text(
            "🌸 Привет! Я Дарья!\n\n"
            "Напиши мне что-нибудь, и я отвечу! 💕\n\n"
            "/help - помощь\n/mood - моё настроение\n/play - поиграем!\n"
        )
        self._remember_bot_message(update.effective_chat.id, getattr(sent, "message_id", None))

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self._remember_chat_meta(update, "user", "/help")
        sent = await update.message.reply_text(
            "📚 Помощь\n\nПросто напиши мне сообщение!\n\n"
            "/mood - моё настроение\n/play - предложить игру"
        )
        self._remember_bot_message(update.effective_chat.id, getattr(sent, "message_id", None))

    async def _cmd_mood(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self._remember_chat_meta(update, "user", "/mood")
        try:
            brain = self.api.get_brain()
            if brain:
                state = brain.get_state()
                sent = await update.message.reply_text(
                    f"{state.get('mood_emoji', '😌')} Сейчас я {state.get('mood_label', 'спокойна')}\n"
                    f"⚡ Энергия: {int(state.get('energy', 0.7) * 100)}%"
                )
                self._remember_bot_message(update.effective_chat.id, getattr(sent, "message_id", None))
            else:
                sent = await update.message.reply_text("Не могу определить настроение... 💭")
                self._remember_bot_message(update.effective_chat.id, getattr(sent, "message_id", None))
        except:
            sent = await update.message.reply_text("Ой, что-то пошло не так... 💔")
            self._remember_bot_message(update.effective_chat.id, getattr(sent, "message_id", None))

    async def _cmd_play(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self._remember_chat_meta(update, "user", "/play")
        games = [
            "Давай поиграем в слова! Я говорю слово, ты — следующее на последнюю букву 🔤\nМоё слово: Солнце",
            "Хочешь загадку? 🤔\nЧто можно увидеть с закрытыми глазами?",
            "Давай в ассоциации! Я говорю слово, а ты — первое что придёт в голову 💭\nМоё слово: Звёзды",
            "Правда или ложь? 🎯\nСлоны умеют прыгать. Правда или ложь?",
        ]
        sent = await update.message.reply_text(random.choice(games))
        self._remember_bot_message(update.effective_chat.id, getattr(sent, "message_id", None))

    async def _on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_type = str(update.effective_chat.type)
        user_id = update.effective_user.id
        # Whitelist by users is enforced in private chats.
        # For groups we rely on allowed group ids + trigger checks.
        if chat_type == "private" and self.allowed_users and user_id not in self.allowed_users:
            return

        self._remember_chat_id(update.effective_chat.id)
        text = update.message.text
        reply_info = self._reply_info(update)
        self._remember_chat_meta(update, "user", text)

        if chat_type == "private" and not self._private_mode:
            return
        if chat_type in ("group", "supergroup"):
            if not self._group_mode:
                return
            if not self._group_allowed(update.effective_chat.id):
                return
            if not reply_info.get("to_bot") and not self._looks_like_group_trigger(text):
                return

        try:
            user_input = self._compose_user_input(text, reply_info)
            use_group_mode = self._group_mode and str(update.effective_chat.type) in ("group", "supergroup")
            if use_group_mode:
                # LLM generation is blocking; move it off the bot event loop.
                result = await asyncio.to_thread(self._process_group_message, update.effective_chat.id, user_input)
            else:
                # LLM generation is blocking; move it off the bot event loop.
                result = await asyncio.to_thread(self.api.send_message, user_input)

            # Multi-message support
            messages = result.get("messages", [result.get("response", "Ой, что-то пошло не так... 💔")])

            if self._mirror_to_web:
                self._mirror_message(update.effective_chat.id, "user", text)

            for i, msg in enumerate(messages):
                if i > 0:
                    await update.effective_chat.send_action("typing")
                    # Keep a tiny pause between multi-part messages without
                    # introducing long delivery lag.
                    await asyncio.sleep(0.2)
                sent = await update.message.reply_text(msg)
                self._remember_bot_message(update.effective_chat.id, getattr(sent, "message_id", None))
                self._remember_chat_meta(update, "assistant", msg)
                if self._mirror_to_web:
                    self._mirror_message(update.effective_chat.id, "assistant", msg)

        except Exception as e:
            self.api.log(f"Message error: {e}", "error")
            sent = await update.message.reply_text("Извини, у меня сейчас небольшие проблемы... 💭")
            self._remember_bot_message(update.effective_chat.id, getattr(sent, "message_id", None))

    def _process_group_message(self, chat_id: int, text: str) -> Dict[str, Any]:
        key = str(chat_id)
        history = self._group_histories.get(key, [])
        history.append({"role": "user", "content": text})
        history = history[-20:]
        system = {
            "role": "system",
            "content": (
                "Ты Даша. Это отдельный групповой чат Telegram. "
                "Отвечай мягко и дружелюбно, но не используй персональную долговременную память."
            ),
        }
        response = self.api.generate([system, *history])
        text_out = response.get("content") or "Я рядом, давайте продолжим 🌸"
        history.append({"role": "assistant", "content": text_out})
        self._group_histories[key] = history[-20:]
        self._save_settings()
        return {"response": text_out, "messages": [text_out]}

    def _mirror_message(self, chat_id: int, role: str, content: str):
        if not HAS_REQUESTS:
            return
        try:
            requests.post(
                "http://127.0.0.1:7777/api/chats/external",
                json={
                    "source": "telegram",
                    "source_chat_id": str(chat_id),
                    "role": role,
                    "content": content,
                },
                timeout=1.5,
            )
        except Exception:
            pass
