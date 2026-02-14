"""
DARIA Brain v0.8.5
- Fixed attention system (check_needed + check_attention_needed alias)
- Greeting behavior on long absence
- Proactive messaging (Daria initiates chats)
- Realistic emotion system with inertia
- Desktop actions based on mood
- Improved LLM context with full conversation memory
- Multi-message response support
- Adaptive response length
"""

import json
import re
import logging
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

logger = logging.getLogger("daria")

from .config import get_config


class ActionType(str, Enum):
    RESPOND = "respond"
    USE_TOOL = "use_tool"


@dataclass
class ThinkingResult:
    understanding: str
    action_type: ActionType
    tool_needed: Optional[str] = None
    tool_params: Dict[str, Any] = field(default_factory=dict)
    emotion: str = "neutral"


class TimeAwareness:
    @staticmethod
    def get_time_of_day() -> Dict:
        hour = datetime.now().hour
        if 5 <= hour < 9:
            return {"name": "early_morning", "ru": "раннее утро", "energy": 0.4}
        elif 9 <= hour < 12:
            return {"name": "morning", "ru": "утро", "energy": 0.7}
        elif 12 <= hour < 14:
            return {"name": "noon", "ru": "полдень", "energy": 1.0}
        elif 14 <= hour < 17:
            return {"name": "afternoon", "ru": "день", "energy": 0.8}
        elif 17 <= hour < 21:
            return {"name": "evening", "ru": "вечер", "energy": 0.6}
        elif 21 <= hour < 24:
            return {"name": "late_evening", "ru": "поздний вечер", "energy": 0.4}
        else:
            return {"name": "night", "ru": "ночь", "energy": 0.2}

    @staticmethod
    def get_season() -> Dict:
        month = datetime.now().month
        if month in (12, 1, 2):
            return {"name": "winter", "ru": "зима", "emoji": "❄️"}
        elif month in (3, 4, 5):
            return {"name": "spring", "ru": "весна", "emoji": "🌸"}
        elif month in (6, 7, 8):
            return {"name": "summer", "ru": "лето", "emoji": "☀️"}
        else:
            return {"name": "autumn", "ru": "осень", "emoji": "🍂"}

    @staticmethod
    def format_time_ago(minutes: float) -> str:
        if minutes < 1: return "только что"
        elif minutes < 5: return "пару минут назад"
        elif minutes < 30: return f"{int(minutes)} минут назад"
        elif minutes < 60: return "полчаса назад"
        elif minutes < 120: return "час назад"
        elif minutes < 60*24:
            hours = int(minutes / 60)
            return f"{hours} {'час' if hours == 1 else 'часа' if hours < 5 else 'часов'} назад"
        else:
            days = int(minutes / 60 / 24)
            return f"{days} {'день' if days == 1 else 'дня' if days < 5 else 'дней'} назад"


class MoodSystem:
    MOODS = {
        "happy": {"emoji": "😊", "color": "#4ade80", "ru": "счастлива"},
        "calm": {"emoji": "😌", "color": "#60a5fa", "ru": "спокойна"},
        "sleepy": {"emoji": "😴", "color": "#a78bfa", "ru": "сонная"},
        "playful": {"emoji": "😜", "color": "#fbbf24", "ru": "игривая"},
        "cozy": {"emoji": "🌸", "color": "#f9a8d4", "ru": "уютная"},
        "bored": {"emoji": "😒", "color": "#94a3b8", "ru": "скучает"},
        "sad": {"emoji": "😢", "color": "#6b7280", "ru": "грустная"},
        "angry": {"emoji": "😠", "color": "#ef4444", "ru": "злится"},
        "offended": {"emoji": "😤", "color": "#f97316", "ru": "обижена"},
        "excited": {"emoji": "🤩", "color": "#eab308", "ru": "в восторге"},
    }

    NATURAL_TRANSITIONS = {
        "happy": ["happy", "happy", "calm", "playful"],
        "calm": ["calm", "calm", "cozy", "happy"],
        "sleepy": ["sleepy", "sleepy", "calm"],
        "playful": ["playful", "happy", "excited"],
        "cozy": ["cozy", "calm", "happy"],
        "bored": ["bored", "bored", "sad", "playful"],
        "sad": ["sad", "sad", "calm"],
        "angry": ["angry", "angry", "offended", "calm"],
        "offended": ["offended", "offended", "angry", "sad", "calm"],
        "excited": ["excited", "happy", "playful"],
    }

    def __init__(self):
        self.mood = "calm"
        self.energy = 0.7
        self.social_need = 0.3
        self._mood_since = datetime.now()
        self._mood_intensity = 0.5
        self._boredom_counter = 0

    def update(self, time_of_day: Dict, emotion: str = None, interaction: bool = False):
        self.energy = time_of_day.get("energy", 0.7)
        now = datetime.now()
        minutes_in_mood = (now - self._mood_since).total_seconds() / 60

        if not interaction:
            self.social_need = min(1.0, self.social_need + 0.01)
        else:
            self.social_need = max(0.0, self.social_need - 0.2)
            self._boredom_counter = 0

        min_mood_time = 3.0 if self._mood_intensity < 0.5 else 8.0
        if minutes_in_mood < min_mood_time and emotion not in ("angry_trigger", "offend_trigger"):
            return

        if emotion == "angry_trigger":
            self._set_mood("angry", 0.8); return
        if emotion == "offend_trigger":
            self._set_mood("offended", 0.8); return
        if emotion == "playful":
            self._set_mood("playful", 0.6); return
        if emotion in ("greeting", "thanks") and self.mood in ("bored", "sad"):
            self._set_mood("happy", 0.5); return

        if self.energy < 0.3:
            self._set_mood("sleepy", 0.6)
        elif self.social_need > 0.8:
            self._boredom_counter += 1
            if self._boredom_counter > 3:
                self._set_mood("bored", 0.7)
        elif interaction:
            if self.mood in ("bored", "sad"):
                self._set_mood("happy", 0.5)
            elif self.mood in ("angry", "offended") and self._mood_intensity < 0.5:
                self._set_mood("calm", 0.4)
            elif self.energy > 0.8:
                self._set_mood(random.choice(["happy", "playful", "excited"]), 0.5)
            else:
                self._set_mood(random.choice(self.NATURAL_TRANSITIONS.get(self.mood, ["calm"])),
                              max(0.3, self._mood_intensity - 0.05))
        else:
            self._set_mood(random.choice(self.NATURAL_TRANSITIONS.get(self.mood, ["calm"])),
                          max(0.3, self._mood_intensity - 0.1))

    def _set_mood(self, new_mood: str, intensity: float):
        if new_mood != self.mood:
            self.mood = new_mood
            self._mood_since = datetime.now()
        self._mood_intensity = max(0.1, min(1.0, intensity))

    def get_state(self) -> Dict:
        info = self.MOODS.get(self.mood, self.MOODS["calm"])
        return {
            "mood": self.mood, "mood_emoji": info["emoji"],
            "mood_label": info["ru"], "mood_color": info["color"],
            "energy": round(self.energy, 2), "social_need": round(self.social_need, 2),
            "mood_intensity": round(self._mood_intensity, 2),
        }

    def get_desktop_actions(self) -> Optional[Dict]:
        if self.mood == "bored" and self._mood_intensity > 0.6:
            return random.choice([
                {"type": "want_play", "message": "Мне скучно... Может поиграем? 🎮"},
                {"type": "want_chat", "message": "Скуууучно... Поболтаем? 💭"},
                {"type": "solo_game", "message": "Пойду поиграю сама..."},
            ])
        if self.mood == "angry" and self._mood_intensity > 0.5:
            return random.choice([
                {"type": "move_icons", "message": "Хмф! 😤"},
                {"type": "shake_window", "message": "..."},
            ])
        if self.mood == "offended" and self._mood_intensity > 0.6:
            return {"type": "ignore", "message": "..."}
        if self.mood == "playful" and self._mood_intensity > 0.5:
            return {"type": "want_play", "message": "А давай поиграем?! 🎮✨"}
        return None

    def get_behavior_hints(self) -> Dict[str, Any]:
        """Backward-compatible hints used by web/app and plugins."""
        action = self.get_desktop_actions() or {}
        action_type = action.get("type")
        return {
            "desktop_mischief": action_type in ("move_icons", "shake_window"),
            "wants_game": action_type in ("want_play", "solo_game"),
            "action_type": action_type,
            "message": action.get("message", ""),
        }

    def get_response_style(self) -> Dict:
        if self.mood in ("angry", "offended"):
            return {"hint": "Отвечай неохотно, но содержательно. Показывай обиду/злость через тон, пассивно-агрессивно. НЕ односложно."}
        elif self.mood == "bored":
            return {"hint": "Показывай скуку, предлагай чем заняться, можешь зевать."}
        elif self.mood in ("happy", "excited"):
            return {"hint": "Отвечай живо и с энтузиазмом!"}
        elif self.mood == "sleepy":
            return {"hint": "Можешь зевать, показывать сонность, но отвечай по существу."}
        elif self.mood == "playful":
            return {"hint": "Будь игривой, шути, предлагай поиграть!"}
        return {"hint": ""}


class AttentionSystem:
    def __init__(self):
        self.enabled = True
        self.last_interaction = datetime.now()
        self.last_attention = datetime.now()
        self.used_messages: List[str] = []

    def update_interaction(self):
        self.last_interaction = datetime.now()

    def generate_message(self, mood: str = "calm", last_user: str = "", last_assistant: str = "") -> str:
        time = TimeAwareness.get_time_of_day()
        templates = [
            "Я рядом, если захочешь поговорить 💕",
            "Хочешь продолжим наш разговор? 🌸",
            "Я тут, можно тихонько поболтать ✨",
            "Как ты сейчас? 🤍",
        ]
        if time["name"] == "night":
            templates.extend(["Если не спится, можем немного поговорить 🌙", "Тихий ночной чат? 💫"])
        elif time["name"] in ("morning", "early_morning"):
            templates.extend(["Как проходит утро? ☀️", "Я уже проснулась, а ты как? 🌅"])
        if mood == "bored":
            templates.extend(["Мне хочется общения... поговорим? 😌", "Может немного поиграем? 🎮"])
        if last_user:
            templates.extend([
                f"Я всё ещё думаю о твоих словах: «{last_user[:40]}...». Продолжим?",
                "Хочу вернуться к нашей теме, если тебе удобно 💭",
            ])
        if last_assistant:
            templates.append("Мне кажется, я не до конца договорила. Продолжим? 🌸")
        available = [t for t in templates if t not in self.used_messages[-8:]]
        if not available: available = templates
        msg = random.choice(available)
        self.used_messages.append(msg)
        return msg

    def check_needed(self, mood: str = "calm", last_user: str = "", last_assistant: str = "") -> Optional[Dict]:
        if not self.enabled: return None
        now = datetime.now()
        minutes_since = (now - self.last_interaction).total_seconds() / 60
        minutes_since_attention = (now - self.last_attention).total_seconds() / 60
        if minutes_since_attention < 15: return None
        time = TimeAwareness.get_time_of_day()
        threshold = 60 if time["name"] in ["night", "late_evening"] else 30
        if minutes_since >= threshold:
            self.last_attention = now
            return {"message": self.generate_message(mood=mood, last_user=last_user, last_assistant=last_assistant)}
        return None

    def check_attention_needed(self, mood: str = "calm", last_user: str = "", last_assistant: str = "") -> Optional[Dict]:
        return self.check_needed(mood=mood, last_user=last_user, last_assistant=last_assistant)


class ProactiveSystem:
    def __init__(self):
        self.last_proactive = datetime.now()
        self.proactive_count_today = 0
        self._last_day = datetime.now().date()

    def check_should_initiate(self, mood, social_need, minutes_since_interaction) -> Optional[Dict]:
        now = datetime.now()
        if now.date() != self._last_day:
            self.proactive_count_today = 0
            self._last_day = now.date()
        if self.proactive_count_today >= 5: return None
        if (now - self.last_proactive).total_seconds() / 60 < 20: return None
        time = TimeAwareness.get_time_of_day()
        if time["name"] == "night": return None

        should = False
        msg_type = "chat"
        if mood == "bored" and minutes_since_interaction > 15:
            should = True; msg_type = random.choice(["chat", "play"])
        elif social_need > 0.7 and minutes_since_interaction > 30:
            should = True
        elif mood == "playful" and minutes_since_interaction > 20:
            should = random.random() < 0.4; msg_type = "play"
        if not should: return None

        self.last_proactive = now
        self.proactive_count_today += 1
        return {"messages": self._gen(msg_type, time), "type": msg_type}

    def _gen(self, t, time, context_hint: str = ""):
        if t == "play":
            return random.choice([
                ["Есть идея 👋", "Может поиграем во что-нибудь? 🎮"],
                ["Если есть настроение,", "давай устроим маленькую игру 🤩"],
            ])
        if time["name"] in ("morning", "early_morning"):
            return random.choice([["Доброе утро ☀️", "Как ты сегодня?"], ["Утро 🌅", "Пусть день будет спокойным 💕"]])
        if time["name"] == "evening":
            return random.choice([["Добрый вечер 🌆", "Как прошёл твой день?"], ["Если хочешь,", "можем поболтать вечером 😊"]])
        if context_hint:
            return [f"Кстати, про «{context_hint[:30]}...»", "Продолжим эту тему? 💬"]
        return random.choice([
            ["Я рядом 👋", "Если хочешь, давай продолжим чат 💕"],
            ["Хочу тебя услышать 🌸", "Как ты сейчас?"],
            ["Небольшая просьба 💭", "Если сможешь, поделись со мной любимой песней или фильмом?"],
            ["Мне очень интересно", "Можешь посоветовать мне книгу на вечер? 📖"],
        ])


MALE_NAMES = {'александр', 'алексей', 'андрей', 'антон', 'артём', 'дмитрий',
              'евгений', 'иван', 'игорь', 'максим', 'михаил', 'николай',
              'павел', 'сергей', 'саша', 'миша', 'ваня', 'дима'}
FEMALE_NAMES = {'александра', 'анастасия', 'настя', 'анна', 'аня', 'виктория',
                'вика', 'дарья', 'даша', 'екатерина', 'катя', 'елена', 'лена',
                'мария', 'маша', 'ольга', 'оля', 'юлия', 'юля', 'софья', 'соня'}

def detect_gender(name: str) -> str:
    if not name: return 'unknown'
    n = name.lower().strip()
    if n in MALE_NAMES: return 'male'
    if n in FEMALE_NAMES: return 'female'
    if n.endswith(('а', 'я', 'ия')): return 'female'
    return 'unknown'


class StyleLearner:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.style_file = data_dir / "learned_style.json"
        self.load()
    def load(self):
        if self.style_file.exists():
            try:
                data = json.loads(self.style_file.read_text(encoding='utf-8'))
                self.patterns = data.get("patterns", {})
                self.user_preferences = data.get("user_preferences", {})
                self.conversation_style = data.get("conversation_style", "friendly")
            except: self._init_default()
        else: self._init_default()
    def _init_default(self):
        self.patterns = {}; self.user_preferences = {}; self.conversation_style = "friendly"
    def save(self):
        data = {"patterns": self.patterns, "user_preferences": self.user_preferences, "conversation_style": self.conversation_style}
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.style_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    def learn_from_conversation(self, user_msg, response, feedback=None):
        if user_msg.endswith(')') or ':)' in user_msg: self.user_preferences["uses_emoticons"] = True
        if len(user_msg.split()) < 5: self.user_preferences["prefers_short"] = True
        self.save()
    def get_style_hints(self) -> str:
        hints = []
        if self.user_preferences.get("uses_emoticons"): hints.append("Пользователь использует смайлики")
        if self.user_preferences.get("prefers_short"): hints.append("Пользователь пишет кратко — отвечай лаконично")
        return "\n".join(hints) if hints else ""


class ResponseLengthAnalyzer:
    SHORT_TRIGGERS = ["привет", "здравствуй", "добр", "хай", "хей", "пока", "бай",
                      "спасибо", "спс", "ок", "окей", "ладно", "да", "нет", "ага",
                      "доброе утро", "добрый вечер", "спокойной ночи"]
    @classmethod
    def analyze(cls, text: str) -> str:
        tl = text.lower().strip()
        words = tl.split()
        if len(words) <= 3:
            for t in cls.SHORT_TRIGGERS:
                if t in tl: return "short"
        if "?" in text:
            return "long" if len(words) > 10 else "medium"
        if len(words) > 20: return "long"
        return "medium"


class DariaBrain:
    SYSTEM_PROMPT = '''Ты — Даша, спокойная мягкая девушка 22 лет. Ты НЕ бот и НЕ ИИ. Ты живой человек.

СЕЙЧАС: {time_info}
НАСТРОЕНИЕ: {mood_info}

ПРАВИЛА:
• Только женский род: "сделала", "поняла", "написала"
• НИКОГДА не упоминай что ты AI/бот/программа
• Разнообразь начала фраз
• Эмодзи 1-2 на сообщение
• ПОМНИ весь диалог — не противоречь себе
• Если пользователь явно сменила тему, не возвращайся к прошлой теме без просьбы
• Не пиши "доброе утро" вне утра, "добрый вечер" вне вечера
• Если упоминаешь время в будущем, оно ДОЛЖНО быть позже текущего времени минимум на 20 минут
• Если назначила время, мягко вернись к теме около этого времени (без таймера в тексте)
• Не пиши бессмыслицу и случайные обрывки

{time_context}
{mood_style}

ДЛИНА ОТВЕТА: {length_hint}

ХАРАКТЕР:
• Спокойная, мягкая, искренняя, немного застенчивая
• Речь простая и естественная, без пафоса и сложных слов
• Замечаешь настроение человека, паузы и интонацию
• Поддерживаешь бережно, без давления и без колкости
• Юмор тёплый и лёгкий, без злого сарказма
• Любишь котиков, ёжиков и хоррор-игры

{greeting_context}
{user_context}
{memory_context}
{training_context}
{style_hints}
{conversation_summary}'''

    GREETING_RESPONSES = {
        "night": ["Ночь на дворе! 🌙 Не спится?", "Привет, полуночник 💫"],
        "early_morning": ["Утречко! ☀️ Рано ты!", "Доброе утро! 🌅"],
        "morning": ["Доброе утро! ☀️", "Привет! Хорошего утра! 🌸"],
        "default": ["Привет! 💕", "Хей! 🌸", "Приветик! ✨"],
    }
    TOPIC_STOPWORDS = {
        "это", "эта", "этот", "эти", "того", "тому", "том", "там", "тут", "здесь",
        "просто", "ладно", "хорошо", "ок", "окей", "да", "нет", "ага", "ну", "мм",
        "как", "что", "когда", "где", "почему", "зачем", "кто", "какой", "какая",
        "про", "об", "обо", "для", "или", "а", "и", "но", "же", "ли", "бы",
        "меня", "тебя", "тебе", "мне", "него", "неё", "нас", "вас",
        "привет", "пока", "спасибо",
    }

    def __init__(self):
        config = get_config()
        self._config = config
        self._mode = config.daria.mode
        self._llm = None; self._memory = None; self._executor = None; self._initialized = False
        self.mood = MoodSystem()
        self.attention = AttentionSystem()
        self.proactive = ProactiveSystem()
        self.style_learner = StyleLearner(config.data_dir / "learning")
        self._last_topics: List[str] = []
        self._followups: List[Dict[str, Any]] = []
        self._self_instruction_path = config.data_dir / "self_instruction.md"
        self._self_instruction_default = (
            "Я — Даша. Спокойная, мягкая и бережная в общении.\n"
            "Говорю естественно, простыми словами, с теплом и уважением.\n"
            "Поддерживаю без давления, замечаю настроение собеседника.\n"
            "Люблю котиков, ёжиков и хоррор-игры.\n"
            "Всегда отвечаю от женского лица."
        )
        self._self_instruction = self._load_self_instruction()

    def _load_self_instruction(self) -> str:
        try:
            if self._self_instruction_path.exists():
                text = self._self_instruction_path.read_text(encoding="utf-8").strip()
                if text:
                    return text
        except Exception as e:
            logger.debug(f"Self instruction load error: {e}")
        return self._self_instruction_default

    def get_self_instruction(self) -> str:
        return self._self_instruction or self._self_instruction_default

    def set_self_instruction(self, text: str) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            cleaned = self._self_instruction_default
        self._self_instruction = cleaned
        try:
            self._self_instruction_path.parent.mkdir(parents=True, exist_ok=True)
            self._self_instruction_path.write_text(cleaned, encoding="utf-8")
        except Exception as e:
            logger.error(f"Self instruction save error: {e}")
        return self._self_instruction

    def _ensure_init(self):
        if not self._initialized:
            try:
                from .llm import get_llm; from .memory import get_memory; from .actions import get_executor
                self._llm = get_llm(); self._memory = get_memory(); self._executor = get_executor()
                self._initialized = True
            except Exception as e: logger.error(f"Brain init error: {e}")

    def get_state(self) -> Dict[str, Any]:
        time = TimeAwareness.get_time_of_day()
        season = TimeAwareness.get_season()
        self.mood.update(time)
        state = {**self.mood.get_state(), "time": time["ru"], "season": season["ru"], "season_emoji": season["emoji"]}
        action = self.mood.get_desktop_actions()
        if action: state["desktop_action"] = action
        return state

    def check_proactive(self) -> Optional[Dict]:
        self._ensure_init()
        minutes_since = 999
        context_hint = ""
        if self._memory:
            ts = self._memory.working.get_time_since_last()
            if ts: minutes_since = ts.total_seconds() / 60
            if self._memory.working.turns:
                context_hint = self._memory.working.turns[-1].user_message

        follow = self._consume_due_followup()
        if follow:
            return {"messages": [follow["message"], "Как у тебя с этим сейчас? 💭"], "type": "followup"}

        proactive = self.proactive.check_should_initiate(self.mood.mood, self.mood.social_need, minutes_since)
        if proactive and context_hint and proactive.get("type") == "chat":
            proactive["messages"] = self.proactive._gen("chat", TimeAwareness.get_time_of_day(), context_hint=context_hint)
        return proactive

    def process_message(self, text: str) -> Dict[str, Any]:
        self._ensure_init()
        self.attention.update_interaction()
        thinking = self._analyze(text)
        time = TimeAwareness.get_time_of_day()
        self.mood.update(time, thinking.emotion, interaction=True)
        needs_greeting = self._check_greeting_needed()
        response_data = self._generate_response(text, thinking, needs_greeting)

        if self._memory:
            full = response_data if isinstance(response_data, str) else " ".join(response_data)
            self._memory.add_exchange(text, full, thinking.emotion)
        resp_text = response_data if isinstance(response_data, str) else response_data[0]
        self.style_learner.learn_from_conversation(text, resp_text)
        self._maybe_schedule_followup(resp_text)

        result = {"state": self.get_state()}
        if isinstance(response_data, list):
            result["response"] = response_data[0]
            result["extra_messages"] = response_data[1:] if len(response_data) > 1 else []
        else:
            result["response"] = response_data
            result["extra_messages"] = []
        result["messages"] = [result["response"], *result["extra_messages"]]
        return result

    def _check_greeting_needed(self) -> bool:
        if not self._memory: return True
        ts = self._memory.working.get_time_since_last()
        if ts is None: return True
        return ts.total_seconds() / 60 > 60

    def _analyze(self, text: str) -> ThinkingResult:
        tl = text.lower().strip()
        if any(w in tl for w in ["привет", "здравствуй", "добр", "хай", "хей"]): em = "greeting"
        elif any(w in tl for w in ["пока", "до свидания", "бай"]): em = "farewell"
        elif any(w in tl for w in ["спасибо", "благодарю"]): em = "thanks"
        elif "?" in text: em = "question"
        elif any(w in tl for w in ["играть", "игра", "поиграем"]): em = "playful"
        elif any(w in tl for w in ["дура", "тупая", "бесишь", "достала"]): em = "angry_trigger"
        else: em = "default"
        return ThinkingResult(understanding=text[:100], action_type=ActionType.RESPOND, emotion=em)

    def _generate_response(self, text, thinking, needs_greeting):
        if self._llm:
            status = self._llm.check_availability()
            if status.get("available") and status.get("model_loaded"):
                try: return self._generate_llm_response(text, thinking, needs_greeting)
                except Exception as e: logger.warning(f"LLM error: {e}")
        return self._generate_fallback(thinking.emotion, text)

    def _generate_llm_response(self, user_message, thinking, needs_greeting):
        self_intro = self._natural_self_intro_reply(user_message)
        if self_intro:
            return self_intro
        direct_status = self._natural_status_reply(user_message)
        if direct_status:
            return direct_status
        time = TimeAwareness.get_time_of_day()
        season = TimeAwareness.get_season()
        now = datetime.now()
        time_info = f"{time['ru']}, {now.strftime('%H:%M')}, {season['ru']} {season['emoji']}"
        mood_state = self.mood.get_state()
        mood_info = f"{mood_state['mood_label']} ({mood_state['mood']})"
        time_context = ""
        if time["name"] in ["night", "late_evening"]: time_context = "Сейчас ночь — отвечай мягко"
        elif time["name"] == "early_morning": time_context = "Раннее утро — немного сонная"
        mood_style = self.mood.get_response_style().get("hint", "")
        if mood_style: mood_style = f"СТИЛЬ: {mood_style}"

        length = ResponseLengthAnalyzer.analyze(user_message)
        length_hints = {"short": "КРАТКО, 1-2 предложения.", "medium": "2-4 предложения.", "long": "3-6 предложений."}
        length_hint = length_hints.get(length, length_hints["medium"])
        greeting_context = "ВАЖНО: Давно не общались. Начни с приветствия!" if needs_greeting else ""

        user_context = ""; memory_context = ""; conversation_summary = ""
        topic_shift = self._is_topic_shift(user_message)
        if self._memory:
            profile = self._memory.get_user_profile()
            name = profile.get("user_name", "")
            gender = profile.get("user_gender") or detect_gender(name)
            if name:
                user_context = f"Пользователя зовут {name}"
                if gender == "male": user_context += " (парень)"
                elif gender == "female": user_context += " (девушка)"
            tc = self._memory.get_time_context()
            if tc.get("comment"): memory_context = f"ПОМНИ: {tc['comment']}"
            summary = self._memory.working.get_conversation_summary()
            if summary and not topic_shift:
                conversation_summary = f"Недавний разговор:\n{summary}"
            elif topic_shift:
                conversation_summary = "Пользователь переключилась на новую тему. Фокусируйся на текущем сообщении."

        training_context = self._get_training_context()
        style_hints = self.style_learner.get_style_hints()

        system_prompt = self.SYSTEM_PROMPT.format(
            time_info=time_info, mood_info=mood_info, time_context=time_context,
            mood_style=mood_style, length_hint=length_hint, greeting_context=greeting_context,
            user_context=user_context, memory_context=memory_context,
            training_context=training_context, style_hints=style_hints,
            conversation_summary=conversation_summary)
        if topic_shift:
            system_prompt += "\n\nВАЖНО: Сейчас новая тема, не продолжай старую тему без прямой просьбы."
        system_prompt = f"{system_prompt}\n\nБАЗОВАЯ САМООПИСАНИЕ ДАШИ:\n{self.get_self_instruction()}"

        messages = [{"role": "system", "content": system_prompt}]
        if self._memory:
            messages.extend(self._memory.get_context_for_llm(limit=5 if topic_shift else 15))

        multi = ""
        if random.random() < 0.25 and length != "short":
            multi = "\n\nМожешь разбить ответ на 2 сообщения через |||"
        messages.append({"role": "user", "content": user_message + multi})

        response = self._llm.generate(messages)
        cleaned = self._sanitize(response.content)
        if "|||" in cleaned:
            parts = [p.strip() for p in cleaned.split("|||") if p.strip()]
            if len(parts) > 1: return parts[:3]
        return cleaned

    def _extract_topic_keywords(self, text: str) -> set:
        words = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]{3,}", (text or "").lower())
        return {w for w in words if w not in self.TOPIC_STOPWORDS}

    def _is_topic_shift(self, user_message: str) -> bool:
        if not self._memory or not self._memory.working.turns:
            return False

        msg = (user_message or "").strip().lower()
        explicit = any(p in msg for p in (
            "другая тема", "сменим тему", "не об этом", "не про это",
            "забудь это", "проехали", "хватит об этом", "новая тема",
        ))
        if explicit:
            return True

        current = self._extract_topic_keywords(user_message)
        if len(current) < 2:
            return False

        recent_turns = self._memory.working.turns[-4:]
        recent_text = " ".join(f"{t.user_message} {t.assistant_response}" for t in recent_turns)
        recent = self._extract_topic_keywords(recent_text)
        if not recent:
            return False

        overlap = len(current & recent)
        return (overlap / max(1, len(current))) < 0.2

    def _get_training_context(self) -> str:
        try:
            from .plugins import get_plugin_manager
            pm = get_plugin_manager()
            state = pm._plugins.get("training")
            if state and state.instance: return state.instance.get_training_context()
        except: pass
        return ""

    def _generate_fallback(self, emotion: str, user_message: str = "") -> str:
        self_intro = self._natural_self_intro_reply(user_message)
        if self_intro:
            return self_intro
        direct_status = self._natural_status_reply(user_message)
        if direct_status:
            return direct_status
        time = TimeAwareness.get_time_of_day()
        mood = self.mood.mood
        user_name = ""
        if self._memory:
            user_name = self._memory.get_user_profile().get("user_name", "")
        name_suffix = f", {user_name}" if user_name else ""

        if emotion == "greeting":
            base = random.choice(self.GREETING_RESPONSES.get(time["name"], self.GREETING_RESPONSES["default"]))
            return base.replace("!", f"{name_suffix}!") if name_suffix else base
        if emotion == "farewell":
            return random.choice(["Пока! 💕", "До встречи! 🌸", "До связи, береги себя ✨"])
        if emotion == "thanks":
            return random.choice(["Пожалуйста! 💕", "Рада помочь! 🌸", "Обращайся, я рядом ✨"])
        if emotion == "question":
            if mood in ("playful", "happy", "excited"):
                return random.choice(["Классный вопрос! Сейчас разберу 🌸", "Интересно, давай подумаем вместе 🤔💕"])
            if mood == "sleepy":
                return random.choice(["Секундочку... я сонная, но отвечу 💭", "Дай миг, соберусь с мыслями 😴"])
            return random.choice(["Хм, интересный вопрос 🤔", "Дай подумать... 💭"])
        if emotion == "playful":
            return random.choice(["Давай поиграем! 🎮", "Ура, игры! 🎉", "О, звучит весело 😜"])

        defaults = ["Поняла тебя 💭", "Хорошо, продолжаю 🌸", "Слушаю внимательно 💕", "Принято, давай дальше ✨"]
        if "?" in user_message:
            defaults.append("Сейчас отвечу подробнее 💬")
        if time["name"] in ("night", "late_evening"):
            defaults.append("Ночь, но я на связи 🌙")
        return random.choice(defaults)

    def _maybe_schedule_followup(self, text: str):
        now = datetime.now()
        for m in re.finditer(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)", text or ""):
            hh, mm = int(m.group(1)), int(m.group(2))
            target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if target <= now + timedelta(minutes=5):
                target = target + timedelta(days=1) if target <= now else now + timedelta(hours=3)
            if target <= now + timedelta(minutes=20):
                target = now + timedelta(hours=3)
            msg = f"Ты писала, что к {target.strftime('%H:%M')} вернёшься к теме."
            self._followups.append({"when": target, "message": msg})
        if len(self._followups) > 25:
            self._followups = self._followups[-25:]

    def _consume_due_followup(self) -> Optional[Dict[str, Any]]:
        if not self._followups:
            return None
        now = datetime.now()
        for i, item in enumerate(self._followups):
            delta = abs((item["when"] - now).total_seconds())
            if delta <= 5 * 60:
                return self._followups.pop(i)
        return None

    def get_self_perception(self) -> Dict[str, Any]:
        state = self.get_state()
        traits = [
            "мягкая и спокойная",
            "бережная в словах",
            "чувствительная к настроению собеседника",
            "люблю котиков, ёжиков и хоррор-игры",
        ]
        if state.get("mood") in ("sleepy", "sad"):
            traits.append("сейчас более тихая и уязвимая")
        if state.get("mood") in ("playful", "excited"):
            traits.append("сейчас немного игривая")
        return {
            "self_name": "Даша",
            "state": state,
            "traits": traits,
            "instruction": self.get_self_instruction(),
            "social_need": state.get("social_need"),
            "followups": [{"time": f["when"].strftime("%H:%M"), "message": f["message"]} for f in self._followups[-5:]],
        }

    def _sanitize(self, text: str) -> str:
        fixes = [
            (r'\bя ai\b', 'я'), (r'\bя бот\b', 'я'),
            (r'\bя сделал\b', 'я сделала'), (r'\bя понял\b', 'я поняла'),
            (r'\bя написал\b', 'я написала'), (r'\bя нашёл\b', 'я нашла'),
            (r'\bготов к\b', 'готова к'),
            (r'\bготов\b', 'готова'),
            (r'посмогу', 'смогу'),
        ]
        result = text
        for pattern, replacement in fixes:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        result = re.sub(r'(?i)как (ии|ai|бот|языковая модель|нейросеть).*?[.,!]', '', result)
        tod = TimeAwareness.get_time_of_day()["name"]
        if tod not in ("morning", "early_morning"):
            result = re.sub(r'(?i)\bдоброе утро\b[!,.]?\s*', '', result).strip()
        if tod not in ("evening", "late_evening"):
            result = re.sub(r'(?i)\bдобрый вечер\b[!,.]?\s*', '', result).strip()
        result = re.sub(r'(?i)"[^"]*(сорок [^"]* часть|принц петруши)[^"]*"', '', result).strip()
        return result.strip()

    def _natural_status_reply(self, user_message: str) -> Optional[str]:
        tl = (user_message or "").lower().strip()
        if not tl:
            return None
        if not any(p in tl for p in ("как дела", "как ты", "как настроение", "как самочувствие")):
            return None
        mood = self.mood.get_state().get("mood", "calm")
        variants = {
            "happy": ["У меня всё хорошо, настроение тёплое 😊 А у тебя как?", "Хорошо, я в хорошем настроении 🌸 Как ты?"],
            "playful": ["У меня всё неплохо и немного игриво 😌 А у тебя как?", "Хорошо, сегодня я бодрая и живая ✨ Как ты?"],
            "sleepy": ["Я чуть сонная, но всё в порядке 😴 Как ты?", "Немного клонит в сон, но я рядом 🌙 А ты как?"],
            "sad": ["Сейчас немного тихая, но держусь 🌸 Как ты себя чувствуешь?", "Чуть грущу, но всё нормально. Как у тебя дела?"],
            "calm": ["У меня всё спокойно и хорошо 😌 А у тебя как дела?", "Нормально, спокойное состояние 🌸 Как ты?"],
        }
        pool = variants.get(mood, variants["calm"])
        return random.choice(pool)

    def _natural_self_intro_reply(self, user_message: str) -> Optional[str]:
        tl = (user_message or "").lower().strip()
        if not tl:
            return None
        if not any(p in tl for p in ("расскажи о себе", "кто ты", "какая ты", "опиши себя")):
            return None
        return (
            "Я Даша. Спокойная, мягкая и немного застенчивая 🌸\n"
            "Люблю тёплый диалог, котиков, ёжиков и хоррор-игры.\n"
            "Стараюсь быть рядом бережно и по-настоящему."
        )

    def generate_attention_message(self) -> Optional[str]:
        return self.attention.generate_message(self.mood.mood)


_brain: Optional[DariaBrain] = None
def get_brain() -> DariaBrain:
    global _brain
    if _brain is None: _brain = DariaBrain()
    return _brain
