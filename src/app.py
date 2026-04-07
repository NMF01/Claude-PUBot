"""Main application controller — orchestrates startup checks and reminder scheduling."""
import os
import sys
import atexit
import platform
import tkinter as tk
from datetime import datetime

from .storage import Storage, LOCK_FILE
from .ai_client import AIClient
from .ui.daily_setup import DailySetupWindow
from .ui.reminder import ReminderWindow


class PUBotApp:
    """Hidden background app that owns all popup windows and the scheduling loop."""

    def __init__(self):
        self._enforce_single_instance()

        self.storage    = Storage()
        cfg             = self.storage.get_config()
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

        self._setup_shown   = False
        self._reminder_up   = False

        # Start check 1 s after mainloop begins
        self.root.after(1_000, self._startup_check)
        # Background minute-tick for day-rollover detection
        self.root.after(60_000, self._tick)

    # ── Single-instance guard ─────────────────────────────────────────────

    def _enforce_single_instance(self):
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        if LOCK_FILE.exists():
            try:
                pid = int(LOCK_FILE.read_text().strip())
                self._pid_exists(pid)   # raises if dead
                print(f'PUBot already running (PID {pid}). Exiting.')
                sys.exit(0)
            except (ValueError, OSError):
                pass  # stale lock
        LOCK_FILE.write_text(str(os.getpid()))
        atexit.register(self._cleanup)

    @staticmethod
    def _pid_exists(pid: int):
        """Raise OSError if the PID does not correspond to a running process."""
        if platform.system() == 'Windows':
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(0x0400, False, pid)
            if not handle:
                raise OSError('dead')
            ctypes.windll.kernel32.CloseHandle(handle)
        else:
            os.kill(pid, 0)   # raises ProcessLookupError if dead

    def _cleanup(self):
        try:
            LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    # ── Scheduling ────────────────────────────────────────────────────────

    def _startup_check(self):
        now  = datetime.now()
        cfg  = self.storage.get_config()
        hour = cfg.get('start_hour', 6)

        if now.hour < hour:
            # Sleep until start_hour
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
        """Called every minute to catch day-rollover and missed setups."""
        now = datetime.now()
        cfg = self.storage.get_config()
        if now.hour >= cfg.get('start_hour', 6) and not self._setup_shown:
            if not self.storage.get_today_tasks():
                self._show_setup()
        self.root.after(60_000, self._tick)

    # ── Windows ───────────────────────────────────────────────────────────

    def _show_setup(self):
        if self._setup_shown:
            return
        self._setup_shown = True
        DailySetupWindow(
            parent=self.root,
            storage=self.storage,
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
        ReminderWindow(
            parent=self.root,
            storage=self.storage,
            ai_client=self.ai_client,
            on_close=self._after_reminder,
        )

    def _after_reminder(self, remind_later: bool = True):
        self._reminder_up = False
        tasks = self.storage.get_today_tasks()
        if tasks:
            interval_ms = tasks.get('reminder_interval', 60) * 60_000
            self.root.after(interval_ms, self._show_reminder)

    # ── Entry point ───────────────────────────────────────────────────────

    def run(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self._cleanup()
