"""Persistent storage for tasks and configuration."""
import json
import os
from datetime import date
from pathlib import Path

DATA_DIR   = Path.home() / '.pubot'
CONFIG_FILE = DATA_DIR / 'config.json'
TASKS_FILE  = DATA_DIR / 'tasks.json'
LOCK_FILE   = DATA_DIR / 'pubot.pid'
HISTORY_FILE = DATA_DIR / 'history.json'

_DEFAULT_CONFIG = {
    'api_key':    '',
    'start_hour': 6,
}


class Storage:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ── Config ────────────────────────────────────────────────────────────

    def get_config(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    return {**_DEFAULT_CONFIG, **json.load(f)}
            except (json.JSONDecodeError, OSError):
                pass
        return dict(_DEFAULT_CONFIG)

    def save_config(self, config: dict) -> None:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        try:
            os.chmod(CONFIG_FILE, 0o600)
        except OSError:
            pass

    # ── Daily Tasks ───────────────────────────────────────────────────────

    def get_today_tasks(self) -> dict | None:
        """Return today's task data dict, or None if not set for today."""
        if not TASKS_FILE.exists():
            return None
        try:
            with open(TASKS_FILE) as f:
                data = json.load(f)
            if data.get('date') != str(date.today()):
                return None
            return data
        except (json.JSONDecodeError, OSError):
            return None

    def save_today_tasks(
        self,
        tasks: list[str],
        completed: list[bool] | None = None,
        reminder_interval: int = 60,
    ) -> None:
        data = {
            'date':              str(date.today()),
            'tasks':             tasks,
            'completed':         completed or [False] * len(tasks),
            'reminder_interval': reminder_interval,
        }
        with open(TASKS_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def update_completion(self, completed: list[bool]) -> None:
        data = self.get_today_tasks()
        if data:
            data['completed'] = completed
            with open(TASKS_FILE, 'w') as f:
                json.dump(data, f, indent=2)

    # ── History ───────────────────────────────────────────────────────────

    def archive_today(self) -> None:
        """Append today's completed tasks to history (called at end of day)."""
        today = self.get_today_tasks()
        if not today:
            return
        history = self._load_history()
        history = [h for h in history if h.get('date') != today['date']]
        history.append(today)
        history.sort(key=lambda x: x.get('date', ''), reverse=True)
        history = history[:60]
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)

    def _load_history(self) -> list:
        if not HISTORY_FILE.exists():
            return []
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def get_completion_streak(self) -> int:
        """Return number of consecutive days where all 3 tasks were completed."""
        from datetime import timedelta
        history = self._load_history()
        streak = 0
        check_date = date.today()
        date_map = {h['date']: h for h in history}
        for _ in range(len(history) + 1):
            key = str(check_date)
            entry = date_map.get(key)
            if entry and all(entry.get('completed', [])):
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        return streak
