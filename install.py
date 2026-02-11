#!/usr/bin/env python3
"""
🌸 DARIA v0.7.4 Installation Script
"""

import os, sys, subprocess, platform, shutil, socket
from pathlib import Path

VERSION = "0.7.4"
DEFAULT_PORT = 7777
LOCAL_DOMAIN = "dasha.local"

class C:
    PINK = '\033[95m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'
class Colors:
    PINK = '\033[38;5;213m'
    PURPLE = '\033[38;5;141m'
    LAVENDER = '\033[38;5;183m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
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
    print(f"""{Colors.PINK}
╔══════════════════════════════════════════════╗
║{Colors.LAVENDER}    ██████╗  █████╗ ██████╗ ██╗ █████╗        {Colors.PINK}║
║{Colors.LAVENDER}    ██╔══██╗██╔══██╗██╔══██╗██║██╔══██╗       {Colors.PINK}║
║{Colors.PURPLE}    ██║  ██║███████║██████╔╝██║███████║       {Colors.PINK}║
║{Colors.PURPLE}    ██║  ██║██╔══██║██╔══██╗██║██╔══██║       {Colors.PINK}║
║{Colors.PURPLE}    ██████╔╝██║  ██║██║  ██║██║██║  ██║       {Colors.PINK}║
║{Colors.PURPLE}    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝       {Colors.PINK}║
║{Colors.LAVENDER}         🌸 v{VERSION} •  Installer 🌸            {Colors.PINK}║
╚══════════════════════════════════════════════╝{Colors.END}
""")



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
    is_admin = os.geteuid() == 0 if system != 'Windows' else False
    return {'system': system, 'is_windows': system == 'Windows', 'is_admin': is_admin, 'home': Path.home(), 'cwd': Path.cwd()}

def check_python():
    step("Проверка Python", "🐍")
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        err(f"Python {v.major}.{v.minor} - нужен 3.10+")
        return False
    ok(f"Python {v.major}.{v.minor}.{v.micro}")
    return True

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

def install_deps(pip):
    step("Зависимости", "📚")
    subprocess.run([str(pip), 'install', '--upgrade', 'pip', '-q'], check=True)
    ok("pip обновлён")
    if Path('requirements.txt').exists():
        info("Устанавливаю пакеты...")
        subprocess.run([str(pip), 'install', '-r', 'requirements.txt', '-q'], check=True)
        ok("Установлены")
        return True
    return False

def setup_dirs(info):
    step("Директории", "📁")
    d = info['home'] / '.daria'
    for sub in ['plugins', 'data', 'uploads', 'files', 'ssl', 'chats']:
        (d / sub).mkdir(parents=True, exist_ok=True)
    ok(f"{d}")
    return d

def setup_ssl(info, daria_dir):
    step("SSL сертификат", "🔐")
    ssl_dir = daria_dir / 'ssl'
    cert, key = ssl_dir / 'cert.pem', ssl_dir / 'key.pem'
    
    if cert.exists() and key.exists():
        warn("Уже существует")
        if input(f"  {C.CYAN}Перегенерировать? [y/N]: {C.END}").strip().lower() != 'y':
            return True
    
    if not shutil.which('openssl'):
        warn("OpenSSL не найден")
        return False
    
    ip = get_ip()
    info(f"IP: {ip}")
    
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
        subprocess.run(['openssl', 'req', '-x509', '-nodes', '-days', '365', '-newkey', 'rsa:2048',
                       '-keyout', str(key), '-out', str(cert), '-config', str(cfg)],
                      check=True, capture_output=True)
        cfg.unlink()
        ok("Создан")
        return True
    except:
        err("Ошибка")
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
    if src.exists():
        for p in src.iterdir():
            if p.is_dir() and (p / 'plugin.yaml').exists():
                d = dst / p.name
                if d.exists(): shutil.rmtree(d)
                shutil.copytree(p, d)
                ok(p.name)

def create_scripts(info, daria_dir):
    step("Скрипты", "🚀")
    cert, key = daria_dir / 'ssl' / 'cert.pem', daria_dir / 'ssl' / 'key.pem'
    
    if info['is_windows']:
        Path('start.bat').write_text(f'@echo off\ncall venv\\Scripts\\activate\npython main.py --port {DEFAULT_PORT} %*\n')
        ok("start.bat")
        if cert.exists():
            Path('start-https.bat').write_text(f'@echo off\ncall venv\\Scripts\\activate\npython main.py --ssl --ssl-cert "{cert}" --ssl-key "{key}" --host 0.0.0.0 --port {DEFAULT_PORT} %*\n')
            ok("start-https.bat")
    else:
        s = Path('start.sh')
        s.write_text(f'#!/bin/bash\nsource venv/bin/activate\npython main.py --port {DEFAULT_PORT} "$@"\n')
        s.chmod(0o755)
        ok("start.sh")
        if cert.exists():
            h = Path('start-https.sh')
            h.write_text(f'#!/bin/bash\nsource venv/bin/activate\npython main.py --ssl --ssl-cert "{cert}" --ssl-key "{key}" --host 0.0.0.0 --port {DEFAULT_PORT} "$@"\n')
            h.chmod(0o755)
            ok("start-https.sh")

def print_final(info, daria_dir):
    ssl_ok = (daria_dir / 'ssl' / 'cert.pem').exists()
    ip = get_ip()
    cmd = "start.bat" if info['is_windows'] else "./start.sh"
    hcmd = "start-https.bat" if info['is_windows'] else "./start-https.sh"
    
    print(f"""
{C.PINK}{C.BOLD}
    ╔═══════════════════════════════════════════════════════════════╗
    ║         🌸  Установка завершена!  🌸                         ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║                                                               ║
    ║  {C.GREEN}Запуск:{C.PINK}  {C.CYAN}{cmd:<48}{C.PINK} ║""")
    
    if ssl_ok:
        print(f"""    ║  {C.GREEN}HTTPS:{C.PINK}   {C.CYAN}{hcmd:<48}{C.PINK} ║
    ║                                                               ║
    ║  {C.YELLOW}Адреса:{C.PINK}                                                    ║
    ║    {C.CYAN}http://localhost:{DEFAULT_PORT}{C.PINK}                                     ║
    ║    {C.CYAN}https://{ip}:{DEFAULT_PORT}{C.PINK}                                   ║""")
    
    print(f"""    ║                                                               ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║  {C.YELLOW}Ollama:{C.PINK}  ollama serve && ollama pull llama3.1:8b-instruct-q4_K_M ║
    ╚═══════════════════════════════════════════════════════════════╝
{C.END}""")

def main():
    banner()
    info = get_info()
    print(f"  {C.CYAN}ℹ Система: {info['system']}{C.END}")
    
    if not check_python(): sys.exit(1)
    
    pip = setup_venv(info)
    install_deps(pip)
    daria_dir = setup_dirs(info)
    
    if input(f"\n{C.CYAN}🔐 Настроить SSL? [Y/n]: {C.END}").strip().lower() != 'n':
        setup_ssl(info, daria_dir)
    
    check_ollama()
    install_plugins(daria_dir)
    create_scripts(info, daria_dir)
    print_final(info, daria_dir)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}Прервано{C.END}")
    except Exception as e:
        print(f"\n{C.RED}Ошибка: {e}{C.END}")
        sys.exit(1)
