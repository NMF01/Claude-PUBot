"""Periodic reminder popup — shows tasks, progress, and an AI coaching message."""
import tkinter as tk
from datetime import datetime

from .styles import (
    COLORS, get_font, create_button, create_lang_button,
    t, current_lang, set_lang,
)


class ReminderWindow:
    """Shown every N minutes to check in on the user's 3 daily tasks.

    Features a language toggle (EN ↔ עב) with RTL support.
    The AI coaching message is re-fetched in the new language when toggled.
    """

    def __init__(self, parent: tk.Tk, storage, ai_client, on_close):
        self.storage    = storage
        self.ai_client  = ai_client
        self.on_close   = on_close

        self._check_vars:   list[tk.BooleanVar] = []
        self._task_labels:  list[tk.Label]      = []
        self._done_badges:  list[tk.Label | None] = []

        # Refs updated by _apply_lang()
        self._lbl_title:       tk.Label | None = None
        self._lbl_dateline:    tk.Label | None = None
        self._lbl_tasks_hdr:   tk.Label | None = None
        self._lbl_progress:    tk.Label | None = None
        self._lbl_alldone:     tk.Label | None = None
        self._lbl_coach:       tk.Label | None = None
        self._ai_lbl:          tk.Label | None = None
        self._btn_remind:      tk.Button | None = None
        self._btn_save:        tk.Button | None = None
        self._btn_lang:        tk.Button | None = None
        self._bar_outer:       tk.Frame | None = None
        self._bar_inner:       tk.Frame | None = None

        self.data = self.storage.get_today_tasks()
        if not self.data:
            return

        # Store for _apply_lang() regeneration of the date line
        self._now      = datetime.now()
        self._interval = self.data.get('reminder_interval', 60)

        win = tk.Toplevel(parent)
        win.title('PUBot')
        win.configure(bg=COLORS['bg'])
        win.resizable(False, False)
        win.attributes('-topmost', True)
        win.protocol('WM_DELETE_WINDOW', lambda: self._close(remind_later=True))
        self.win = win

        self._center(530, 620)
        self._build()
        win.grab_set()
        win.focus_force()
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

        outer = tk.Frame(self.win, bg=COLORS['bg'], padx=34, pady=24)
        outer.pack(fill='both', expand=True)

        # ── Top row: lang toggle ──────────────────────────────────────────
        top_row = tk.Frame(outer, bg=COLORS['bg'])
        top_row.pack(fill='x', pady=(0, 4))

        self._btn_lang = create_lang_button(top_row, self._toggle_lang)
        self._btn_lang.pack(side='right')

        # ── Header ────────────────────────────────────────────────────────
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
        self._bar_inner = None
        if total > 0 and done_count > 0:
            self._bar_inner = tk.Frame(
                self._bar_outer, bg=COLORS['progress_fill'], height=7,
            )
            self._bar_inner.place(relwidth=done_count / total, relheight=1.0)

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

        # ── Buttons ───────────────────────────────────────────────────────
        tk.Frame(outer, bg=COLORS['divider'], height=1).pack(fill='x', pady=(12, 12))

        btn_row = tk.Frame(outer, bg=COLORS['bg'])
        btn_row.pack(fill='x')

        self._btn_remind = create_button(
            btn_row, t('remind_later'),
            lambda: self._close(remind_later=True), style='secondary',
        )
        self._btn_remind.pack(side='left')

        self._btn_save = create_button(
            btn_row, t('save_close'),
            lambda: self._close(remind_later=False), style='primary',
        )
        self._btn_save.pack(side='right')

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

    # ── Language toggle ───────────────────────────────────────────────────

    def _toggle_lang(self):
        new = 'he' if current_lang() == 'en' else 'en'
        set_lang(new)
        cfg = self.storage.get_config()
        cfg['lang'] = new
        self.storage.save_config(cfg)
        self._apply_lang()
        # Re-fetch AI message in new language
        self._ai_lbl.configure(text=t('loading'), fg=COLORS['text_muted'],
                               font=get_font('body_italic'))
        self._fetch_ai_message()

    def _apply_lang(self):
        """Update all stored widget texts and alignments for the active language."""
        rtl     = current_lang() == 'he'
        anchor  = 'e' if rtl else 'w'
        justify = 'right' if rtl else 'left'

        self._lbl_title.configure(
            text=t('checkin_title'), anchor=anchor, font=get_font('title'),
        )
        self._lbl_dateline.configure(
            text=self._make_dateline(), anchor=anchor, font=get_font('small'),
        )
        self._lbl_tasks_hdr.configure(
            text=t('tasks_header'), anchor=anchor, font=get_font('label'),
        )

        # Task label text direction (task text itself stays as entered by user)
        for lbl in self._task_labels:
            lbl.configure(anchor=anchor, justify=justify, font=get_font('body'))

        # Done badges
        for badge in self._done_badges:
            if badge:
                badge.configure(text=t('done_badge'), font=get_font('small'))

        # Progress
        done_count = sum(v.get() for v in self._check_vars)
        total      = len(self._check_vars)
        self._lbl_progress.configure(
            text=t('progress', done=done_count, total=total),
            anchor=anchor, font=get_font('body'),
        )
        if self._lbl_alldone:
            self._lbl_alldone.configure(
                text=f"  {t('all_done')}", font=get_font('body'),
            )

        # AI card
        self._lbl_coach.configure(
            text=t('coach_label'), anchor=anchor, font=get_font('small'),
        )
        self._ai_lbl.configure(anchor=anchor, justify=justify, font=get_font('body_italic'))

        # Buttons
        self._btn_remind.configure(text=t('remind_later'), font=get_font('button'))
        self._btn_save.configure(text=t('save_close'), font=get_font('button'))
        self._btn_lang.configure(text=t('lang_btn'), font=get_font('lang_btn'))

    # ── Helpers ───────────────────────────────────────────────────────────

    def _make_dateline(self) -> str:
        """Build the date + reminder frequency line in the current language."""
        day  = self._now.day
        date = f"{self._now.strftime('%A, %B')} {day}"
        intv = t('interval_text').get(str(self._interval), str(self._interval))
        return f"{date}  ·  {t('reminders_line')} {intv}"

    # ── Callbacks ─────────────────────────────────────────────────────────

    def _on_check_changed(self):
        pass  # trace_add handles updates

    def _on_task_toggled(self, idx: int):
        done = self._check_vars[idx].get()
        self._task_labels[idx].configure(
            fg=COLORS['text_dim'] if done else COLORS['text'],
        )
        self._refresh_progress()

    def _refresh_progress(self):
        done_count = sum(v.get() for v in self._check_vars)
        total      = len(self._check_vars)
        self._lbl_progress.configure(
            text=t('progress', done=done_count, total=total),
            fg=COLORS['success'] if done_count == total else COLORS['text_muted'],
        )
        # Redraw bar
        for child in self._bar_outer.winfo_children():
            child.destroy()
        if total > 0 and done_count > 0:
            tk.Frame(self._bar_outer, bg=COLORS['progress_fill'], height=7).place(
                relwidth=done_count / total, relheight=1.0,
            )
        # Show / hide "All done" label
        if done_count == total:
            self._lbl_alldone.pack(side='left')
        else:
            self._lbl_alldone.pack_forget()

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

    def _close(self, remind_later: bool):
        completed = [v.get() for v in self._check_vars]
        self.storage.update_completion(completed)
        self.win.destroy()
        self.on_close(remind_later=remind_later)
