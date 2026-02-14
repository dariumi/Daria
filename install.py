#!/usr/bin/env python3
"""
🌸 DARIA Installation Script
- Installation profiles (base/recommended/full)
- Optional extras for senses/files/tray/music
- Autostart configuration
"""

import os, sys, subprocess, platform, shutil, socket, json
from pathlib import Path

def _read_version() -> str:
    try:
        return Path("VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        return "0.8.5.1"

VERSION = _read_version()
DEFAULT_PORT = 7777
LOCAL_DOMAIN = "dasha.local"

INSTALL_PROFILES = {
    "1": {
        "id": "base",
        "label": "Базовая",
        "desc": "Только ядро DARIA (минимум зависимостей).",
        "extras": [],
    },
    "2": {
        "id": "recommended",
        "label": "Рекомендуемая",
        "desc": "Ядро + визуальные/офисные функции + трей.",
        "extras": ["Pillow>=10.0.0", "pystray>=0.19.5", "python-docx>=1.1.0", "openpyxl>=3.1.2"],
    },
    "3": {
        "id": "full",
        "label": "Полная",
        "desc": "Все возможности + speech stack (может ставиться дольше).",
        "extras": [
            "Pillow>=10.0.0", "pystray>=0.19.5", "python-docx>=1.1.0", "openpyxl>=3.1.2",
            "SpeechRecognition>=3.10.0", "pydub>=0.25.1",
        ],
    },
}

class C:
    PINK = '\033[38;5;213m'
    PURPLE = '\033[38;5;141m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'

if platform.system() == 'Windows':
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
    except:
        for a in dir(C):
            if not a.startswith('_'): setattr(C, a, '')

def banner():
    print(f"""
{C.PINK}{C.BOLD}
  ╭────────────────────────────────────────────────────────╮
  │                                                        │
  │      ♥♥♥♥♥   ♥♥♥♥♥                                    │
  │    ♥♥     ♥ ♥     ♥♥    DARIA                          │
  │    ♥♥             ♥♥    v{VERSION}                          │
  │      ♥♥         ♥♥      AI Desktop Companion           │
  │        ♥♥     ♥♥        Installer                      │
  │          ♥♥ ♥♥                                         │
  │            ♥                                           │
  │                                                        │
  ╰────────────────────────────────────────────────────────╯
{C.END}""")

def step(m, i="🔹"): print(f"\n{C.CYAN}{i} {m}{C.END}")
def ok(m): print(f"  {C.GREEN}✓ {m}{C.END}")
def warn(m): print(f"  {C.YELLOW}⚠ {m}{C.END}")
def err(m): print(f"  {C.RED}✗ {m}{C.END}")
def info(m): print(f"  {C.CYAN}ℹ {m}{C.END}")

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

def get_info():
    system = platform.system()
    is_admin = False
    if system != 'Windows':
        try:
            is_admin = os.geteuid() == 0
        except:
            pass
    return {'system': system, 'is_windows': system == 'Windows', 'is_macos': system == 'Darwin',
            'is_admin': is_admin, 'home': Path.home(), 'cwd': Path.cwd()}

def check_python():
    step("Проверка Python", "🐍")
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        err(f"Python {v.major}.{v.minor} - нужен 3.10+")
        return False
    ok(f"Python {v.major}.{v.minor}.{v.micro}")
    return True


def choose_install_profile():
    step("Тип установки", "🧭")
    for key, profile in INSTALL_PROFILES.items():
        print(f"  {C.CYAN}{key}) {profile['label']}{C.END} — {profile['desc']}")
    try:
        choice = input(f"\n{C.CYAN}Выбери профиль [2]: {C.END}").strip() or "2"
    except (EOFError, KeyboardInterrupt):
        choice = "2"
    if choice not in INSTALL_PROFILES:
        warn("Неизвестный выбор, использую 'Рекомендуемая'")
        choice = "2"
    p = INSTALL_PROFILES[choice]
    ok(f"Профиль: {p['label']}")
    return p

def setup_venv(info):
    step("Виртуальное окружение", "📦")
    venv = info['cwd'] / 'venv'
    if not venv.exists():
        subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
        ok("Создано")
    else:
        warn("Уже существует")
    pip = venv / ('Scripts' if info['is_windows'] else 'bin') / ('pip.exe' if info['is_windows'] else 'pip')
    return pip

def install_deps(pip, profile):
    step("Зависимости", "📚")
    subprocess.run([str(pip), 'install', '--upgrade', 'pip', '-q'], check=True)
    ok("pip обновлён")
    if Path('requirements.txt').exists():
        info("Устанавливаю пакеты...")
        subprocess.run([str(pip), 'install', '-r', 'requirements.txt', '-q'], check=True)
        ok("Базовые зависимости установлены")
    extras = profile.get("extras", [])
    if extras:
        info(f"Устанавливаю дополнительные пакеты ({profile['id']})...")
        try:
            subprocess.run([str(pip), 'install', *extras, '-q'], check=True)
            ok("Дополнительные зависимости установлены")
        except subprocess.CalledProcessError as e:
            warn(f"Часть дополнительных зависимостей не установилась: {e}")
    return False

def setup_dirs(info):
    step("Директории", "📁")
    d = info['home'] / '.daria'
    for sub in ['plugins', 'data', 'uploads', 'files', 'ssl', 'chats', 'learning', 'memory']:
        (d / sub).mkdir(parents=True, exist_ok=True)
    ok(f"{d}")
    return d

def setup_ssl(info, daria_dir):
    step("SSL сертификат", "🔐")
    ssl_dir = daria_dir / 'ssl'
    cert, key = ssl_dir / 'cert.pem', ssl_dir / 'key.pem'

    if cert.exists() and key.exists():
        warn("Уже существует")
        try:
            answer = input(f"  {C.CYAN}Перегенерировать? [y/N]: {C.END}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = 'n'
        if answer != 'y':
            ok("Оставлено без изменений")
            return True
        # Remove old certs before regenerating (FIXED: Point #9)
        try:
            if cert.exists():
                cert.unlink()
            if key.exists():
                key.unlink()
        except Exception as e:
            err(f"Не удалось удалить старые сертификаты: {e}")
            return False

    if not shutil.which('openssl'):
        warn("OpenSSL не найден")
        return False

    ip = get_ip()
    info_msg = f"IP: {ip}"
    print(f"  {C.CYAN}ℹ {info_msg}{C.END}")

    cfg = ssl_dir / 'openssl.cnf'
    cfg.write_text(f"""[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_req

[dn]
CN = DARIA

[v3_req]
basicConstraints = CA:TRUE
keyUsage = digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = {LOCAL_DOMAIN}
IP.1 = 127.0.0.1
IP.2 = {ip}
""")

    try:
        result = subprocess.run(['openssl', 'req', '-x509', '-nodes', '-days', '365', '-newkey', 'rsa:2048',
                       '-keyout', str(key), '-out', str(cert), '-config', str(cfg)],
                      check=True, capture_output=True, text=True)
        try:
            cfg.unlink()
        except:
            pass
        ok("Создан")
        return True
    except subprocess.CalledProcessError as e:
        err(f"Ошибка OpenSSL: {e.stderr[:100] if e.stderr else 'unknown'}")
        # Cleanup on failure
        try:
            cfg.unlink()
        except:
            pass
        return False
    except Exception as e:
        err(f"Ошибка: {e}")
        return False

def check_ollama():
    step("Ollama", "🤖")
    if not shutil.which('ollama'):
        warn("Не найдена - https://ollama.ai")
        return False
    ok("Найдена")
    return True

def install_plugins(daria_dir):
    step("Плагины", "🧩")
    src, dst = Path('plugins'), daria_dir / 'plugins'
    count = 0
    if src.exists():
        for p in src.iterdir():
            if p.is_dir() and (p / 'plugin.yaml').exists():
                d = dst / p.name
                if d.exists(): shutil.rmtree(d)
                shutil.copytree(p, d)
                ok(p.name)
                count += 1
    if count == 0:
        info("Нет плагинов для установки")

def _autostart_path(nfo):
    home = nfo["home"]
    if nfo["is_windows"]:
        appdata = Path(os.environ.get("APPDATA", home))
        return appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "DARIA.bat"
    if nfo["is_macos"]:
        return home / "Library" / "LaunchAgents" / "com.daria.app.plist"
    return home / ".config" / "autostart" / "daria.desktop"


def configure_autostart(nfo, use_tray=False):
    step("Автозапуск", "🟢")
    try:
        ans = input(f"  {C.CYAN}Включить автозапуск DARIA? [y/N]: {C.END}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = "n"

    target = _autostart_path(nfo)
    if ans != "y":
        if target.exists():
            target.unlink()
            ok("Старый автозапуск удалён")
        else:
            info("Автозапуск выключен")
        return False

    target.parent.mkdir(parents=True, exist_ok=True)
    project = nfo["cwd"]
    py = sys.executable
    tray_arg = "--tray " if use_tray else ""

    if nfo["is_windows"]:
        target.write_text(
            f"@echo off\ncd /d \"{project}\"\n\"{py}\" \"{project / 'main.py'}\" {tray_arg}--port {DEFAULT_PORT}\n",
            encoding="utf-8",
        )
    elif nfo["is_macos"]:
        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.daria.app</string>
  <key>ProgramArguments</key>
  <array><string>{py}</string><string>{project / 'main.py'}</string>{'<string>--tray</string>' if use_tray else ''}<string>--port</string><string>{DEFAULT_PORT}</string></array>
  <key>RunAtLoad</key><true/>
  <key>WorkingDirectory</key><string>{project}</string>
</dict></plist>"""
        target.write_text(plist, encoding="utf-8")
    else:
        target.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=DARIA\n"
            f"Exec={py} {project / 'main.py'} {tray_arg}--port {DEFAULT_PORT}\n"
            "X-GNOME-Autostart-enabled=true\n",
            encoding="utf-8",
        )
    ok(f"Автозапуск включён: {target}")
    return True


def create_scripts(info, daria_dir):
    step("Скрипты запуска", "🚀")
    cert, key = daria_dir / 'ssl' / 'cert.pem', daria_dir / 'ssl' / 'key.pem'

    if info['is_windows']:
        Path('start.bat').write_text(
            f'@echo off\ncall venv\\Scripts\\activate\npython main.py --port {DEFAULT_PORT} %*\n',
            encoding='utf-8')
        ok("start.bat")
        Path('start-tray.bat').write_text(
            f'@echo off\ncall venv\\Scripts\\activate\npython main.py --tray --port {DEFAULT_PORT} %*\n',
            encoding='utf-8')
        ok("start-tray.bat")
        if cert.exists():
            Path('start-https.bat').write_text(
                f'@echo off\ncall venv\\Scripts\\activate\n'
                f'python main.py --ssl --ssl-cert "{cert}" --ssl-key "{key}" --host 0.0.0.0 --port {DEFAULT_PORT} %*\n',
                encoding='utf-8')
            ok("start-https.bat")
    else:
        s = Path('start.sh')
        s.write_text(f'#!/bin/bash\nsource venv/bin/activate\npython main.py --port {DEFAULT_PORT} "$@"\n')
        s.chmod(0o755)
        ok("start.sh")
        t = Path('start-tray.sh')
        t.write_text(f'#!/bin/bash\nsource venv/bin/activate\npython main.py --tray --port {DEFAULT_PORT} "$@"\n')
        t.chmod(0o755)
        ok("start-tray.sh")
        if cert.exists():
            h = Path('start-https.sh')
            h.write_text(
                f'#!/bin/bash\nsource venv/bin/activate\n'
                f'python main.py --ssl --ssl-cert "{cert}" --ssl-key "{key}" --host 0.0.0.0 --port {DEFAULT_PORT} "$@"\n')
            h.chmod(0o755)
            ok("start-https.sh")

def save_install_config(daria_dir, profile_id: str, autostart: bool, tray_default: bool):
    cfg = {
        "profile": profile_id,
        "autostart": autostart,
        "tray_default": tray_default,
        "version": VERSION,
        "installed_at": str(Path().cwd()),
    }
    (daria_dir / "install_config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def print_final(info, daria_dir, profile_id: str, autostart_enabled: bool, tray_default: bool):
    ssl_ok = (daria_dir / 'ssl' / 'cert.pem').exists()
    ip = get_ip()
    cmd = "start.bat" if info['is_windows'] else "./start.sh"
    tray_cmd = "start-tray.bat" if info['is_windows'] else "./start-tray.sh"
    hcmd = "start-https.bat" if info['is_windows'] else "./start-https.sh"

    print(f"""
{C.PINK}{C.BOLD}
  ╭────────────────────────────────────────────────────────╮
  │      ♥  Установка DARIA v{VERSION} завершена!  ♥           │
  ├────────────────────────────────────────────────────────┤
  │                                                        │
  │  {C.GREEN}Запуск:{C.PINK}  {C.CYAN}{cmd:<46}{C.PINK}│
  │  {C.GREEN}Трей:{C.PINK}    {C.CYAN}{tray_cmd:<46}{C.PINK}│""")

    if ssl_ok:
        print(f"""  │  {C.GREEN}HTTPS:{C.PINK}   {C.CYAN}{hcmd:<46}{C.PINK}│
  │                                                        │
  │  {C.YELLOW}Адреса:{C.PINK}                                              │
  │    {C.CYAN}http://localhost:{DEFAULT_PORT}{C.PINK}                               │
  │    {C.CYAN}https://{ip}:{DEFAULT_PORT}{C.PINK}                             │""")

    print(f"""  │                                                        │
  │  {C.YELLOW}Профиль:{C.PINK} {profile_id:<38}│
  │  {C.YELLOW}Автозапуск:{C.PINK} {"включён" if autostart_enabled else "выключен":<35}│
  │  {C.YELLOW}Трей по умолчанию:{C.PINK} {"да" if tray_default else "нет":<28}│
  │                                                        │
  ├────────────────────────────────────────────────────────┤
  │  {C.YELLOW}Ollama:{C.PINK}  ollama serve                                │
  │  {C.YELLOW}Модель:{C.PINK}  ollama pull llama3.1:8b-instruct-q4_K_M     │
  ╰────────────────────────────────────────────────────────╯
{C.END}""")

def main():
    banner()
    nfo = get_info()
    os_name = "Windows" if nfo['is_windows'] else ("macOS" if nfo['is_macos'] else "Linux")
    print(f"  {C.CYAN}ℹ Система: {os_name} ({platform.machine()}){C.END}")

    if not check_python(): sys.exit(1)

    profile = choose_install_profile()
    pip = setup_venv(nfo)
    install_deps(pip, profile)
    daria_dir = setup_dirs(nfo)

    try:
        ssl_answer = input(f"\n{C.CYAN}🔐 Настроить SSL? [Y/n]: {C.END}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ssl_answer = 'n'

    if ssl_answer != 'n':
        setup_ssl(nfo, daria_dir)

    try:
        tray_ans = input(f"\n{C.CYAN}🪟 Использовать трей по умолчанию в скриптах? [Y/n]: {C.END}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        tray_ans = 'y'
    tray_default = tray_ans != 'n'

    check_ollama()
    install_plugins(daria_dir)
    create_scripts(nfo, daria_dir)
    autostart_enabled = configure_autostart(nfo, use_tray=tray_default)
    save_install_config(daria_dir, profile["id"], autostart_enabled, tray_default)
    print_final(nfo, daria_dir, profile["id"], autostart_enabled, tray_default)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}Прервано{C.END}")
    except Exception as e:
        print(f"\n{C.RED}Ошибка: {e}{C.END}")
        sys.exit(1)
