#!/usr/bin/env python3
"""PUBot — Daily Focus Tracker

Runs silently in the background. After 6 AM it pops up to capture three
daily focus tasks, then reminds you every 20/30/60/90 minutes throughout the day.
"""
import sys
import os
import logging
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Logging — always write to ~/.pubot/pubot.log ──────────────────────────

def _setup_logging():
    log = Path.home() / '.pubot' / 'pubot.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    # Rotate if the log exceeds 200 KB
    if log.exists() and log.stat().st_size > 200_000:
        log.rename(log.with_suffix('.log.1'))
    logging.basicConfig(
        filename=str(log),
        filemode='a',
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

_setup_logging()
logging.info('PUBot launching (PID %s, Python %s)', os.getpid(), sys.version.split()[0])


def _require_tkinter():
    try:
        import tkinter  # noqa: F401
    except ImportError:
        msg = (
            'Error: tkinter is not installed.\n'
            '  Ubuntu/Debian : sudo apt-get install python3-tk\n'
            '  Fedora        : sudo dnf install python3-tkinter\n'
            '  macOS (brew)  : brew install python-tk'
        )
        logging.error(msg)
        print(msg)
        sys.exit(1)


def main():
    _require_tkinter()

    import tkinter as tk
    try:
        from src.app import PUBotApp
        app = PUBotApp()
        app.run()
        logging.info('PUBot exited cleanly.')
    except tk.TclError as exc:
        msg = str(exc).lower()
        if 'display' in msg or 'connect' in msg:
            logging.info('No display available — exiting (watchdog will retry).')
            sys.exit(0)
        logging.exception('Fatal TclError')
        sys.exit(1)
    except SystemExit:
        raise   # pass through sys.exit() calls (e.g. single-instance guard)
    except Exception:
        logging.exception('Fatal crash')
        sys.exit(1)


if __name__ == '__main__':
    main()
