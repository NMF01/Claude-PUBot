"""Shared UI styles, colours, translations and font definitions."""
import platform
import tkinter as tk

_OS = platform.system()

# Base font families
if _OS == 'Windows':
    _FONT_EN = 'Segoe UI'
elif _OS == 'Darwin':
    _FONT_EN = 'Helvetica Neue'
else:
    _FONT_EN = 'Helvetica'

_FONT_HE = 'Arial'   # Arial has full Hebrew glyph coverage on all platforms

# ── Colour palette — light white / green ─────────────────────────────────

COLORS = {
    'bg':            '#f7fdf7',   # near-white with faint green tint
    'surface':       '#ffffff',   # pure white cards / inputs
    'surface_alt':   '#f0faf0',   # light green row background
    'accent':        '#16a34a',   # medium green — primary buttons, progress bar
    'accent_hover':  '#15803d',   # darker green on hover
    'accent_light':  '#166534',   # dark green for card icon labels
    'success':       '#15803d',
    'success_bg':    '#dcfce7',
    'warning':       '#d97706',
    'error':         '#dc2626',
    'text':          '#14532d',   # dark green — primary readable text
    'text_muted':    '#4b7a54',
    'text_dim':      '#86a98c',
    'input_bg':      '#ffffff',
    'input_border':  '#bbf7d0',
    'divider':       '#d1fae5',
    'progress_fill': '#16a34a',
    'progress_bg':   '#dcfce7',
    'card_bg':       '#f0faf0',
    'celebration_bg':'#f0fdf4',   # very light mint for celebration screen
}

# ── Font specs — (size, *attrs) without family ────────────────────────────
# get_font() injects the right family for the active language.

FONT_SPECS: dict[str, tuple] = {
    'heading':       (22, 'bold'),
    'title':         (17, 'bold'),
    'subtitle':      (12,),
    'label':         (11, 'bold'),
    'body':          (11,),
    'body_italic':   (11, 'italic'),
    'small':         (9,),
    'button':        (11, 'bold'),
    'counter':       (9,),
    'lang_btn':      (9, 'bold'),
    'celebration_h': (26, 'bold'),
    'celebration_s': (13,),
}

# Convenience alias kept for any code that imports FONTS directly
FONTS: dict[str, tuple] = {k: (_FONT_EN, *v) for k, v in FONT_SPECS.items()}


# ── Language state ────────────────────────────────────────────────────────

_lang: str = 'en'


def get_font(style: str) -> tuple:
    """Return (family, size, *attrs) for the current language."""
    family = _FONT_HE if _lang == 'he' else _FONT_EN
    return (family, *FONT_SPECS[style])


def current_lang() -> str:
    return _lang


def set_lang(lang: str) -> None:
    global _lang
    _lang = lang if lang in STRINGS else 'en'


def t(key: str, **kw) -> str:
    """Translate key in the current language, with optional .format() kwargs."""
    s = STRINGS[_lang].get(key, STRINGS['en'].get(key, key))
    return s.format(**kw) if kw else s


# ── Translation strings ───────────────────────────────────────────────────

STRINGS: dict[str, dict] = {
    'en': {
        # daily_setup
        'setup_title':   'Good Morning!',
        'setup_subtitle':'What are your 3 focus tasks for today?',
        'task_icons':    ['🎯', '📌', '✨'],
        'task_labels':   ['Primary task', 'Second task', 'Third task'],
        'remind_every':  '⏰  Remind me every:',
        'interval_vals': ['20', '30', '60', '90'],
        'interval_lbls': ['20 min', '30 min', '1 hour', '90 min'],
        'hint':          'Fill in all 3 tasks to continue',
        'start_btn':     '  Start My Day  →',
        'refuse_title':  'Daily Focus Required',
        'refuse_body':   (
            'Please enter your 3 focus tasks for today before continuing.\n\n'
            'PUBot keeps you on track — just a moment!'
        ),
        # reminder
        'checkin_title': '⏰  Focus Check-In',
        'tasks_header':  "Today's 3 tasks:",
        'remind_later':  'Remind me later',
        'save_close':    'Save & Close  ✓',
        'coach_label':   '✦  Coach',
        'loading':       'Loading insight…',
        'all_done':      '🎉 All done!',
        'progress':      '{done} of {total} tasks completed',
        'done_badge':    '✓ Done',
        'interval_text': {
            '20': '20 min', '30': '30 min', '60': '1 hour', '90': '90 min',
        },
        'reminders_line':'reminders every',
        # page header
        'page_header':   'My daily focus list.',
        # settings dialog
        'settings_title': 'Settings',
        'api_key_label':  'Claude API Key',
        'api_key_hint':   'Paste your Anthropic key (sk-ant-…) to enable personalised coaching.',
        'save_btn':       'Save',
        'cancel_btn':     'Cancel',
        # celebration screen
        'celebration_emoji':   '🎉',
        'celebration_title':   'You did it!',
        'celebration_sub':     'All 3 focus tasks completed for today.',
        'celebration_body':    'Reminders will pause until tomorrow morning.\nEnjoy the rest of your day!',
        'celebration_close':   'Close & Finish  ✓',
        'celebration_countdown': 'Closing in {n}…',
        # toggle button text (shown when THIS is the CURRENT language)
        'lang_btn':      'עב',
    },
    'he': {
        # daily_setup
        'setup_title':   'בוקר טוב!',
        'setup_subtitle':'מהן 3 המשימות שלך להיום?',
        'task_icons':    ['🎯', '📌', '✨'],
        'task_labels':   ['משימה ראשית', 'משימה שנייה', 'משימה שלישית'],
        'remind_every':  '⏰  הזכר לי כל:',
        'interval_vals': ['20', '30', '60', '90'],
        'interval_lbls': ['20 דקות', '30 דקות', 'שעה', '90 דקות'],
        'hint':          'מלא את 3 המשימות כדי להמשיך',
        'start_btn':     '← התחל את היום שלי  ',
        'refuse_title':  'נדרש מיקוד יומי',
        'refuse_body':   'אנא הזן 3 משימות לפני שתמשיך.\n\nPUBot כאן כדי לעזור — רק רגע!',
        # reminder
        'checkin_title': "⏰  צ'ק אין — מיקוד",
        'tasks_header':  'המשימות שלך להיום:',
        'remind_later':  'הזכר לי מאוחר יותר',
        'save_close':    'שמור וסגור  ✓',
        'coach_label':   '✦  מאמן',
        'loading':       'טוען תובנה…',
        'all_done':      '🎉 הכל הושלם!',
        'progress':      '{done} מתוך {total} משימות הושלמו',
        'done_badge':    '✓ הושלם',
        'interval_text': {
            '20': '20 דקות', '30': '30 דקות', '60': 'שעה', '90': '90 דקות',
        },
        'reminders_line':'תזכורות כל',
        # page header
        'page_header':   'המיקוד היומי שלי...',
        # settings dialog
        'settings_title': 'הגדרות',
        'api_key_label':  'מפתח Claude API',
        'api_key_hint':   'הדבק את מפתח ה-API של Anthropic (sk-ant-…) כדי לאפשר אימון מותאם אישית.',
        'save_btn':       'שמור',
        'cancel_btn':     'ביטול',
        # celebration screen
        'celebration_emoji':   '🎉',
        'celebration_title':   'כל הכבוד!',
        'celebration_sub':     'כל 3 המשימות היומיות הושלמו.',
        'celebration_body':    'התזכורות יופסקו עד מחר בבוקר.\nתיהנה משאר היום!',
        'celebration_close':   'סגור וסיים  ✓',
        'celebration_countdown': 'נסגר בעוד {n}…',
        # toggle button text (shown when THIS is the CURRENT language)
        'lang_btn':      'EN',
    },
}


# ── Button factory ────────────────────────────────────────────────────────

def create_button(
    parent,
    text: str,
    command,
    style: str = 'primary',
    **kwargs,
) -> tk.Button:
    """Return a flat styled tk.Button with hover effect."""
    palettes = {
        'primary':   (COLORS['accent'],      COLORS['accent_hover'], '#ffffff'),
        'secondary': ('#d1fae5',             '#a7f3d0',              COLORS['accent_light']),
        'success':   (COLORS['success'],     '#166534',              '#ffffff'),
        'lang':      (COLORS['surface'],     COLORS['divider'],      COLORS['accent']),
    }
    bg, hover, fg = palettes.get(style, palettes['primary'])

    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        font=get_font('button'),
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


def create_lang_button(parent, command) -> tk.Button:
    """Small pill-shaped language toggle button."""
    btn = tk.Button(
        parent,
        text=t('lang_btn'),
        command=command,
        bg=COLORS['success_bg'],
        fg=COLORS['accent'],
        font=get_font('lang_btn'),
        relief='flat',
        padx=10,
        pady=4,
        cursor='hand2',
        activebackground=COLORS['divider'],
        activeforeground=COLORS['accent_light'],
        bd=0,
    )
    btn.bind('<Enter>', lambda _: btn.configure(bg=COLORS['divider']))
    btn.bind('<Leave>', lambda _: btn.configure(bg=COLORS['success_bg']))
    return btn
