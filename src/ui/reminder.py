"""Periodic reminder popup — shows tasks, progress, and an AI coaching message."""
import tkinter as tk
from datetime import datetime

from .styles import COLORS, FONTS, create_button


class ReminderWindow:
    """Shown every N minutes to check in on the user's 3 daily tasks.

    The user can tick tasks complete, then either close (schedules next
    reminder) or dismiss with 'Remind me later'.
    """

    def __init__(self, parent: tk.Tk, storage, ai_client, on_close):
        self.storage   = storage
        self.ai_client = ai_client
        self.on_close  = on_close

        self._check_vars: list[tk.BooleanVar] = []
        self._task_labels: list[tk.Label]     = []
        self._progress_lbl: tk.Label | None   = None
        self._ai_lbl: tk.Label | None         = None

        self.data = self.storage.get_today_tasks()
        if not self.data:
            return  # Nothing to show yet

        win = tk.Toplevel(parent)
        win.title('PUBot — Focus Check-In')
        win.configure(bg=COLORS['bg'])
        win.resizable(False, False)
        win.attributes('-topmost', True)
        win.protocol('WM_DELETE_WINDOW', lambda: self._close(remind_later=True))
        self.win = win

        self._center(520, 600)
        self._build()
        win.grab_set()
        win.focus_force()

        # Fetch AI message in background
        self._fetch_ai_message()

    # ── Layout ────────────────────────────────────────────────────────────

    def _center(self, w: int, h: int):
        self.win.update_idletasks()
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        self.win.geometry(f'{w}x{h}+{(sw - w)//2}+{(sh - h)//2}')

    def _build(self):
        tasks     = self.data['tasks']
        completed = self.data['completed']
        interval  = self.data.get('reminder_interval', 60)

        outer = tk.Frame(self.win, bg=COLORS['bg'], padx=34, pady=26)
        outer.pack(fill='both', expand=True)

        # ── Header ────────────────────────────────────────────────────────
        now  = datetime.now()
        time_str = now.strftime('%I:%M %p').lstrip('0')
        date_str = f"{now.strftime('%A, %B')} {now.day}"

        hdr = tk.Frame(outer, bg=COLORS['bg'])
        hdr.pack(fill='x')

        tk.Label(
            hdr, text='⏰  Focus Check-In',
            font=FONTS['title'], bg=COLORS['bg'], fg=COLORS['text'], anchor='w',
        ).pack(side='left')

        tk.Label(
            hdr, text=time_str,
            font=FONTS['subtitle'], bg=COLORS['bg'], fg=COLORS['text_muted'], anchor='e',
        ).pack(side='right')

        interval_label = {30: '30 min', 60: '1 hour', 90: '90 min'}.get(interval, f'{interval} min')
        tk.Label(
            outer, text=f'{date_str}  ·  reminders every {interval_label}',
            font=FONTS['small'], bg=COLORS['bg'], fg=COLORS['text_dim'], anchor='w',
        ).pack(fill='x', pady=(3, 0))

        tk.Frame(outer, bg=COLORS['divider'], height=1).pack(fill='x', pady=(12, 14))

        # ── Task list ─────────────────────────────────────────────────────
        tk.Label(
            outer, text="Today's 3 tasks:",
            font=FONTS['label'], bg=COLORS['bg'], fg=COLORS['text_muted'], anchor='w',
        ).pack(fill='x', pady=(0, 8))

        icons = ['🎯', '📌', '✨']
        for i, (task, done) in enumerate(zip(tasks, completed)):
            self._build_task_row(outer, i, task, done, icons[i])

        # ── Progress ──────────────────────────────────────────────────────
        tk.Frame(outer, bg=COLORS['divider'], height=1).pack(fill='x', pady=(12, 10))

        prog_row = tk.Frame(outer, bg=COLORS['bg'])
        prog_row.pack(fill='x')

        done_count = sum(completed)
        total      = len(tasks)

        self._progress_lbl = tk.Label(
            prog_row,
            text=self._progress_text(done_count, total),
            font=FONTS['body'],
            bg=COLORS['bg'],
            fg=COLORS['success'] if done_count == total else COLORS['text_muted'],
        )
        self._progress_lbl.pack(side='left')

        if done_count == total:
            tk.Label(
                prog_row, text='  🎉 All done!',
                font=FONTS['body'], bg=COLORS['bg'], fg=COLORS['success'],
            ).pack(side='left')

        # Progress bar
        bar_outer = tk.Frame(outer, bg=COLORS['progress_bg'], height=7)
        bar_outer.pack(fill='x', pady=(6, 0))
        bar_outer.pack_propagate(False)
        if total > 0 and done_count > 0:
            tk.Frame(bar_outer, bg=COLORS['progress_fill'], height=7).place(
                relwidth=done_count / total, relheight=1.0,
            )
        self._bar_outer = bar_outer
        self._bar_done  = done_count
        self._bar_total = total

        # ── AI coaching card ──────────────────────────────────────────────
        tk.Frame(outer, bg=COLORS['divider'], height=1).pack(fill='x', pady=(12, 10))

        card = tk.Frame(outer, bg=COLORS['card_bg'], padx=14, pady=12)
        card.pack(fill='x')

        tk.Label(
            card, text='✦  Coach',
            font=FONTS['small'], bg=COLORS['card_bg'], fg=COLORS['accent_light'],
        ).pack(anchor='w', pady=(0, 5))

        self._ai_lbl = tk.Label(
            card, text='Loading insight…',
            font=FONTS['body_italic'],
            bg=COLORS['card_bg'], fg=COLORS['text_muted'],
            wraplength=420, justify='left', anchor='w',
        )
        self._ai_lbl.pack(fill='x')

        # ── Buttons ───────────────────────────────────────────────────────
        tk.Frame(outer, bg=COLORS['divider'], height=1).pack(fill='x', pady=(14, 14))

        btn_row = tk.Frame(outer, bg=COLORS['bg'])
        btn_row.pack(fill='x')

        create_button(
            btn_row, 'Remind me later',
            lambda: self._close(remind_later=True), style='secondary',
        ).pack(side='left')

        create_button(
            btn_row, 'Save & Close  ✓',
            lambda: self._close(remind_later=False), style='primary',
        ).pack(side='right')

    def _build_task_row(
        self, parent, idx: int, task: str, done: bool, icon: str,
    ):
        row = tk.Frame(parent, bg=COLORS['surface_alt'], padx=12, pady=10)
        row.pack(fill='x', pady=(0, 6))

        var = tk.BooleanVar(value=done)
        self._check_vars.append(var)

        tk.Checkbutton(
            row, variable=var,
            bg=COLORS['surface_alt'],
            activebackground=COLORS['surface_alt'],
            selectcolor=COLORS['accent'],
            fg=COLORS['accent_light'],
            cursor='hand2',
            command=self._on_check_changed,
        ).pack(side='left', padx=(0, 8))

        lbl = tk.Label(
            row, text=f'{icon}  {task}',
            font=FONTS['body'],
            bg=COLORS['surface_alt'],
            fg=COLORS['text_dim'] if done else COLORS['text'],
            anchor='w', wraplength=360, justify='left',
        )
        lbl.pack(side='left', fill='x', expand=True)
        self._task_labels.append(lbl)

        if done:
            tk.Label(
                row, text='✓ Done',
                font=FONTS['small'],
                bg=COLORS['success_bg'], fg=COLORS['success'],
                padx=6, pady=2,
            ).pack(side='right', padx=(8, 0))

        var.trace_add('write', lambda *_a, i=idx: self._on_task_toggled(i))

    # ── Callbacks ─────────────────────────────────────────────────────────

    def _on_check_changed(self):
        pass  # trace handles the update

    def _on_task_toggled(self, idx: int):
        done = self._check_vars[idx].get()
        self._task_labels[idx].configure(
            fg=COLORS['text_dim'] if done else COLORS['text'],
        )
        self._refresh_progress()

    def _refresh_progress(self):
        done_count = sum(v.get() for v in self._check_vars)
        total      = len(self._check_vars)
        if self._progress_lbl:
            self._progress_lbl.configure(
                text=self._progress_text(done_count, total),
                fg=COLORS['success'] if done_count == total else COLORS['text_muted'],
            )
        # Redraw progress bar fill
        for child in self._bar_outer.winfo_children():
            child.destroy()
        if total > 0 and done_count > 0:
            tk.Frame(self._bar_outer, bg=COLORS['progress_fill'], height=7).place(
                relwidth=done_count / total, relheight=1.0,
            )

    def _fetch_ai_message(self):
        tasks     = self.data['tasks']
        completed = self.data['completed']

        def _cb(msg: str, err):
            if self.win.winfo_exists():
                self.win.after(0, lambda: self._set_ai(msg))

        self.ai_client.get_motivational_message(tasks, completed, _cb)

    def _set_ai(self, message: str):
        if self._ai_lbl and self.win.winfo_exists():
            self._ai_lbl.configure(text=f'"{message}"', fg=COLORS['text'])

    def _close(self, remind_later: bool):
        completed = [v.get() for v in self._check_vars]
        self.storage.update_completion(completed)
        self.win.destroy()
        self.on_close(remind_later=remind_later)

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _progress_text(done: int, total: int) -> str:
        return f'{done} of {total} tasks completed'
