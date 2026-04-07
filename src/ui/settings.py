"""Settings dialog — lets the user paste a Claude API key."""
import tkinter as tk

from .styles import COLORS, get_font, create_button, t, current_lang


class SettingsDialog:
    """Small modal dialog for entering / updating the Anthropic API key."""

    def __init__(self, parent, storage, ai_client):
        self.storage    = storage
        self.ai_client  = ai_client

        win = tk.Toplevel(parent)
        win.title(t('settings_title'))
        win.configure(bg=COLORS['bg'])
        win.resizable(False, False)
        win.attributes('-topmost', True)
        self.win = win

        self._build()
        self._center(460, 230)
        win.grab_set()
        win.focus_force()

    # ── Layout ────────────────────────────────────────────────────────────

    def _center(self, w: int, h: int):
        self.win.update_idletasks()
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        self.win.geometry(f'{w}x{h}+{(sw - w)//2}+{(sh - h)//2}')

    def _build(self):
        cfg         = self.storage.get_config()
        current_key = cfg.get('api_key', '')
        rtl         = current_lang() == 'he'
        anchor      = 'e' if rtl else 'w'
        justify     = 'right' if rtl else 'left'

        outer = tk.Frame(self.win, bg=COLORS['bg'], padx=28, pady=22)
        outer.pack(fill='both', expand=True)

        # Title
        tk.Label(
            outer, text=t('settings_title'),
            font=get_font('title'), bg=COLORS['bg'], fg=COLORS['text'], anchor=anchor,
        ).pack(fill='x', pady=(0, 2))

        tk.Frame(outer, bg=COLORS['divider'], height=1).pack(fill='x', pady=(4, 12))

        # Label
        tk.Label(
            outer, text=t('api_key_label'),
            font=get_font('label'), bg=COLORS['bg'], fg=COLORS['text_muted'], anchor=anchor,
        ).pack(fill='x', pady=(0, 5))

        # Key entry — masked with bullets
        self._key_var = tk.StringVar(value=current_key)
        entry_frame = tk.Frame(outer, bg=COLORS['input_bg'])
        entry_frame.pack(fill='x')

        self._entry = tk.Entry(
            entry_frame, textvariable=self._key_var,
            font=get_font('body'),
            bg=COLORS['input_bg'], fg=COLORS['text'],
            insertbackground=COLORS['accent'],
            relief='flat', bd=0,
            show='•',
            justify=justify,
        )
        self._entry.pack(side='left', fill='x', expand=True, ipady=8, padx=(8, 0))

        # Show / hide toggle
        self._visible = False
        self._eye_btn = tk.Button(
            entry_frame, text='👁',
            command=self._toggle_visibility,
            bg=COLORS['input_bg'], fg=COLORS['text_muted'],
            relief='flat', bd=0, padx=6, cursor='hand2',
            activebackground=COLORS['input_bg'],
        )
        self._eye_btn.pack(side='right', padx=(0, 4))

        # Hint
        tk.Label(
            outer, text=t('api_key_hint'),
            font=get_font('small'), bg=COLORS['bg'], fg=COLORS['text_dim'],
            anchor=anchor, justify=justify, wraplength=400,
        ).pack(fill='x', pady=(5, 14))

        # Buttons
        btn_row = tk.Frame(outer, bg=COLORS['bg'])
        btn_row.pack(fill='x')

        create_button(
            btn_row, t('cancel_btn'), self.win.destroy, style='secondary',
        ).pack(side='left')

        create_button(
            btn_row, t('save_btn'), self._save, style='primary',
        ).pack(side='right')

        self._entry.focus_set()

    # ── Callbacks ─────────────────────────────────────────────────────────

    def _toggle_visibility(self):
        self._visible = not self._visible
        self._entry.configure(show='' if self._visible else '•')

    def _save(self):
        key = self._key_var.get().strip()
        cfg = self.storage.get_config()
        cfg['api_key'] = key
        self.storage.save_config(cfg)
        self.ai_client.update_api_key(key)
        self.win.destroy()
