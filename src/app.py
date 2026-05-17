"""Main application controller — orchestrates startup checks and reminder scheduling."""
import os
import sys
import socket as _socket
import atexit
import logging
import platform
import tkinter as tk
from datetime import datetime, date
from pathlib import Path

from .storage import Storage, LOCK_FILE
from .ai_client import AIClient
from .ui import styles as _styles
from .ui.daily_setup import DailySetupWindow
from .ui.reminder import ReminderWindow

# Loopback port used as a single-instance lock.
# A bound TCP socket is automatically released by the OS when the process
# dies for any reason — unlike a PID file which can become stale.
_LOCK_PORT = 47384


class PUBotApp:
    """Hidden background app that owns all popup windows and the scheduling loop."""

    def __init__(self):
        self._lock_sock: _socket.socket | None = None
        self._enforce_single_instance()

        self.storage    = Storage()
        cfg             = self.storage.get_config()
        _styles.set_lang(cfg.get('lang', 'en'))
        self.ai_client  = AIClient(cfg.get('api_key', ''))

        # Invisible root window — just owns the event loop and child Toplevels
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title('PUBot')
        try:
            self.root.attributes('-alpha', 0.0)
            self.root.geometry('1x1+-32000+-32000')
        except tk.TclError:
            pass

        # Log (but don't crash) any exception raised inside a tkinter callback
        self.root.report_callback_exception = _log_callback_exception

        self._setup_shown   = False
        self._reminder_up   = False
        self._current_date  = date.today()   # for day-rollover detection

        # Start check 1 s after mainloop begins
        self.root.after(1_000, self._startup_check)
        # Background minute-tick for day-rollover detection
        self.root.after(60_000, self._tick)
        # Hard restart at midnight for a guaranteed fresh daily slate
        self.root.after(self._ms_until_midnight(), self._midnight_restart)

    # ── Single-instance guard ─────────────────────────────────────────────

    def _enforce_single_instance(self):
        """Bind a loopback TCP port as a cross-platform single-instance lock.

        The OS automatically releases the port when the process dies for any
        reason (crash, kill, shutdown), eliminating stale-lock false positives.
        """
        sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        # SO_REUSEADDR must be OFF so the bind truly signals exclusive ownership
        sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 0)
        try:
            sock.bind(('127.0.0.1', _LOCK_PORT))
            sock.listen(1)
            self._lock_sock = sock
        except OSError:
            sock.close()
            logging.info('Another PUBot instance is running — exiting.')
            sys.exit(0)

        # Write PID for diagnostic purposes only (not used for locking)
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOCK_FILE.write_text(str(os.getpid()))
        atexit.register(self._cleanup)

    def _cleanup(self):
        if self._lock_sock:
            try:
                self._lock_sock.close()
            except Exception:
                pass
        try:
            LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    # ── Midnight restart ─────────────────────────────────────────────────

    @staticmethod
    def _ms_until_midnight() -> int:
        """Milliseconds from now until the next 00:00:00."""
        now = datetime.now()
        secs = (23 - now.hour) * 3600 + (59 - now.minute) * 60 + (60 - now.second)
        return max(secs * 1000, 1_000)

    def _midnight_restart(self):
        """Replace this process with a fresh instance at midnight.

        If a popup is open, defer by one minute so the user can finish;
        the day-rollover logic in _tick() will still reset state correctly.
        """
        if self._setup_shown or self._reminder_up:
            logging.info('Midnight restart deferred — popup is open.')
            self.root.after(60_000, self._midnight_restart)
            return

        logging.info('Midnight restart: replacing process image.')
        try:
            self._cleanup()   # release socket before execv so new instance can acquire it
        except Exception:
            pass

        main_py = str(Path(__file__).parent.parent / 'main.py')
        try:
            os.execv(sys.executable, [sys.executable, main_py])
        except Exception:
            logging.exception('os.execv failed — exiting; watchdog will restart.')
            sys.exit(1)

    # ── Scheduling ────────────────────────────────────────────────────────

    def _startup_check(self):
        now  = datetime.now()
        cfg  = self.storage.get_config()
        hour = cfg.get('start_hour', 6)

        if now.hour < hour:
            secs = (hour - now.hour) * 3600 - now.minute * 60 - now.second
            self.root.after(max(secs * 1000, 60_000), self._startup_check)
            return

        tasks = self.storage.get_today_tasks()
        if not tasks:
            if not self._setup_shown:
                self._show_setup()
        else:
            interval_ms = tasks.get('reminder_interval', 60) * 60_000
            self.root.after(interval_ms, self._show_reminder)

    def _tick(self):
        """Called every minute — catches day-rollover and missed setups."""
        now = datetime.now()
        cfg = self.storage.get_config()

        # Day has rolled over: reset flags so tomorrow's morning popup fires
        today = date.today()
        if today != self._current_date:
            logging.info('Day rollover detected (%s → %s); resetting setup flag.',
                         self._current_date, today)
            self._current_date = today
            self._setup_shown  = False
            self._reminder_up  = False

        if now.hour >= cfg.get('start_hour', 6) and not self._setup_shown:
            if not self.storage.get_today_tasks():
                self._show_setup()

        self.root.after(60_000, self._tick)

    # ── Windows ───────────────────────────────────────────────────────────

    def _show_setup(self):
        if self._setup_shown:
            return
        self._setup_shown = True
        logging.info('Showing daily setup window.')
        DailySetupWindow(
            parent=self.root,
            storage=self.storage,
            ai_client=self.ai_client,
            on_complete=self._after_setup,
        )

    def _after_setup(self):
        tasks = self.storage.get_today_tasks()
        if tasks:
            interval_ms = tasks.get('reminder_interval', 60) * 60_000
            self.root.after(interval_ms, self._show_reminder)

    def _show_reminder(self):
        if self._reminder_up:
            return
        tasks = self.storage.get_today_tasks()
        if not tasks:
            return
        self._reminder_up = True
        logging.info('Showing reminder window.')
        ReminderWindow(
            parent=self.root,
            storage=self.storage,
            ai_client=self.ai_client,
            on_close=self._after_reminder,
        )

    def _after_reminder(self, remind_later: bool = True):
        self._reminder_up = False
        tasks = self.storage.get_today_tasks()
        if not tasks:
            return
        if all(tasks.get('completed', [])):
            logging.info('All tasks complete — stopping reminders for today.')
            return
        interval_ms = tasks.get('reminder_interval', 60) * 60_000
        self.root.after(interval_ms, self._show_reminder)

    # ── Entry point ───────────────────────────────────────────────────────

    def run(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self._cleanup()


def _log_callback_exception(exc_type, exc_val, exc_tb):
    """Replace tkinter's default stderr dump with a logged entry.

    The app keeps running — only the individual callback is aborted.
    """
    import traceback
    logging.error(
        'Unhandled exception in tkinter callback:\n%s',
        ''.join(traceback.format_exception(exc_type, exc_val, exc_tb)),
    )
