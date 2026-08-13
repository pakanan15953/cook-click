import win32gui
import win32con
import time
import random
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

def click_bg_range(hwnd, x_min, x_max, y_min, y_max, label=""):
    """สุ่มพิกัด X และ Y ในช่วงที่กำหนด แล้วส่งคลิกเมาส์เสมือนเบื้องหลัง"""
    target_hwnd = find_render_hwnd(hwnd)
    left, top, w_client, h_client = win32gui.GetClientRect(target_hwnd)
    
    x_norm = random.randint(x_min, x_max)
    y_norm = random.randint(y_min, y_max)
    
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
    
    print(f"[{time.strftime('%H:%M:%S')}] 🖱️ {label} -> คลิกพิกัดสุ่ม X={x_norm}, Y={y_norm}")
    
    win32gui.PostMessage(target_hwnd, win32con.WM_MOUSEMOVE, 0, lParam)
    time.sleep(random.uniform(0.03, 0.05))
    win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
    time.sleep(random.uniform(0.08, 0.15))
    win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONUP, 0, lParam)
    
    return x_norm, y_norm

# รายการพิกัดกล่องของขวัญทั้ง 5 กล่อง
GIFT_BOXES = [
    {"name": "กล่องที่ 1", "x_range": (180, 220), "y_range": (200, 220)},
    {"name": "กล่องที่ 2", "x_range": (390, 400), "y_range": (200, 220)},
    {"name": "กล่องที่ 3", "x_range": (560, 600), "y_range": (200, 220)},
    {"name": "กล่องที่ 4", "x_range": (260, 320), "y_range": (350, 360)},
    {"name": "กล่องที่ 5", "x_range": (480, 510), "y_range": (350, 360)},
]

def run_auto_gift_loop(hwnd, max_rounds=None, stop_checker=None):
    """ฟังก์ชันวนลูปเปิดกล่องของขวัญอัตโนมัติตามขั้นตอน"""
    print("\n🎁 เริ่มต้นระบบเปิดกล่องของขวัญอัตโนมัติ...")
    
    # 1. กดเปิดกล่อง (Initial Open)
    click_bg_range(hwnd, 510, 620, 360, 380, label="ขั้นตอนที่ 1: กดเปิดกล่อง")
    time.sleep(random.uniform(1.2, 1.8))
    
    round_count = 0
    while True:
        if stop_checker is not None and stop_checker():
            print("⏹️ หยุดการทำงานของระบบเปิดกล่องของขวัญ")
            break
            
        if max_rounds and round_count >= max_rounds:
            print(f"✅ ทำงานครบ {max_rounds} รอบเรียบร้อยแล้ว!")
            break
            
        round_count += 1
        print(f"\n--- 📦 รอบเปิดกล่องที่ {round_count} ---")
        
        # 2. กดเลือกกล่องของขวัญ (สุ่มเลือก 1 จาก 5 กล่อง)
        selected_box = random.choice(GIFT_BOXES)
        box_name = selected_box["name"]
        x_min, x_max = selected_box["x_range"]
        y_min, y_max = selected_box["y_range"]
        
        click_bg_range(hwnd, x_min, x_max, y_min, y_max, label=f"ขั้นตอนที่ 2: สุ่มเลือก {box_name}")
        time.sleep(random.uniform(1.2, 1.6))
        
        if stop_checker is not None and stop_checker():
            break

        # 3. กดเปิดอีกครั้ง (Open Again)
        click_bg_range(hwnd, 450, 550, 350, 360, label="ขั้นตอนที่ 3: กดเปิดอีกครั้ง")
        time.sleep(random.uniform(1.5, 2.0))

def main():
    hwnd = get_mumu_hwnd()
    if not hwnd:
        print("❌ ไม่พบหน้าต่าง MuMu Player! กรุณาเปิด MuMu Player ก่อนรันสคริปต์")
        input("\nกด Enter เพื่อปิด...")
        return
        
    print(f"✅ ตรวจพบหน้าต่าง MuMu Player (HWND: {hwnd})")
    rounds_str = input("🔢 ต้องการรันเปิดกี่รอบ? (กด Enter เพื่อให้ทำไปเรื่อยๆ จนกว่าจะกด Ctrl+C): ").strip()
    max_rounds = int(rounds_str) if rounds_str.isdigit() and int(rounds_str) > 0 else None
    
    try:
        run_auto_gift_loop(hwnd, max_rounds=max_rounds)
    except KeyboardInterrupt:
        print("\nหยุดการทำงานเรียบร้อย")

if __name__ == "__main__":
    main()
