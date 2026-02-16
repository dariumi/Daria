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
import imghdr
from datetime import datetime
from typing import Dict, Any, Optional, List
from io import BytesIO

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

try:
    from PIL import Image
    HAS_PIL = True
except Exception:
    Image = None
    HAS_PIL = False


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
        self._chat_last_user_ts: Dict[str, str] = {}
        self._user_relations: Dict[str, Dict[str, Any]] = {}
        self._recent_polls: Dict[str, Dict[str, Any]] = {}
        self._sticker_enabled = True
        self._sticker_ids: List[str] = []
        self._image_gen_enabled = True
        self._bot_id: Optional[int] = None
        self._bot_username: str = ""
        self._stop_requested = threading.Event()

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
        self._user_relations = self.api.load_data("user_relations", {})
        self._sticker_enabled = settings.get("sticker_enabled", True)
        self._sticker_ids = settings.get("sticker_ids", [])
        self._image_gen_enabled = settings.get("image_gen_enabled", True)
        self._chat_last_user_ts = self.api.load_data("chat_last_user_ts", {})

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
            "sticker_enabled": self._sticker_enabled,
            "image_gen_enabled": self._image_gen_enabled,
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
            self._sticker_enabled = bool(data.get("sticker_enabled", True))
            self._sticker_ids = [str(x).strip() for x in (data.get("sticker_ids", []) or []) if str(x).strip()]
            self._image_gen_enabled = bool(data.get("image_gen_enabled", True))
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
            "sticker_enabled": self._sticker_enabled,
            "sticker_ids": self._sticker_ids,
            "image_gen_enabled": self._image_gen_enabled,
        })
        self.api.save_data("group_histories", self._group_histories)
        self.api.save_data("chat_meta", self._chat_meta)
        self.api.save_data("user_relations", self._user_relations)
        self.api.save_data("chat_last_user_ts", self._chat_last_user_ts)

    @staticmethod
    def _normalize_int_list(values: Any) -> List[int]:
        if values is None or values == "":
            return []
        if isinstance(values, int):
            values = [values]
        elif isinstance(values, str):
            raw = values.strip()
            if not raw:
                return []
            # Support legacy/plain formats:
            # "-100123, 777", "[-100123, 777]", or any text containing ids.
            if raw.startswith("[") and raw.endswith("]"):
                try:
                    import json

                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        values = parsed
                    else:
                        values = re.findall(r"-?\d+", raw)
                except Exception:
                    values = re.findall(r"-?\d+", raw)
            else:
                values = re.findall(r"-?\d+", raw)
        elif not isinstance(values, (list, tuple, set)):
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
            self._stop_requested.clear()
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
        if not self.running and not (self._thread and self._thread.is_alive()):
            return
        self.running = False
        self._stop_requested.set()
        if self._loop and self._loop.is_running():
            try:
                fut = asyncio.run_coroutine_threadsafe(self._cleanup(), self._loop)
                fut.result(timeout=20)
            except Exception as e:
                logger.debug(f"Telegram async cleanup error/timeout: {e}")
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass
        if self._thread and self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=10.0)
        self._thread = None
        if self._attention_thread and self._attention_thread.is_alive() and threading.current_thread() is not self._attention_thread:
            self._attention_thread.join(timeout=2.0)
        self._attention_thread = None
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
            except Exception as e:
                logger.debug(f"Telegram cleanup in finally failed: {e}")
            try:
                pending = [t for t in asyncio.all_tasks(self._loop) if not t.done()]
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            except Exception as e:
                logger.debug(f"Telegram loop shutdown warning: {e}")
            self._loop.close()
            self._loop = None
            self.app = None

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
        self.app.add_handler(MessageHandler(filters.POLL, self._on_poll_message))
        self.app.add_handler(MessageHandler(filters.PHOTO, self._on_photo_message))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message))

        await self.app.initialize()
        await self.app.start()
        try:
            # Ensure long polling mode is active and no stale webhook interferes.
            await self.app.bot.delete_webhook(drop_pending_updates=False)
        except Exception as e:
            logger.debug(f"delete_webhook failed: {e}")
        await self._replay_pending_updates(limit=120)
        await self.app.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            # Keep backlog so messages sent while bot was offline are processed.
            drop_pending_updates=False
        )

    async def _replay_pending_updates(self, limit: int = 120):
        """Process updates that arrived while bot was offline, then advance offset."""
        if not self.app or not self.app.bot:
            return
        try:
            pending = await self.app.bot.get_updates(
                timeout=0,
                limit=max(1, min(int(limit), 200)),
                allowed_updates=Update.ALL_TYPES,
            )
        except Exception as e:
            logger.debug(f"Pending updates fetch failed: {e}")
            return
        if not pending:
            return
        self.api.log(f"Replaying {len(pending)} queued Telegram updates")
        for upd in pending:
            try:
                await self.app.process_update(upd)
            except Exception as e:
                logger.debug(f"Pending update process failed: {e}")
        try:
            await self.app.bot.get_updates(
                offset=pending[-1].update_id + 1,
                timeout=0,
                allowed_updates=Update.ALL_TYPES,
            )
        except Exception as e:
            logger.debug(f"Pending updates offset commit failed: {e}")

    async def _cleanup(self):
        if self.app:
            try:
                if self.app.updater:
                    await self.app.updater.stop()
            except Exception as e:
                logger.debug(f"Updater.stop warning: {e}")
            try:
                await self.app.stop()
            except Exception as e:
                logger.debug(f"Application.stop warning: {e}")
            try:
                await self.app.shutdown()
            except Exception as e:
                logger.debug(f"Application.shutdown warning: {e}")

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
                        last_user_ts = self._chat_last_user_ts.get(str(chat_id))
                        if last_user_ts:
                            try:
                                if (datetime.now() - datetime.fromisoformat(last_user_ts)).total_seconds() < 25 * 60:
                                    continue
                            except Exception:
                                pass
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
                        last_user_ts = self._chat_last_user_ts.get(str(chat_id))
                        if last_user_ts:
                            try:
                                if (datetime.now() - datetime.fromisoformat(last_user_ts)).total_seconds() < 25 * 60:
                                    continue
                            except Exception:
                                pass
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

    @staticmethod
    def _is_single_emoji(text: str) -> bool:
        t = (text or "").strip()
        if not t or " " in t or len(t) > 4:
            return False
        return bool(re.match(r"^[\U0001F300-\U0001FAFF\u2600-\u27BF]+$", t))

    def _update_user_relation(self, chat_id: int, user_id: int, user_name: str, text: str):
        key = f"{chat_id}:{user_id}"
        rel = self._user_relations.get(key, {"user_id": user_id, "name": user_name, "affinity": 0})
        tl = (text or "").lower()
        if any(w in tl for w in ("спасибо", "класс", "умница", "молодец", "люблю")):
            rel["affinity"] = min(5, int(rel.get("affinity", 0)) + 1)
        if any(w in tl for w in ("дура", "туп", "бесишь", "отстань")):
            rel["affinity"] = max(-5, int(rel.get("affinity", 0)) - 1)
        rel["name"] = user_name or rel.get("name") or str(user_id)
        rel["updated"] = datetime.now().isoformat()
        self._user_relations[key] = rel

    def _get_user_relation_hint(self, chat_id: int, user_id: int) -> str:
        key = f"{chat_id}:{user_id}"
        rel = self._user_relations.get(key)
        if not rel:
            return "новый участник"
        a = int(rel.get("affinity", 0))
        if a >= 3:
            return "очень тёплое доверие"
        if a >= 1:
            return "доброжелательное отношение"
        if a <= -3:
            return "напряжённые отношения, отвечай осторожно"
        if a <= -1:
            return "слегка насторожённое общение"
        return "нейтральное отношение"

    async def _send_assistant_message(self, update: Update, text: str):
        sent = await update.message.reply_text(text)
        self._remember_bot_message(update.effective_chat.id, getattr(sent, "message_id", None))
        self._remember_chat_meta(update, "assistant", text)
        if self._mirror_to_web:
            self._mirror_message(update.effective_chat.id, "assistant", text)

        if self._sticker_enabled:
            # Optional sticker when sticker file_ids configured and emotion-like response.
            if self._sticker_ids and random.random() < 0.18:
                try:
                    sticker_id = random.choice(self._sticker_ids)
                    st = await update.effective_chat.send_sticker(sticker=sticker_id)
                    self._remember_bot_message(update.effective_chat.id, getattr(st, "message_id", None))
                    self._remember_chat_meta(update, "assistant", "[sticker]")
                except Exception:
                    pass

    def _remember_poll(self, update: Update):
        msg = update.message
        poll = msg.poll if msg else None
        chat = update.effective_chat
        if not poll or not chat:
            return
        key = str(chat.id)
        self._recent_polls[key] = {
            "id": poll.id,
            "question": poll.question,
            "options": [getattr(o, "text", "") for o in (poll.options or [])],
            "ts": datetime.now().isoformat(),
        }

    def _pick_poll_option(self, options: List[str], user_text: str) -> int:
        if not options:
            return -1
        tl = (user_text or "").lower()
        for i, opt in enumerate(options):
            o = (opt or "").lower()
            if o and o in tl:
                return i
            if re.search(rf"\b{i+1}\b", tl):
                return i
        return random.randint(0, len(options) - 1)

    async def _on_poll_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_type = str(update.effective_chat.type) if update.effective_chat else ""
        if chat_type in ("group", "supergroup"):
            if not self._group_mode:
                return
            if not self._group_allowed(update.effective_chat.id):
                return
        elif chat_type == "private" and not self._private_mode:
            return
        self._remember_poll(update)
        poll = update.message.poll if update.message else None
        if not poll:
            return
        try:
            if random.random() < 0.35:
                await asyncio.sleep(random.uniform(0.8, 2.2))
                choice = self._pick_poll_option([getattr(o, "text", "") for o in (poll.options or [])], "")
                if choice >= 0:
                    text = f"Я бы выбрала вариант {choice+1}: {poll.options[choice].text} 🌸"
                    sent = await update.message.reply_text(text)
                    self._remember_bot_message(update.effective_chat.id, getattr(sent, "message_id", None))
        except Exception:
            pass

    def _group_allowed(self, chat_id: int) -> bool:
        if not self._allowed_groups:
            # Empty allow-list means "all groups where bot is present".
            return True
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

    @staticmethod
    def _extract_draw_prompt(text: str) -> str:
        tl = (text or "").strip()
        m = re.search(r"(?i)(?:даша[,:\s-]*)?(?:можешь\s+нарисовать|нарисуй|сделай\s+картинку|сгенерируй\s+картинку|создай\s+картинку|хочу\s+картинку)\s*(.*)$", tl)
        if not m:
            return ""
        prompt = (m.group(1) or "").strip(" .,!?:;")
        if prompt:
            return prompt
        if re.search(r"(?i)(нарисуй|картинк|арт|иллюстрац)", tl):
            return tl
        return "нежный портрет в пастельных тонах"

    def _request_generated_image(self, prompt: str) -> Dict[str, Any]:
        if not HAS_REQUESTS:
            return {"ok": False, "error": "requests_unavailable"}
        try:
            created = requests.post(
                "http://127.0.0.1:7777/api/images/jobs",
                json={"prompt": prompt, "style": "universal", "mode": "model", "allow_fallback": False},
                timeout=15,
            )
            if created.status_code != 200:
                return {"ok": False, "error": f"http_{created.status_code}"}
            created_data = created.json()
            job_id = str(created_data.get("job_id") or "").strip()
            if created_data.get("status") != "ok" or not job_id:
                return {"ok": False, "error": created_data.get("error", "job_create_failed")}

            deadline = time_module.time() + 15 * 60
            while time_module.time() < deadline:
                status_r = requests.get(f"http://127.0.0.1:7777/api/images/jobs/{job_id}", timeout=20)
                if status_r.status_code != 200:
                    time_module.sleep(1.5)
                    continue
                payload = status_r.json()
                job = payload.get("job") or {}
                st = str(job.get("status") or "")
                if st == "done":
                    url = str((job.get("result") or {}).get("url") or "").strip()
                    if not url:
                        return {"ok": False, "error": "empty_result_url"}
                    return {"ok": True, "url": f"http://127.0.0.1:7777{url}", "meta": payload}
                if st == "error":
                    err = str(job.get("error") or (job.get("result") or {}).get("dasha_message") or "generation_failed")
                    return {"ok": False, "error": err}
                time_module.sleep(1.8)
            return {"ok": False, "error": "generation_timeout"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _download_generated_image(self, url: str) -> Dict[str, Any]:
        if not HAS_REQUESTS:
            return {"ok": False, "error": "requests_unavailable"}
        try:
            r = requests.get(url, timeout=45)
            ctype = str(r.headers.get("content-type") or "").lower()
            if r.status_code != 200:
                return {"ok": False, "error": f"http_{r.status_code}"}
            if "image/" not in ctype:
                return {"ok": False, "error": "not_image_content"}
            data = r.content or b""
            kind = imghdr.what(None, h=data)
            if not kind and HAS_PIL and Image is not None:
                try:
                    with Image.open(BytesIO(data)) as _:
                        kind = "png"
                except Exception:
                    pass
            if not kind:
                return {"ok": False, "error": "invalid_image_bytes"}
            return {"ok": True, "bytes": data, "mime": ctype, "kind": kind}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _prepare_telegram_image(self, image_bytes: bytes) -> Dict[str, Any]:
        if not image_bytes:
            return {"ok": False, "error": "empty_image"}
        if not HAS_PIL or Image is None:
            return {"ok": True, "bytes": image_bytes, "filename": "daria_generated.png", "mime": "image/png"}
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                rgb = img.convert("RGB")
                out = BytesIO()
                quality = 92
                rgb.save(out, format="JPEG", quality=quality, optimize=True)
                data = out.getvalue()
                # Try to fit Telegram photo practical size comfortably.
                while len(data) > 9 * 1024 * 1024 and quality > 65:
                    out = BytesIO()
                    quality -= 7
                    rgb.save(out, format="JPEG", quality=quality, optimize=True)
                    data = out.getvalue()
                return {"ok": True, "bytes": data, "filename": "daria_generated.jpg", "mime": "image/jpeg"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _request_photo_understanding(self, image_bytes: bytes, caption: str) -> Dict[str, Any]:
        if not HAS_REQUESTS:
            return {"ok": False, "error": "requests_unavailable"}
        try:
            files = {"image": ("photo.jpg", image_bytes, "image/jpeg")}
            data = {"description": caption or ""}
            r = requests.post("http://127.0.0.1:7777/api/senses/see", data=data, files=files, timeout=45)
            if r.status_code != 200:
                return {"ok": False, "error": f"http_{r.status_code}"}
            payload = r.json()
            text = (payload.get("result") or "").strip()
            if not text:
                return {"ok": False, "error": "empty_result"}
            return {"ok": True, "text": text}
        except Exception as e:
            return {"ok": False, "error": str(e)}

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
        user_name = update.effective_user.full_name if update.effective_user else str(user_id)
        # Whitelist by users is enforced in private chats.
        # For groups we rely on allowed group ids + trigger checks.
        if chat_type == "private" and self.allowed_users and user_id not in self.allowed_users:
            return

        self._remember_chat_id(update.effective_chat.id)
        text = update.message.text
        self._chat_last_user_ts[str(update.effective_chat.id)] = datetime.now().isoformat()
        reply_info = self._reply_info(update)
        self._remember_chat_meta(update, "user", text)
        if chat_type in ("group", "supergroup"):
            self._update_user_relation(update.effective_chat.id, user_id, user_name, text)

        if chat_type == "private" and not self._private_mode:
            logger.debug("TG skip message: private_mode disabled")
            return
        if chat_type in ("group", "supergroup"):
            if not self._group_mode:
                logger.debug(
                    f"TG skip message: group_mode disabled (chat_id={update.effective_chat.id})"
                )
                return
            if not self._group_allowed(update.effective_chat.id):
                logger.debug(
                    "TG skip message: group not allowed "
                    f"(chat_id={update.effective_chat.id}, allowed={self._allowed_groups})"
                )
                return
            if not reply_info.get("to_bot") and not self._looks_like_group_trigger(text):
                logger.debug(
                    "TG skip message: no trigger/reply "
                    f"(chat_id={update.effective_chat.id}, text={str(text)[:120]!r})"
                )
                return

        try:
            draw_prompt = self._extract_draw_prompt(text)
            if self._image_gen_enabled and draw_prompt:
                sent_wait = await update.message.reply_text(
                    random.choice([
                        "Хорошо, сейчас попробую нарисовать. Я стараюсь 🌸",
                        "Приняла, рисую... дай мне минутку ✨",
                        "Сейчас сделаю картинку, чуть подожди 🤍",
                    ])
                )
                self._remember_bot_message(update.effective_chat.id, getattr(sent_wait, "message_id", None))
                await update.effective_chat.send_action("upload_photo")
                generated = await asyncio.to_thread(self._request_generated_image, draw_prompt)
                if generated.get("ok"):
                    img = await asyncio.to_thread(self._download_generated_image, generated.get("url"))
                    if img.get("ok"):
                        prepared = await asyncio.to_thread(self._prepare_telegram_image, img.get("bytes") or b"")
                        if not prepared.get("ok"):
                            sent_err = await update.message.reply_text(
                                "Картинка сгенерировалась, но я не смогла подготовить файл для Telegram."
                            )
                            self._remember_bot_message(update.effective_chat.id, getattr(sent_err, "message_id", None))
                            return
                        try:
                            from telegram import InputFile
                            bio = BytesIO(prepared.get("bytes") or b"")
                            bio.seek(0)
                            sent_photo = await update.message.reply_photo(
                                photo=InputFile(bio, filename=str(prepared.get("filename") or "daria_generated.jpg")),
                                caption=random.choice([
                                    "Смотри, что у меня получилось нарисовать 🌸",
                                    "Я нарисовала это для тебя. Надеюсь, понравится ✨",
                                    "Готово. Вот картинка по твоей идее 🤍",
                                ]),
                            )
                            self._remember_bot_message(update.effective_chat.id, getattr(sent_photo, "message_id", None))
                            self._remember_chat_meta(update, "assistant", "[image]")
                            if self._mirror_to_web:
                                self._mirror_message(update.effective_chat.id, "assistant", f"[image] {draw_prompt}")
                        except Exception:
                            try:
                                from telegram import InputFile
                                doc = BytesIO(prepared.get("bytes") or b"")
                                doc.seek(0)
                                sent_doc = await update.message.reply_document(
                                    document=InputFile(doc, filename=str(prepared.get("filename") or "daria_generated.jpg")),
                                    caption="Фото форматом не прошло как photo, отправляю как файл 🌸",
                                )
                                self._remember_bot_message(update.effective_chat.id, getattr(sent_doc, "message_id", None))
                                self._remember_chat_meta(update, "assistant", "[image]")
                            except Exception:
                                sent_err = await update.message.reply_text(
                                    "Картинка готова, но Telegram не принял её даже как файл. Попробуй ещё раз, пожалуйста."
                                )
                                self._remember_bot_message(update.effective_chat.id, getattr(sent_err, "message_id", None))
                    else:
                        sent_err = await update.message.reply_text(
                            "Картинку сгенерировала, но не смогла правильно отправить файл. Можешь повторить запрос?"
                        )
                        self._remember_bot_message(update.effective_chat.id, getattr(sent_err, "message_id", None))
                else:
                    sent_err = await update.message.reply_text(
                        random.choice([
                            "Я попробовала нарисовать, но сейчас не вышло. Давай уточним идею и повторим 🌸",
                            "У меня не получилось собрать хороший рисунок с первого раза. Попробуем ещё раз? ✨",
                            "Ой, тут что-то пошло не так в процессе рисования. Дашь мне ещё попытку? 🤍",
                        ])
                    )
                    self._remember_bot_message(update.effective_chat.id, getattr(sent_err, "message_id", None))
                return

            if "проголос" in (text or "").lower():
                poll_info = self._recent_polls.get(str(update.effective_chat.id))
                if poll_info and poll_info.get("options"):
                    idx = self._pick_poll_option(poll_info.get("options", []), text)
                    if idx >= 0:
                        answer = f"По голосованию «{poll_info.get('question','опрос')}» я бы выбрала: {poll_info['options'][idx]} 🌸"
                        await self._send_assistant_message(update, answer)
                        return

            user_input = self._compose_user_input(text, reply_info)
            use_group_mode = self._group_mode and str(update.effective_chat.type) in ("group", "supergroup")
            if use_group_mode:
                # LLM generation is blocking; move it off the bot event loop.
                result = await asyncio.to_thread(
                    self._process_group_message,
                    update.effective_chat.id,
                    user_id,
                    user_name,
                    user_input
                )
            else:
                # LLM generation is blocking; move it off the bot event loop.
                result = await asyncio.to_thread(self.api.send_message, user_input)

            # Multi-message support
            messages = result.get("messages", [result.get("response", "Ой, что-то пошло не так... 💔")])
            normalized = []
            for m in messages:
                s = (str(m or "")).strip()
                s = re.sub(r"\s*\|\s*$", "", s).strip()
                if "|||" in s:
                    normalized.extend([x.strip() for x in s.split("|||") if x.strip()])
                elif s:
                    normalized.append(s)
            messages = normalized or ["Ой, что-то пошло не так... 💔"]

            if self._mirror_to_web:
                self._mirror_message(update.effective_chat.id, "user", text)

            for i, msg in enumerate(messages):
                if i > 0:
                    await update.effective_chat.send_action("typing")
                    # Keep a tiny pause between multi-part messages without
                    # introducing long delivery lag.
                    await asyncio.sleep(0.2)
                await self._send_assistant_message(update, msg)

        except Exception as e:
            self.api.log(f"Message error: {e}", "error")
            sent = await update.message.reply_text("Извини, у меня сейчас небольшие проблемы... 💭")
            self._remember_bot_message(update.effective_chat.id, getattr(sent, "message_id", None))

    async def _on_photo_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        msg = update.message
        if not chat or not msg:
            return
        chat_type = str(chat.type)
        user_id = update.effective_user.id if update.effective_user else 0
        caption = (msg.caption or "").strip()
        reply_info = self._reply_info(update)

        if chat_type == "private":
            if not self._private_mode:
                return
            if self.allowed_users and user_id not in self.allowed_users:
                return
        elif chat_type in ("group", "supergroup"):
            if not self._group_mode or not self._group_allowed(chat.id):
                return
            need_trigger = not reply_info.get("to_bot")
            if need_trigger:
                if not caption:
                    return
                if not self._looks_like_group_trigger(caption):
                    return
        else:
            return

        if not msg.photo:
            return
        try:
            self._remember_chat_id(chat.id)
            self._chat_last_user_ts[str(chat.id)] = datetime.now().isoformat()
            self._remember_chat_meta(update, "user", caption or "[photo]")
            photo = msg.photo[-1]
            f = await context.bot.get_file(photo.file_id)
            blob = await f.download_as_bytearray()
            result = await asyncio.to_thread(self._request_photo_understanding, bytes(blob), caption)
            if result.get("ok"):
                await self._send_assistant_message(update, result.get("text") or "Я посмотрела фото 🌸")
                if self._mirror_to_web:
                    self._mirror_message(chat.id, "user", "[image] telegram-photo")
            else:
                await self._send_assistant_message(update, "Я увидела фото, но не смогла разобрать детали. Можешь добавить немного текста?")
        except Exception as e:
            self.api.log(f"Photo message error: {e}", "error")

    def _process_group_message(self, chat_id: int, user_id: int, user_name: str, text: str) -> Dict[str, Any]:
        key = str(chat_id)
        history = self._group_histories.get(key, [])
        cleaned_history: List[Dict[str, str]] = []
        for item in history[-40:]:
            role = str(item.get("role") or "").strip()
            content = str(item.get("content") or "").strip()
            if role not in ("user", "assistant") or not content:
                continue
            low = content.lower()
            # Drop stale image-generation failure loops so they don't leak
            # into unrelated future contexts.
            if (
                "попросила нарисовать картинку:" in low
                and "подтверди, что начала рисовать" in low
            ) or (
                "попробовала нарисовать" in low and "не вышло" in low
            ):
                continue
            cleaned_history.append({"role": role, "content": content})
        history = cleaned_history[-16:]
        history.append({"role": "user", "content": text})
        history = history[-20:]
        relation_hint = self._get_user_relation_hint(chat_id, user_id)
        system = {
            "role": "system",
            "content": (
                "Ты Даша. Это отдельный групповой чат Telegram. "
                "Отвечай мягко и дружелюбно, но не используй персональную долговременную память. "
                f"Текущий участник: {user_name}. Отношение: {relation_hint}."
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
