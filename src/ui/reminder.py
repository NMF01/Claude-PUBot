"""Periodic reminder popup — shows tasks, progress, and an AI coaching message.

Design contract
───────────────
* The X button and any "save and close" shortcut are DISABLED.
  The only legal exits are:
    1. Click "Remind me later"  → window closes, reminder reschedules.
    2. Tick all 3 tasks         → celebration screen appears, then window
                                   auto-closes after a countdown (or user
                                   clicks the close button). No more reminders
                                   until tomorrow.
* While the window is open it stays topmost and re-grabs focus every 500 ms
  so the user cannot switch away without acknowledging their tasks.
  (Focus is released while the Settings dialog is open.)
"""
import tkinter as tk
from datetime import datetime

from .styles import (
    COLORS, get_font, create_button, create_lang_button,
    t, current_lang, set_lang,
)
from .settings import SettingsDialog
from . import desktop_lock

_CELEBRATION_COUNTDOWN = 6   # seconds before auto-close on celebration screen


class ReminderWindow:
    """Shown every N minutes to check in on the user's 3 daily tasks."""

    def __init__(self, parent: tk.Tk, storage, ai_client, on_close):
        self.storage    = storage
        self.ai_client  = ai_client
        self.on_close   = on_close

        self._check_vars:   list[tk.BooleanVar] = []
        self._task_labels:  list[tk.Label]      = []
        self._done_badges:  list[tk.Label | None] = []

        # Refs updated by _apply_lang()
        self._lbl_page_hdr:  tk.Label | None = None
        self._lbl_title:     tk.Label | None = None
        self._lbl_dateline:  tk.Label | None = None
        self._lbl_tasks_hdr: tk.Label | None = None
        self._lbl_progress:  tk.Label | None = None
        self._lbl_alldone:   tk.Label | None = None
        self._lbl_coach:     tk.Label | None = None
        self._ai_lbl:        tk.Label | None = None
        self._btn_remind:    tk.Button | None = None
        self._btn_lang:      tk.Button | None = None
        self._bar_outer:     tk.Frame | None = None

        # State flags
        self._settings_open:    bool = False
        self._celebration_shown: bool = False
        self._outer:            tk.Frame | None = None

        self.data = self.storage.get_today_tasks()
        if not self.data:
            return

        self._now      = datetime.now()
        self._interval = self.data.get('reminder_interval', 60)

        win = tk.Toplevel(parent)
        win.title('PUBot')
        win.configure(bg=COLORS['bg'])
        win.resizable(False, False)
        win.attributes('-topmost', True)
        # X button does nothing — user must interact with the window
        win.protocol('WM_DELETE_WINDOW', lambda: None)
        self.win = win

        self._center(530, 620)
        self._build()

        # Lock the desktop — blackout is created first, popup lifted above it.
        self._blackout = desktop_lock.lock(parent)
        if self._blackout:
            win.lift()

        win.grab_set()
        win.focus_force()

        # Periodic focus enforcement
        win.after(500, self._keep_on_top)
        self._fetch_ai_message()

    # ── Layout helpers ────────────────────────────────────────────────────

    def _center(self, w: int, h: int):
        self.win.update_idletasks()
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        self.win.geometry(f'{w}x{h}+{(sw - w)//2}+{(sh - h)//2}')

    # ── Main build ────────────────────────────────────────────────────────

    def _build(self):
        tasks     = self.data['tasks']
        completed = self.data['completed']

        outer = tk.Frame(self.win, bg=COLORS['bg'], padx=34, pady=24)
        outer.pack(fill='both', expand=True)
        self._outer = outer

        # ── Top row: gear + lang toggle ───────────────────────────────────
        top_row = tk.Frame(outer, bg=COLORS['bg'])
        top_row.pack(fill='x', pady=(0, 4))

        self._btn_lang = create_lang_button(top_row, self._toggle_lang)
        self._btn_lang.pack(side='right')

        gear_btn = tk.Button(
            top_row, text='⚙',
            command=self._open_settings,
            bg=COLORS['bg'], fg=COLORS['text_muted'],
            font=get_font('label'),
            relief='flat', bd=0, padx=4, cursor='hand2',
            activebackground=COLORS['bg'], activeforeground=COLORS['accent'],
        )
        gear_btn.pack(side='left')

        # ── Page header ───────────────────────────────────────────────────
        self._lbl_page_hdr = tk.Label(
            outer, text=t('page_header'),
            font=get_font('label'), bg=COLORS['bg'],
            fg=COLORS['accent'], anchor='w',
        )
        self._lbl_page_hdr.pack(fill='x', pady=(0, 6))

        # ── Title row ─────────────────────────────────────────────────────
        hdr = tk.Frame(outer, bg=COLORS['bg'])
        hdr.pack(fill='x')

        self._lbl_title = tk.Label(
            hdr, text=t('checkin_title'),
            font=get_font('title'), bg=COLORS['bg'], fg=COLORS['text'], anchor='w',
        )
        self._lbl_title.pack(side='left')

        time_str = self._now.strftime('%I:%M %p').lstrip('0')
        tk.Label(
            hdr, text=time_str,
            font=get_font('subtitle'), bg=COLORS['bg'], fg=COLORS['text_muted'],
        ).pack(side='right')

        self._lbl_dateline = tk.Label(
            outer, text=self._make_dateline(),
            font=get_font('small'), bg=COLORS['bg'], fg=COLORS['text_dim'], anchor='w',
        )
        self._lbl_dateline.pack(fill='x', pady=(3, 0))

        tk.Frame(outer, bg=COLORS['divider'], height=1).pack(fill='x', pady=(12, 12))

        # ── Task list ─────────────────────────────────────────────────────
        self._lbl_tasks_hdr = tk.Label(
            outer, text=t('tasks_header'),
            font=get_font('label'), bg=COLORS['bg'], fg=COLORS['text_muted'], anchor='w',
        )
        self._lbl_tasks_hdr.pack(fill='x', pady=(0, 8))

        icons = t('task_icons')
        for i, (task, done) in enumerate(zip(tasks, completed)):
            self._build_task_row(outer, i, task, done, icons[i])

        # ── Progress ──────────────────────────────────────────────────────
        tk.Frame(outer, bg=COLORS['divider'], height=1).pack(fill='x', pady=(10, 8))

        done_count = sum(completed)
        total      = len(tasks)

        prog_row = tk.Frame(outer, bg=COLORS['bg'])
        prog_row.pack(fill='x')

        self._lbl_progress = tk.Label(
            prog_row,
            text=t('progress', done=done_count, total=total),
            font=get_font('body'), bg=COLORS['bg'],
            fg=COLORS['success'] if done_count == total else COLORS['text_muted'],
        )
        self._lbl_progress.pack(side='left')

        self._lbl_alldone = tk.Label(
            prog_row, text=f"  {t('all_done')}",
            font=get_font('body'), bg=COLORS['bg'], fg=COLORS['success'],
        )
        if done_count == total:
            self._lbl_alldone.pack(side='left')

        # Progress bar
        self._bar_outer = tk.Frame(outer, bg=COLORS['progress_bg'], height=7)
        self._bar_outer.pack(fill='x', pady=(6, 0))
        self._bar_outer.pack_propagate(False)
        if total > 0 and done_count > 0:
            tk.Frame(self._bar_outer, bg=COLORS['progress_fill'], height=7).place(
                relwidth=done_count / total, relheight=1.0,
            )

        # ── AI coaching card ──────────────────────────────────────────────
        tk.Frame(outer, bg=COLORS['divider'], height=1).pack(fill='x', pady=(10, 8))

        card = tk.Frame(outer, bg=COLORS['card_bg'], padx=14, pady=12)
        card.pack(fill='x')

        self._lbl_coach = tk.Label(
            card, text=t('coach_label'),
            font=get_font('small'), bg=COLORS['card_bg'], fg=COLORS['accent_light'],
        )
        self._lbl_coach.pack(anchor='w', pady=(0, 5))

        self._ai_lbl = tk.Label(
            card, text=t('loading'),
            font=get_font('body_italic'),
            bg=COLORS['card_bg'], fg=COLORS['text_muted'],
            wraplength=430, justify='left', anchor='w',
        )
        self._ai_lbl.pack(fill='x')

        # ── Bottom button — "Remind me later" only ────────────────────────
        tk.Frame(outer, bg=COLORS['divider'], height=1).pack(fill='x', pady=(12, 12))

        btn_row = tk.Frame(outer, bg=COLORS['bg'])
        btn_row.pack(fill='x')

        note = tk.Label(
            btn_row,
            text='✓ Tick a task as done, or',
            font=get_font('small'), bg=COLORS['bg'], fg=COLORS['text_dim'],
        )
        note.pack(side='left', pady=(2, 0))
        self._lbl_remind_note = note

        self._btn_remind = create_button(
            btn_row, t('remind_later'),
            lambda: self._close(remind_later=True), style='secondary',
        )
        self._btn_remind.pack(side='right')

    def _build_task_row(self, parent, idx: int, task: str, done: bool, icon: str):
        row = tk.Frame(parent, bg=COLORS['surface_alt'], padx=12, pady=10)
        row.pack(fill='x', pady=(0, 6))

        var = tk.BooleanVar(value=done)
        self._check_vars.append(var)

        tk.Checkbutton(
            row, variable=var,
            bg=COLORS['surface_alt'],
            activebackground=COLORS['surface_alt'],
            selectcolor=COLORS['accent'],
            fg=COLORS['accent'],
            cursor='hand2',
            command=self._on_check_changed,
        ).pack(side='left', padx=(0, 8))

        lbl = tk.Label(
            row, text=f'{icon}  {task}',
            font=get_font('body'),
            bg=COLORS['surface_alt'],
            fg=COLORS['text_dim'] if done else COLORS['text'],
            anchor='w', wraplength=360, justify='left',
        )
        lbl.pack(side='left', fill='x', expand=True)
        self._task_labels.append(lbl)

        badge = None
        if done:
            badge = tk.Label(
                row, text=t('done_badge'),
                font=get_font('small'),
                bg=COLORS['success_bg'], fg=COLORS['success'],
                padx=6, pady=2,
            )
            badge.pack(side='right', padx=(8, 0))
        self._done_badges.append(badge)

        var.trace_add('write', lambda *_a, i=idx: self._on_task_toggled(i))

    # ── Focus enforcement ─────────────────────────────────────────────────

    def _keep_on_top(self):
        """Runs every 500 ms; re-lifts and re-grabs focus unless settings open."""
        if not self.win.winfo_exists():
            return
        if not self._settings_open and not self._celebration_shown:
            try:
                self.win.lift()   # stays above the blackout overlay
                self.win.attributes('-topmost', True)
                self.win.focus_force()
                self.win.grab_set()
            except tk.TclError:
                pass
        elif self._celebration_shown:
            try:
                self.win.lift()
                self.win.attributes('-topmost', True)
            except tk.TclError:
                pass
        self.win.after(500, self._keep_on_top)

    # ── Settings dialog ───────────────────────────────────────────────────

    def _open_settings(self):
        self._settings_open = True
        dlg = SettingsDialog(self.win, self.storage, self.ai_client)
        dlg.win.bind('<Destroy>', lambda _e: self._on_settings_closed(), add='+')

    def _on_settings_closed(self):
        self._settings_open = False
        if self.win.winfo_exists():
            try:
                self.win.grab_set()
                self.win.lift()
                self.win.focus_force()
            except tk.TclError:
                pass

    # ── Language toggle ───────────────────────────────────────────────────

    def _toggle_lang(self):
        new = 'he' if current_lang() == 'en' else 'en'
        set_lang(new)
        cfg = self.storage.get_config()
        cfg['lang'] = new
        self.storage.save_config(cfg)
        self._apply_lang()
        self._ai_lbl.configure(text=t('loading'), fg=COLORS['text_muted'],
                               font=get_font('body_italic'))
        self._fetch_ai_message()

    def _apply_lang(self):
        """Update all stored widget texts/alignments for the active language."""
        rtl     = current_lang() == 'he'
        anchor  = 'e' if rtl else 'w'
        justify = 'right' if rtl else 'left'

        self._lbl_page_hdr.configure(
            text=t('page_header'), anchor=anchor, font=get_font('label'),
        )
        self._lbl_title.configure(
            text=t('checkin_title'), anchor=anchor, font=get_font('title'),
        )
        self._lbl_dateline.configure(
            text=self._make_dateline(), anchor=anchor, font=get_font('small'),
        )
        self._lbl_tasks_hdr.configure(
            text=t('tasks_header'), anchor=anchor, font=get_font('label'),
        )
        for lbl in self._task_labels:
            lbl.configure(anchor=anchor, justify=justify, font=get_font('body'))
        for badge in self._done_badges:
            if badge:
                badge.configure(text=t('done_badge'), font=get_font('small'))

        done_count = sum(v.get() for v in self._check_vars)
        total      = len(self._check_vars)
        self._lbl_progress.configure(
            text=t('progress', done=done_count, total=total),
            anchor=anchor, font=get_font('body'),
        )
        self._lbl_alldone.configure(
            text=f"  {t('all_done')}", font=get_font('body'),
        )
        self._lbl_coach.configure(
            text=t('coach_label'), anchor=anchor, font=get_font('small'),
        )
        self._ai_lbl.configure(anchor=anchor, justify=justify, font=get_font('body_italic'))
        self._btn_remind.configure(text=t('remind_later'), font=get_font('button'))
        self._btn_lang.configure(text=t('lang_btn'), font=get_font('lang_btn'))

    # ── Helpers ───────────────────────────────────────────────────────────

    def _make_dateline(self) -> str:
        day  = self._now.day
        date = f"{self._now.strftime('%A, %B')} {day}"
        intv = t('interval_text').get(str(self._interval), str(self._interval))
        return f"{date}  ·  {t('reminders_line')} {intv}"

    # ── Task callbacks ────────────────────────────────────────────────────

    def _on_check_changed(self):
        pass  # trace_add handles updates

    def _on_task_toggled(self, idx: int):
        done = self._check_vars[idx].get()
        self._task_labels[idx].configure(
            fg=COLORS['text_dim'] if done else COLORS['text'],
        )
        self._refresh_progress()
        if sum(v.get() for v in self._check_vars) == len(self._check_vars):
            # Save and trigger celebration after a brief moment so the
            # checkbox tick animation renders first.
            self.storage.update_completion([v.get() for v in self._check_vars])
            self.win.after(350, self._show_celebration)

    def _refresh_progress(self):
        done_count = sum(v.get() for v in self._check_vars)
        total      = len(self._check_vars)
        self._lbl_progress.configure(
            text=t('progress', done=done_count, total=total),
            fg=COLORS['success'] if done_count == total else COLORS['text_muted'],
        )
        for child in self._bar_outer.winfo_children():
            child.destroy()
        if total > 0 and done_count > 0:
            tk.Frame(self._bar_outer, bg=COLORS['progress_fill'], height=7).place(
                relwidth=done_count / total, relheight=1.0,
            )
        if done_count == total:
            self._lbl_alldone.pack(side='left')
        else:
            self._lbl_alldone.pack_forget()

    # ── Celebration screen ────────────────────────────────────────────────

    def _show_celebration(self):
        if not self.win.winfo_exists():
            return
        self._celebration_shown = True

        # Hide the task content
        if self._outer:
            self._outer.pack_forget()

        bg = COLORS['celebration_bg']
        frame = tk.Frame(self.win, bg=bg)
        frame.pack(fill='both', expand=True, padx=0, pady=0)

        # Top accent stripe
        tk.Frame(frame, bg=COLORS['accent'], height=6).pack(fill='x')

        inner = tk.Frame(frame, bg=bg, padx=40, pady=30)
        inner.pack(fill='both', expand=True)

        # Big emoji
        tk.Label(
            inner, text=t('celebration_emoji'),
            font=(get_font('celebration_h')[0], 52),
            bg=bg,
        ).pack(pady=(0, 8))

        # Title
        tk.Label(
            inner, text=t('celebration_title'),
            font=get_font('celebration_h'), bg=bg, fg=COLORS['accent'],
        ).pack(pady=(0, 6))

        # Subtitle
        tk.Label(
            inner, text=t('celebration_sub'),
            font=get_font('celebration_s'), bg=bg, fg=COLORS['text'],
        ).pack(pady=(0, 4))

        # Full progress bar
        bar_outer = tk.Frame(inner, bg=COLORS['progress_bg'], height=10)
        bar_outer.pack(fill='x', pady=(10, 14))
        bar_outer.pack_propagate(False)
        tk.Frame(bar_outer, bg=COLORS['progress_fill'], height=10).place(
            relwidth=1.0, relheight=1.0,
        )

        # Body text
        tk.Label(
            inner, text=t('celebration_body'),
            font=get_font('body'), bg=bg, fg=COLORS['text_muted'],
            justify='center',
        ).pack(pady=(0, 18))

        tk.Frame(inner, bg=COLORS['divider'], height=1).pack(fill='x', pady=(0, 14))

        # Countdown label
        self._lbl_countdown = tk.Label(
            inner, text=t('celebration_countdown', n=_CELEBRATION_COUNTDOWN),
            font=get_font('small'), bg=bg, fg=COLORS['text_dim'],
        )
        self._lbl_countdown.pack(pady=(0, 8))

        # Close button (appears immediately — user can click early)
        create_button(
            inner, t('celebration_close'),
            lambda: self._close(remind_later=False), style='success',
        ).pack(pady=(0, 4))

        # Start countdown
        self._countdown_val = _CELEBRATION_COUNTDOWN
        self.win.after(1000, self._tick_countdown)

        # Release the focus grab and desktop lock — user has earned their
        # desktop back by completing all tasks.
        desktop_lock.unlock()
        try:
            self.win.grab_release()
        except tk.TclError:
            pass

    def _tick_countdown(self):
        if not self.win.winfo_exists() or self._celebration_shown is False:
            return
        self._countdown_val -= 1
        if self._countdown_val <= 0:
            self._close(remind_later=False)
            return
        self._lbl_countdown.configure(
            text=t('celebration_countdown', n=self._countdown_val),
        )
        self.win.after(1000, self._tick_countdown)

    # ── AI message ────────────────────────────────────────────────────────

    def _fetch_ai_message(self):
        tasks     = self.data['tasks']
        completed = [v.get() for v in self._check_vars] if self._check_vars else self.data['completed']
        lang      = current_lang()

        def _cb(msg: str, _err):
            if self.win.winfo_exists():
                self.win.after(0, lambda: self._set_ai(msg))

        self.ai_client.get_motivational_message(tasks, completed, _cb, lang=lang)

    def _set_ai(self, message: str):
        if self._ai_lbl and self.win.winfo_exists():
            rtl = current_lang() == 'he'
            self._ai_lbl.configure(
                text=f'"{message}"',
                fg=COLORS['text'],
                anchor='e' if rtl else 'w',
                justify='right' if rtl else 'left',
            )

    # ── Close ─────────────────────────────────────────────────────────────

    def _close(self, remind_later: bool):
        if not self.win.winfo_exists():
            return
        if self._check_vars:
            self.storage.update_completion([v.get() for v in self._check_vars])
        desktop_lock.unlock()   # idempotent — safe if already unlocked by celebration
        try:
            self.win.grab_release()
        except tk.TclError:
            pass
        self.win.destroy()
        self.on_close(remind_later=remind_later)
