"""Morning popup — collects 3 daily focus tasks from the user."""
import tkinter as tk
from tkinter import messagebox

from .styles import COLORS, FONTS, create_button


class DailySetupWindow:
    """Blocking popup at startup (after 6 AM) that forces the user to set
    three focus tasks before they can continue using the computer."""

    MAX_LEN = 100

    def __init__(self, parent: tk.Tk, storage, on_complete):
        self.storage = storage
        self.on_complete = on_complete

        self._entry_vars: list[tk.StringVar] = []
        self._entry_widgets: list[tk.Entry] = []
        self._char_labels: list[tk.Label] = []
        self._submit_btn: tk.Button | None = None

        win = tk.Toplevel(parent)
        win.title('PUBot — Good Morning!')
        win.configure(bg=COLORS['bg'])
        win.resizable(False, False)
        win.attributes('-topmost', True)
        win.protocol('WM_DELETE_WINDOW', self._refuse_close)
        self.win = win

        self._center(620, 740)
        self._build()

        # Grab all input — user cannot click away
        win.grab_set()
        win.focus_force()

    # ── Layout ────────────────────────────────────────────────────────────

    def _center(self, w: int, h: int):
        self.win.update_idletasks()
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        self.win.geometry(f'{w}x{h}+{(sw - w)//2}+{(sh - h)//2}')

    def _build(self):
        outer = tk.Frame(self.win, bg=COLORS['bg'], padx=44, pady=32)
        outer.pack(fill='both', expand=True)

        # ── Header ────────────────────────────────────────────────────────
        tk.Frame(outer, bg=COLORS['accent'], height=4, width=56).pack(anchor='w', pady=(0, 14))

        tk.Label(
            outer, text='Good Morning!',
            font=FONTS['heading'], bg=COLORS['bg'], fg=COLORS['text'], anchor='w',
        ).pack(fill='x')

        tk.Label(
            outer, text="What are your 3 focus tasks for today?",
            font=FONTS['subtitle'], bg=COLORS['bg'], fg=COLORS['text_muted'], anchor='w',
        ).pack(fill='x', pady=(5, 0))

        tk.Frame(outer, bg=COLORS['divider'], height=1).pack(fill='x', pady=(16, 18))

        # ── Task entries ──────────────────────────────────────────────────
        icons  = ['🎯', '📌', '✨']
        labels = ['Primary task', 'Second task', 'Third task']
        for i in range(3):
            self._build_task_row(outer, i, icons[i], labels[i])

        tk.Frame(outer, bg=COLORS['divider'], height=1).pack(fill='x', pady=(12, 18))

        # ── Reminder interval ─────────────────────────────────────────────
        row = tk.Frame(outer, bg=COLORS['bg'])
        row.pack(fill='x', pady=(0, 6))

        tk.Label(
            row, text='⏰  Remind me every:',
            font=FONTS['label'], bg=COLORS['bg'], fg=COLORS['text'],
        ).pack(side='left', padx=(0, 14))

        self._interval_var = tk.StringVar(value='60')
        for val, lbl in [('30', '30 min'), ('60', '1 hour'), ('90', '90 min')]:
            tk.Radiobutton(
                row, text=lbl,
                variable=self._interval_var, value=val,
                font=FONTS['body'],
                bg=COLORS['bg'], fg=COLORS['text'],
                selectcolor=COLORS['accent'],
                activebackground=COLORS['bg'],
                activeforeground=COLORS['accent_light'],
                cursor='hand2',
            ).pack(side='left', padx=8)

        # ── Submit ────────────────────────────────────────────────────────
        tk.Frame(outer, bg=COLORS['divider'], height=1).pack(fill='x', pady=(18, 18))

        btn_row = tk.Frame(outer, bg=COLORS['bg'])
        btn_row.pack(fill='x')

        tk.Label(
            btn_row, text='Fill in all 3 tasks to continue',
            font=FONTS['small'], bg=COLORS['bg'], fg=COLORS['text_dim'],
        ).pack(side='left', anchor='s', pady=4)

        self._submit_btn = create_button(
            btn_row, '  Start My Day  →', self._submit, style='primary',
            state='disabled',
        )
        self._submit_btn.configure(font=(FONTS['button'][0], 12, 'bold'), padx=26, pady=11)
        self._submit_btn.pack(side='right')
        self._refresh_button()

    def _build_task_row(self, parent, idx: int, icon: str, label_text: str):
        card = tk.Frame(parent, bg=COLORS['card_bg'], padx=16, pady=12)
        card.pack(fill='x', pady=(0, 10))

        # Label row with character counter
        top = tk.Frame(card, bg=COLORS['card_bg'])
        top.pack(fill='x', pady=(0, 7))

        tk.Label(
            top, text=f'{icon}  {label_text}',
            font=FONTS['label'], bg=COLORS['card_bg'], fg=COLORS['accent_light'],
        ).pack(side='left')

        char_lbl = tk.Label(
            top, text=f'0/{self.MAX_LEN}',
            font=FONTS['counter'], bg=COLORS['card_bg'], fg=COLORS['text_dim'],
        )
        char_lbl.pack(side='right')
        self._char_labels.append(char_lbl)

        # Entry widget
        var = tk.StringVar()
        entry = tk.Entry(
            card, textvariable=var,
            font=FONTS['body'],
            bg=COLORS['input_bg'], fg=COLORS['text'],
            insertbackground=COLORS['accent_light'],
            relief='flat', bd=0,
        )
        entry.pack(fill='x', ipady=9)
        entry.bind('<Return>', lambda e, i=idx: self._on_enter_key(i))

        var.trace_add('write', lambda *_a, i=idx, v=var: self._on_text_change(i, v))

        self._entry_vars.append(var)
        self._entry_widgets.append(entry)

        if idx == 0:
            self.win.after(120, entry.focus_set)

    # ── Callbacks ─────────────────────────────────────────────────────────

    def _refuse_close(self):
        messagebox.showwarning(
            'Daily Focus Required',
            'Please enter your 3 focus tasks for today before continuing.\n\n'
            'PUBot keeps you on track — just a moment!',
            parent=self.win,
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
                state='normal',
                bg=COLORS['accent'], fg=COLORS['text'],
            )
            self._submit_btn.bind('<Enter>', lambda _: self._submit_btn.configure(bg=COLORS['accent_hover']))
            self._submit_btn.bind('<Leave>', lambda _: self._submit_btn.configure(bg=COLORS['accent']))
        else:
            self._submit_btn.configure(
                state='disabled',
                bg=COLORS['text_dim'], fg=COLORS['bg'],
            )

    def _submit(self):
        tasks = [v.get().strip() for v in self._entry_vars]
        if not all(tasks):
            self._refuse_close()
            return
        interval = int(self._interval_var.get())
        self.storage.save_today_tasks(tasks, reminder_interval=interval)
        self.win.destroy()
        self.on_complete()
