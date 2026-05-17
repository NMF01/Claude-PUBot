"""Morning popup — collects 3 daily focus tasks from the user."""
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

from .styles import (
    COLORS, get_font, create_button, create_lang_button,
    t, current_lang, set_lang,
)
from .settings import SettingsDialog
from . import desktop_lock


class DailySetupWindow:
    """Blocking popup at startup (after 6 AM) that forces the user to set
    three focus tasks before they can continue using the computer.

    Features a language toggle (EN ↔ עב) with RTL support and
    full Hebrew text when Hebrew is selected.
    """

    MAX_LEN = 100

    def __init__(self, parent: tk.Tk, storage, ai_client, on_complete):
        self.storage     = storage
        self.ai_client   = ai_client
        self.on_complete = on_complete

        # Widget refs updated by _apply_lang()
        self._lbl_page_hdr:   tk.Label | None = None
        self._lbl_title:      tk.Label | None = None
        self._lbl_subtitle:   tk.Label | None = None
        self._lbl_task_names: list[tk.Label]  = []
        self._lbl_remind_lbl: tk.Label | None = None
        self._radiobuttons:   list[tk.Radiobutton] = []
        self._lbl_hint:       tk.Label | None = None
        self._btn_lang:       tk.Button | None = None
        self._submit_btn:     tk.Button | None = None

        self._clock_lbl:     tk.Label | None    = None
        self._entry_vars:    list[tk.StringVar] = []
        self._entry_widgets: list[tk.Entry]     = []
        self._char_labels:   list[tk.Label]     = []
        self._interval_var   = tk.StringVar(value='60')

        win = tk.Toplevel(parent)
        win.title('PUBot')
        win.configure(bg=COLORS['lockscreen_bg'])
        win.overrideredirect(True)
        win.attributes('-fullscreen', True)
        win.attributes('-topmost', True)
        win.protocol('WM_DELETE_WINDOW', self._refuse_close)
        self.win = win

        self._build()

        desktop_lock.lock(parent)

        win.grab_set()
        win.focus_force()

    # ── Layout ────────────────────────────────────────────────────────────

    def _build(self):
        wrapper = tk.Frame(self.win, bg=COLORS['lockscreen_bg'])
        wrapper.pack(fill='both', expand=True)

        outer = tk.Frame(wrapper, bg=COLORS['bg'], padx=44, pady=28)
        outer.place(relx=0.5, rely=0.5, anchor='center', width=640, height=760)

        # ── Top row: gear + language toggle ───────────────────────────────
        top_row = tk.Frame(outer, bg=COLORS['bg'])
        top_row.pack(fill='x', pady=(0, 6))

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

        # ── Page header + live clock (same row) ──────────────────────────
        ph_row = tk.Frame(outer, bg=COLORS['bg'])
        ph_row.pack(fill='x', pady=(0, 4))

        self._lbl_page_hdr = tk.Label(
            ph_row, text=t('page_header'),
            font=get_font('label'), bg=COLORS['bg'],
            fg=COLORS['accent'], anchor='w',
        )
        self._lbl_page_hdr.pack(side='left')

        self._clock_lbl = tk.Label(
            ph_row, text=self._fmt_clock(),
            font=get_font('clock'), bg=COLORS['bg'],
            fg=COLORS['text'], anchor='e',
        )
        self._clock_lbl.pack(side='right')
        self.win.after(60_000, self._tick_clock)

        # ── Header ────────────────────────────────────────────────────────
        tk.Frame(outer, bg=COLORS['accent'], height=4, width=56).pack(anchor='w', pady=(4, 12))

        self._lbl_title = tk.Label(
            outer, text=t('setup_title'),
            font=get_font('heading'), bg=COLORS['bg'], fg=COLORS['text'], anchor='w',
        )
        self._lbl_title.pack(fill='x')

        self._lbl_subtitle = tk.Label(
            outer, text=t('setup_subtitle'),
            font=get_font('subtitle'), bg=COLORS['bg'], fg=COLORS['text_muted'], anchor='w',
        )
        self._lbl_subtitle.pack(fill='x', pady=(5, 0))

        tk.Frame(outer, bg=COLORS['divider'], height=1).pack(fill='x', pady=(14, 16))

        # ── Task entries ──────────────────────────────────────────────────
        for i in range(3):
            self._build_task_row(outer, i)

        tk.Frame(outer, bg=COLORS['divider'], height=1).pack(fill='x', pady=(10, 16))

        # ── Reminder interval ─────────────────────────────────────────────
        interval_frame = tk.Frame(outer, bg=COLORS['bg'])
        interval_frame.pack(fill='x', pady=(0, 6))

        self._lbl_remind_lbl = tk.Label(
            interval_frame, text=t('remind_every'),
            font=get_font('label'), bg=COLORS['bg'], fg=COLORS['text'],
        )
        self._lbl_remind_lbl.pack(side='left', padx=(0, 12))

        vals = t('interval_vals')   # ['20','30','60','90']
        lbls = t('interval_lbls')   # localised labels
        self._radiobuttons = []
        for val, lbl in zip(vals, lbls):
            rb = tk.Radiobutton(
                interval_frame, text=lbl,
                variable=self._interval_var, value=val,
                font=get_font('body'),
                bg=COLORS['bg'], fg=COLORS['text'],
                selectcolor=COLORS['accent'],
                activebackground=COLORS['bg'],
                activeforeground=COLORS['accent'],
                cursor='hand2',
            )
            rb.pack(side='left', padx=6)
            self._radiobuttons.append(rb)

        # ── Submit row ────────────────────────────────────────────────────
        tk.Frame(outer, bg=COLORS['divider'], height=1).pack(fill='x', pady=(16, 16))

        btn_row = tk.Frame(outer, bg=COLORS['bg'])
        btn_row.pack(fill='x')

        self._lbl_hint = tk.Label(
            btn_row, text=t('hint'),
            font=get_font('small'), bg=COLORS['bg'], fg=COLORS['text_dim'],
        )
        self._lbl_hint.pack(side='left', anchor='s', pady=4)

        self._submit_btn = create_button(
            btn_row, t('start_btn'), self._submit, style='primary',
            state='disabled',
        )
        self._submit_btn.configure(font=(get_font('button')[0], 12, 'bold'), padx=26, pady=11)
        self._submit_btn.pack(side='right')
        self._refresh_button()

    def _build_task_row(self, parent, idx: int):
        """Build one task card with label + character counter + entry."""
        card = tk.Frame(parent, bg=COLORS['card_bg'], padx=16, pady=12)
        card.pack(fill='x', pady=(0, 10))

        top = tk.Frame(card, bg=COLORS['card_bg'])
        top.pack(fill='x', pady=(0, 7))

        icon = t('task_icons')[idx]
        lbl_name = tk.Label(
            top, text=f"{icon}  {t('task_labels')[idx]}",
            font=get_font('label'), bg=COLORS['card_bg'], fg=COLORS['accent_light'],
        )
        lbl_name.pack(side='left')
        self._lbl_task_names.append(lbl_name)

        char_lbl = tk.Label(
            top, text=f'0/{self.MAX_LEN}',
            font=get_font('counter'), bg=COLORS['card_bg'], fg=COLORS['text_dim'],
        )
        char_lbl.pack(side='right')
        self._char_labels.append(char_lbl)

        var = tk.StringVar()
        entry = tk.Entry(
            card, textvariable=var,
            font=get_font('body'),
            bg=COLORS['input_bg'], fg=COLORS['text'],
            insertbackground=COLORS['accent'],
            relief='flat', bd=0,
            justify='right' if current_lang() == 'he' else 'left',
        )
        entry.pack(fill='x', ipady=9)
        entry.bind('<Return>', lambda e, i=idx: self._on_enter_key(i))

        var.trace_add('write', lambda *_a, i=idx, v=var: self._on_text_change(i, v))
        self._entry_vars.append(var)
        self._entry_widgets.append(entry)

        if idx == 0:
            self.win.after(120, entry.focus_set)

    # ── Language toggle ───────────────────────────────────────────────────

    def _open_settings(self):
        SettingsDialog(self.win, self.storage, self.ai_client)

    def _toggle_lang(self):
        new = 'he' if current_lang() == 'en' else 'en'
        set_lang(new)
        cfg = self.storage.get_config()
        cfg['lang'] = new
        self.storage.save_config(cfg)
        self._apply_lang()

    def _apply_lang(self):
        """Update all widget text and alignment for the active language."""
        rtl     = current_lang() == 'he'
        anchor  = 'e' if rtl else 'w'
        justify = 'right' if rtl else 'left'

        # Page header + header labels
        self._lbl_page_hdr.configure(
            text=t('page_header'), anchor=anchor, font=get_font('label'),
        )
        self._lbl_title.configure(
            text=t('setup_title'), anchor=anchor, font=get_font('heading'),
        )
        self._lbl_subtitle.configure(
            text=t('setup_subtitle'), anchor=anchor, font=get_font('subtitle'),
        )

        # Task name labels
        for i, lbl in enumerate(self._lbl_task_names):
            icon = t('task_icons')[i]
            lbl.configure(
                text=f"{icon}  {t('task_labels')[i]}",
                anchor=anchor, font=get_font('label'),
            )

        # Character counter alignment
        for char_lbl in self._char_labels:
            char_lbl.configure(font=get_font('counter'))

        # Entry text direction
        for entry in self._entry_widgets:
            entry.configure(justify=justify, font=get_font('body'))

        # Interval label + radiobuttons
        self._lbl_remind_lbl.configure(
            text=t('remind_every'), font=get_font('label'),
        )
        lbls = t('interval_lbls')
        for rb, lbl_text in zip(self._radiobuttons, lbls):
            rb.configure(text=lbl_text, font=get_font('body'))

        # Bottom row
        self._lbl_hint.configure(text=t('hint'), font=get_font('small'))
        self._submit_btn.configure(
            text=t('start_btn'),
            font=(get_font('button')[0], 12, 'bold'),
        )
        self._refresh_button()

        # Lang toggle button label (shows the OTHER language)
        self._btn_lang.configure(text=t('lang_btn'), font=get_font('lang_btn'))

    # ── Live clock ────────────────────────────────────────────────────────

    def _fmt_clock(self) -> str:
        now = datetime.now()
        return now.strftime('%H:%M') if current_lang() == 'he' else now.strftime('%I:%M %p').lstrip('0')

    def _tick_clock(self):
        if not self.win.winfo_exists():
            return
        self._clock_lbl.configure(text=self._fmt_clock())
        self.win.after(60_000, self._tick_clock)

    # ── Callbacks ─────────────────────────────────────────────────────────

    def _refuse_close(self):
        messagebox.showwarning(
            t('refuse_title'), t('refuse_body'), parent=self.win,
        )
        self.win.focus_force()

    def _on_text_change(self, idx: int, var: tk.StringVar):
        text = var.get()
        if len(text) > self.MAX_LEN:
            var.set(text[:self.MAX_LEN])
            text = text[:self.MAX_LEN]
        count = len(text)
        color = COLORS['warning'] if count > self.MAX_LEN * 0.88 else COLORS['text_dim']
        self._char_labels[idx].configure(text=f'{count}/{self.MAX_LEN}', fg=color)
        self._refresh_button()

    def _on_enter_key(self, idx: int):
        if idx < len(self._entry_widgets) - 1:
            self._entry_widgets[idx + 1].focus_set()
        elif self._all_filled():
            self._submit()

    def _all_filled(self) -> bool:
        return all(v.get().strip() for v in self._entry_vars)

    def _refresh_button(self):
        if not self._submit_btn:
            return
        if self._all_filled():
            self._submit_btn.configure(
                state='normal', bg=COLORS['accent'], fg='#ffffff',
            )
            self._submit_btn.bind('<Enter>', lambda _: self._submit_btn.configure(bg=COLORS['accent_hover']))
            self._submit_btn.bind('<Leave>', lambda _: self._submit_btn.configure(bg=COLORS['accent']))
        else:
            self._submit_btn.configure(
                state='disabled', bg=COLORS['text_dim'], fg=COLORS['bg'],
            )

    def _submit(self):
        tasks = [v.get().strip() for v in self._entry_vars]
        if not all(tasks):
            self._refuse_close()
            return
        interval = int(self._interval_var.get())
        self.storage.save_today_tasks(tasks, reminder_interval=interval)
        desktop_lock.unlock()
        self.win.destroy()
        self.on_complete()
