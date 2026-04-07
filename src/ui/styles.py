"""Shared UI styles, colours and font definitions."""
import platform
import tkinter as tk

_OS = platform.system()

if _OS == 'Windows':
    _FONT = 'Segoe UI'
elif _OS == 'Darwin':
    _FONT = 'Helvetica Neue'
else:
    _FONT = 'Helvetica'

COLORS = {
    'bg':            '#0f0e17',
    'surface':       '#1e1b4b',
    'surface_alt':   '#252444',
    'accent':        '#7c3aed',
    'accent_hover':  '#6d28d9',
    'accent_light':  '#a78bfa',
    'success':       '#10b981',
    'success_bg':    '#022c22',
    'warning':       '#f59e0b',
    'error':         '#ef4444',
    'text':          '#f8fafc',
    'text_muted':    '#94a3b8',
    'text_dim':      '#64748b',
    'input_bg':      '#1e1b4b',
    'input_border':  '#4c1d95',
    'divider':       '#2d2b55',
    'progress_fill': '#7c3aed',
    'progress_bg':   '#2d2b55',
    'card_bg':       '#1a1730',
}

FONTS = {
    'heading':      (_FONT, 22, 'bold'),
    'title':        (_FONT, 17, 'bold'),
    'subtitle':     (_FONT, 12),
    'label':        (_FONT, 11, 'bold'),
    'body':         (_FONT, 11),
    'body_italic':  (_FONT, 11, 'italic'),
    'small':        (_FONT, 9),
    'button':       (_FONT, 11, 'bold'),
    'counter':      (_FONT, 9),
}


def create_button(
    parent,
    text: str,
    command,
    style: str = 'primary',
    **kwargs,
) -> tk.Button:
    """Return a flat, styled tk.Button with hover effect."""
    palettes = {
        'primary':   (COLORS['accent'],      COLORS['accent_hover'], COLORS['text']),
        'secondary': (COLORS['surface_alt'], COLORS['surface'],      COLORS['text']),
        'success':   ('#0d9668',             '#0a7a56',              '#ffffff'),
    }
    bg, hover, fg = palettes.get(style, palettes['primary'])

    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        font=FONTS['button'],
        relief='flat',
        padx=20,
        pady=9,
        cursor='hand2',
        activebackground=hover,
        activeforeground=fg,
        **kwargs,
    )
    btn.bind('<Enter>', lambda _: btn.configure(bg=hover))
    btn.bind('<Leave>', lambda _: btn.configure(bg=bg))
    return btn
