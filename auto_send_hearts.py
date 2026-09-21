import cv2
import numpy as np
import win32gui
import win32con
import win32ui
import time
import random
import os
import sys

import ctypes

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

def capture_window_bg(hwnd):
    """ดึงภาพสกรีนช็อกจากวินโดวส์เป้าหมายเบื้องหลัง แม้จะมีหน้าต่างอื่นบังอยู่ โดยจับที่หน้าต่างย่อยก่อน ถ้าไม่ได้ค่อยครอปหน้าต่างหลัก"""
    try:
        target_hwnd = find_render_hwnd(hwnd)
        left, top, right, bot = win32gui.GetWindowRect(target_hwnd)
        w = right - left
        h = bot - top
        
        if w > 50 and h > 50:
            hwndDC = win32gui.GetWindowDC(target_hwnd)
            mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
            saveDC.SelectObject(saveBitMap)
            
            result = ctypes.windll.user32.PrintWindow(target_hwnd, saveDC.GetSafeHdc(), 3)
            
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype='uint8')
            img.shape = (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
            
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(target_hwnd, hwndDC)
            
            if result == 1:
                img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                if np.mean(img_bgr) > 5.0:
                    return cv2.resize(img_bgr, (800, 450))

        # 2. ถ้าดึงจากหน้าต่างย่อยไม่สำเร็จ ให้ย้อนกลับไปดึงจากหน้าต่างหลักแล้วครอปตัดขอบ (Fallback)
        left, top, right, bot = win32gui.GetWindowRect(hwnd)
        w = right - left
        h = bot - top
        if w <= 0 or h <= 0:
            return None

        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)
        
        result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)
        
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        img = np.frombuffer(bmpstr, dtype='uint8')
        img.shape = (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
        
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        
        if result == 1:
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            if img_bgr.shape[0] > 50 and img_bgr.shape[1] > 50:
                cropped = img_bgr[38:-8, 8:-8]
                return cv2.resize(cropped, (800, 450))
            return cv2.resize(img_bgr, (800, 450))
    except Exception:
        pass
    return None

def click_bg_point(hwnd, x_norm, y_norm, label=""):
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
    
    if label:
        print(f"[{time.strftime('%H:%M:%S')}] 💌 {label} -> พิกัด ({x_norm}, {y_norm})")
    
    win32gui.PostMessage(target_hwnd, win32con.WM_MOUSEMOVE, 0, lParam)
    time.sleep(random.uniform(0.03, 0.05))
    win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
    time.sleep(random.uniform(0.08, 0.12))
    win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONUP, 0, lParam)

def drag_scroll_bg(hwnd, x_start=200, y_start=370, x_end=200, y_end=335, steps=10, duration=0.2):
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

    print(f"[{time.strftime('%H:%M:%S')}] 📜 ลากเลื่อนตารางลง...")

    win32gui.PostMessage(target_hwnd, win32con.WM_MOUSEMOVE, 0, lParam_start)
    time.sleep(0.05)
    win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam_start)
    time.sleep(0.05)

    step_delay = duration / float(steps)
    for i in range(1, steps + 1):
        curr_x = int(xs + (xe - xs) * (i / float(steps)))
        curr_y = int(ys + (ye - ys) * (i / float(steps)))
        lParam_curr = (curr_y << 16) | (curr_x & 0xFFFF)
        win32gui.PostMessage(target_hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, lParam_curr)
        time.sleep(step_delay)

    # ค้างเมาส์แช่ไว้เพื่อลดแรงเฉื่อยให้หยุดเป๊ะ
    time.sleep(0.25)
    win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONUP, 0, lParam_end)

def load_all_heart_templates():
    """โหลดรูปต้นแบบปุ่มส่งหัวใจทั้งหมด (รองรับทั้งหลายไฟล์ในโฟลเดอร์ และไฟล์เดี่ยว)"""
    templates = []
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. โหลดจากโฟลเดอร์ templates/send_heart/ (ถ้ามี)
    folder_path = os.path.join(base_dir, "templates", "send_heart")
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        for fn in sorted(os.listdir(folder_path)):
            if fn.lower().endswith((".png", ".jpg", ".jpeg")):
                img = cv2.imread(os.path.join(folder_path, fn))
                if img is not None:
                    templates.append((fn, img))
                    
    # 2. โหลดไฟล์เดี่ยวจากโฟลเดอร์ templates/ (เช่น send_heart.png, send_heart_1.png, ฯลฯ)
    templates_dir = os.path.join(base_dir, "templates")
    if os.path.exists(templates_dir):
        for fn in sorted(os.listdir(templates_dir)):
            if fn.lower().startswith("send_heart") and fn.lower().endswith((".png", ".jpg", ".jpeg")):
                full_p = os.path.join(templates_dir, fn)
                if os.path.isfile(full_p):
                    img = cv2.imread(full_p)
                    if img is not None and not any(t[0] == fn for t in templates):
                        templates.append((fn, img))

    return templates

def is_valid_heart_button_color(frame, cx, cy):
    """ตรวจสอบว่า ณ พิกัดที่สแกนเจอ มีองค์ประกอบสีของปุ่มส่งหัวใจ (หัวใจสีแดง / ปุ่มสีเขียว) จริงๆ หรือไม่"""
    try:
        h, w = frame.shape[:2]
        x_min = max(0, cx - 15)
        x_max = min(w, cx + 15)
        y_min = max(0, cy - 15)
        y_max = min(h, cy + 15)
        
        roi = frame[y_min:y_max, x_min:x_max]
        if roi.size == 0:
            return True
            
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # ช่วงสีแดง (Red Heart)
        mask_red1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
        mask_red2 = cv2.inRange(hsv, np.array([170, 100, 100]), np.array([180, 255, 255]))
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)
        
        # ช่วงสีเขียว (Green Oval Button)
        mask_green = cv2.inRange(hsv, np.array([35, 60, 60]), np.array([85, 255, 255]))
        
        red_pixels = cv2.countNonZero(mask_red)
        
        # ต้องมีองค์ประกอบหัวใจสีแดง (Red Heart Envelope) ปรากฏอยู่ในพื้นที่ปุ่มเท่านั้น
        if red_pixels >= 6:
            return True
        return False
    except Exception:
        return True

def find_all_heart_buttons(frame, templates, threshold=0.62):
    """สแกนหาพิกัดปุ่มส่งหัวใจทั้งหมดจากหลายรูปต้นแบบบนหน้าจอ (มาตรฐาน 800x450)"""
    if frame is None or not templates:
        return []
        
    h_frame, w_frame = frame.shape[:2]
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    all_matches = []
    
    for t_name, template_img in templates:
        gray_template = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY) if len(template_img.shape) == 3 else template_img
        h_temp, w_temp = gray_template.shape[:2]
        
        res = cv2.matchTemplate(gray_frame, gray_template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        print(f"  🔍 [Debug Match '{t_name}'] คะแนนสแกนสูงสุด: {max_val:.4f} (Threshold: {threshold})")
        
        loc = np.where(res >= threshold)
        
        for pt in zip(*loc[::-1]): # (x, y)
            cx = pt[0] + w_temp // 2
            cy = pt[1] + h_temp // 2
            
            # ตรวจสอบสีพิกเซลรอบๆ ก่อนว่าใช่หัวใจสีแดง/ปุ่มสีเขียวจริงไหม (ป้องกันพื้นหลังคล้ายกัน)
            if not is_valid_heart_button_color(frame, cx, cy):
                continue

            # ปรับสเกลเข้า 800x450
            cx_norm = int(cx * (800.0 / w_frame))
            cy_norm = int(cy * (450.0 / h_frame))
            
            # ขยายพื้นที่ค้นหาให้อยู่ในช่วงตารางพิกัด X: 250-550, Y: 100-420
            if 250 <= cx_norm <= 550 and 100 <= cy_norm <= 420:
                is_duplicate = False
                for mx, my in all_matches:
                    if abs(cx_norm - mx) < 30 and abs(cy_norm - my) < 20:
                        is_duplicate = True
                        break
                        
                if not is_duplicate:
                    all_matches.append((cx_norm, cy_norm))
            
    # เรียงลำดับจากบนลงล่างตามแกน Y
    all_matches.sort(key=lambda item: item[1])
    return all_matches

def run_auto_send_hearts_loop(hwnd, max_scrolls=300, stop_checker=None):
    """ฟังก์ชันหลักสแกนหาและส่งหัวใจอัตโนมัติพร้อมเลื่อนตารางลง"""
    heart_templates = load_all_heart_templates()
    if not heart_templates:
        print("❌ ไม่พบไฟล์รูปเทมเพลตปุ่มส่งหัวใจในโฟลเดอร์ 'templates/'")
        return
        
    print(f"\n❤️ เริ่มต้นระบบกดส่งหัวใจอัตโนมัติ (โหลดเทมเพลตปุ่มส่งหัวใจสำเร็จ {len(heart_templates)} รูป)...")
    for t_name, _ in heart_templates:
        print(f"   - โหลดเทมเพลต: '{t_name}'")
    
    total_sent = 0
    empty_pages = 0
    
    for page_idx in range(1, max_scrolls + 1):
        if stop_checker is not None and stop_checker():
            print("⏹️ หยุดการทำงานของระบบส่งหัวใจ")
            break
            
        print(f"\n🔍 [หน้า {page_idx}/{max_scrolls}] กำลังสแกนหาปุ่มส่งหัวใจบนตาราง...")
        
        frame = capture_window_bg(hwnd)
        heart_buttons = find_all_heart_buttons(frame, heart_templates, threshold=0.62)
        
        if heart_buttons:
            empty_pages = 0
            print(f"  ✨ ตรวจพบปุ่มส่งหัวใจ {len(heart_buttons)} ปุ่มในตารางหน้านี้:")
            for idx, (hx, hy) in enumerate(heart_buttons, 1):
                if stop_checker is not None and stop_checker():
                    return
                    
                # 1. กดปุ่มส่งหัวใจบนตาราง
                click_bg_point(hwnd, hx, hy, label=f"ส่งหัวใจคนที่ {total_sent + 1}")
                total_sent += 1
                time.sleep(0.8)
                
                if stop_checker is not None and stop_checker():
                    return

                # 2. กดคอนเฟิร์มรอบที่ 1 (x=470-500, y=260-270)
                conf1_x = random.randint(470, 500)
                conf1_y = random.randint(260, 270)
                click_bg_point(hwnd, conf1_x, conf1_y, label="  -> 1. กดคอนเฟิร์มครั้งที่ 1")
                
                # 3. รออนิเมชั่น 3 วินาที
                print("     ⏳ รออนิเมชั่น 3 วินาที...")
                time.sleep(3.0)
                
                if stop_checker is not None and stop_checker():
                    return

                # 4. กดคอนเฟิร์มรอบที่ 2 (x=380-400, y=260-280)
                conf2_x = random.randint(380, 400)
                conf2_y = random.randint(260, 280)
                click_bg_point(hwnd, conf2_x, conf2_y, label="  -> 2. กดคอนเฟิร์มครั้งที่ 2")
                time.sleep(1.0)

        else:
            print("  ℹ️ ไม่พบปุ่มส่งหัวใจในหน้านี้ (ส่งแล้วหรือกำลังโหลดรายชื่อ)")

        if stop_checker is not None and stop_checker():
            break

        # สั่งเลื่อนตารางลงเพื่อไปยังรายชื่อชุดถัดไป (X:200 Y:370 -> X:200 Y:335 เวลา 0.2s)
        drag_scroll_bg(hwnd, x_start=200, y_start=370, x_end=200, y_end=335, duration=0.2)
        
        # รอหน้าต่างหยุดนิ่ง 1.2 วินาทีเพื่อให้ภาพคมชัดก่อนสแกนรอบถัดไป
        print("  ⏳ รอหน้าจอหยุดนิ่ง 1.2 วินาที...")
        time.sleep(1.2)

    print(f"\n🎉 เสร็จสิ้นการส่งหัวใจ! รวมส่งไปทั้งสิ้น {total_sent} คน")

def main():
    hwnd = get_mumu_hwnd()
    if not hwnd:
        print("❌ ไม่พบหน้าต่าง MuMu Player! กรุณาเปิด MuMu Player ก่อนรันสคริปต์")
        input("\nกด Enter เพื่อปิด...")
        return
        
    print(f"✅ ตรวจพบหน้าต่าง MuMu Player (HWND: {hwnd})")
    pages_str = input("🔢 ต้องการเลื่อนตารางสแกนกี่หน้า? [กด Enter = 300 หน้า]: ").strip()
    max_pages = int(pages_str) if pages_str.isdigit() and int(pages_str) > 0 else 300
    
    try:
        run_auto_send_hearts_loop(hwnd, max_scrolls=max_pages)
    except KeyboardInterrupt:
        print("\nหยุดการทำงานเรียบร้อย")

if __name__ == "__main__":
    main()
