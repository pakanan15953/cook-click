import win32gui

def find_mumu_handles():
    hwnds = []
    def win_enum_handler(hwnd, ctx):
        text = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        if text or cls:
            ctx.append((hwnd, text, cls))
        return True

    results = []
    try:
        win32gui.EnumWindows(win_enum_handler, results)
    except Exception as e:
        print(f"Enum error: {e}")
    return results

res = find_mumu_handles()
print(f"Found {len(res)} windows total")
for h, t, c in res:
    if t:
        print(f"HWND: {h} | Title: '{t}' | Class: '{c}'")
