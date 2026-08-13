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

def drag_scroll_bg(hwnd, x_start, y_start, x_end, y_end, steps=20, duration=0.8):
    """ส่งคำสั่งลากเมาส์เสมือนเบื้องหลังเพื่อเลื่อนตาราง (Background Drag Scroll)"""
    target_hwnd = find_render_hwnd(hwnd)
    left, top, w_client, h_client = win32gui.GetClientRect(target_hwnd)
    
    if w_client <= 0 or h_client <= 0:
        left_w, top_w, right_w, bot_w = win32gui.GetWindowRect(hwnd)
        w_client = (right_w - left_w) - 16
        h_client = (bot_w - top_w) - 46
        target_hwnd = hwnd
        xs = int(8 + x_start * (w_client / 800.0))
        ys = int(38 + y_start * (h_client / 450.0))
        xe = int(8 + x_end * (w_client / 800.0))
        ye = int(38 + y_end * (h_client / 450.0))
    else:
        xs = int(x_start * (w_client / 800.0))
        ys = int(y_start * (h_client / 450.0))
        xe = int(x_end * (w_client / 800.0))
        ye = int(y_end * (h_client / 450.0))

    lParam_start = (ys << 16) | (xs & 0xFFFF)
    lParam_end = (ye << 16) | (xe & 0xFFFF)

    print(f"  📜 กำลังลากเมาส์จากพิกัด ({x_start}, {y_start}) ไปยัง ({x_end}, {y_end})...")

    # 1. เลื่อนเมาส์ไปยังจุดเริ่ม + กดเมาส์ซ้ายค้าง
    win32gui.PostMessage(target_hwnd, win32con.WM_MOUSEMOVE, 0, lParam_start)
    time.sleep(0.05)
    win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam_start)
    time.sleep(0.05)

    # 2. ค่อยๆ ลากตำแหน่งเมาส์ระหว่างทาง (Interpolation steps)
    step_delay = duration / float(steps)
    for i in range(1, steps + 1):
        curr_x = int(xs + (xe - xs) * (i / float(steps)))
        curr_y = int(ys + (ye - ys) * (i / float(steps)))
        lParam_curr = (curr_y << 16) | (curr_x & 0xFFFF)
        win32gui.PostMessage(target_hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, lParam_curr)
        time.sleep(step_delay)

    # 2.5 ค้างเมาส์ไว้ที่จุดสิ้นสุด 0.25 วินาที เพื่อฆ่าแรงเฉื่อย (Zero-Fling Brake)
    time.sleep(0.25)

    # 3. ปล่อยเมาส์ซ้ายที่จุดสิ้นสุด
    win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONUP, 0, lParam_end)
    print("  ✅ ส่งคำสั่งลากเมาส์สำเร็จ! สังเกตการเลื่อนตารางบน MuMu Player")

def main():
    print("==========================================")
    print(" 📜 โปรแกรมทดสอบเลื่อนตาราง/ลากเมาส์ MuMu Player")
    print("==========================================")
    
    hwnd = get_mumu_hwnd()
    if not hwnd:
        print("❌ ไม่พบหน้าต่าง MuMu Player! กรุณาเปิด MuMu Player ก่อนทดสอบ")
        input("\nกด Enter เพื่อปิดโปรแกรม...")
        return
        
    print(f"✅ ตรวจพบหน้าต่าง MuMu Player (HWND: {hwnd})\n")
    print("💡 คุณสามารถระบุค่าเองได้ตลอดเวลาตามรูปแบบ:")
    print("   Xเริ่ม, Yเริ่ม, Xจบ, Yจบ, เวลาลาก(วินาที)")
    print("   ตัวอย่าง: 250,370,250,170,0.8")
    print("   (หรือกด Enter เพื่อใช้ค่าเริ่มต้น: 250,370,250,170 เวลา 0.8s)\n")
    
    while True:
        try:
            cmd = input("👉 ป้อนค่า 'Xเริ่ม,Yเริ่ม,Xจบ,Yจบ,เวลา' (หรือ Enter=ค่าเดิม / q=ออก): ").strip()
            if cmd.lower() in ['q', 'exit', 'quit']:
                break
                
            xs, ys, xe, ye = 250, 370, 250, 170
            duration = 0.8
            
            if cmd:
                parts = [p.strip() for p in cmd.split(',')]
                if len(parts) >= 4:
                    xs = int(parts[0])
                    ys = int(parts[1])
                    xe = int(parts[2])
                    ye = int(parts[3])
                if len(parts) >= 5:
                    duration = float(parts[4])

            steps = max(10, int(duration * 25))
            drag_scroll_bg(hwnd, xs, ys, xe, ye, steps=steps, duration=duration)
            print("-" * 55)
            
        except ValueError:
            print("⚠️ รูปแบบพิกัดไม่ถูกต้อง! ตัวอย่างรูปแบบที่ถูกต้อง: 250,370,250,170,0.8\n")
        except KeyboardInterrupt:
            break

    print("\nปิดการทำงานโปรแกรมทดสอบเลื่อนตารางเรียบร้อย")

if __name__ == "__main__":
    main()
