# -*- coding: utf-8 -*-
import win32gui
import win32con
import win32ui
import ctypes
import numpy as np
import cv2
import time
import random

# Windows Background Input Configuration
SCAN_SHIFT = 0x2A
SCAN_SPACE = 0x39
SCAN_ALT = 0x38

VK_LSHIFT = win32con.VK_LSHIFT
VK_SPACE = win32con.VK_SPACE
VK_ALT = win32con.VK_MENU

def find_render_hwnd(parent_hwnd):
    """ค้นหาหน้าต่างลูกของ Emulator ที่เป็นหน้าต่างเรนเดอร์/รับอินพุตจริง รองรับทุกค่าย (MuMu, LDPlayer, BlueStacks, Nox, MEmu)"""
    children = []
    def cb(hwnd, extra):
        children.append(hwnd)
        return True
    try:
        win32gui.EnumChildWindows(parent_hwnd, cb, None)
    except Exception:
        pass
        
    if not children:
        return parent_hwnd
        
    # ลำดับความสำคัญในการหาหน้าจอรับ Input / Render:
    # 1. MuMu Player: mumunxdevice / nemudisplay
    for hwnd in children:
        classname = win32gui.GetClassName(hwnd).lower()
        title = win32gui.GetWindowText(hwnd).lower()
        if "mumunxdevice" in title or "mumunxdevice" in classname:
            return hwnd

    # 2. LDPlayer: TheRender / RenderWindow
    for hwnd in children:
        classname = win32gui.GetClassName(hwnd).lower()
        title = win32gui.GetWindowText(hwnd).lower()
        if "therender" in title or "renderwindow" in classname:
            return hwnd

    # 3. BlueStacks & MEmu: BlueStacks_Display / MEmuRenderWindow / nemu
    for hwnd in children:
        classname = win32gui.GetClassName(hwnd).lower()
        title = win32gui.GetWindowText(hwnd).lower()
        if "bluestacks_display" in classname or "memurender" in classname or "nemu" in classname or "nemu" in title:
            return hwnd

    # 4. NoxPlayer: ScreenBoardClassWindow
    for hwnd in children:
        classname = win32gui.GetClassName(hwnd).lower()
        if "screenboardclasswindow" in classname:
            return hwnd

    # 5. Generic Render Window (render, d3d, opengl, sub, etc.)
    for hwnd in children:
        classname = win32gui.GetClassName(hwnd).lower()
        title = win32gui.GetWindowText(hwnd).lower()
        if "render" in classname or "render" in title or "d3d" in classname or "sub" in classname:
            return hwnd
            
    # Fallback: ถ้าหาไม่เจอ คืนค่าหน้าต่างลูกที่มีขนาดพื้นที่ใหญ่ที่สุด
    best_hwnd = children[-1]
    max_area = 0
    for hwnd in children:
        try:
            l, t, r, b = win32gui.GetClientRect(hwnd)
            area = (r - l) * (b - t)
            if area > max_area:
                max_area = area
                best_hwnd = hwnd
        except Exception:
            pass

    return best_hwnd

def human_click_bg(hwnd, x_norm, y_norm, click_name=""):
    """คลิกเมาส์ซ้ายเบื้องหลังจำลองแบบมนุษย์ โดยสเกลพิกัด 800x450 ไปยังพิกัดจริงของหน้าต่างย่อยที่เรนเดอร์เกม"""
    try:
        target_hwnd = find_render_hwnd(hwnd)
        left, top, w_client, h_client = win32gui.GetClientRect(target_hwnd)
        
        if w_client <= 0 or h_client <= 0:
            left_w, top_w, right_w, bot_w = win32gui.GetWindowRect(hwnd)
            w = right_w - left_w
            h = bot_w - top_w
            w_client = w - 16
            h_client = h - 46
            target_hwnd = hwnd
            x_actual = int(8 + x_norm * (w_client / 800.0))
            y_actual = int(38 + y_norm * (h_client / 450.0))
        else:
            x_actual = int(x_norm * (w_client / 800.0))
            y_actual = int(y_norm * (h_client / 450.0))
            
        x_final = x_actual + random.randint(-3, 3)
        y_final = y_actual + random.randint(-3, 3)
        x_final = max(0, min(x_final, w_client - 1))
        y_final = max(0, min(y_final, h_client - 1))
        
        lParam = (y_final << 16) | (x_final & 0xFFFF)
        
        if click_name:
            print(f"🖱️ คลิก: {click_name}")
        
        win32gui.PostMessage(target_hwnd, win32con.WM_MOUSEMOVE, 0, lParam)
        time.sleep(random.uniform(0.03, 0.06))
        win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        time.sleep(random.uniform(0.08, 0.15))
        win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONUP, 0, lParam)
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการคลิกเมาส์เบื้องหลัง: {e}")

def human_press_bg(hwnd, vk_code, scan_code, duration_min=0.05, duration_max=0.12):
    """ส่งสัญญาณกดคีย์บอร์ดเสมือนตรงไปที่หน้าต่างเบื้องหลัง (Background Input)"""
    try:
        target_hwnd = find_render_hwnd(hwnd)
        lParam_down = 1 | (scan_code << 16)
        lParam_up = 1 | (scan_code << 16) | (1 << 30) | (1 << 31)
        
        win32gui.PostMessage(target_hwnd, win32con.WM_KEYDOWN, vk_code, lParam_down)
        hold_time = random.uniform(duration_min, duration_max)
        time.sleep(hold_time)
        win32gui.PostMessage(target_hwnd, win32con.WM_KEYUP, vk_code, lParam_up)
    except Exception:
        pass

def _printwindow_capture(target_hwnd):
    """ดึงภาพจาก HWND ด้วย PrintWindow พร้อม try/finally ป้องกัน GDI resource leak ทุกกรณี
    คืนค่า BGR numpy array หรือ None ถ้าไม่สำเร็จ"""
    if not target_hwnd or not win32gui.IsWindow(target_hwnd):
        return None

    hwndDC = None
    mfcDC = None
    saveDC = None
    saveBitMap = None

    try:
        left, top, right, bot = win32gui.GetWindowRect(target_hwnd)
        w = right - left
        h = bot - top

        if w <= 50 or h <= 50:
            return None

        hwndDC = win32gui.GetWindowDC(target_hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)

        result = ctypes.windll.user32.PrintWindow(target_hwnd, saveDC.GetSafeHdc(), 3)

        if result != 1:
            return None

        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        img = np.frombuffer(bmpstr, dtype='uint8')
        img.shape = (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)

        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    except Exception:
        return None
    finally:
        # Cleanup GDI resources ไม่ว่าจะสำเร็จหรือ error — ป้องกัน memory leak 100%
        try:
            if saveBitMap is not None:
                win32gui.DeleteObject(saveBitMap.GetHandle())
        except Exception:
            pass
        try:
            if saveDC is not None:
                saveDC.DeleteDC()
        except Exception:
            pass
        try:
            if mfcDC is not None:
                mfcDC.DeleteDC()
        except Exception:
            pass
        try:
            if hwndDC is not None:
                win32gui.ReleaseDC(target_hwnd, hwndDC)
        except Exception:
            pass

def capture_window_bg(hwnd):
    """ดึงภาพสกรีนช็อกจากวินโดวส์เป้าหมายเบื้องหลัง แม้จะมีหน้าต่างอื่นบังอยู่ โดยจับที่หน้าต่างย่อยก่อน ถ้าไม่ได้ค่อยครอปหน้าต่างหลัก"""
    try:
        target_hwnd = find_render_hwnd(hwnd)

        # 1. พยายามดึงภาพจากหน้าต่างย่อยโดยตรง (ไม่มีขอบ/ไตเติลบาร์)
        img_bgr = _printwindow_capture(target_hwnd)
        if img_bgr is not None and np.mean(img_bgr) > 5.0:
            return cv2.resize(img_bgr, (800, 450))

        # 2. ถ้าดึงจากหน้าต่างย่อยไม่สำเร็จ ให้ย้อนกลับไปดึงจากหน้าต่างหลักแล้วครอปตัดขอบ (Fallback)
        img_bgr = _printwindow_capture(hwnd)
        if img_bgr is not None:
            if img_bgr.shape[0] > 50 and img_bgr.shape[1] > 50:
                cropped = img_bgr[38:-8, 8:-8]
                return cv2.resize(cropped, (800, 450))
            return cv2.resize(img_bgr, (800, 450))
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการดึงภาพเบื้องหลัง: {e}")
    return None
