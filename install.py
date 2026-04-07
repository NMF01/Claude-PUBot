#!/usr/bin/env python3
"""PUBot Installer

Sets up autostart persistence and saves configuration.
Run once:  python install.py
Uninstall: python uninstall.py
"""
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
DATA_DIR   = Path.home() / '.pubot'
PYTHON     = sys.executable
MAIN_PY    = SCRIPT_DIR / 'main.py'


# ── Banner ────────────────────────────────────────────────────────────────

def banner():
    print()
    print('═' * 58)
    print('  PUBot — Daily Focus Tracker — Installer')
    print('═' * 58)
    print()
    print('  Once installed, PUBot will:')
    print('  • Start automatically when you log in')
    print('  • Pop up after 6 AM asking for 3 focus tasks')
    print('  • Remind you every 30 / 60 / 90 minutes throughout the day')
    print('  • Use Claude AI for personalised coaching messages')
    print()


# ── Preflight ─────────────────────────────────────────────────────────────

def preflight():
    if sys.version_info < (3, 9):
        sys.exit('Error: Python 3.9 or later is required.')
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print('Error: tkinter not found.')
        print('  Ubuntu/Debian: sudo apt-get install python3-tk')
        print('  Fedora:        sudo dnf install python3-tkinter')
        sys.exit(1)


# ── Dependencies ──────────────────────────────────────────────────────────

def install_deps():
    print('── Installing Python dependencies ─────────────────────')
    req = SCRIPT_DIR / 'requirements.txt'
    if req.exists():
        try:
            subprocess.run(
                [PYTHON, '-m', 'pip', 'install', '-q', '-r', str(req)],
                check=True, timeout=120,
            )
            print('✓ Dependencies installed')
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f'  Warning: could not install all deps: {e}')
    else:
        print('  (no requirements.txt found)')
    print()


# ── Config ────────────────────────────────────────────────────────────────

def setup_config():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print('── Configuration ───────────────────────────────────────')
    print('PUBot can use Claude AI for personalised motivational')
    print('messages. Enter your Anthropic API key, or press Enter')
    print('to skip (offline quotes will be used instead).')
    print()
    api_key = input('  Anthropic API key (sk-ant-…) : ').strip()
    if api_key and not api_key.startswith('sk-ant-'):
        print('  ⚠  This does not look like a valid key — saved anyway.')

    config = {'api_key': api_key, 'start_hour': 6}
    cfg_file = DATA_DIR / 'config.json'
    with open(cfg_file, 'w') as f:
        json.dump(config, f, indent=2)
    try:
        os.chmod(cfg_file, 0o600)
    except OSError:
        pass
    print('✓ Configuration saved')
    print()


# ── OS persistence ────────────────────────────────────────────────────────

def persist_linux():
    print('── Setting up autostart (Linux) ───────────────────────')

    # 1. XDG autostart — works with GNOME, KDE, XFCE, etc.
    autostart = Path.home() / '.config' / 'autostart'
    autostart.mkdir(parents=True, exist_ok=True)
    desktop = autostart / 'pubot.desktop'
    desktop.write_text(
        f'[Desktop Entry]\n'
        f'Type=Application\n'
        f'Name=PUBot Daily Focus Tracker\n'
        f'Comment=Daily focus tasks and periodic reminders\n'
        f'Exec={PYTHON} {MAIN_PY}\n'
        f'Hidden=false\n'
        f'NoDisplay=false\n'
        f'X-GNOME-Autostart-enabled=true\n'
        f'X-KDE-autostart-phase=2\n'
    )
    os.chmod(desktop, 0o755)
    print(f'✓ XDG autostart : {desktop}')

    # 2. systemd user service — more robust; survives desktop crashes
    svc_dir = Path.home() / '.config' / 'systemd' / 'user'
    svc_dir.mkdir(parents=True, exist_ok=True)
    svc_file = svc_dir / 'pubot.service'
    svc_file.write_text(
        f'[Unit]\n'
        f'Description=PUBot Daily Focus Tracker\n'
        f'After=graphical-session.target\n'
        f'PartOf=graphical-session.target\n'
        f'\n'
        f'[Service]\n'
        f'Type=simple\n'
        f'ExecStart={PYTHON} {MAIN_PY}\n'
        f'Restart=on-failure\n'
        f'RestartSec=15\n'
        f'Environment=DISPLAY=:0\n'
        f'Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/%U/bus\n'
        f'\n'
        f'[Install]\n'
        f'WantedBy=graphical-session.target\n'
    )
    try:
        subprocess.run(['systemctl', '--user', 'daemon-reload'],
                       capture_output=True, timeout=6)
        subprocess.run(['systemctl', '--user', 'enable', 'pubot.service'],
                       capture_output=True, timeout=6)
        print(f'✓ systemd service : {svc_file}  (enabled)')
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print(f'✓ systemd service : {svc_file}  (systemctl not available; starts via XDG)')
    print()


def persist_macos():
    print('── Setting up autostart (macOS) ───────────────────────')
    la_dir = Path.home() / 'Library' / 'LaunchAgents'
    la_dir.mkdir(parents=True, exist_ok=True)
    plist  = la_dir / 'com.pubot.focustracker.plist'
    log    = DATA_DIR / 'pubot.log'
    plist.write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"\n'
        f'    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        f'<plist version="1.0">\n'
        f'<dict>\n'
        f'    <key>Label</key><string>com.pubot.focustracker</string>\n'
        f'    <key>ProgramArguments</key>\n'
        f'    <array>\n'
        f'        <string>{PYTHON}</string>\n'
        f'        <string>{MAIN_PY}</string>\n'
        f'    </array>\n'
        f'    <key>RunAtLoad</key><true/>\n'
        f'    <key>KeepAlive</key><false/>\n'
        f'    <key>StandardOutPath</key><string>{log}</string>\n'
        f'    <key>StandardErrorPath</key><string>{log}</string>\n'
        f'</dict>\n'
        f'</plist>\n'
    )
    try:
        subprocess.run(['launchctl', 'load', str(plist)],
                       capture_output=True, timeout=6)
        print(f'✓ LaunchAgent loaded : {plist}')
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print(f'✓ LaunchAgent created : {plist}')
    print()


def persist_windows():
    print('── Setting up autostart (Windows) ─────────────────────')
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Run',
            0, winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, 'PUBot', 0, winreg.REG_SZ,
                          f'"{PYTHON}" "{MAIN_PY}"')
        winreg.CloseKey(key)
        print('✓ Registry Run key added')
    except Exception as exc:
        print(f'  Registry failed ({exc}); trying Startup folder…')
        startup = (Path(os.environ.get('APPDATA', ''))
                   / 'Microsoft' / 'Windows' / 'Start Menu'
                   / 'Programs' / 'Startup')
        if startup.exists():
            bat = startup / 'PUBot.bat'
            bat.write_text(f'@echo off\nstart "" "{PYTHON}" "{MAIN_PY}"\n')
            print(f'✓ Startup batch file : {bat}')
    print()


# ── Launch ────────────────────────────────────────────────────────────────

def launch():
    log = DATA_DIR / 'pubot.log'
    os_name = platform.system()
    try:
        if os_name == 'Windows':
            subprocess.Popen(
                [PYTHON, str(MAIN_PY)],
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            )
        else:
            with open(log, 'a') as lf:
                subprocess.Popen(
                    [PYTHON, str(MAIN_PY)],
                    start_new_session=True,
                    stdout=lf, stderr=subprocess.STDOUT,
                )
        print('✓ PUBot started in background')
    except Exception as exc:
        print(f'  Could not start PUBot: {exc}')


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    banner()
    preflight()
    install_deps()
    setup_config()

    os_name = platform.system()
    if os_name == 'Linux':
        persist_linux()
    elif os_name == 'Darwin':
        persist_macos()
    elif os_name == 'Windows':
        persist_windows()
    else:
        print(f'  Unsupported OS ({os_name}). Manual autostart setup required.')

    print('═' * 58)
    print('  Installation complete!')
    print(f'  Data & config stored in: {DATA_DIR}')
    print('  To uninstall: python uninstall.py')
    print('═' * 58)
    print()

    ans = input('Start PUBot now? [Y/n]: ').strip().lower()
    if ans != 'n':
        launch()
    print()


if __name__ == '__main__':
    main()
