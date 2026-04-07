#!/usr/bin/env python3
"""PUBot Uninstaller — removes all persistence and optionally all data."""
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

DATA_DIR = Path.home() / '.pubot'


def _kill_running():
    lock = DATA_DIR / 'pubot.pid'
    if not lock.exists():
        return
    try:
        pid = int(lock.read_text().strip())
        if platform.system() == 'Windows':
            subprocess.run(['taskkill', '/PID', str(pid), '/F'],
                           capture_output=True)
        else:
            os.kill(pid, 15)   # SIGTERM
        print(f'✓ Stopped PUBot (PID {pid})')
    except (ValueError, OSError):
        pass
    lock.unlink(missing_ok=True)


def _remove_linux():
    desktop = Path.home() / '.config' / 'autostart' / 'pubot.desktop'
    if desktop.exists():
        desktop.unlink()
        print(f'✓ Removed XDG autostart: {desktop}')

    svc = Path.home() / '.config' / 'systemd' / 'user' / 'pubot.service'
    if svc.exists():
        try:
            subprocess.run(['systemctl', '--user', 'disable', '--now', 'pubot.service'],
                           capture_output=True, timeout=6)
            subprocess.run(['systemctl', '--user', 'daemon-reload'],
                           capture_output=True, timeout=6)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        svc.unlink()
        print(f'✓ Removed systemd service: {svc}')


def _remove_macos():
    plist = Path.home() / 'Library' / 'LaunchAgents' / 'com.pubot.focustracker.plist'
    if plist.exists():
        try:
            subprocess.run(['launchctl', 'unload', str(plist)],
                           capture_output=True, timeout=6)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        plist.unlink()
        print(f'✓ Removed LaunchAgent: {plist}')


def _remove_windows():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Run',
            0, winreg.KEY_SET_VALUE,
        )
        try:
            winreg.DeleteValue(key, 'PUBot')
            print('✓ Removed Registry Run key')
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception as exc:
        print(f'  Registry cleanup: {exc}')

    startup = (Path(os.environ.get('APPDATA', ''))
               / 'Microsoft' / 'Windows' / 'Start Menu'
               / 'Programs' / 'Startup' / 'PUBot.bat')
    if startup.exists():
        startup.unlink()
        print(f'✓ Removed startup batch file: {startup}')


def main():
    print()
    print('═' * 50)
    print('  PUBot Uninstaller')
    print('═' * 50)
    print()

    if input('Uninstall PUBot? [y/N]: ').strip().lower() != 'y':
        print('Cancelled.')
        return

    keep = input('Keep task history and settings? [Y/n]: ').strip().lower() != 'n'
    print()

    _kill_running()

    os_name = platform.system()
    if os_name == 'Linux':
        _remove_linux()
    elif os_name == 'Darwin':
        _remove_macos()
    elif os_name == 'Windows':
        _remove_windows()

    if not keep and DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
        print(f'✓ Removed data directory: {DATA_DIR}')
    else:
        print(f'  Data kept: {DATA_DIR}')

    print()
    print('PUBot has been uninstalled.')
    print()


if __name__ == '__main__':
    main()
