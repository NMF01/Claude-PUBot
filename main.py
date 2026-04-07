#!/usr/bin/env python3
"""PUBot — Daily Focus Tracker

Runs silently in the background. After 6 AM it pops up to capture three
daily focus tasks, then reminds you every 30/60/90 minutes throughout the day.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _require_tkinter():
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print('Error: tkinter is not installed.')
        print('  Ubuntu/Debian : sudo apt-get install python3-tk')
        print('  Fedora        : sudo dnf install python3-tkinter')
        print('  macOS (brew)  : brew install python-tk')
        sys.exit(1)


def main():
    _require_tkinter()

    import tkinter as tk
    try:
        from src.app import PUBotApp
        app = PUBotApp()
        app.run()
    except tk.TclError as exc:
        msg = str(exc).lower()
        if 'display' in msg or 'connect' in msg:
            # Headless / no X session — exit silently (systemd will retry later)
            sys.exit(0)
        raise


if __name__ == '__main__':
    main()
