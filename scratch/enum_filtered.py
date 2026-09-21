import win32gui
import ctypes

hdesk = ctypes.windll.user32.OpenInputDesktop(0, False, 0x01ff)
wins = []
def enum_cb(hwnd, lparam):
    t = win32gui.GetWindowText(hwnd).strip()
    c = win32gui.GetClassName(hwnd).strip()
    if t and not any(k in t.lower() for k in ["default ime", "msctfime ui", "gdi+", "broadcast", "program manager"]):
        wins.append((hwnd, t, c))
    return True

win32gui.EnumDesktopWindows(hdesk, enum_cb, None)
for h, t, c in wins:
    print(f"HWND: {h} | Title: '{t}' | Class: '{c}'")
