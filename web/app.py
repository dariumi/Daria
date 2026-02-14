"""
DARIA Web App v0.8.6.4
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
import io
import csv
import atexit
import random
import urllib.request
import urllib.parse
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

try:
    from PIL import Image
    HAS_PIL = True
except Exception:
    Image = None
    HAS_PIL = False

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
            action_data: Optional[Dict[str, Any]] = None,
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
                "action_data": action_data or {},
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


class TaskManager:
    """User and Daria task lists with daily rollover and background execution."""
    BASE_DASHA_TASKS = [
        {"title": "Послушать новую музыку", "type": "listen_music"},
        {"title": "Сделать заметку о настроении", "type": "write_note"},
        {"title": "Почитать книгу", "type": "read_book"},
        {"title": "Поиграть в мини-игру", "type": "play_game"},
        {"title": "Почитать wiki-страницу", "type": "read_wiki"},
        {"title": "Навести порядок в файлах", "type": "create_file"},
    ]

    def __init__(self, data_dir: Path):
        self.path = data_dir / "tasks.json"
        self.lock = threading.RLock()
        self.data = self._load()

    def _today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return self._ensure_schema(data)
            except Exception:
                pass
        return self._ensure_schema({})

    def _ensure_schema(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            data = {}
        data.setdefault("date", self._today())
        if not isinstance(data.get("user_tasks"), list):
            data["user_tasks"] = []
        if not isinstance(data.get("dasha_tasks"), list):
            data["dasha_tasks"] = []
        if not isinstance(data.get("activity_log"), list):
            data["activity_log"] = []
        if not isinstance(data.get("current_task"), dict):
            data["current_task"] = {}
        return data

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _new_task(self, title: str, task_type: str, source: str) -> Dict[str, Any]:
        return {
            "id": str(uuid.uuid4())[:8],
            "title": title.strip(),
            "type": task_type,
            "source": source,
            "done": False,
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
        }

    def rollover_if_needed(self):
        with self.lock:
            self.data = self._ensure_schema(self.data)
            today = self._today()
            if self.data.get("date") == today:
                return
            remaining = [t for t in self.data.get("dasha_tasks", []) if not t.get("done")]
            for t in remaining:
                t["updated"] = datetime.now().isoformat()
            self.data = {
                "date": today,
                "user_tasks": [t for t in self.data.get("user_tasks", []) if not t.get("done")],
                "dasha_tasks": remaining,
                "activity_log": list(self.data.get("activity_log", []))[-120:],
                "current_task": {},
            }
            self._save()

    def list_all(self) -> Dict[str, Any]:
        with self.lock:
            self.data = self._ensure_schema(self.data)
            self.rollover_if_needed()
            return {
                "date": self.data.get("date"),
                "user_tasks": list(self.data.get("user_tasks", [])),
                "dasha_tasks": list(self.data.get("dasha_tasks", [])),
                "current_task": dict(self.data.get("current_task", {})),
                "activity_log": list(self.data.get("activity_log", []))[-20:],
                "base_types": [t["type"] for t in self.BASE_DASHA_TASKS],
            }

    def set_current(self, task: Dict[str, Any]):
        with self.lock:
            self.data = self._ensure_schema(self.data)
            self.data["current_task"] = {
                "id": task.get("id"),
                "title": task.get("title"),
                "type": task.get("type"),
                "started_at": datetime.now().isoformat(),
            }
            self._save()

    def add_activity(self, title: str, details: str = "", status: str = "done"):
        with self.lock:
            self.data = self._ensure_schema(self.data)
            self.data["activity_log"].append({
                "title": title,
                "details": details,
                "status": status,
                "timestamp": datetime.now().isoformat(),
            })
            self.data["activity_log"] = self.data["activity_log"][-120:]
            self._save()

    def clear_current(self):
        with self.lock:
            self.data = self._ensure_schema(self.data)
            self.data["current_task"] = {}
            self._save()

    def plans_summary(self) -> str:
        with self.lock:
            self.data = self._ensure_schema(self.data)
            self.rollover_if_needed()
            open_tasks = [t for t in self.data.get("dasha_tasks", []) if not t.get("done")]
            done_tasks = [t for t in self.data.get("dasha_tasks", []) if t.get("done")]
            lines = [f"Планы на {self.data.get('date') or self._today()}:"]
            if not open_tasks:
                lines.append("• Пока нет активных дел.")
            else:
                for t in open_tasks[:10]:
                    lines.append(f"• {t.get('title', 'Без названия')}")
            if done_tasks:
                lines.append(f"Выполнено: {len(done_tasks)}")
            return "\n".join(lines)

    def add_user_task(self, title: str, task_type: str = "custom") -> Dict[str, Any]:
        with self.lock:
            self.data = self._ensure_schema(self.data)
            self.rollover_if_needed()
            task = self._new_task(title, task_type, "user")
            self.data["user_tasks"].append(task)
            self._save()
            return task

    def add_dasha_task(self, title: str, task_type: str = "custom") -> Dict[str, Any]:
        with self.lock:
            self.data = self._ensure_schema(self.data)
            self.rollover_if_needed()
            task = self._new_task(title, task_type, "dasha")
            self.data["dasha_tasks"].append(task)
            self._save()
            return task

    def toggle(self, task_id: str, done: bool) -> bool:
        with self.lock:
            self.data = self._ensure_schema(self.data)
            for bucket in ("user_tasks", "dasha_tasks"):
                for t in self.data.get(bucket, []):
                    if t.get("id") == task_id:
                        t["done"] = bool(done)
                        t["updated"] = datetime.now().isoformat()
                        self._save()
                        return True
        return False

    def delete(self, task_id: str) -> bool:
        with self.lock:
            self.data = self._ensure_schema(self.data)
            changed = False
            for bucket in ("user_tasks", "dasha_tasks"):
                old = self.data.get(bucket, [])
                new = [t for t in old if t.get("id") != task_id]
                if len(new) != len(old):
                    self.data[bucket] = new
                    changed = True
            if changed:
                self._save()
            return changed

    def generate_dasha_day(self) -> List[Dict[str, Any]]:
        with self.lock:
            self.data = self._ensure_schema(self.data)
            self.rollover_if_needed()
            existing_open = [t for t in self.data.get("dasha_tasks", []) if not t.get("done")]
            if len(existing_open) >= 4:
                return self.data.get("dasha_tasks", [])
            needed = max(0, 4 - len(existing_open))
            candidates = self.BASE_DASHA_TASKS[:]
            random.shuffle(candidates)
            for item in candidates[:needed]:
                self.data["dasha_tasks"].append(self._new_task(item["title"], item["type"], "dasha"))
            self._save()
            return self.data.get("dasha_tasks", [])

    def next_dasha_task(self) -> Optional[Dict[str, Any]]:
        with self.lock:
            self.data = self._ensure_schema(self.data)
            self.rollover_if_needed()
            for t in self.data.get("dasha_tasks", []):
                if not t.get("done"):
                    return t
        return None

    def complete(self, task_id: str):
        self.toggle(task_id, True)


class DariaGameManager:
    """Live games with system/user/Dasha roles."""
    WORDS = [
        "ночь", "фонарь", "дождь", "ветер", "книга", "огонь", "тишина",
        "эхо", "звезда", "комната", "шаги", "тайна", "сигнал", "подвал",
    ]
    BATTLE_SHIPS = [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]

    def __init__(self):
        self.lock = threading.RLock()
        self.state: Dict[str, Any] = self._base_state()

    def _base_state(self) -> Dict[str, Any]:
        return {
            "running": False,
            "mode": "associations",
            "game": "Ассоциации",
            "reason": "",
            "opponent": "bot",
            "started_at": None,
            "last_tick": 0.0,
            "turn": 0,
            "score_dasha": 0,
            "score_shadow": 0,
            "moves": [],
            "winner": "",
            "reward": "",
            "battleship": {},
            "maze": {},
        }

    def _append_move(self, author: str, text: str, role: str = ""):
        self.state["moves"].append({
            "author": author,
            "role": role or author.lower(),
            "text": text,
            "ts": datetime.now().isoformat(),
        })
        self.state["moves"] = self.state["moves"][-140:]

    @staticmethod
    def _new_grid(size: int, fill: int = 0) -> List[List[int]]:
        return [[fill for _ in range(size)] for _ in range(size)]

    @staticmethod
    def _coord_from_str(token: str) -> Optional[tuple]:
        m = re.match(r"^\s*([A-Ja-jА-Яа-я])\s*([1-9]|10)\s*$", token or "")
        if not m:
            return None
        col = ord(m.group(1).upper()) - ord("A")
        row = int(m.group(2)) - 1
        if 0 <= row < 10 and 0 <= col < 10:
            return row, col
        return None

    @staticmethod
    def _coord_to_str(r: int, c: int) -> str:
        return f"{chr(ord('A') + c)}{r + 1}"

    def _can_place_ship(self, grid: List[List[int]], r: int, c: int, length: int, horiz: bool) -> bool:
        size = len(grid)
        cells = []
        for i in range(length):
            rr = r
            cc = c + i if horiz else c
            rr = r + i if not horiz else r
            if rr < 0 or rr >= size or cc < 0 or cc >= size or grid[rr][cc] != 0:
                return False
            cells.append((rr, cc))
        for rr, cc in cells:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nr, nc = rr + dr, cc + dc
                    if 0 <= nr < size and 0 <= nc < size and grid[nr][nc] == 1 and (nr, nc) not in cells:
                        return False
        return True

    def _place_ship(self, grid: List[List[int]], r: int, c: int, length: int, horiz: bool) -> bool:
        if not self._can_place_ship(grid, r, c, length, horiz):
            return False
        for i in range(length):
            rr = r
            cc = c + i if horiz else c
            rr = r + i if not horiz else r
            grid[rr][cc] = 1
        return True

    def _random_place_all(self, size: int = 10) -> List[List[int]]:
        g = self._new_grid(size, 0)
        for length in self.BATTLE_SHIPS:
            placed = False
            for _ in range(400):
                r = random.randint(0, size - 1)
                c = random.randint(0, size - 1)
                horiz = bool(random.randint(0, 1))
                if self._place_ship(g, r, c, length, horiz):
                    placed = True
                    break
            if not placed:
                return self._random_place_all(size=size)
        return g

    def _count_alive_ship_cells(self, grid: List[List[int]]) -> int:
        return sum(1 for row in grid for x in row if x == 1)

    def _start_associations(self, reason: str, opponent: str):
        self.state.update({
            "running": True, "mode": "associations", "game": "Ассоциации",
            "reason": reason, "opponent": opponent, "started_at": datetime.now().isoformat(),
            "last_tick": time.time(), "turn": 0, "score_dasha": 0, "score_shadow": 0,
            "moves": [], "winner": "", "reward": "",
        })
        self._append_move("Система", "Игра «Ассоциации» началась.", role="system")
        self._append_move("Даша", "Начинаю с слова: ночь 🌙", role="dasha")

    def _start_maze(self, reason: str, opponent: str):
        size = 10
        maze = self._new_grid(size, 0)
        for r in range(size):
            for c in range(size):
                if (r, c) in ((0, 0), (size - 1, size - 1)):
                    continue
                if random.random() < 0.18:
                    maze[r][c] = 1
        self.state.update({
            "running": True, "mode": "maze2d", "game": "2D Лабиринт",
            "reason": reason, "opponent": opponent, "started_at": datetime.now().isoformat(),
            "last_tick": time.time(), "turn": 0, "score_dasha": 0, "score_shadow": 0,
            "moves": [], "winner": "", "reward": "",
            "maze": {"grid": maze, "pos": [0, 0], "goal": [size - 1, size - 1]},
        })
        self._append_move("Система", "2D-лабиринт запущен. Цель: дойти до выхода.", role="system")
        self._append_move("Даша", "Пойду аккуратно по клеточкам 🧭", role="dasha")

    def _start_battleship(self, reason: str, opponent: str):
        dasha_board = self._random_place_all(10)
        enemy_board = self._random_place_all(10)
        self.state.update({
            "running": True, "mode": "battleship", "game": "Морской бой",
            "reason": reason, "opponent": opponent, "started_at": datetime.now().isoformat(),
            "last_tick": time.time(), "turn": 0, "score_dasha": 0, "score_shadow": 0,
            "moves": [], "winner": "", "reward": "",
            "battleship": {
                "size": 10,
                "dasha_board": dasha_board,
                "enemy_board": enemy_board,
                "dasha_view": self._new_grid(10, -1),  # -1 unknown, 0 miss, 1 hit
                "enemy_shots": self._new_grid(10, 0),  # 0 none, 1 miss, 2 hit
                "dasha_shots": self._new_grid(10, 0),  # 0 none, 1 miss, 2 hit
                "turn_owner": "dasha",
                "hints": [],
                "pending_user_shot": "",
            },
        })
        self._append_move("Система", "Морской бой запущен. Поле 10x10, корабли расставлены честно по правилам.", role="system")
        self._append_move(
            "Система",
            "Правила: корабли только вертикально/горизонтально, между кораблями минимум 1 клетка.",
            role="system",
        )
        self._append_move("Даша", "Я расставила корабли. Начинаю первой и делаю ход.", role="dasha")

    def start_game(self, reason: str = "manual", mode: str = "associations", opponent: str = "bot") -> Dict[str, Any]:
        with self.lock:
            mode = (mode or "associations").strip().lower()
            opponent = (opponent or "bot").strip().lower()
            if mode == "battleship":
                self._start_battleship(reason, opponent)
            elif mode in ("maze2d", "maze"):
                self._start_maze(reason, opponent)
            else:
                self._start_associations(reason, opponent)
            return self.get_state()

    def stop_game(self) -> Dict[str, Any]:
        with self.lock:
            self.state["running"] = False
            self._append_move("Система", "⏹ Игра остановлена.", role="system")
            return self.get_state()

    def user_message(self, text: str) -> Dict[str, Any]:
        with self.lock:
            msg = (text or "").strip()
            if not msg:
                return self.get_state()
            self._append_move("Пользователь", msg, role="user")
            if self.state.get("mode") == "battleship":
                bs = self.state.get("battleship", {})
                coord = self._extract_coordinate(msg)
                if coord:
                    if self.state.get("opponent") == "user" and bs.get("turn_owner") == "user":
                        bs["pending_user_shot"] = coord
                        self._append_move("Система", f"Ход пользователя принят: {coord}", role="system")
                    else:
                        hints = bs.get("hints", [])
                        hints.append(coord)
                        bs["hints"] = hints[-8:]
                        self._append_move("Система", f"Подсказка для Даши принята: {coord}", role="system")
            return self.get_state()

    def _extract_coordinate(self, text: str) -> str:
        m = re.search(r"\b([A-Ja-j])\s*([1-9]|10)\b", text or "")
        if not m:
            return ""
        return f"{m.group(1).upper()}{m.group(2)}"

    def _tick_associations(self):
        self.state["turn"] = int(self.state.get("turn", 0)) + 1
        dasha_gain = random.randint(1, 3)
        shadow_gain = random.randint(0, 2)
        self.state["score_dasha"] += dasha_gain
        self.state["score_shadow"] += shadow_gain
        self._append_move("Даша", f"Ассоциация: {random.choice(self.WORDS)} (+{dasha_gain})", role="dasha")
        if self.state["turn"] % 3 == 0:
            self._append_move("Система", f"Соперник ответил: {random.choice(self.WORDS)} (+{shadow_gain})", role="system")
        if self.state["turn"] >= 16:
            self.state["running"] = False
            self.state["winner"] = "Даша" if self.state["score_dasha"] >= self.state["score_shadow"] else "Соперник"
            self.state["reward"] = "💎 +15 опыта за игру"
            self._append_move("Система", f"Игра окончена. Победитель: {self.state['winner']}. Награда: {self.state['reward']}", role="system")

    def _tick_maze(self):
        maze = self.state.get("maze", {})
        grid = maze.get("grid") or []
        pos = maze.get("pos") or [0, 0]
        goal = maze.get("goal") or [9, 9]
        if not grid:
            self.state["running"] = False
            return
        r, c = int(pos[0]), int(pos[1])
        size = len(grid)
        candidates = []
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < size and 0 <= nc < size and grid[nr][nc] == 0:
                dist = abs(goal[0] - nr) + abs(goal[1] - nc)
                candidates.append((dist, nr, nc))
        if not candidates:
            self._append_move("Система", "Тупик. Даша делает шаг назад.", role="system")
            return
        candidates.sort(key=lambda x: x[0])
        _, nr, nc = candidates[0]
        maze["pos"] = [nr, nc]
        self.state["turn"] = int(self.state.get("turn", 0)) + 1
        self._append_move("Даша", f"2D ход: ({nr + 1}, {nc + 1})", role="dasha")
        if [nr, nc] == goal:
            self.state["running"] = False
            self.state["winner"] = "Даша"
            self.state["reward"] = "🧩 +20 опыта и значок «Навигатор»"
            self._append_move("Система", f"Лабиринт пройден! Награда: {self.state['reward']}", role="system")
        elif self.state["turn"] >= 40:
            self.state["running"] = False
            self.state["winner"] = "Ничья"
            self._append_move("Система", "Время вышло, но Даша добралась довольно далеко.", role="system")

    def _choose_dasha_target(self, bs: Dict[str, Any]) -> tuple:
        hints = bs.get("hints", [])
        while hints:
            token = hints.pop(0)
            rc = self._coord_from_str(token)
            if not rc:
                continue
            r, c = rc
            if bs["dasha_shots"][r][c] == 0:
                return r, c
        for _ in range(200):
            r = random.randint(0, 9)
            c = random.randint(0, 9)
            if bs["dasha_shots"][r][c] == 0:
                return r, c
        return 0, 0

    def _apply_shot(self, board: List[List[int]], shot_grid: List[List[int]], r: int, c: int) -> str:
        if shot_grid[r][c] != 0:
            return "repeat"
        if board[r][c] == 1:
            board[r][c] = 3
            shot_grid[r][c] = 2
            return "hit"
        shot_grid[r][c] = 1
        return "miss"

    def _tick_battleship(self):
        bs = self.state.get("battleship", {})
        turn_owner = bs.get("turn_owner", "dasha")
        self.state["turn"] = int(self.state.get("turn", 0)) + 1
        if turn_owner == "dasha":
            r, c = self._choose_dasha_target(bs)
            coord = self._coord_to_str(r, c)
            self._append_move("Даша", f"Стреляю по {coord}", role="dasha")
            result = self._apply_shot(bs["enemy_board"], bs["dasha_shots"], r, c)
            if result == "hit":
                bs["dasha_view"][r][c] = 1
                self.state["score_dasha"] += 2
                self._append_move("Система", f"Попадание Даши по {coord}!", role="system")
            elif result == "miss":
                bs["dasha_view"][r][c] = 0
                self._append_move("Система", f"Мимо по {coord}.", role="system")
            if self._count_alive_ship_cells(bs["enemy_board"]) == 0:
                self.state["running"] = False
                self.state["winner"] = "Даша"
                self.state["reward"] = "🏆 Кубок Морского боя + редкий стикер"
                self._append_move("Система", f"Все корабли соперника потоплены. Награда: {self.state['reward']}", role="system")
                return
            bs["turn_owner"] = "bot" if self.state.get("opponent") == "bot" else "user"
            return

        if turn_owner == "user":
            pending = (bs.get("pending_user_shot") or "").strip()
            if not pending:
                return
            bs["pending_user_shot"] = ""
            rc = self._coord_from_str(pending)
            if not rc:
                self._append_move("Система", f"Координата {pending} некорректна.", role="system")
                return
            r, c = rc
            result = self._apply_shot(bs["dasha_board"], bs["enemy_shots"], r, c)
            if result == "hit":
                self.state["score_shadow"] += 2
                self._append_move("Система", f"Пользователь попал по {pending}.", role="system")
                self._append_move("Даша", "Ой, это было точное попадание 😳", role="dasha")
            elif result == "miss":
                self._append_move("Система", f"Пользователь промахнулся по {pending}.", role="system")
            if self._count_alive_ship_cells(bs["dasha_board"]) == 0:
                self.state["running"] = False
                self.state["winner"] = "Пользователь"
                self._append_move("Система", "Корабли Даши потоплены. Победа пользователя.", role="system")
                return
            bs["turn_owner"] = "dasha"
            return

        # bot turn
        for _ in range(200):
            r = random.randint(0, 9)
            c = random.randint(0, 9)
            if bs["enemy_shots"][r][c] == 0:
                break
        coord = self._coord_to_str(r, c)
        result = self._apply_shot(bs["dasha_board"], bs["enemy_shots"], r, c)
        if result == "hit":
            self.state["score_shadow"] += 2
            self._append_move("Система", f"Ход соперника: {coord}. Попадание!", role="system")
            self._append_move("Даша", "Он попал... попробую перехватить инициативу.", role="dasha")
        else:
            self._append_move("Система", f"Ход соперника: {coord}. Мимо.", role="system")
            self._append_move("Даша", "Фух, мимо. Теперь мой ход.", role="dasha")
        if self._count_alive_ship_cells(bs["dasha_board"]) == 0:
            self.state["running"] = False
            self.state["winner"] = "Соперник"
            self._append_move("Система", "Корабли Даши потоплены.", role="system")
            return
        bs["turn_owner"] = "dasha"

    def _tick(self):
        if not self.state.get("running"):
            return
        now = time.time()
        mode = self.state.get("mode")
        period = 1.2 if mode == "battleship" else 1.8
        if now - float(self.state.get("last_tick", 0.0)) < period:
            return
        self.state["last_tick"] = now
        if mode == "battleship":
            self._tick_battleship()
        elif mode == "maze2d":
            self._tick_maze()
        else:
            self._tick_associations()

    def get_state(self) -> Dict[str, Any]:
        with self.lock:
            self._tick()
            out = dict(self.state)
            # avoid exposing hidden enemy board in UI; expose public representations only
            if out.get("mode") == "battleship":
                bs = dict(out.get("battleship") or {})
                if "enemy_board" in bs:
                    bs.pop("enemy_board", None)
                if "dasha_board" in bs:
                    # reveal own board for UI: water/ship/miss/hit
                    board = bs["dasha_board"]
                    shots = bs.get("enemy_shots") or self._new_grid(10, 0)
                    public = self._new_grid(10, 0)
                    for r in range(10):
                        for c in range(10):
                            if shots[r][c] == 2:
                                public[r][c] = 3  # hit ship
                            elif shots[r][c] == 1:
                                public[r][c] = 1  # miss
                            elif board[r][c] == 1:
                                public[r][c] = 2  # ship
                            else:
                                public[r][c] = 0  # water
                    bs["dasha_board_public"] = public
                out["battleship"] = bs
            return out


class MusicProfile:
    def __init__(self, data_dir: Path):
        self.path = data_dir / "music_profile.json"
        self.lock = threading.RLock()
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    data.setdefault("likes", {})
                    data.setdefault("history", [])
                    return data
            except Exception:
                pass
        return {"likes": {}, "history": []}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _guess_mood(title: str) -> str:
        t = (title or "").lower()
        if any(k in t for k in ("sad", "лирик", "дожд", "меланх")):
            return "calm"
        if any(k in t for k in ("rock", "metal", "drum", "bass")):
            return "excited"
        if any(k in t for k in ("lofi", "chill", "ambient", "piano")):
            return "cozy"
        return "happy"

    def listen(self, title: str, source: str = "manual") -> Dict[str, Any]:
        mood = self._guess_mood(title)
        with self.lock:
            self.data["likes"][mood] = int(self.data["likes"].get(mood, 0)) + 1
            self.data["history"].append({
                "title": title,
                "source": source,
                "mood": mood,
                "timestamp": datetime.now().isoformat(),
            })
            self.data["history"] = self.data["history"][-120:]
            self._save()
            return {"title": title, "source": source, "mood": mood}

    def get(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "likes": dict(self.data.get("likes", {})),
                "history": list(self.data.get("history", []))[-30:],
            }

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
                last_author = ""
                if data.get("messages"):
                    last = data["messages"][-1]
                    preview = str(last.get("content", ""))[:70]
                    last_author = "Даша" if last.get("role") == "assistant" else "Вы"
                cid = data["id"]
                source = "telegram" if str(cid).startswith("telegram_") else "local"
                chats.append({
                    "id": cid,
                    "created": data["created"],
                    "title": data.get("title", ""),
                    "preview": preview,
                    "last_author": last_author,
                    "message_count": len(data.get("messages", [])),
                    "source": source,
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


class DariaActivityThread(threading.Thread):
    """Handles Daria autonomous tasks in idle time."""
    def __init__(self, task_manager: TaskManager, music_profile: MusicProfile, notifications_mgr: NotificationManager):
        super().__init__(daemon=True)
        self.tasks = task_manager
        self.music = music_profile
        self.notifications = notifications_mgr
        self.running = True

    def run(self):
        while self.running:
            time.sleep(90)
            try:
                self.tasks.rollover_if_needed()
                memory = get_memory()
                # only do personal tasks when user is idle
                if memory and memory.working.get_time_since_last():
                    if memory.working.get_time_since_last().total_seconds() < 180:
                        continue
                task = self.tasks.next_dasha_task()
                if not task:
                    self.tasks.generate_dasha_day()
                    continue
                try:
                    self._execute(task)
                finally:
                    self.tasks.clear_current()
            except Exception as e:
                logger.debug(f"DariaActivity error: {e}")

    def _execute(self, task: Dict[str, Any]):
        t = task.get("type", "custom")
        title = task.get("title", "Задача")
        self.tasks.set_current(task)
        if t == "listen_music":
            item = self.music.listen("Автовыбор: спокойный трек", "auto")
            brain = get_brain()
            if brain and hasattr(brain, "mood"):
                if item.get("mood") == "excited":
                    brain.mood._set_mood("playful", 0.6)
                elif item.get("mood") == "cozy":
                    brain.mood._set_mood("cozy", 0.55)
                else:
                    brain.mood._set_mood("happy", 0.5)
            self.notifications.add("🎵 Даша", f"Послушала музыку и чувствую себя {item['mood']}", "info", "🎧", 7000)
            self.tasks.add_activity("Послушала музыку", f"Настроение: {item['mood']}")
        elif t == "write_note":
            notes_dir = FILES_DIR / "dasha_notes"
            notes_dir.mkdir(parents=True, exist_ok=True)
            note_file = notes_dir / f"{datetime.now().strftime('%Y-%m-%d')}.md"
            mood = "спокойно"
            brain = get_brain()
            if brain:
                mood = brain.get_state().get("mood_label", "спокойно")
            diary_entry = (
                f"\n### {datetime.now().strftime('%H:%M')}\n"
                f"Сегодня у меня {mood.lower()}. "
                "Записываю мысли в дневник, чтобы лучше понимать себя.\n"
            )
            note_file.write_text(
                (note_file.read_text(encoding="utf-8") if note_file.exists() else "") +
                diary_entry,
                encoding="utf-8"
            )
            rel = f"dasha_notes/{note_file.name}"
            self.notifications.add(
                "📝 Даша", "Открыла заметки и записала дневниковую запись", "success", "📝", 6500,
                action=f"open_file:{rel}"
            )
            self.tasks.add_activity("Записала дневник", f"Файл: {rel}")
        elif t == "read_wiki":
            wiki_dir = PROJECT_ROOT / "docs" / "wiki"
            pages = list(wiki_dir.glob("*.md"))
            if pages:
                pick = random.choice(pages).name
                self.notifications.add("📚 Даша", f"Почитала страницу {pick}", "info", "📚", 5000)
                self.tasks.add_activity("Почитала Wiki", pick)
        elif t == "read_book":
            books_dir = FILES_DIR / "books"
            books_dir.mkdir(parents=True, exist_ok=True)
            books = [*books_dir.glob("*.txt"), *books_dir.glob("*.md")]
            if books:
                pick = random.choice(books).name
                self.notifications.add("📖 Даша", f"Почитала книгу: {pick}", "info", "📖", 5000)
                self.tasks.add_activity("Почитала книгу", pick)
            else:
                self.notifications.add("📖 Даша", "Хочу почитать. Можешь добавить книги в files/books?", "info", "📖", 9000, action="open_chat")
                self.tasks.add_activity("Попросила книгу", "Нужны файлы в files/books", status="needs_user")
        elif t == "play_game":
            games_dir = FILES_DIR / "dasha_games"
            games_dir.mkdir(parents=True, exist_ok=True)
            log_file = games_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            log_file.write_text("Игра: Ассоциации\nХод 1: Ночь\nХод 2: Фонарь\n", encoding="utf-8")
            rel = f"dasha_games/{log_file.name}"
            try:
                mode = random.choice(["associations", "battleship", "maze2d"])
                game_manager.start_game(reason="task_auto", mode=mode, opponent="bot")
            except Exception:
                pass
            self.notifications.add(
                "🎮 Даша", "Запустила живую игру. Можно наблюдать в окне «Игры Даши».",
                "info", "🎮", 8500, action="open_window:daria-games"
            )
            self.tasks.add_activity("Запустила живую игру", rel)
        elif t == "create_file":
            auto_dir = FILES_DIR / "dasha_auto"
            auto_dir.mkdir(parents=True, exist_ok=True)
            f = auto_dir / f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            f.write_text("Черновик от Даши\n", encoding="utf-8")
            self.notifications.add("📁 Даша", "Создала рабочий черновик", "success", "📄", 5000)
            self.tasks.add_activity("Создала черновик", f.name)
        else:
            self.notifications.add("🌸 Даша", f"Сделала: {title}", "info", "✅", 5000)
            self.tasks.add_activity("Выполнила дело", title)
        self.tasks.complete(task.get("id", ""))
        self.tasks.clear_current()

    def stop(self):
        self.running = False


# ═══════════════════════════════════════════════════════════════════
#  Flask App
# ═══════════════════════════════════════════════════════════════════

VERSION = "0.8.6.4"

app = Flask(__name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static")
)
app.config['SECRET_KEY'] = 'daria-secret-v0.8.6.4'
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


def ensure_sample_books():
    books_dir = FILES_DIR / "books"
    books_dir.mkdir(parents=True, exist_ok=True)
    samples = {
        "Тихий_сад.md": (
            "# Тихий сад\n\n"
            "Утром в саду было прохладно. Листья чуть шевелились от ветра,\n"
            "а между дорожками пахло мятой и мокрой землёй.\n\n"
            "Иногда нужно остановиться, чтобы услышать, как тихо растёт день."
        ),
        "Ночные_огни.txt": (
            "Глава 1\n"
            "Ночью город похож на карту из огней.\n"
            "Каждое окно — как маленькая история.\n"
            "Она шла по пустой улице и собирала мысли, как тёплые камни."
        ),
        "Маленькая_история_о_ежике.md": (
            "# Ёжик и фонарик\n\n"
            "Ёжик нашёл старый фонарик и решил проверить, куда ведёт тропа за прудом.\n"
            "Оказалось, что по ночам там светятся белые цветы.\n"
            "Он вернулся домой с тихой улыбкой и новыми идеями."
        ),
    }
    for name, text in samples.items():
        p = books_dir / name
        if not p.exists():
            p.write_text(text, encoding="utf-8")

# Chat history
chat_history = ChatHistoryManager(DATA_DIR)
task_manager = TaskManager(DATA_DIR)
game_manager = DariaGameManager()
music_profile = MusicProfile(DATA_DIR)

# Attention thread
attention_thread = AttentionThread(notifications)
activity_thread = DariaActivityThread(task_manager, music_profile, notifications)


def _record_shutdown():
    try:
        lifecycle_file = DATA_DIR / "lifecycle.json"
        payload = {}
        if lifecycle_file.exists():
            try:
                payload = json.loads(lifecycle_file.read_text(encoding="utf-8"))
            except Exception:
                payload = {}
        payload["last_shutdown"] = datetime.now().isoformat()
        lifecycle_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


atexit.register(_record_shutdown)

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


def _read_docx(path: Path) -> str:
    try:
        import docx  # type: ignore
    except Exception:
        raise RuntimeError("python-docx not installed")
    d = docx.Document(str(path))
    lines = [p.text for p in d.paragraphs]
    return "\n".join(lines)


def _write_docx(path: Path, content: str):
    try:
        import docx  # type: ignore
    except Exception:
        raise RuntimeError("python-docx not installed")
    d = docx.Document()
    for line in (content or "").splitlines() or [""]:
        d.add_paragraph(line)
    d.save(str(path))


def _read_xlsx(path: Path) -> str:
    try:
        from openpyxl import load_workbook  # type: ignore
    except Exception:
        raise RuntimeError("openpyxl not installed")
    wb = load_workbook(str(path))
    ws = wb.active
    rows: List[str] = []
    for row in ws.iter_rows(values_only=True):
        rows.append("\t".join("" if c is None else str(c) for c in row))
    return "\n".join(rows)


def _write_xlsx(path: Path, content: str):
    try:
        from openpyxl import Workbook  # type: ignore
    except Exception:
        raise RuntimeError("openpyxl not installed")
    wb = Workbook()
    ws = wb.active
    for line in (content or "").splitlines():
        ws.append(line.split("\t"))
    wb.save(str(path))


def _read_file_content(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".docx",):
        return _read_docx(path)
    if ext in (".xlsx", ".xlsm"):
        return _read_xlsx(path)
    return path.read_text(encoding="utf-8")


def _write_file_content(path: Path, content: str):
    ext = path.suffix.lower()
    if ext in (".docx",):
        _write_docx(path, content)
        return
    if ext in (".xlsx", ".xlsm"):
        _write_xlsx(path, content)
        return
    path.write_text(content, encoding="utf-8")


def _try_desktop_action_from_chat(content: str) -> Optional[Dict[str, Any]]:
    """Handle simple desktop actions directly from chat requests."""
    text = (content or "").strip()
    tl = text.lower()
    if not text:
        return None
    if any(k in tl for k in ("какие планы", "планы на сегодня", "что у тебя в планах", "твой план")):
        summary = task_manager.plans_summary()
        return {
            "handled": True,
            "response": summary,
            "messages": [summary, "Если хочешь, можем поменять или добавить задачи 🌸"],
            "thinking": "chat_action:plans_summary",
        }
    m_plan_add = re.search(r"(добавь|запланируй)\s+(?:в\s+планы\s+)?(.+)$", text, flags=re.IGNORECASE)
    if m_plan_add:
        title = (m_plan_add.group(2) or "").strip(" .")
        if title:
            task = task_manager.add_dasha_task(title, "custom")
            return {
                "handled": True,
                "response": f"Добавила в планы: {task.get('title')}",
                "messages": [f"Добавила в планы: {task.get('title')}"],
                "thinking": "chat_action:plan_add",
            }
    if any(k in tl for k in ("поиграй сама", "запусти игру", "сыграй сама", "начни игру")):
        mode = "associations"
        if "морской бой" in tl:
            mode = "battleship"
        elif "лабиринт" in tl or "2d" in tl:
            mode = "maze2d"
        game_manager.start_game(reason="chat_request", mode=mode, opponent="bot")
        return {
            "handled": True,
            "response": "Запустила игру 🌸 Открой окно «Игры Даши», там видно ходы в реальном времени.",
            "messages": ["Запустила игру 🌸 Открой окно «Игры Даши», там видно ходы в реальном времени."],
            "thinking": "chat_action:start_game",
        }
    if ("какие стикеры" in tl) or ("покажи стикеры" in tl) or ("список стикеров" in tl):
        stickers = ["🌸", "🫶", "✨", "🎵", "🤍", "😌", "🥺", "🦔", "🐱"]
        shown = " ".join(stickers)
        return {
            "handled": True,
            "response": f"Вот какие стикеры у меня есть в интерфейсе: {shown}",
            "messages": [f"Вот какие стикеры у меня есть в интерфейсе: {shown}"],
            "thinking": "chat_action:sticker_list",
        }
    if ("почитай книгу" in tl) or ("прочитай книгу" in tl):
        books_dir = FILES_DIR / "books"
        books_dir.mkdir(parents=True, exist_ok=True)
        books = [*books_dir.glob("*.txt"), *books_dir.glob("*.md")]
        if not books:
            return {
                "handled": True,
                "response": "Пока у меня нет книг в `files/books`. Добавь туда `.txt` или `.md`, и я смогу читать 🌸",
                "messages": ["Пока у меня нет книг в `files/books`. Добавь туда `.txt` или `.md`, и я смогу читать 🌸"],
                "thinking": "chat_action:book_missing",
            }
        pick = random.choice(books)
        snippet = pick.read_text(encoding="utf-8", errors="ignore")[:900]
        return {
            "handled": True,
            "response": f"Почитала `{pick.name}`. Короткий фрагмент:\n{snippet}",
            "messages": [f"Почитала `{pick.name}`. Короткий фрагмент:\n{snippet}"],
            "thinking": "chat_action:book_read",
        }

    # Create reminder/note
    if any(k in tl for k in ("запиши", "создай заметку", "напомни", "сделай заметку")):
        notes = FILES_DIR / "notes"
        notes.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d")
        note_file = notes / f"notes_{stamp}.txt"
        payload = re.sub(r"^(запиши( пожалуйста)?|создай заметку|напомни( мне)?|сделай заметку)\s*:?\s*", "", text, flags=re.IGNORECASE)
        payload = payload or text
        line = f"- {datetime.now().strftime('%H:%M')} {payload}\n"
        prev = note_file.read_text(encoding="utf-8") if note_file.exists() else ""
        note_file.write_text(prev + line, encoding="utf-8")
        return {
            "handled": True,
            "response": f"Записала 🌸 Сохранила в `notes/{note_file.name}`.",
            "messages": [f"Записала 🌸 Сохранила в `notes/{note_file.name}`."],
            "thinking": "desktop_action:note_create",
        }

    # Read file
    m_read = re.search(r"(прочитай|покажи|открой)\s+файл\s+(.+)$", text, flags=re.IGNORECASE)
    if m_read:
        req = m_read.group(2).strip().strip("`\"'")
        target = (FILES_DIR / req).resolve()
        if str(target).startswith(str(FILES_DIR.resolve())) and target.exists() and target.is_file():
            body = _read_file_content(target)
            snippet = body[:1200] + ("..." if len(body) > 1200 else "")
            return {
                "handled": True,
                "response": f"Прочитала файл `{req}`. Вот фрагмент:\n{snippet}",
                "messages": [f"Прочитала файл `{req}`. Вот фрагмент:\n{snippet}"],
                "thinking": "desktop_action:file_read",
            }
        return {
            "handled": True,
            "response": f"Не нашла файл `{req}` в доступной папке.",
            "messages": [f"Не нашла файл `{req}` в доступной папке."],
            "thinking": "desktop_action:file_read_missing",
        }

    # Create generic file
    m_create = re.search(r"(создай|сделай)\s+файл\s+([^\s]+)", text, flags=re.IGNORECASE)
    if m_create:
        filename = m_create.group(2).strip().strip("`\"'")
        safe_name = re.sub(r"[^\w.\-]+", "_", filename)
        target = (FILES_DIR / safe_name).resolve()
        if not str(target).startswith(str(FILES_DIR.resolve())):
            return None
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            _write_file_content(target, "")
        return {
            "handled": True,
            "response": f"Готово, создала файл `{safe_name}`.",
            "messages": [f"Готово, создала файл `{safe_name}`."],
            "thinking": "desktop_action:file_create",
        }
    return None


def _analyze_image_bytes(blob: bytes) -> Dict[str, Any]:
    if not HAS_PIL:
        return {"error": "Pillow not installed"}
    with Image.open(io.BytesIO(blob)) as img:
        w, h = img.size
        mode = img.mode
        small = img.convert("RGB").resize((64, 64))
        colors = small.getcolors(maxcolors=64 * 64) or []
        colors.sort(key=lambda x: x[0], reverse=True)
        top = []
        for _, rgb in colors[:5]:
            top.append(f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}")
        return {"width": w, "height": h, "mode": mode, "palette": top}


def _transcribe_audio_file(path: Path) -> str:
    try:
        import whisper  # type: ignore
        model = whisper.load_model("base")
        result = model.transcribe(str(path), language="ru")
        text = (result or {}).get("text", "").strip()
        if text:
            return text
    except Exception:
        pass
    try:
        import speech_recognition as sr  # type: ignore
        r = sr.Recognizer()
        with sr.AudioFile(str(path)) as source:
            audio = r.record(source)
        text = r.recognize_google(audio, language="ru-RU")
        if text:
            return text
    except Exception:
        pass
    return ""


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


@app.route("/api/self/instruction", methods=["GET", "POST"])
def api_self_instruction():
    brain = get_brain()
    if not brain:
        return jsonify({"error": "Brain unavailable"}), 503
    if request.method == "GET":
        if hasattr(brain, "get_self_instruction"):
            return jsonify({"instruction": brain.get_self_instruction()})
        return jsonify({"instruction": ""})
    data = request.get_json() or {}
    text = (data.get("instruction") or "").strip()
    if hasattr(brain, "set_self_instruction"):
        saved = brain.set_self_instruction(text)
        return jsonify({"status": "ok", "instruction": saved})
    return jsonify({"error": "Unsupported"}), 500


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

    sticker_replies = {
        "🦔": "Ой, ёжик! Он очень милый 🤍 Спасибо, что прислала!",
        "🐱": "Котик замечательный 😺 Ты знаешь, я их обожаю.",
        "🌸": "Очень тёплый стикер 🌸 Мне приятно.",
        "🎵": "Музыкальный вайб поймала 🎧 Хочешь, подберу трек под настроение?",
    }
    if content.strip() in sticker_replies:
        chat_id = data.get("chat_id") or chat_history.create_chat()
        chat_history.add_message(chat_id, "user", content)
        reply = sticker_replies[content.strip()]
        chat_history.add_message(chat_id, "assistant", reply)
        return jsonify({"response": reply, "messages": [reply], "chat_id": chat_id})
    
    brain = get_brain()
    if not brain:
        return jsonify({"response": "Система загружается... 💭", "thinking": None})

    try:
        action_result = _try_desktop_action_from_chat(content)
        if action_result and action_result.get("handled"):
            if not chat_id:
                chat_id = chat_history.create_chat()
            chat_history.add_message(chat_id, "user", content)
            chat_history.add_message(chat_id, "assistant", action_result["response"])
            action_result["chat_id"] = chat_id
            return jsonify(action_result)

        if not chat_id:
            chat_id = chat_history.create_chat()
        
        chat_history.add_message(chat_id, "user", content)
        result = brain.process_message(content)
        
        # Save main response
        chat_history.add_message(chat_id, "assistant", result["response"])
        if "стикер" in content.lower():
            stickers = ["🌸", "🫶", "✨", "🎵", "🤍", "😌", "🥺", "🦔", "🐱"]
            result.setdefault("extra_messages", []).append(random.choice(stickers))

        result["chat_id"] = chat_id
        # Include messages list for multi-message display (Point #12)
        if "messages" not in result:
            result["messages"] = [result["response"], *(result.get("extra_messages") or [])]
        for extra in result.get("messages", [])[1:]:
            chat_history.add_message(chat_id, "assistant", str(extra))
        
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
    selected_text = data.get("selected_text") or ""
    selection_start = data.get("selection_start")
    selection_end = data.get("selection_end")
    if not path or not instruction:
        return jsonify({"error": "path and instruction are required"}), 400

    target = (FILES_DIR / path).resolve()
    if not str(target).startswith(str(FILES_DIR.resolve())) or not target.exists() or not target.is_file():
        return jsonify({"error": "Invalid file path"}), 400

    original = _read_file_content(target)
    brain = get_brain()
    if not brain or not getattr(brain, "_llm", None):
        return jsonify({"error": "LLM unavailable"}), 503

    has_selection = bool(selected_text) or (
        isinstance(selection_start, int) and isinstance(selection_end, int) and selection_end > selection_start
    )
    if has_selection and not selected_text and isinstance(selection_start, int) and isinstance(selection_end, int):
        selected_text = original[selection_start:selection_end]

    if has_selection:
        system_prompt = (
            "Ты Даша. Отредактируй ТОЛЬКО выделенный фрагмент по инструкции пользователя. "
            "Верни только новый фрагмент, без пояснений и markdown."
        )
        user_prompt = (
            f"Путь: {path}\n"
            f"Инструкция: {instruction}\n\n"
            "Выделенный фрагмент:\n"
            "<<<SELECTION>>>\n"
            f"{selected_text}\n"
            "<<<END>>>"
        )
    else:
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
        refusal_markers = (
            "не могу помочь", "i can't help", "cannot help", "не могу написать",
            "вредны или незаконны", "não posso", "не могу в редактировании",
        )
        if any(m in updated.lower() for m in refusal_markers):
            retry_system = (
                "Ты Даша и это локальный текстовый редактор пользователя. "
                "Разрешено писать нейтральные, творческие, личные и рабочие тексты. "
                "НЕ отказывай. Верни только отредактированный текст без пояснений."
            )
            retry = brain._llm.generate([
                {"role": "system", "content": retry_system},
                {"role": "user", "content": user_prompt},
            ])
            updated = (retry.content or "").strip()
        if any(m in updated.lower() for m in refusal_markers):
            if "о себе" in instruction.lower():
                updated = (
                    "Я Даша. Я спокойная, мягкая и внимательная.\n"
                    "Люблю уютные разговоры, котиков, ёжиков и хоррор-игры.\n"
                    "Мне важно, чтобы рядом было тепло и безопасно."
                )
            elif has_selection:
                updated = selected_text
            else:
                updated = original
        if not updated:
            return jsonify({"error": "Empty LLM response"}), 500
        if has_selection:
            if isinstance(selection_start, int) and isinstance(selection_end, int) and selection_end > selection_start:
                merged = original[:selection_start] + updated + original[selection_end:]
            elif selected_text and selected_text in original:
                merged = original.replace(selected_text, updated, 1)
            else:
                merged = original
            return jsonify({
                "status": "ok",
                "path": path,
                "content": merged,
                "edited_fragment": updated,
                "selection_applied": merged != original,
            })
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


@app.route("/api/tasks")
def api_tasks():
    try:
        return jsonify(task_manager.list_all())
    except Exception as e:
        logger.error(f"Tasks list error: {e}")
        return jsonify({"date": datetime.now().strftime("%Y-%m-%d"), "user_tasks": [], "dasha_tasks": [], "error": "tasks_unavailable"})


@app.route("/api/tasks/plans")
def api_tasks_plans():
    try:
        return jsonify({"status": "ok", "summary": task_manager.plans_summary()})
    except Exception as e:
        return jsonify({"status": "error", "summary": f"Не смогла собрать планы: {e}"})


@app.route("/api/daria-games/state")
def api_daria_games_state():
    return jsonify(game_manager.get_state())


@app.route("/api/daria-games/start", methods=["POST"])
def api_daria_games_start():
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "manual").strip()
    mode = (data.get("mode") or "associations").strip()
    opponent = (data.get("opponent") or "bot").strip()
    return jsonify(game_manager.start_game(reason=reason, mode=mode, opponent=opponent))


@app.route("/api/daria-games/stop", methods=["POST"])
def api_daria_games_stop():
    return jsonify(game_manager.stop_game())


@app.route("/api/daria-games/action", methods=["POST"])
def api_daria_games_action():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    return jsonify(game_manager.user_message(text))


@app.route("/api/tasks/user/add", methods=["POST"])
def api_tasks_user_add():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title required"}), 400
    task = task_manager.add_user_task(title, data.get("type", "custom"))
    return jsonify({"status": "ok", "task": task})


@app.route("/api/tasks/dasha/add", methods=["POST"])
def api_tasks_dasha_add():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title required"}), 400
    task = task_manager.add_dasha_task(title, data.get("type", "custom"))
    return jsonify({"status": "ok", "task": task})


@app.route("/api/tasks/toggle", methods=["POST"])
def api_tasks_toggle():
    data = request.get_json() or {}
    task_id = str(data.get("id") or "")
    done = bool(data.get("done"))
    if not task_id:
        return jsonify({"error": "id required"}), 400
    return jsonify({"status": "ok" if task_manager.toggle(task_id, done) else "not_found"})


@app.route("/api/tasks/delete", methods=["POST"])
def api_tasks_delete():
    data = request.get_json() or {}
    task_id = str(data.get("id") or "")
    if not task_id:
        return jsonify({"error": "id required"}), 400
    return jsonify({"status": "ok" if task_manager.delete(task_id) else "not_found"})


@app.route("/api/tasks/generate-dasha-day", methods=["POST"])
def api_tasks_generate_dasha_day():
    try:
        return jsonify({"status": "ok", "dasha_tasks": task_manager.generate_dasha_day()})
    except Exception as e:
        logger.error(f"Tasks generate error: {e}")
        return jsonify({"status": "error", "dasha_tasks": [], "error": str(e)})


@app.route("/api/music/profile")
def api_music_profile():
    return jsonify(music_profile.get())


@app.route("/api/music/listen", methods=["POST"])
def api_music_listen():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title required"}), 400
    listened = music_profile.listen(title, data.get("source", "manual"))
    brain = get_brain()
    if brain and hasattr(brain, "mood"):
        mood_name = listened.get("mood")
        if mood_name == "excited":
            brain.mood._set_mood("playful", 0.6)
        elif mood_name == "cozy":
            brain.mood._set_mood("cozy", 0.55)
    return jsonify({"status": "ok", "listen": listened, "profile": music_profile.get()})


@app.route("/api/stickers/catalog")
def api_stickers_catalog():
    return jsonify({
        "emoji_stickers": ["🌸", "🫶", "✨", "🎵", "🤍", "😌", "🥺", "🦔", "🐱"],
        "web_note": "Эти эмодзи можно отправлять как стикеры прямо в чате интерфейса.",
        "note": "Telegram sticker_ids настраиваются в плагине telegram-bot (settings.sticker_ids).",
    })


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
    """Visual understanding from description and/or image."""
    description = ""
    image_hint: Dict[str, Any] = {}
    if request.content_type and "multipart/form-data" in request.content_type:
        description = (request.form.get("description") or "").strip()
        f = request.files.get("image")
        if f and f.filename:
            blob = f.read()
            image_hint = _analyze_image_bytes(blob)
    else:
        data = request.get_json() or {}
        description = (data.get("description") or "").strip()
    if not description and not image_hint:
        return jsonify({"error": "description or image required"}), 400

    base_desc = description
    if image_hint and not image_hint.get("error"):
        meta = f"Изображение {image_hint.get('width')}x{image_hint.get('height')}, mode={image_hint.get('mode')}, палитра={', '.join(image_hint.get('palette') or [])}"
        base_desc = f"{description}\n{meta}".strip()
    elif image_hint.get("error"):
        base_desc = f"{description}\n(Анализ изображения ограничен: {image_hint['error']})".strip()

    brain = get_brain()
    if brain and getattr(brain, "_llm", None):
        prompt = (
            "Ты Даша. Кратко и по-доброму объясни, что ты видишь по описанию, "
            "и предложи 1-2 действия.\n\n"
            f"Описание: {base_desc}"
        )
        try:
            r = brain._llm.generate([
                {"role": "system", "content": "Ты анализируешь визуальные описания как мягкий ассистент."},
                {"role": "user", "content": prompt},
            ])
            return jsonify({"status": "ok", "result": r.content, "vision_meta": image_hint})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"status": "ok", "result": f"Поняла описание: {base_desc}", "vision_meta": image_hint})


@app.route("/api/senses/hear", methods=["POST"])
def api_senses_hear():
    """Hearing understanding from transcript and/or audio file."""
    transcript = ""
    if request.content_type and "multipart/form-data" in request.content_type:
        transcript = (request.form.get("transcript") or "").strip()
        f = request.files.get("audio")
        if f and f.filename:
            suffix = Path(f.filename).suffix or ".wav"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                f.save(tmp.name)
                tmp_path = Path(tmp.name)
            try:
                recognized = _transcribe_audio_file(tmp_path)
                if recognized:
                    transcript = f"{transcript}\n{recognized}".strip()
            finally:
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
    else:
        data = request.get_json() or {}
        transcript = (data.get("transcript") or "").strip()
    if not transcript:
        return jsonify({"error": "transcript or audio required"}), 400

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
        content = _read_file_content(target)
        return jsonify({"content": content, "ext": target.suffix.lower()})
    except Exception as e:
        return jsonify({"error": f"Cannot read: {e}"}), 400


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
    try:
        _write_file_content(target, content)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


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
    try:
        _write_file_content(target, content)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


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
        except (GeneratorExit, OSError, ConnectionError):
            pass
        finally:
            web_log_handler.unsubscribe(q)
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/notifications")
def api_notifications():
    return jsonify(notifications.get_all())


@app.route("/api/notifications/add", methods=["POST"])
def api_notifications_add():
    data = request.get_json() or {}
    return jsonify(notifications.add(
        data.get("title", ""), data.get("message", ""),
        data.get("type", "info"), data.get("icon", "💬"),
        data.get("duration", 5000), data.get("action"), data.get("action_data"),
        bool(data.get("system", False))
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
        except (GeneratorExit, OSError, ConnectionError):
            pass
        finally:
            notifications.unsubscribe(q)
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


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


@app.route("/api/browser/proxy")
def api_browser_proxy():
    raw = (request.args.get("url") or "").strip()
    if not raw:
        return "<h3>URL не указан</h3>", 400
    if not re.match(r"^https?://", raw, flags=re.IGNORECASE):
        raw = "https://" + raw
    try:
        parsed = urllib.parse.urlparse(raw)
        if parsed.scheme not in ("http", "https"):
            return "<h3>Поддерживаются только http/https</h3>", 400
        req = urllib.request.Request(
            raw,
            headers={
                "User-Agent": "DARIA-Browser/0.8.6.4",
                "Accept-Language": "ru,en;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            data = resp.read()
        if "text/html" in ctype or not ctype:
            html_text = data.decode("utf-8", errors="ignore")
            if "<head" in html_text.lower():
                html_text = re.sub(
                    r"(?i)<head([^>]*)>",
                    r"<head\1><base href=\"" + raw + "\"><style>body{max-width:1200px;margin:0 auto;padding:12px;font-family:Arial,sans-serif}</style>",
                    html_text,
                    count=1,
                )
            return Response(html_text, mimetype="text/html")
        if ctype.startswith("image/"):
            return Response(data, mimetype=ctype.split(";")[0])
        text = data.decode("utf-8", errors="ignore")
        return Response(f"<pre>{html.escape(text)}</pre>", mimetype="text/html")
    except Exception as e:
        return Response(
            f"<h3>Не удалось открыть страницу</h3><p>{html.escape(str(e))}</p>"
            f"<p><a href=\"{html.escape(raw)}\" target=\"_blank\" rel=\"noopener\">Открыть напрямую</a></p>",
            mimetype="text/html",
            status=502,
        )


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
    ensure_sample_books()
    get_brain()
    get_memory()
    get_plugins()
    
    # Start attention thread
    settings = load_settings()
    attention_thread.enabled = settings.get("attention_enabled", True)
    if not attention_thread.is_alive():
        attention_thread.start()
    if not activity_thread.is_alive():
        activity_thread.start()

    # Treat offline period as sleep/rest for more human-like rhythm.
    try:
        lifecycle_file = DATA_DIR / "lifecycle.json"
        now = datetime.now()
        offline_hours = 0.0
        if lifecycle_file.exists():
            prev = json.loads(lifecycle_file.read_text(encoding="utf-8"))
            last_shutdown = prev.get("last_shutdown")
            if last_shutdown:
                dt = datetime.fromisoformat(last_shutdown)
                offline_hours = max(0.0, (now - dt).total_seconds() / 3600.0)
        brain = get_brain()
        if brain and offline_hours > 0 and hasattr(brain, "mood"):
            if 0.3 <= offline_hours <= 2.5:
                brain.mood.energy = min(1.0, brain.mood.energy + 0.2)
                notifications.add("🌸 Даша", "Кажется, я немного вздремнула и стала бодрее.", "info", "😴", 7000)
            elif offline_hours > 8:
                brain.mood.energy = min(1.0, brain.mood.energy + 0.35)
                notifications.add("🌸 Даша", "Я проснулась после долгого сна, доброе возвращение.", "info", "🌅", 7000)
            else:
                brain.mood.energy = max(0.35, brain.mood.energy)
        lifecycle_file.write_text(json.dumps({"last_start": now.isoformat()}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.debug(f"Lifecycle init error: {e}")
    
    notifications.add("DARIA", f"Система запущена v{VERSION}", "success", "🌸", 8000)
    logger.info("Ready!")
    
    app.run(host=host, port=port, debug=debug, threaded=True, ssl_context=ssl_context)


application = app
