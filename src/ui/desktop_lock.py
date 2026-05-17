"""Windows desktop lock — invoked when a PUBot popup opens.

Two layers of enforcement
─────────────────────────
1. Keyboard hook (WH_KEYBOARD_LL, runs in its own message-pump thread):
   Blocks Windows key, Alt+Tab, Alt+F4, Alt+Esc, Alt+Space, Ctrl+Esc,
   and Ctrl+Shift+Esc (Task Manager) so the user cannot keyboard-navigate
   away from the popup.

2. Taskbar hidden:
   FindWindowW('Shell_TrayWnd') → ShowWindow(SW_HIDE).  Restored on unlock.

The popup windows themselves are fullscreen (overrideredirect + full screen
geometry), so the OS cannot route mouse clicks to any other application.

On non-Windows platforms every function is a no-op so the rest of the code
does not need platform guards.
"""
import logging
import platform
import threading
import tkinter as tk

_IS_WIN = platform.system() == 'Windows'

if _IS_WIN:
    import ctypes
    import ctypes.wintypes as _wt

    _user32   = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32

    # ── Constants ─────────────────────────────────────────────────────────
    _SW_HIDE         = 0
    _SW_SHOW         = 5
    _WH_KB_LL        = 13
    _WM_KEYDOWN      = 0x0100
    _WM_SYSKEYDOWN   = 0x0104
    _WM_QUIT         = 0x0012
    _LLKHF_ALTDOWN   = 0x20    # flags bit in KBDLLHOOKSTRUCT

    _VK_LWIN         = 0x5B
    _VK_RWIN         = 0x5C
    _VK_TAB          = 0x09
    _VK_ESCAPE       = 0x1B
    _VK_F4           = 0x73
    _VK_SPACE        = 0x20
    _VK_SHIFT        = 0x10
    _VK_CTRL         = 0x11

    _HOOKPROC = ctypes.WINFUNCTYPE(
        ctypes.c_longlong,
        ctypes.c_int, _wt.WPARAM, _wt.LPARAM,
    )

    class _KBDLL(ctypes.Structure):
        _fields_ = [
            ('vkCode',      _wt.DWORD),
            ('scanCode',    _wt.DWORD),
            ('flags',       _wt.DWORD),
            ('time',        _wt.DWORD),
            ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong)),
        ]

# ── Module-level state (one lock active at a time) ────────────────────────

_hook_handle: object = None   # HHOOK
_hook_fn:     object = None   # HOOKPROC — must stay alive or callback is GC'd
_hook_tid:    int    = 0
_locked:      bool   = False


# ── Internal helpers ──────────────────────────────────────────────────────

def _taskbar_hwnd():
    return _user32.FindWindowW('Shell_TrayWnd', None)


def _ctrl_down() -> bool:
    return bool(_user32.GetAsyncKeyState(_VK_CTRL) & 0x8000)


def _shift_down() -> bool:
    return bool(_user32.GetAsyncKeyState(_VK_SHIFT) & 0x8000)


def _make_hook_proc():
    """Build and return a HOOKPROC that swallows desktop-escape key combos."""

    def _hook(nCode, wParam, lParam):
        if nCode >= 0 and wParam in (_WM_KEYDOWN, _WM_SYSKEYDOWN):
            kb  = ctypes.cast(lParam, ctypes.POINTER(_KBDLL)).contents
            vk  = kb.vkCode
            alt = bool(kb.flags & _LLKHF_ALTDOWN)

            # ── Windows key (left and right) ──────────────────────────────
            if vk in (_VK_LWIN, _VK_RWIN):
                return 1

            # ── Alt+Tab  /  Alt+Shift+Tab ─────────────────────────────────
            if vk == _VK_TAB and alt:
                return 1

            # ── Alt+F4 ────────────────────────────────────────────────────
            if vk == _VK_F4 and alt:
                return 1

            # ── Alt+Esc (cycle open windows in taskbar) ───────────────────
            if vk == _VK_ESCAPE and alt:
                return 1

            # ── Alt+Space (window system menu) ────────────────────────────
            if vk == _VK_SPACE and alt:
                return 1

            # ── Ctrl+Esc (Start / taskbar) ────────────────────────────────
            if vk == _VK_ESCAPE and _ctrl_down():
                return 1

            # ── Ctrl+Shift+Esc (Task Manager) ─────────────────────────────
            if vk == _VK_ESCAPE and _ctrl_down() and _shift_down():
                return 1

        return _user32.CallNextHookEx(None, nCode, wParam, lParam)

    return _HOOKPROC(_hook)


def _hook_thread_main():
    """Install the keyboard hook and run the message pump that services it.

    WH_KEYBOARD_LL requires the installing thread to call GetMessage — the
    hook callback is dispatched via that thread's message queue.
    """
    global _hook_handle, _hook_fn, _hook_tid

    _hook_tid = _kernel32.GetCurrentThreadId()
    _hook_fn  = _make_hook_proc()

    _hook_handle = _user32.SetWindowsHookExW(
        _WH_KB_LL,
        _hook_fn,
        _kernel32.GetModuleHandleW(None),
        0,
    )
    if not _hook_handle:
        logging.warning('desktop_lock: SetWindowsHookExW failed (err %d)',
                        _kernel32.GetLastError())
        return

    logging.info('desktop_lock: keyboard hook installed (TID %d).', _hook_tid)

    msg = _wt.MSG()
    while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        _user32.TranslateMessage(ctypes.byref(msg))
        _user32.DispatchMessageW(ctypes.byref(msg))

    _user32.UnhookWindowsHookEx(_hook_handle)
    _hook_handle = None
    logging.info('desktop_lock: keyboard hook removed.')


# ── Public API ────────────────────────────────────────────────────────────

def lock(tk_root: tk.Misc) -> None:
    """Activate the desktop lock: hide the taskbar and install the keyboard hook.

    The popup windows are fullscreen (overrideredirect), so no blackout overlay
    is needed — the popup IS the screen.  Call unlock() when the popup closes.
    No-op on non-Windows platforms.
    """
    global _locked

    if not _IS_WIN:
        return

    if _locked:
        return

    _locked = True

    # 1. Hide the taskbar
    hwnd = _taskbar_hwnd()
    if hwnd:
        _user32.ShowWindow(hwnd, _SW_HIDE)
        logging.info('desktop_lock: taskbar hidden.')

    # 2. Low-level keyboard hook (needs its own message pump thread)
    t = threading.Thread(
        target=_hook_thread_main,
        daemon=True,
        name='PUBot-KBHook',
    )
    t.start()

    logging.info('desktop_lock: locked.')


def unlock():
    """Release the desktop lock. Safe to call even if not currently locked."""
    global _locked, _hook_tid

    if not _IS_WIN or not _locked:
        return

    _locked = False

    # Restore the taskbar
    hwnd = _taskbar_hwnd()
    if hwnd:
        _user32.ShowWindow(hwnd, _SW_SHOW)
        logging.info('desktop_lock: taskbar restored.')

    # Stop the keyboard hook thread
    if _hook_tid:
        _user32.PostThreadMessageW(_hook_tid, _WM_QUIT, 0, 0)
        _hook_tid = 0

    logging.info('desktop_lock: unlocked.')
