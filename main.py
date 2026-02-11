#!/usr/bin/env python3
"""
🌸 DARIA v0.7.4 - AI Desktop Companion
"""

import sys
import os
import argparse
import logging
import threading
from pathlib import Path

# Отключаем Flask логи
import warnings
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════════
#  Version
# ═══════════════════════════════════════════════════════════════════

def get_version() -> str:
    version_file = Path(__file__).parent / 'VERSION'
    if version_file.exists():
        return version_file.read_text().strip()
    return '0.7.4'

VERSION = get_version()

# ═══════════════════════════════════════════════════════════════════
#  Colors & Banner
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

def print_banner():
    # Градиентный баннер
    lines = [
        "",
        f"  {c.PINK}╭{'─'*58}╮{c.END}",
        f"  {c.PINK}│{c.END}                                                          {c.PINK}│{c.END}",
        f"  {c.PINK}│{c.END}      {c.BOLD}{c.PINK}██████{c.PURPLE}╗  {c.PINK}█████{c.PURPLE}╗ {c.PINK}██████{c.PURPLE}╗ {c.PINK}██{c.PURPLE}╗{c.PINK}█████{c.PURPLE}╗{c.END}                   {c.PINK}│{c.END}",
        f"  {c.PINK}│{c.END}      {c.BOLD}{c.PINK}██{c.PURPLE}╔══{c.PINK}██{c.PURPLE}╗{c.PINK}██{c.PURPLE}╔══{c.PINK}██{c.PURPLE}╗{c.PINK}██{c.PURPLE}╔══{c.PINK}██{c.PURPLE}╗{c.PINK}██{c.PURPLE}║{c.PINK}██{c.PURPLE}╔══{c.PINK}██{c.PURPLE}╗{c.END}                 {c.PINK}│{c.END}",
        f"  {c.PINK}│{c.END}      {c.BOLD}{c.PINK}██{c.PURPLE}║  {c.PINK}██{c.PURPLE}║{c.PINK}███████{c.PURPLE}║{c.PINK}██████{c.PURPLE}╔╝{c.PINK}██{c.PURPLE}║{c.PINK}███████{c.PURPLE}║{c.END}                 {c.PINK}│{c.END}",
        f"  {c.PINK}│{c.END}      {c.BOLD}{c.PURPLE}██{c.PINK}║  {c.PURPLE}██{c.PINK}║{c.PURPLE}██{c.PINK}╔══{c.PURPLE}██{c.PINK}║{c.PURPLE}██{c.PINK}╔══{c.PURPLE}██{c.PINK}╗{c.PURPLE}██{c.PINK}║{c.PURPLE}██{c.PINK}╔══{c.PURPLE}██{c.PINK}║{c.END}                 {c.PINK}│{c.END}",
        f"  {c.PINK}│{c.END}      {c.BOLD}{c.PURPLE}██████{c.PINK}╔╝{c.PURPLE}██{c.PINK}║  {c.PURPLE}██{c.PINK}║{c.PURPLE}██{c.PINK}║  {c.PURPLE}██{c.PINK}║{c.PURPLE}██{c.PINK}║{c.PURPLE}██{c.PINK}║  {c.PURPLE}██{c.PINK}║{c.END}                 {c.PINK}│{c.END}",
        f"  {c.PINK}│{c.END}      {c.BOLD}{c.PURPLE}╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝{c.END}                 {c.PINK}│{c.END}",
        f"  {c.PINK}│{c.END}                                                          {c.PINK}│{c.END}",
        f"  {c.PINK}│{c.END}        {c.GRAY}v{VERSION}{c.END}  {c.WHITE}•{c.END}  {c.CYAN}AI Desktop Companion{c.END}  {c.WHITE}•{c.END}  {c.PINK}🌸{c.END}            {c.PINK}│{c.END}",
        f"  {c.PINK}│{c.END}                                                          {c.PINK}│{c.END}",
        f"  {c.PINK}╰{'─'*58}╯{c.END}",
        "",
    ]
    print('\n'.join(lines))

# ═══════════════════════════════════════════════════════════════════
#  NoSleep - Prevent system sleep
# ═══════════════════════════════════════════════════════════════════

class NoSleep:
    """Предотвращает переход системы в спящий режим"""
    
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
        """Windows: SetThreadExecutionState"""
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
        """macOS: caffeinate"""
        try:
            import subprocess
            self._process = subprocess.Popen(['caffeinate', '-d', '-i'])
        except:
            pass
    
    def _start_linux(self):
        """Linux: xdg-screensaver / systemd-inhibit"""
        try:
            import subprocess
            # Try systemd-inhibit first
            self._process = subprocess.Popen([
                'systemd-inhibit', '--what=idle:sleep', 
                '--who=DARIA', '--why=Running', 
                'sleep', 'infinity'
            ])
        except:
            try:
                subprocess.run(['xdg-screensaver', 'suspend', str(os.getpid())])
            except:
                pass

no_sleep = NoSleep()

# ═══════════════════════════════════════════════════════════════════
#  OS Notifications (plyer)
# ═══════════════════════════════════════════════════════════════════

def send_os_notification(title: str, message: str):
    """Отправить системное уведомление через plyer"""
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name='DARIA',
            timeout=10
        )
        return True
    except ImportError:
        logging.debug("plyer not installed, skipping OS notification")
        return False
    except Exception as e:
        logging.debug(f"OS notification failed: {e}")
        return False

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

def setup_logging(debug: bool = False):
    # Отключаем Flask/Werkzeug логи
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    logging.getLogger('flask').setLevel(logging.ERROR)
    
    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(ColoredFormatter())
    
    logger = logging.getLogger('daria')
    logger.setLevel(level)
    logger.handlers = [handler]
    
    return logger

# ═══════════════════════════════════════════════════════════════════
#  System Check
# ═══════════════════════════════════════════════════════════════════

def check_system():
    print(f"\n  {c.CYAN}🔍 Проверка системы...{c.END}\n")
    
    checks = []
    
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    checks.append(('Python', py_ver, sys.version_info >= (3, 10)))
    
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
    
    # Plyer
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
#  Server
# ═══════════════════════════════════════════════════════════════════

def run_server(host: str, port: int, debug: bool, ssl_context):
    logger = setup_logging(debug)
    
    print_banner()
    
    # Start NoSleep
    no_sleep.start()
    logger.info("NoSleep mode активирован")
    
    from web.app import run_server as start_flask
    
    protocol = 'https' if ssl_context else 'http'
    
    print(f"  {c.GREEN}✨ DARIA готова!{c.END}")
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
    print()
    
    # Отправляем системное уведомление
    send_os_notification("🌸 DARIA", "Я запустилась и готова к общению!")
    
    start_flask(
        host=host,
        port=port,
        debug=debug,
        ssl_context=ssl_context
    )

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
    parser.add_argument('--ssl', action='store_true', help='HTTPS')
    parser.add_argument('--ssl-cert', help='SSL сертификат')
    parser.add_argument('--ssl-key', help='SSL ключ')
    parser.add_argument('--check', action='store_true', help='Проверка')
    parser.add_argument('--version', action='store_true', help='Версия')
    parser.add_argument('--no-sleep', action='store_true', default=True, help='NoSleep (по умолчанию вкл)')
    
    args = parser.parse_args()
    
    if args.version:
        print(f"DARIA v{VERSION}")
        return
    
    if args.check:
        print_banner()
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
    
    try:
        run_server(args.host, args.port, args.debug, ssl_context)
    except KeyboardInterrupt:
        no_sleep.stop()
        print(f"\n  {c.PINK}👋 Пока-пока! До встречи! 🌸{c.END}\n")
    except Exception as e:
        no_sleep.stop()
        print(f"\n{c.RED}Ошибка: {e}{c.END}")
        sys.exit(1)

if __name__ == '__main__':
    main()
