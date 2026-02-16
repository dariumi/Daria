#!/usr/bin/env python3
"""
🌸 DARIA v0.9.0 - AI Desktop Companion
"""

import sys
import os
import argparse
import logging
import threading
import platform
import time
import webbrowser
import json
import subprocess
from pathlib import Path
from typing import Optional

# Disable Flask logs
import warnings
warnings.filterwarnings('ignore')


# ═══════════════════════════════════════════════════════════════════
#  Version
# ═══════════════════════════════════════════════════════════════════

def get_version() -> str:
    version_file = Path(__file__).parent / 'VERSION'
    if version_file.exists():
        return version_file.read_text().strip()
    return '0.9.0'

VERSION = get_version()
TRAY_LOG_FILE = Path.home() / ".daria" / "tray.log"
TRAY_ICON_PNG = Path.home() / ".daria" / "cache" / "tray-favicon.png"
TRACE_LOG_FILE = Path.home() / ".daria" / "debug-trace.log"

# ═══════════════════════════════════════════════════════════════════
#  Colors
# ═══════════════════════════════════════════════════════════════════

class Colors:
    PINK = '\033[38;5;213m'
    PURPLE = '\033[38;5;141m'
    CYAN = '\033[38;5;87m'
    GREEN = '\033[38;5;120m'
    YELLOW = '\033[38;5;228m'
    RED = '\033[38;5;210m'
    WHITE = '\033[38;5;255m'
    GRAY = '\033[38;5;245m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'

c = Colors

# ═══════════════════════════════════════════════════════════════════
#  Pulsating Heart Animation (Point #10)
# ═══════════════════════════════════════════════════════════════════

HEART_FRAMES = [
    # Frame 1 - small
    [
        "          ♥ ♥          ",
        "        ♥     ♥        ",
        "         ♥   ♥         ",
        "           ♥           ",
    ],
    # Frame 2 - medium
    [
        "        ♥♥   ♥♥        ",
        "      ♥♥  ♥ ♥  ♥♥      ",
        "       ♥♥     ♥♥       ",
        "         ♥♥ ♥♥         ",
        "           ♥           ",
    ],
    # Frame 3 - big
    [
        "      ♥♥♥♥   ♥♥♥♥      ",
        "    ♥♥    ♥ ♥    ♥♥    ",
        "    ♥♥           ♥♥    ",
        "      ♥♥       ♥♥      ",
        "        ♥♥   ♥♥        ",
        "          ♥♥♥          ",
        "           ♥           ",
    ],
    # Frame 4 - biggest
    [
        "     ♥♥♥♥♥   ♥♥♥♥♥     ",
        "   ♥♥     ♥ ♥     ♥♥   ",
        "   ♥♥             ♥♥   ",
        "    ♥♥           ♥♥    ",
        "      ♥♥       ♥♥      ",
        "        ♥♥   ♥♥        ",
        "          ♥♥♥          ",
        "           ♥           ",
    ],
]

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_heart_frame(frame_idx, message="", color=None):
    """Print a single heart frame centered"""
    if color is None:
        colors = [c.PINK, c.RED, c.PURPLE, c.PINK]
        color = colors[frame_idx % len(colors)]

    frame = HEART_FRAMES[frame_idx % len(HEART_FRAMES)]
    width = 60

    lines = [
        "",
        f"{c.GRAY}{'─' * width}{c.END}",
    ]

    for line in frame:
        padded = line.center(width)
        lines.append(f"  {color}{c.BOLD}{padded}{c.END}")

    lines.append("")
    lines.append(f"  {c.WHITE}{c.BOLD}{'DARIA'.center(width)}{c.END}")
    lines.append(f"  {c.GRAY}{'v' + VERSION + ' • AI Desktop Companion'.center(width)}{c.END}")
    lines.append("")

    if message:
        lines.append(f"  {c.CYAN}{message.center(width)}{c.END}")
    else:
        lines.append(f"  {c.GRAY}{'Загрузка...'.center(width)}{c.END}")

    lines.append(f"{c.GRAY}{'─' * width}{c.END}")

    return '\n'.join(lines)


def animate_loading(stop_event, status_ref):
    """Animate pulsating heart during loading"""
    frame = 0
    while not stop_event.is_set():
        clear_screen()
        msg = status_ref.get("message", "Загрузка...")
        print(print_heart_frame(frame, msg))
        frame = (frame + 1) % len(HEART_FRAMES)
        time.sleep(0.5)


# ═══════════════════════════════════════════════════════════════════
#  NoSleep - Prevent system sleep
# ═══════════════════════════════════════════════════════════════════

class NoSleep:
    def __init__(self):
        self.running = False
        self._thread = None
        self._platform = sys.platform

    def start(self):
        if self.running:
            return
        self.running = True
        if self._platform == 'win32':
            self._start_windows()
        elif self._platform == 'darwin':
            self._start_macos()
        else:
            self._start_linux()

    def stop(self):
        self.running = False
        if self._platform == 'win32':
            self._stop_windows()

    def _start_windows(self):
        try:
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_DISPLAY_REQUIRED = 0x00000002
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )
        except:
            pass

    def _stop_windows(self):
        try:
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        except:
            pass

    def _start_macos(self):
        try:
            import subprocess
            self._process = subprocess.Popen(['caffeinate', '-d', '-i'])
        except:
            pass

    def _start_linux(self):
        try:
            import subprocess
            self._process = subprocess.Popen([
                'systemd-inhibit', '--what=idle:sleep',
                '--who=DARIA', '--why=Running',
                'sleep', 'infinity'
            ])
        except:
            try:
                import subprocess
                subprocess.run(['xdg-screensaver', 'suspend', str(os.getpid())])
            except:
                pass

no_sleep = NoSleep()

# ═══════════════════════════════════════════════════════════════════
#  OS Notifications
# ═══════════════════════════════════════════════════════════════════

def send_os_notification(title: str, message: str):
    try:
        from plyer import notification
        notification.notify(title=title, message=message, app_name='DARIA', timeout=10)
        return True
    except ImportError:
        return False
    except Exception:
        return False

# ═══════════════════════════════════════════════════════════════════
#  OS-Dependent Server Setup (Point #8)
# ═══════════════════════════════════════════════════════════════════

def get_os_type() -> str:
    """Determine OS type"""
    system = platform.system().lower()
    if system == 'darwin':
        return 'macos'
    elif system == 'windows':
        return 'windows'
    return 'linux'

def setup_server_env(os_type: str):
    """Setup environment variables based on OS"""
    cpu_threads = max(2, min(6, int((os.cpu_count() or 4) / 2)))
    os.environ.setdefault("HF_HOME", str(Path.home() / ".daria" / "hf-cache"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(Path.home() / ".daria" / "hf-cache"))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(Path.home() / ".daria" / "hf-cache"))
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True,max_split_size_mb:128")
    os.environ.setdefault("OMP_NUM_THREADS", str(cpu_threads))
    os.environ.setdefault("MKL_NUM_THREADS", str(cpu_threads))
    os.environ.setdefault("NUMEXPR_MAX_THREADS", str(cpu_threads))
    if os_type == 'windows':
        os.environ.setdefault('FLASK_ENV', 'production')
        os.environ.setdefault('DARIA_SERVER', 'waitress')
        # Windows-specific: disable ANSI in some terminals
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except:
            pass
    elif os_type == 'macos':
        os.environ.setdefault('FLASK_ENV', 'production')
        os.environ.setdefault('DARIA_SERVER', 'flask')
        os.environ.setdefault('OBJC_DISABLE_INITIALIZE_FORK_SAFETY', 'YES')
    else:  # linux
        os.environ.setdefault('FLASK_ENV', 'production')
        os.environ.setdefault('DARIA_SERVER', 'flask')

def run_with_server(app_module, host, port, debug, ssl_context, os_type):
    """Run Flask with appropriate server for OS (Point #8)"""
    server_type = os.environ.get('DARIA_SERVER', 'flask')

    if server_type == 'waitress' and not debug:
        try:
            from waitress import serve
            serve(app_module, host=host, port=port)
            return
        except ImportError:
            pass

    # Default Flask dev server
    from web.app import run_server as start_flask
    start_flask(host=host, port=port, debug=debug, ssl_context=ssl_context)


# ═══════════════════════════════════════════════════════════════════
#  Logger
# ═══════════════════════════════════════════════════════════════════

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': c.GRAY, 'INFO': c.GREEN,
        'WARNING': c.YELLOW, 'ERROR': c.RED
    }
    ICONS = {'DEBUG': '🔍', 'INFO': '✨', 'WARNING': '⚠️', 'ERROR': '❌'}

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        icon = self.ICONS.get(record.levelname, '')
        time_str = self.formatTime(record, '%H:%M:%S')
        return f"{color}{icon} [{time_str}] {record.getMessage()}{c.END}"

def setup_logging(debug: bool = False, trace: bool = False):
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    logging.getLogger('flask').setLevel(logging.ERROR)

    level = logging.DEBUG if debug else logging.INFO
    stream_handler = logging.StreamHandler()
    if trace:
        stream_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(module)s:%(funcName)s:%(lineno)d | %(message)s",
            datefmt="%H:%M:%S",
        ))
    else:
        stream_handler.setFormatter(ColoredFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [stream_handler]

    if trace:
        try:
            TRACE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(TRACE_LOG_FILE, encoding="utf-8")
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(module)s:%(funcName)s:%(lineno)d | %(message)s"
            ))
            root.addHandler(file_handler)
        except Exception:
            pass

    logger = logging.getLogger('daria')
    logger.setLevel(level)
    return logger

# ═══════════════════════════════════════════════════════════════════
#  System Check
# ═══════════════════════════════════════════════════════════════════

def check_system():
    print(f"\n  {c.CYAN}🔍 Проверка системы...{c.END}\n")

    checks = []
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    checks.append(('Python', py_ver, sys.version_info >= (3, 10)))

    os_type = get_os_type()
    checks.append(('ОС', f"{platform.system()} ({os_type})", True))

    try:
        from core.config import get_config
        config = get_config()
        checks.append(('Конфигурация', '✓', True))
    except Exception as e:
        checks.append(('Конфигурация', str(e)[:30], False))

    try:
        from core.llm import get_llm
        llm = get_llm()
        status = llm.check_availability()
        if status.get('available'):
            model = '✓' if status.get('model_loaded') else 'Нет модели'
            checks.append(('Ollama', model, status.get('model_loaded', False)))
        else:
            checks.append(('Ollama', 'Недоступна', False))
    except Exception as e:
        checks.append(('Ollama', str(e)[:30], False))

    try:
        from core.memory import get_memory
        memory = get_memory()
        stats = memory.get_stats()
        checks.append(('Память', f"{stats.get('facts', 0)} фактов", True))
    except Exception as e:
        checks.append(('Память', str(e)[:30], False))

    try:
        from plyer import notification
        checks.append(('Plyer (уведомления)', '✓', True))
    except:
        checks.append(('Plyer', 'Не установлен', False))

    for name, value, ok in checks:
        status = f"{c.GREEN}✓{c.END}" if ok else f"{c.YELLOW}○{c.END}"
        print(f"    {status} {c.WHITE}{name}:{c.END} {c.GRAY}{value}{c.END}")
    print()

# ═══════════════════════════════════════════════════════════════════
#  Server with animated loading (Point #10)
# ═══════════════════════════════════════════════════════════════════

def run_server(host: str, port: int, debug: bool, ssl_context, trace: bool = False):
    logger = setup_logging(debug, trace=trace)
    os_type = get_os_type()
    setup_server_env(os_type)

    # Start animated loading
    stop_anim = threading.Event()
    status = {"message": "Инициализация..."}

    anim_thread = threading.Thread(target=animate_loading, args=(stop_anim, status), daemon=True)
    anim_thread.start()

    # Load components with status updates
    no_sleep.start()
    status["message"] = "NoSleep активирован..."
    time.sleep(0.3)

    status["message"] = "Загрузка мозга..."
    time.sleep(0.3)

    status["message"] = "Загрузка памяти..."
    time.sleep(0.3)

    status["message"] = "Загрузка плагинов..."
    time.sleep(0.3)

    status["message"] = "Почти готово..."
    time.sleep(0.5)

    # Stop animation
    stop_anim.set()
    time.sleep(0.1)
    clear_screen()

    # Print final startup info (pinned at top, logs below)
    protocol = 'https' if ssl_context else 'http'

    print(f"\n  {c.PINK}{'─' * 58}{c.END}")
    print(f"  {c.PINK}♥{c.END}  {c.BOLD}{c.WHITE}DARIA v{VERSION}{c.END} — {c.CYAN}AI Desktop Companion{c.END}  {c.PINK}♥{c.END}")
    print(f"  {c.PINK}{'─' * 58}{c.END}")
    print()
    print(f"  {c.GREEN}✨ DARIA готова!{c.END}  |  {c.GRAY}ОС: {os_type}{c.END}")
    print()
    print(f"    {c.WHITE}Локально:{c.END}  {c.CYAN}{protocol}://localhost:{port}{c.END}")

    if host == '0.0.0.0':
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print(f"    {c.WHITE}Сеть:{c.END}      {c.CYAN}{protocol}://{local_ip}:{port}{c.END}")
        except:
            pass

    print()
    print(f"    {c.GRAY}Нажми Ctrl+C для остановки{c.END}")
    print(f"  {c.PINK}{'─' * 58}{c.END}")
    print()

    send_os_notification("🌸 DARIA", "Я запустилась и готова к общению!")

    logger.info(f"DARIA v{VERSION} запущена на {os_type}")

    from web.app import run_server as start_flask
    start_flask(host=host, port=port, debug=debug, ssl_context=ssl_context)


def _autostart_path() -> Path:
    home = Path.home()
    if sys.platform.startswith("linux"):
        return home / ".config" / "autostart" / "daria.desktop"
    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", home))
        return appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "DARIA.bat"
    return home / ".daria" / "autostart.unsupported"


def set_autostart(enabled: bool, host: str = "127.0.0.1", port: int = 7777):
    p = _autostart_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    if not enabled:
        if p.exists():
            p.unlink()
        return
    project = Path(__file__).resolve().parent
    if sys.platform.startswith("linux"):
        p.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=DARIA\n"
            f"Exec={sys.executable} {project / 'main.py'} --host {host} --port {port} --tray\n"
            "X-GNOME-Autostart-enabled=true\n",
            encoding="utf-8",
        )
        return
    if sys.platform == "win32":
        p.write_text(
            f"@echo off\n\"{sys.executable}\" \"{project / 'main.py'}\" --host {host} --port {port} --tray\n",
            encoding="utf-8",
        )


def run_tray(host: str, port: int, debug: bool, ssl_context, trace: bool = False):
    setup_logging(debug, trace=trace)
    if sys.platform.startswith("linux"):
        # Do not hard-force appindicator: on some DE/Wayland setups it breaks context menu behavior.
        preferred_backend = os.environ.get("DARIA_TRAY_BACKEND", "").strip()
        if preferred_backend:
            os.environ["PYSTRAY_BACKEND"] = preferred_backend
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception:
        # Fallback to normal mode if tray deps unavailable
        run_server(host, port, debug, ssl_context, trace=trace)
        return

    from web.app import run_server as start_flask
    server_thread = threading.Thread(
        target=start_flask,
        kwargs={"host": host, "port": port, "debug": debug, "ssl_context": ssl_context},
        daemon=True
    )
    server_thread.start()

    def ensure_tray_icon_png() -> Optional[Path]:
        project = Path(__file__).resolve().parent
        svg = project / "web" / "static" / "favicon.svg"
        if not svg.exists():
            return None
        try:
            TRAY_ICON_PNG.parent.mkdir(parents=True, exist_ok=True)
            # 1) python converter, if available
            try:
                import cairosvg  # type: ignore
                cairosvg.svg2png(url=str(svg), write_to=str(TRAY_ICON_PNG), output_width=64, output_height=64)
                if TRAY_ICON_PNG.exists():
                    return TRAY_ICON_PNG
            except Exception:
                pass
            # 2) system converters
            for cmd in (
                ["rsvg-convert", "-w", "64", "-h", "64", str(svg), "-o", str(TRAY_ICON_PNG)],
                ["inkscape", str(svg), "--export-type=png", "--export-filename", str(TRAY_ICON_PNG), "-w", "64", "-h", "64"],
            ):
                try:
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if TRAY_ICON_PNG.exists():
                        return TRAY_ICON_PNG
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def make_icon():
        project = Path(__file__).resolve().parent
        icon_candidates = []
        tray_png = ensure_tray_icon_png()
        if tray_png:
            icon_candidates.append(tray_png)
        icon_candidates.extend([
            project / "web" / "static" / "img" / "logo.png",
            project / "web" / "static" / "favicon.png",
        ])
        for p in icon_candidates:
            if p.exists():
                try:
                    return Image.open(p).convert("RGBA").resize((64, 64))
                except Exception:
                    pass
        img = Image.new("RGBA", (64, 64), (255, 105, 180, 255))
        d = ImageDraw.Draw(img)
        d.ellipse((8, 8, 56, 56), fill=(255, 20, 147, 255))
        d.text((20, 20), "D", fill=(255, 255, 255, 255))
        return img

    def open_ui(_icon=None, _item=None):
        proto = "https" if ssl_context else "http"
        webbrowser.open(f"{proto}://localhost:{port}")

    def open_trace_log(_icon=None, _item=None):
        try:
            TRACE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            if not TRACE_LOG_FILE.exists():
                TRACE_LOG_FILE.write_text("Trace log initialized.\n", encoding="utf-8")
            if sys.platform.startswith("linux"):
                subprocess.Popen(["xdg-open", str(TRACE_LOG_FILE)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(TRACE_LOG_FILE)])
            elif sys.platform == "win32":
                os.startfile(str(TRACE_LOG_FILE))  # type: ignore[attr-defined]
        except Exception:
            pass

    def open_log_file(_icon=None, _item=None):
        try:
            TRAY_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            if not TRAY_LOG_FILE.exists():
                TRAY_LOG_FILE.write_text("DARIA tray log initialized.\n", encoding="utf-8")
            if sys.platform.startswith("linux"):
                subprocess.Popen(["xdg-open", str(TRAY_LOG_FILE)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(TRAY_LOG_FILE)])
            elif sys.platform == "win32":
                os.startfile(str(TRAY_LOG_FILE))  # type: ignore[attr-defined]
        except Exception:
            pass

    def toggle_autostart(_icon=None, _item=None):
        p = _autostart_path()
        enable = not p.exists()
        set_autostart(enable, host, port)

    def quit_all(icon, _item=None):
        try:
            icon.stop()
        finally:
            os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Открыть DARIA", open_ui, default=True),
        pystray.MenuItem("Открыть trace-лог", open_trace_log),
        pystray.MenuItem("Открыть лог-файл", open_log_file),
        pystray.MenuItem("Автозапуск", toggle_autostart),
        pystray.MenuItem("Выход", quit_all),
    )
    icon = pystray.Icon("DARIA", make_icon(), "DARIA", menu)
    icon.run()

# ═══════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='🌸 DARIA - AI Desktop Companion',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--host', default='127.0.0.1', help='Хост')
    parser.add_argument('--port', type=int, default=7777, help='Порт')
    parser.add_argument('--debug', action='store_true', help='Debug')
    parser.add_argument('--debug-trace', action='store_true', help='Трассировка запросов/функций в терминал и ~/.daria/debug-trace.log')
    parser.add_argument('--ssl', action='store_true', help='HTTPS')
    parser.add_argument('--ssl-cert', help='SSL сертификат')
    parser.add_argument('--ssl-key', help='SSL ключ')
    parser.add_argument('--check', action='store_true', help='Проверка')
    parser.add_argument('--version', action='store_true', help='Версия')
    parser.add_argument('--no-sleep', action='store_true', default=True, help='NoSleep')
    parser.add_argument('--tray', action='store_true', help='Запуск в системном трее (если доступно)')
    parser.add_argument('--tray-daemon', action='store_true', help=argparse.SUPPRESS)

    args = parser.parse_args()

    if args.version:
        print(f"DARIA v{VERSION}")
        return

    if args.check:
        check_system()
        return

    ssl_context = None
    if args.ssl:
        if args.ssl_cert and args.ssl_key:
            ssl_context = (args.ssl_cert, args.ssl_key)
        else:
            home = Path.home()
            cert = home / '.daria' / 'ssl' / 'cert.pem'
            key = home / '.daria' / 'ssl' / 'key.pem'
            if cert.exists() and key.exists():
                ssl_context = (str(cert), str(key))
            else:
                print(f"{c.RED}SSL сертификаты не найдены!{c.END}")
                sys.exit(1)

    # If launched from terminal in tray mode, detach into background so tray keeps running
    # even after terminal window is closed.
    if args.tray and not args.tray_daemon and os.name != "nt":
        try:
            is_tty = sys.stdin.isatty()
        except Exception:
            is_tty = False
        if is_tty:
            TRAY_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            cmd = [
                sys.executable, str(Path(__file__).resolve()),
                "--host", args.host,
                "--port", str(args.port),
                "--tray",
                "--tray-daemon",
            ]
            if args.debug:
                cmd.append("--debug")
            if args.debug_trace:
                cmd.append("--debug-trace")
            if args.ssl:
                cmd.append("--ssl")
            if args.ssl_cert:
                cmd.extend(["--ssl-cert", args.ssl_cert])
            if args.ssl_key:
                cmd.extend(["--ssl-key", args.ssl_key])
            with open(TRAY_LOG_FILE, "a", encoding="utf-8") as logf:
                subprocess.Popen(
                    cmd,
                    stdout=logf,
                    stderr=logf,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
            print(f"{c.GREEN}DARIA запущена в трее. Лог: {TRAY_LOG_FILE}{c.END}")
            return

    try:
        if args.tray:
            run_tray(args.host, args.port, args.debug, ssl_context, trace=args.debug_trace)
        else:
            run_server(args.host, args.port, args.debug, ssl_context, trace=args.debug_trace)
    except KeyboardInterrupt:
        no_sleep.stop()
        print(f"\n  {c.PINK}👋 Пока-пока! До встречи! 🌸{c.END}\n")
    except Exception as e:
        no_sleep.stop()
        print(f"\n{c.RED}Ошибка: {e}{c.END}")
        sys.exit(1)

if __name__ == '__main__':
    main()
