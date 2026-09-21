import win32gui
import win32process
import win32service
import ctypes

def list_desktop_windows():
    # Open input desktop
    hdesk = ctypes.windll.user32.OpenInputDesktop(0, False, 0x01ff)
    print(f"OpenInputDesktop: {hdesk}")
    
    wins = []
    def enum_cb(hwnd, lparam):
        t = win32gui.GetWindowText(hwnd)
        c = win32gui.GetClassName(hwnd)
        if t or c:
            wins.append((hwnd, t, c))
        return True

    try:
        win32gui.EnumDesktopWindows(hdesk, enum_cb, None)
    except Exception as e:
        print(f"EnumDesktopWindows error: {e}")
        
    print(f"Found {len(wins)} windows on input desktop:")
    for h, t, c in wins:
        if t:
            print(f"  [{h}] '{t}' ({c})")

if __name__ == "__main__":
    list_desktop_windows()
