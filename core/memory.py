"""
DARIA Memory v0.8.1
Persistent memory with time awareness
"""

import json
import sqlite3
import hashlib
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("daria")

from .config import get_config


class MemoryType(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


@dataclass
class Memory:
    id: str
    content: str
    memory_type: MemoryType
    importance: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "type": self.memory_type.value,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags
        }


@dataclass
class ConversationTurn:
    user_message: str
    assistant_response: str
    timestamp: datetime = field(default_factory=datetime.now)
    emotion: str = "neutral"
    
    def to_dict(self) -> Dict:
        return {
            "user": self.user_message,
            "assistant": self.assistant_response,
            "timestamp": self.timestamp.isoformat(),
            "emotion": self.emotion
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationTurn':
        return cls(
            user_message=data["user"],
            assistant_response=data["assistant"],
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            emotion=data.get("emotion", "neutral")
        )


class WorkingMemory:
    """Working memory - current conversation with persistence"""
    
    def __init__(self, data_dir: Path, max_turns: int = 30):
        self.max_turns = max_turns
        self.turns: List[ConversationTurn] = []
        self.context: Dict[str, Any] = {}
        self.total_exchanges = 0
        self.last_interaction: Optional[datetime] = None
        
        self._file = data_dir / "working_memory.json"
        self._load()
    
    def _load(self):
        """Load from disk"""
        if self._file.exists():
            try:
                data = json.loads(self._file.read_text(encoding='utf-8'))
                self.turns = [ConversationTurn.from_dict(t) for t in data.get("turns", [])]
                self.total_exchanges = data.get("total_exchanges", len(self.turns))
                self.context = data.get("context", {})
                if data.get("last_interaction"):
                    self.last_interaction = datetime.fromisoformat(data["last_interaction"])
                logger.debug(f"Loaded {len(self.turns)} turns from working memory")
            except Exception as e:
                logger.error(f"Failed to load working memory: {e}")
    
    def _save(self):
        """Save to disk"""
        try:
            data = {
                "turns": [t.to_dict() for t in self.turns],
                "total_exchanges": self.total_exchanges,
                "context": self.context,
                "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None
            }
            self._file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to save working memory: {e}")
    
    def add_turn(self, user_msg: str, assistant_resp: str, emotion: str = "neutral"):
        turn = ConversationTurn(
            user_message=user_msg,
            assistant_response=assistant_resp,
            emotion=emotion
        )
        self.turns.append(turn)
        self.total_exchanges += 1
        self.last_interaction = datetime.now()
        
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]
        
        self._save()
    
    def get_messages_for_llm(self, limit: int = 15) -> List[Dict[str, str]]:
        """Get conversation history for LLM context"""
        messages = []
        for turn in self.turns[-limit:]:
            messages.append({"role": "user", "content": turn.user_message})
            messages.append({"role": "assistant", "content": turn.assistant_response})
        return messages
    
    def get_time_since_last(self) -> Optional[timedelta]:
        """Get time since last interaction"""
        if self.last_interaction:
            return datetime.now() - self.last_interaction
        return None
    
    def get_conversation_summary(self) -> str:
        """Get a summary of recent conversation for context"""
        if not self.turns:
            return ""
        
        recent = self.turns[-5:]
        summary_parts = []
        for turn in recent:
            u = turn.user_message.replace("\n", " ").strip()[:90]
            a = turn.assistant_response.replace("\n", " ").strip()[:90]
            summary_parts.append(f"Пользователь: {u} | Даша: {a}")
        return " | ".join(summary_parts)
    
    def clear(self):
        self.turns = []
        self.context = {}
        self._save()


class LongTermMemory:
    """Long-term memory with SQLite persistence"""
    
    def __init__(self, data_dir: Path):
        self.db_path = data_dir / "memory.db"
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    type TEXT,
                    importance REAL,
                    created_at TEXT,
                    last_accessed TEXT,
                    access_count INTEGER,
                    tags TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_facts (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    confidence REAL,
                    updated_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)
    
    def store(self, memory: Memory):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memories 
                (id, content, type, importance, created_at, last_accessed, access_count, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.id, memory.content, memory.memory_type.value, memory.importance,
                memory.created_at.isoformat(), memory.last_accessed.isoformat(),
                memory.access_count, json.dumps(memory.tags)
            ))
    
    def search(self, query: str, limit: int = 10) -> List[Memory]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM memories WHERE content LIKE ?
                ORDER BY importance DESC, last_accessed DESC LIMIT ?
            """, (f"%{query}%", limit)).fetchall()
            return [self._row_to_memory(r) for r in rows]
    
    def store_fact(self, key: str, value: str, confidence: float = 1.0):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_facts (key, value, confidence, updated_at)
                VALUES (?, ?, ?, ?)
            """, (key, value, confidence, datetime.now().isoformat()))
    
    def get_fact(self, key: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT value FROM user_facts WHERE key = ?", (key,)).fetchone()
            return row[0] if row else None
    
    def get_all_facts(self) -> Dict[str, str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT key, value FROM user_facts").fetchall()
            return {row[0]: row[1] for row in rows}
    
    def set_profile(self, key: str, value: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_profile (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now().isoformat()))
    
    def get_profile(self, key: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT value FROM user_profile WHERE key = ?", (key,)).fetchone()
            return row[0] if row else None
    
    def get_full_profile(self) -> Dict[str, str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT key, value FROM user_profile").fetchall()
            return {row[0]: row[1] for row in rows}
    
    def get_stats(self) -> Dict[str, int]:
        with sqlite3.connect(self.db_path) as conn:
            mem_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            fact_count = conn.execute("SELECT COUNT(*) FROM user_facts").fetchone()[0]
            return {"memories": mem_count, "facts": fact_count}
    
    def _row_to_memory(self, row) -> Memory:
        return Memory(
            id=row["id"],
            content=row["content"],
            memory_type=MemoryType(row["type"]),
            importance=row["importance"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_accessed=datetime.fromisoformat(row["last_accessed"]),
            access_count=row["access_count"],
            tags=json.loads(row["tags"])
        )


class FactExtractor:
    """Extract facts from user messages"""
    
    PATTERNS = {
        "user_name": [
            r"меня зовут (\w+)",
            r"я (\w+)[,.\s]",
            r"моё имя (\w+)",
            r"зови меня (\w+)",
            r"привет[!,.]?\s*(?:я\s+)?(\w+)",
        ],
        "user_age": [
            r"мне (\d+) (?:год|лет|года)"
        ],
        "user_location": [
            r"живу в ([А-Яа-яЁё\s\-]+)",
            r"я из ([А-Яа-яЁё\s\-]+)",
        ],
    }
    
    EXCLUDED_NAMES = {'привет', 'меня', 'мне', 'я', 'как', 'что', 'тут', 'здесь', 'там'}
    
    def extract(self, text: str) -> Dict[str, str]:
        facts = {}
        text_lower = text.lower()
        
        for fact_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    value = match.group(1).strip()
                    if fact_type == "user_name":
                        if value in self.EXCLUDED_NAMES or len(value) < 2:
                            continue
                        value = value.capitalize()
                    facts[fact_type] = value
                    break
        
        return facts


class MemoryManager:
    """Memory Manager with full persistence"""
    
    def __init__(self):
        config = get_config()
        self.data_dir = config.data_dir / "memory"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.working = WorkingMemory(self.data_dir)
        self.long_term = LongTermMemory(self.data_dir)
        self.fact_extractor = FactExtractor()
        
        # Load profile from both facts and profile tables
        self._user_profile = {}
        self._user_profile.update(self.long_term.get_all_facts())
        self._user_profile.update(self.long_term.get_full_profile())
    
    def add_exchange(self, user_msg: str, assistant_resp: str, emotion: str = "neutral"):
        """Add conversation exchange"""
        self.working.add_turn(user_msg, assistant_resp, emotion)
        
        # Extract and save facts
        facts = self.fact_extractor.extract(user_msg)
        for key, value in facts.items():
            self.long_term.store_fact(key, value)
            self.long_term.set_profile(key, value)
            self._user_profile[key] = value
            logger.debug(f"Saved fact: {key}={value}")
    
    def remember(self, content: str, importance: float = 0.5) -> str:
        """Remember something"""
        memory_id = hashlib.md5(f"{content}{datetime.now()}".encode()).hexdigest()[:16]
        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=MemoryType.SEMANTIC,
            importance=importance
        )
        self.long_term.store(memory)
        return memory_id
    
    def recall(self, query: str, limit: int = 5) -> List[Memory]:
        """Recall memories"""
        return self.long_term.search(query, limit)
    
    def get_user_profile(self) -> Dict[str, str]:
        """Get user profile"""
        # Merge facts and profile
        profile = self.long_term.get_all_facts()
        profile.update(self._user_profile)
        return profile
    
    def set_user_profile(self, key: str, value: str):
        """Set user profile value - saves to both tables"""
        self._user_profile[key] = value
        self.long_term.set_profile(key, value)
        self.long_term.store_fact(key, value)
        logger.debug(f"Profile saved: {key}={value}")
    
    def get_user_name(self) -> Optional[str]:
        """Get user name"""
        return self._user_profile.get("user_name") or self.long_term.get_fact("user_name")
    
    def get_context_for_llm(self, limit: int = 15) -> List[Dict[str, str]]:
        """Get conversation context for LLM"""
        return self.working.get_messages_for_llm(limit)
    
    def get_time_context(self) -> Dict[str, Any]:
        """Get time-related context"""
        time_since = self.working.get_time_since_last()
        
        if time_since is None:
            return {"first_conversation": True, "greeting": "Привет! Мы ещё не общались 💕"}
        
        minutes = time_since.total_seconds() / 60
        hours = minutes / 60
        days = hours / 24
        
        if minutes < 5:
            return {"just_talked": True, "comment": ""}
        elif minutes < 30:
            return {"recent": True, "comment": "Мы только недавно болтали!"}
        elif hours < 1:
            return {"short_break": True, "comment": f"Прошло {int(minutes)} минут"}
        elif hours < 24:
            return {"hours_ago": True, "comment": f"Не виделись {int(hours)} часов!"}
        else:
            return {"long_time": True, "comment": f"Целых {int(days)} дней не общались! Я скучала 💕"}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        lt_stats = self.long_term.get_stats()
        return {
            "conversations": self.working.total_exchanges,
            "working_turns": len(self.working.turns),
            "memories": lt_stats["memories"],
            "facts": lt_stats["facts"]
        }
    
    def clear_working(self):
        """Clear working memory"""
        self.working.clear()


# Singleton
_memory: Optional[MemoryManager] = None


def get_memory() -> MemoryManager:
    global _memory
    if _memory is None:
        _memory = MemoryManager()
    return _memory
