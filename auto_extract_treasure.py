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

def click_bg_point(hwnd, x_norm, y_norm, label="", jitter=2):
    """ส่งคำสั่งคลิกที่พิกัด x_norm, y_norm พร้อมสุ่มสเกลเบี่ยงเบน jitter พิกเซล"""
    target_hwnd = find_render_hwnd(hwnd)
    left, top, w_client, h_client = win32gui.GetClientRect(target_hwnd)
    
    x_rand = x_norm + random.randint(-jitter, jitter)
    y_rand = y_norm + random.randint(-jitter, jitter)
    
    if w_client <= 0 or h_client <= 0:
        left_w, top_w, right_w, bot_w = win32gui.GetWindowRect(hwnd)
        w_client = (right_w - left_w) - 16
        h_client = (bot_w - top_w) - 46
        target_hwnd = hwnd
        x_actual = int(8 + x_rand * (w_client / 800.0))
        y_actual = int(38 + y_rand * (h_client / 450.0))
    else:
        x_actual = int(x_rand * (w_client / 800.0))
        y_actual = int(y_rand * (h_client / 450.0))

    lParam = (y_actual << 16) | (x_actual & 0xFFFF)
    
    print(f"[{time.strftime('%H:%M:%S')}] 🖱️ {label} -> พิกัด ({x_rand}, {y_rand})")
    
    win32gui.PostMessage(target_hwnd, win32con.WM_MOUSEMOVE, 0, lParam)
    time.sleep(random.uniform(0.03, 0.05))
    win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
    time.sleep(random.uniform(0.08, 0.14))
    win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONUP, 0, lParam)

def click_bg_range(hwnd, x_min, x_max, y_min, y_max, label=""):
    """ส่งคำสั่งคลิกที่พิกัดสุ่มในช่วง x_min..x_max, y_min..y_max"""
    x_norm = random.randint(x_min, x_max)
    y_norm = random.randint(y_min, y_max)
    return click_bg_point(hwnd, x_norm, y_norm, label=label, jitter=0)

# พิกัดตำแหน่งสมบัติทั้ง 12 ชิ้น ( grid 4 x 3 )
TREASURE_ITEMS = [
    (125, 125), (200, 125), (300, 125), (380, 125), # Row 1: 1..4
    (125, 200), (200, 200), (300, 200), (380, 200), # Row 2: 5..8
    (125, 270), (200, 270), (300, 270), (380, 270), # Row 3: 9..12
]

def run_auto_extract_loop(hwnd, max_loops=None, stop_checker=None):
    """ฟังก์ชันทำงานลูปย่อยสมบัติอัตโนมัติตามขั้นตอนที่กำหนด"""
    print("\n💎 เริ่มต้นระบบย่อยสมบัติอัตโนมัติ (Treasure Extract System)...")
    
    loop_count = 0
    while True:
        if stop_checker is not None and stop_checker():
            print("⏹️ หยุดการทำงานของระบบย่อยสมบัติ")
            break
            
        if max_loops and loop_count >= max_loops:
            print(f"✅ ทำงานย่อยสมบัติครบ {max_loops} รอบใหญ่เรียบร้อยแล้ว!")
            break
            
        loop_count += 1
        print(f"\n==========================================")
        print(f"🔄 เริ่มรอบย่อยสมบัติที่ {loop_count}")
        print(f"==========================================")
        
        # --- ขั้นตอนที่ 1 & 2: ซื้อสมบัติ 12 ครั้ง ---
        for buy_idx in range(1, 13):
            if stop_checker is not None and stop_checker():
                return
                
            print(f"\n🛒 [ซื้อสมบัติ {buy_idx}/12]")
            # 1. กดซื้อสมบัติ (x=150-200, y=200-205)
            click_bg_range(hwnd, 150, 200, 200, 205, label=f"1. กดซื้อสมบัติครั้งที่ {buy_idx}")
            time.sleep(0.5)
            
            # 1.5 กดข้ามอนิเมชั่น (x=150, y=260)
            click_bg_point(hwnd, 150, 260, label="   ⏩ กดข้ามอนิเมชั่น")
            time.sleep(3.0)
            
            if stop_checker is not None and stop_checker():
                return

            # 2. กดคอนเฟิร์ม (x=340-350, y=350)
            click_bg_range(hwnd, 340, 350, 350, 350, label=f"2. กดคอนเฟิร์มหลังซื้อครั้งที่ {buy_idx}")
            time.sleep(1.0)
            
        print("\n✅ ซื้อสมบัติครบ 12 ชิ้นเรียบร้อย! กำลังเข้าสู่ขั้นตอนย่อยสมบัติ...")
        time.sleep(1.0)
        
        if stop_checker is not None and stop_checker():
            return

        # 3. กดเข้าหน้าย่อย (x=150, y=50)
        click_bg_point(hwnd, 150, 50, label="3. กดเข้าหน้าย่อย")
        time.sleep(1.5)
        
        if stop_checker is not None and stop_checker():
            return

        # 4. กดเข้าหน้ารายละเอียดย่อย (x=360, y=425)
        click_bg_point(hwnd, 360, 425, label="4. กดเข้าหน้ารายละเอียดย่อย")
        time.sleep(1.5)
        
        if stop_checker is not None and stop_checker():
            return

        # 5. กดฟิลเตอร์ (x=150-160, y=60)
        click_bg_range(hwnd, 150, 160, 60, 60, label="5. กดฟิลเตอร์")
        time.sleep(1.2)
        
        if stop_checker is not None and stop_checker():
            return

        # 6. เลือกระดับ (x=150, y=205)
        click_bg_point(hwnd, 150, 205, label="6. เลือกระดับ")
        time.sleep(1.2)
        
        if stop_checker is not None and stop_checker():
            return

        # 7. กดเลือกสมบัติ 12 ชิ้นที่สุ่มมา
        print("📦 กำลังเลือกสมบัติทั้ง 12 ชิ้น...")
        for item_idx, (tx, ty) in enumerate(TREASURE_ITEMS, 1):
            if stop_checker is not None and stop_checker():
                return
            click_bg_point(hwnd, tx, ty, label=f"   - เลือกสมบัติชิ้นที่ {item_idx} (X={tx}, Y={ty})")
            time.sleep(0.4)
            
        time.sleep(0.8)
        
        if stop_checker is not None and stop_checker():
            return

        # 8. กดย่อย (x=580-600, y=420-425)
        click_bg_range(hwnd, 580, 600, 420, 425, label="8. กดย่อย")
        time.sleep(1.5)
        
        if stop_checker is not None and stop_checker():
            return

        # 9. กดยืนยันการย่อย (x=390-400, y=310-320)
        click_bg_range(hwnd, 390, 400, 310, 320, label="9. กดยืนยันการย่อย")
        time.sleep(1.5)
        
        if stop_checker is not None and stop_checker():
            return

        # 10. กดคอนเฟิร์ม (x=390-400, y=280-285)
        click_bg_range(hwnd, 390, 400, 280, 285, label="10. กดคอนเฟิร์ม")
        time.sleep(1.5)
        
        if stop_checker is not None and stop_checker():
            return

        # 11. กดออกจากหน้าย่อย (x=700, y=60)
        click_bg_point(hwnd, 700, 60, label="11. กดออกจากหน้าย่อย")
        time.sleep(2.0)
        
        print(f"🎉 เสร็จสิ้นรอบย่อยสมบัติที่ {loop_count}! กำลังเตรียมวนกลับไปซื้อสมบัติ...")

def main():
    hwnd = get_mumu_hwnd()
    if not hwnd:
        print("❌ ไม่พบหน้าต่าง MuMu Player! กรุณาเปิด MuMu Player ก่อนรันสคริปต์")
        input("\nกด Enter เพื่อปิด...")
        return
        
    print(f"✅ ตรวจพบหน้าต่าง MuMu Player (HWND: {hwnd})")
    loops_str = input("🔢 ต้องการทำกี่รอบใหญ่ (1 รอบ = ซื้อ 12 ชิ้น + ย่อย 12 ชิ้น)? [กด Enter เพื่อทำไปเรื่อยๆ]: ").strip()
    max_loops = int(loops_str) if loops_str.isdigit() and int(loops_str) > 0 else None
    
    try:
        run_auto_extract_loop(hwnd, max_loops=max_loops)
    except KeyboardInterrupt:
        print("\nหยุดการทำงานเรียบร้อย")

if __name__ == "__main__":
    main()
