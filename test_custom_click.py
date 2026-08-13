import win32gui
import win32con
import time
import sys

def get_mumu_hwnd():
    hwnd = win32gui.FindWindow("Qt5156QWindowIcon", None)
    if not hwnd:
        hwnd = win32gui.FindWindow(None, "Android Device-1-1")
    if not hwnd:
        found_hwnd = [None]
        def enum_cb(h, extra):
            if win32gui.IsWindowVisible(h):
                t = win32gui.GetWindowText(h)
                c = win32gui.GetClassName(h)
                if "android device" in t.lower() or "mumuplayer" in t.lower() or "mumu" in c.lower() or "mumu" in t.lower():
                    found_hwnd[0] = h
                    return False
            return True
        try:
            win32gui.EnumWindows(enum_cb, None)
        except:
            pass
        hwnd = found_hwnd[0]
    return hwnd

def find_render_hwnd(parent_hwnd):
    render_hwnd = [parent_hwnd]
    def cb(h, extra):
        classname = win32gui.GetClassName(h)
        title = win32gui.GetWindowText(h)
        if "mumunxdevice" in title.lower() or "mumunxdevice" in classname.lower() or "nemudisplay" in classname.lower():
            render_hwnd[0] = h
            return False
        return True
    try:
        win32gui.EnumChildWindows(parent_hwnd, cb, None)
    except:
        pass
    return render_hwnd[0]

def click_bg(hwnd, x_norm, y_norm, count=1):
    target_hwnd = find_render_hwnd(hwnd)
    left, top, w_client, h_client = win32gui.GetClientRect(target_hwnd)
    
    if w_client <= 0 or h_client <= 0:
        left_w, top_w, right_w, bot_w = win32gui.GetWindowRect(hwnd)
        w_client = (right_w - left_w) - 16
        h_client = (bot_w - top_w) - 46
        target_hwnd = hwnd
        x_actual = int(8 + x_norm * (w_client / 800.0))
        y_actual = int(38 + y_norm * (h_client / 450.0))
    else:
        x_actual = int(x_norm * (w_client / 800.0))
        y_actual = int(y_norm * (h_client / 450.0))

    lParam = (y_actual << 16) | (x_actual & 0xFFFF)
    
    for i in range(count):
        print(f"  👉 [ครั้งที่ {i+1}/{count}] ส่งคำสั่งคลิกเบื้องหลังที่ X={x_norm}, Y={y_norm} (พิกัดจริงบนจอ: {x_actual}, {y_actual})")
        win32gui.PostMessage(target_hwnd, win32con.WM_MOUSEMOVE, 0, lParam)
        time.sleep(0.03)
        win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        time.sleep(0.1)
        win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONUP, 0, lParam)
        if i < count - 1:
            time.sleep(0.2)

def main():
    print("==========================================")
    print(" 🎯 โปรแกรมทดสอบคลิกพิกัด MuMu Player (800x450)")
    print("==========================================")
    
    hwnd = get_mumu_hwnd()
    if not hwnd:
        print("❌ ไม่พบหน้าต่างโปรแกรม MuMu Player! กรุณาเปิด MuMu Player ก่อนรันโปรแกรมทดสอบ")
        input("\nกด Enter เพื่อปิดโปรแกรม...")
        return
        
    print(f"✅ ตรวจพบหน้าต่าง MuMu Player (HWND: {hwnd})")
    print("ป้อนพิกัดมาตรฐาน 800x450 เพื่อทดสอบคลิกได้ทันที (หรือพิมพ์ q เพื่อออกจากโปรแกรม)\n")
    
    while True:
        try:
            val_x = input("📌 ป้อนพิกัด X (0 - 800): ").strip()
            if val_x.lower() in ['q', 'exit', 'quit']:
                break
            x = int(val_x)
            
            val_y = input("📌 ป้อนพิกัด Y (0 - 450): ").strip()
            if val_y.lower() in ['q', 'exit', 'quit']:
                break
            y = int(val_y)
            
            count_str = input("🔢 ต้องการคลิกกี่ครั้ง? (1 หรือ 2) [กด Enter = 1 ครั้ง]: ").strip()
            count = int(count_str) if count_str.isdigit() and int(count_str) > 0 else 1
            
            print(f"\n🚀 กำลังทดสอบคลิก พิกัด ({x}, {y}) จำนวน {count} ครั้ง...")
            click_bg(hwnd, x, y, count=count)
            print("✅ ส่งคำสั่งคลิกเรียบร้อย! โปรดสังเกตหน้าจอ MuMu Player\n" + "-"*40)
            
        except ValueError:
            print("⚠️ กรุณากรอกตัวเลขพิกัดให้ถูกต้องครับ!\n")
        except KeyboardInterrupt:
            break

    print("\nปิดการทำงานโปรแกรมทดสอบคลิกเรียบร้อย")

if __name__ == "__main__":
    main()
