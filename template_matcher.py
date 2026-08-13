# -*- coding: utf-8 -*-
import os
import cv2
import time
import win32gui

SHOW_DEBUG_LOGS = False

def set_show_debug_logs(val):
    global SHOW_DEBUG_LOGS
    SHOW_DEBUG_LOGS = bool(val)

def load_multi_templates(folder_path):
    """โหลดรูปเทมเพลตทุกไฟล์ในโฟลเดอร์ที่ระบุ (แบบ grayscale) คืนค่าเป็นลิสต์ (ชื่อไฟล์, ndarray)"""
    templates = []
    if not os.path.isdir(folder_path):
        return templates
    for filename in sorted(os.listdir(folder_path)):
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            img = cv2.imread(os.path.join(folder_path, filename), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                templates.append((filename, img))
    return templates

def find_template_match(hwnd, frame, template_img, threshold=0.75):
    """ค้นหาตำแหน่งรูปภาพต้นแบบในเฟรมหน้าจอ คืนค่า (พบหรือไม่, พิกัด X, พิกัด Y) เทียบกับสเกล 800x450"""
    if template_img is None or hwnd is None or frame is None:
        return False, 0, 0
    try:
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 1. แดมป์ตัวแปรหาค่าจับคู่แบบปกติ (Scale 1)
        res1 = cv2.matchTemplate(gray_frame, template_img, cv2.TM_CCOEFF_NORMED)
        _, max_val1, _, max_loc1 = cv2.minMaxLoc(res1)
        
        best_val = max_val1
        best_loc = max_loc1
        best_shape = template_img.shape
        
        # 2. คำนวณอัตราส่วนการย่อขยายหน้าต่างแบบไดนามิก (Scale 2)
        try:
            left, top, right, bot = win32gui.GetWindowRect(hwnd)
            W_client = right - left - 16
            if W_client > 100:
                scale_factor = 800.0 / W_client
                scaled_w = int(template_img.shape[1] * scale_factor)
                scaled_h = int(template_img.shape[0] * scale_factor)
                if scaled_w > 10 and scaled_h > 10 and gray_frame.shape[0] >= scaled_h and gray_frame.shape[1] >= scaled_w:
                    template_scaled = cv2.resize(template_img, (scaled_w, scaled_h))
                    res2 = cv2.matchTemplate(gray_frame, template_scaled, cv2.TM_CCOEFF_NORMED)
                    _, max_val2, _, max_loc2 = cv2.minMaxLoc(res2)
                    if max_val2 > best_val:
                        best_val = max_val2
                        best_loc = max_loc2
                        best_shape = template_scaled.shape
        except Exception:
            pass

        # แสดงคะแนน Debug สำหรับวิเคราะห์หาปุ่ม
        if SHOW_DEBUG_LOGS:
            h, w = template_img.shape[:2]
            if (h == 58 and w == 176) or (h == 60 and w == 181) or (h == 67 and w == 200) or (h == 65 and w == 264) or (w == 151):
                now = time.time()
                if not hasattr(find_template_match, "debug_times"):
                    find_template_match.debug_times = {}
                
                if w == 176:
                    name = "openall"
                elif w == 181:
                    name = "confirmafteropenall"
                elif w == 264:
                    name = "playlobby"
                else:
                    name = "ok"
                
                last_time = find_template_match.debug_times.get(name, 0)
                if now - last_time > 1.5:
                    find_template_match.debug_times[name] = now
                    print(f"[Debug Match] {name} score: {best_val:.4f} (Threshold: {threshold})")
        
        if best_val >= threshold:
            h_temp, w_temp = best_shape[:2]
            center_x = best_loc[0] + w_temp // 2
            center_y = best_loc[1] + h_temp // 2
            
            # ปรับสเกลพิกัดให้เข้ากับขนาดหน้าจอมาตรฐาน 800x450 พิกเซล
            h_frame, w_frame = gray_frame.shape[:2]
            cx_norm = int(center_x * (800.0 / w_frame))
            cy_norm = int(center_y * (450.0 / h_frame))
            return True, cx_norm, cy_norm
    except Exception:
        pass
    return False, 0, 0

def find_best_template_match(hwnd, frame, templates, threshold=0.65):
    """สแกนรูปภาพเทียบกับรายการเทมเพลตหลายรูป คืนค่าตัวที่ได้คะแนนสูงสุด"""
    best_found = False
    best_cx, best_cy = 0, 0
    max_score = -1.0
    best_name = None

    for name, t_img in templates:
        found, cx, cy = find_template_match(hwnd, frame, t_img, threshold=threshold)
        if found:
            return True, cx, cy, threshold, name
    return False, 0, 0, 0.0, None
