# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import random
import glob
import cv2
import numpy as np
import win32gui
import win32con
import customtkinter as ctk
from PIL import Image

from window_manager import capture_window_bg, human_click_bg, find_render_hwnd

# ----------------- ค่าคอนฟิกและพิกัดเริ่มต้น -----------------
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(BASE_DIR, "treasure_config.json")
TREASURES_DB_DIR = os.path.join(BASE_DIR, "treasures_db")
FULL_TEMPLATE_DIR = os.path.join(BASE_DIR, "templates", "treasure_full")

os.makedirs(TREASURES_DB_DIR, exist_ok=True)
os.makedirs(FULL_TEMPLATE_DIR, exist_ok=True)

# พิกัดตำแหน่งสมบัติ 12 ช่อง ( grid 4 x 3 บนความละเอียดอ้างอิง 800x450 )
TREASURE_ITEMS = [
    (125, 125), (200, 125), (300, 125), (380, 125), # แถว 1: ช่อง 1..4
    (125, 200), (200, 200), (300, 200), (380, 200), # แถว 2: ช่อง 5..8
    (125, 270), (200, 270), (300, 270), (380, 270), # แถว 3: ช่อง 9..12
]

# ----------------- ฟังก์ชันจัดการ Config -----------------
def load_treasure_config():
    """โหลดรายการสมบัติที่ผู้ใช้ตั้งค่าให้ 'เว้น (ห้ามย่อย)' จากไฟล์ JSON"""
    default_config = {
        "keep_list": [],           # รายชื่อไฟล์ภาพที่ไม่ต้องการย่อย เช่น ["angel_feather.png"]
        "match_threshold": 0.70,   # ค่าความแม่นยำขั้นต่ำในการตรวจจับ (0.0 - 1.0)
        "auto_stop_if_full": True  # หยุดอัตโนมัติหากสมบัติเต็มและไม่มีขยะให้ย่อย
    }
    if not os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
        return default_config
        
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in default_config.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        print(f"⚠️ โหลด treasure_config.json ไม่สำเร็จ ({e}) - ใช้ค่าเริ่มต้น")
        return default_config

def save_treasure_config(config_data):
    """บันทึกการตั้งค่าลงไฟล์ JSON"""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ ไม่สามารถบันทึก treasure_config.json ได้: {e}")
        return False

# ----------------- ฟังก์ชันจัดการเวลาแบบตอบสนองทันที (Interruptible Sleep) -----------------
def interruptible_sleep(duration_sec, stop_checker=None, step=0.05):
    """Sleep ที่สามารถตอบสนองและหยุดได้ทันทีภายใน 0.05s เมื่อ stop_checker() คืนค่า True"""
    elapsed = 0.0
    while elapsed < duration_sec:
        if stop_checker is not None and stop_checker():
            return True # ถูกสั่งให้หยุด
        time.sleep(min(step, duration_sec - elapsed))
        elapsed += step
    return False

# ----------------- ฟังก์ชันจัดการภาพและ Template Matching -----------------
def imread_unicode(file_path):
    """อ่านไฟล์ภาพที่รองรับชื่อภาษาไทยและ Unicode บน Windows 100%"""
    try:
        with open(file_path, "rb") as f:
            img_bytes = bytearray(f.read())
            np_arr = np.asarray(img_bytes, dtype=np.uint8)
            return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    except Exception:
        return None

def load_keep_templates(keep_filenames=None):
    """โหลดรูปภาพสมบัติที่ต้องการเว้นเข้ามาในหน่วยความจำ"""
    templates = {}
    if not os.path.exists(TREASURES_DB_DIR):
        return templates
        
    all_files = glob.glob(os.path.join(TREASURES_DB_DIR, "*.*"))
    for file_path in all_files:
        filename = os.path.basename(file_path)
        if not (filename.lower().endswith(".png") or filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg")):
            continue
            
        if keep_filenames is not None and filename not in keep_filenames:
            continue
            
        img = imread_unicode(file_path)
        if img is not None:
            templates[filename] = img
            
    return templates

def scan_keep_items_on_screen(frame, keep_templates, threshold=0.70):
    """
    สแกนหน้าจอทั้งหมดเพื่อค้นหาตำแหน่งของสมบัติที่สั่งให้เว้นไว้
    - ใช้ Multi-scale Matching (0.85x - 1.15x) เพื่อความแม่นยำสูงแม้ขนาดเพี้ยนเล็กน้อย
    - แมปพิกัดที่ตรวจพบเข้ากับช่อง 1..12 ของระบบโดยเลือกช่องที่ใกล้ที่สุดเพียงช่องเดียว
    คืนค่า dict: { slot_idx: (filename, score, (cx, cy)) }
    """
    slots_to_keep = {}
    if frame is None or not keep_templates:
        return slots_to_keep

    fh, fw = frame.shape[:2]
    
    for filename, tmpl in keep_templates.items():
        if tmpl is None:
            continue
        th, tw = tmpl.shape[:2]
        
        best_match_score = 0.0
        best_match_pos = None
        
        # ลองสเกลหลายขนาด [0.85, 0.92, 1.0, 1.08, 1.15]
        for scale in [0.85, 0.92, 1.0, 1.08, 1.15]:
            nw, nh = int(tw * scale), int(th * scale)
            if nw >= fw or nh >= fh or nw < 10 or nh < 10:
                continue
                
            scaled_tmpl = cv2.resize(tmpl, (nw, nh)) if scale != 1.0 else tmpl
            res = cv2.matchTemplate(frame, scaled_tmpl, cv2.TM_CCOEFF_NORMED)
            
            min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)
            if max_v > best_match_score:
                best_match_score = max_v
                best_match_pos = (max_l[0] + nw // 2, max_l[1] + nh // 2)
            
            # ค้นหาทุกจุดที่คะแนน >= threshold
            locs = np.where(res >= threshold)
            for pt_y, pt_x in zip(*locs):
                score = float(res[pt_y, pt_x])
                center_x = pt_x + nw // 2
                center_y = pt_y + nh // 2
                
                # หาว่าจุดนี้ตรงกับช่องสมบัติช่องไหนที่ใกล้ที่สุด (1..12)
                best_idx = None
                min_dist = 999999
                for idx, (tx, ty) in enumerate(TREASURE_ITEMS, 1):
                    dist = ((center_x - tx)**2 + (center_y - ty)**2)**0.5
                    if dist < min_dist:
                        min_dist = dist
                        best_idx = idx
                        
                if best_idx is not None and min_dist <= 42: # ระยะห่างไม่เกิน 42 พิกเซลและใกล้ที่สุด
                    if best_idx not in slots_to_keep or score > slots_to_keep[best_idx][1]:
                        slots_to_keep[best_idx] = (filename, score, (center_x, center_y))

        # พิมพ์ Debug Log ผลการสแกนของแต่ละชิ้น
        print(f"🔍 สแกน [{filename}]: ความคล้ายคลึงสูงสุด = {best_match_score*100:.1f}% (ตำแหน่ง: {best_match_pos})")
        
    return slots_to_keep

def detect_inventory_full(frame, threshold=0.80):
    """ตรวจจับหน้าต่างแจ้งเตือน 'Not enough space!' เมื่อคลังสมบัติเต็ม (ไม่ตรวจจับปุ่ม Confirm เพื่อไม่ให้ชนกับหน้า Congratulations)"""
    if frame is None:
        return False, None
        
    template_files = [
        "not_enough_space_title.png",
        "not_enough_space_text.png"
    ]
    
    for tf in template_files:
        tpath = os.path.join(FULL_TEMPLATE_DIR, tf)
        if not os.path.exists(tpath):
            continue
        tmpl = imread_unicode(tpath)
        if tmpl is None:
            continue
            
        th, tw = tmpl.shape[:2]
        fh, fw = frame.shape[:2]
        if fh < th or fw < tw:
            continue
            
        try:
            res = cv2.matchTemplate(frame, tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val >= threshold:
                center_x = max_loc[0] + tw // 2
                center_y = max_loc[1] + th // 2
                return True, (center_x, center_y)
        except Exception:
            continue
            
    return False, None

# ----------------- ฟังก์ชันส่งคำสั่งคลิก -----------------
def click_bg_point(hwnd, x_norm, y_norm, label="", jitter=2):
    """ส่งคำสั่งคลิกที่พิกัด x_norm, y_norm แบบเบื้องหลัง"""
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
    
    if label:
        print(f"[{time.strftime('%H:%M:%S')}] 🖱️ {label} -> พิกัด ({x_rand}, {y_rand})")
        
    try:
        win32gui.PostMessage(target_hwnd, win32con.WM_MOUSEMOVE, 0, lParam)
        time.sleep(random.uniform(0.02, 0.04))
        win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        time.sleep(random.uniform(0.06, 0.10))
        win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONUP, 0, lParam)
    except Exception as e:
        print(f"❌ คลิกไม่สำเร็จ: {e}")

def click_bg_range(hwnd, x_min, x_max, y_min, y_max, label=""):
    """ส่งคำสั่งคลิกที่พิกัดสุ่มในช่วง x_min..x_max, y_min..y_max"""
    x_norm = random.randint(x_min, x_max)
    y_norm = random.randint(y_min, y_max)
    return click_bg_point(hwnd, x_norm, y_norm, label=label, jitter=0)

# ----------------- ลูปการทำงานหลัก (Smart Extract Loop) -----------------
def run_smart_extract_loop(hwnd, max_loops=None, stop_checker=None):
    """
    ระบบย่อยสมบัติอัจฉริยะ (Smart Extract System)
    - ตรวจจับป๊อปอัปคลังเต็มอัตโนมัติ และหยุดทำงานอย่างปลอดภัย
    - สแกนภาพสมบัติและเว้นชิ้นที่ผู้ใช้เลือกไว้
    - ใช้ interruptible_sleep เพื่อให้หยุดได้ทันทีเมื่อมีคำสั่ง
    """
    print("\n💎 เริ่มต้นระบบย่อยสมบัติอัจฉริยะ (Smart Treasure Extraction)...")
    
    # 1. โหลดการตั้งค่าและภาพ Template
    config = load_treasure_config()
    keep_list = config.get("keep_list", [])
    threshold = config.get("match_threshold", 0.70)
    
    keep_templates = load_keep_templates(keep_list)
    print(f"⚙️ รายการสมบัติที่ต้องเว้น: {len(keep_templates)} ชิ้น จากทั้งหมด {len(keep_list)} รายการที่เลือก")
    if keep_templates:
        print(f"📋 รายชื่อที่เว้น: {', '.join(keep_templates.keys())}")
        print(f"🎯 ค่าความแม่นยำ Threshold: {threshold*100:.0f}%")
    else:
        print("ℹ️ ไม่ได้เลือกเว้นสมบัติใดๆ (จะย่อยทุกชิ้นตามปกติ)")
        
    loop_count = 0
    consecutive_no_extract_count = 0
    
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
        
        # --- ขั้นตอนที่ 1: สุ่มซื้อสมบัติ (สูงสุด 12 ครั้ง หรือจนกว่าจะเต็ม) ---
        bought_count = 0
        
        for buy_idx in range(1, 13):
            if stop_checker is not None and stop_checker():
                return
                
            print(f"\n🛒 [ซื้อสมบัติ {buy_idx}/12]")
            
            # 1.1 กดซื้อสมบัติ (x=150-200, y=200-205)
            click_bg_range(hwnd, 150, 200, 200, 205, label=f"1. กดซื้อสมบัติครั้งที่ {buy_idx}")
            if interruptible_sleep(0.5, stop_checker): return
            
            # ตรวจสอบว่ามีป๊อปอัป "Not enough space!" โผล่มาหรือไม่
            frame_check = capture_window_bg(hwnd)
            is_full, full_pos = detect_inventory_full(frame_check)
            if is_full:
                print("\n=======================================================")
                print("🛑 [ระบบหยุดทำงานอัตโนมัติอย่างปลอดภัย]")
                print("⚠️ ตรวจพบหน้าต่างแจ้งเตือน 'Not enough space!' (ช่องเก็บสมบัติเต็ม)")
                print("💎 สมบัติที่คุณเลือกเว้นไว้สะสมจนเต็มความจุของไอดีแล้ว!")
                print("👉 กรุณาขยายช่องเก็บสมบัติ หรือปลดล็อกบางชิ้นเพื่อทำงานต่อ")
                print("=======================================================\n")
                # กดปุ่ม Confirm สีเขียว (พิกัดปุ่มประมาณ x=400, y=300)
                click_bg_point(hwnd, 400, 300, label="   🟢 กดปุ่ม Confirm ปิดแจ้งเตือนคลังเต็ม")
                interruptible_sleep(0.8, stop_checker)
                return
                
            # 1.2 กดข้ามอนิเมชั่น (x=150, y=260)
            click_bg_point(hwnd, 150, 260, label="   ⏩ กดข้ามอนิเมชั่น")
            if interruptible_sleep(2.8, stop_checker): return

            # 1.3 กดคอนเฟิร์ม (x=340-350, y=350)
            click_bg_range(hwnd, 340, 350, 350, 350, label=f"2. กดคอนเฟิร์มหลังซื้อครั้งที่ {buy_idx}")
            if interruptible_sleep(0.8, stop_checker): return
            bought_count += 1
            
        print(f"\n✅ ซื้อสมบัติครบ {bought_count} ชิ้นเรียบร้อย! กำลังเข้าสู่ขั้นตอนย่อยสมบัติ...")
        if interruptible_sleep(0.8, stop_checker): return

        # 3. กดเข้าหน้าย่อย (x=150, y=50)
        click_bg_point(hwnd, 150, 50, label="3. กดเข้าหน้าย่อย")
        if interruptible_sleep(1.4, stop_checker): return

        # 4. กดเข้าหน้ารายละเอียดย่อย (x=360, y=425)
        click_bg_point(hwnd, 360, 425, label="4. กดเข้าหน้ารายละเอียดย่อย")
        if interruptible_sleep(1.4, stop_checker): return

        # 5. กดฟิลเตอร์ (x=150-160, y=60)
        click_bg_range(hwnd, 150, 160, 60, 60, label="5. กดฟิลเตอร์")
        if interruptible_sleep(1.0, stop_checker): return

        # 6. เลือกจัดเรียงตามที่ได้รับล่าสุด (Obtained: x=150, y=250)
        click_bg_point(hwnd, 150, 250, label="6. เลือกจัดเรียงตามที่ได้รับล่าสุด (Obtained)")
        if interruptible_sleep(1.6, stop_checker): return # รอหน้าต่างโหลดสมบัติครบสมบูรณ์

        # --- ขั้นตอนที่ 7: สแกนตรวจสอบสมบัติ 12 ช่อง และเลือกเฉพาะของขยะ ---
        print("🔍 กำลังสแกนสมบัติทั้ง 12 ช่องเพื่อคัดแยกของที่ต้องเว้น...")
        frame_grid = capture_window_bg(hwnd)
        
        slots_keep_dict = {}
        if frame_grid is not None and keep_templates:
            slots_keep_dict = scan_keep_items_on_screen(frame_grid, keep_templates, threshold)
            
        slots_to_extract = []
        for item_idx, (tx, ty) in enumerate(TREASURE_ITEMS, 1):
            if item_idx in slots_keep_dict:
                name, score, _ = slots_keep_dict[item_idx]
                print(f"🛡️ [เว้น] ช่องที่ {item_idx} ตรงกับ '{name}' ({score*100:.1f}%) ➔ ข้ามไม่ย่อย")
            else:
                slots_to_extract.append((item_idx, tx, ty))

        if slots_to_extract:
            print(f"🗑️ กำลังเลือกสมบัติขยะ {len(slots_to_extract)} ชิ้น เพื่อย่อย:")
            for s_idx, tx, ty in slots_to_extract:
                if stop_checker is not None and stop_checker():
                    return
                click_bg_point(hwnd, tx, ty, label=f"   - เลือกย่อยช่องที่ {s_idx} (X={tx}, Y={ty})")
                if interruptible_sleep(0.3, stop_checker): return
        else:
            print("⚠️ ไม่มีสมบัติที่สามารถย่อยได้ในหน้านี้ (ทุกช่องเป็นสมบัติที่สั่งให้เว้นไว้ทั้งหมด)")

        if interruptible_sleep(0.6, stop_checker): return

        # ตรวจสอบว่ามีการเลือกย่อยอย่างน้อย 1 ชิ้นหรือไม่
        if len(slots_to_extract) > 0:
            consecutive_no_extract_count = 0
            
            # 8. กดย่อย (x=580-600, y=420-425)
            click_bg_range(hwnd, 580, 600, 420, 425, label="8. กดย่อย")
            if interruptible_sleep(1.4, stop_checker): return

            # 9. กดยืนยันการย่อย (x=390-400, y=310-320)
            click_bg_range(hwnd, 390, 400, 310, 320, label="9. กดยืนยันการย่อย")
            if interruptible_sleep(1.4, stop_checker): return

            # 10. กดคอนเฟิร์ม (x=390-400, y=280-285)
            click_bg_range(hwnd, 390, 400, 280, 285, label="10. กดคอนเฟิร์ม")
            if interruptible_sleep(1.4, stop_checker): return
        else:
            consecutive_no_extract_count += 1
            print(f"⚠️ ไม่มีสมบัติให้ย่อยต่อเนื่อง {consecutive_no_extract_count} ครั้ง")
            
            if consecutive_no_extract_count >= 2:
                print("\n=======================================================")
                print("🛑 [ระบบหยุดอัตโนมัติอย่างปลอดภัย]")
                print("⚠️ ช่องเก็บสมบัติเต็ม และสมบัติทุกชิ้นในหน้านี้เป็นของที่สั่งให้เว้นไว้ทั้งหมด!")
                print("👉 กรุณาขยายช่องเก็บสมบัติ หรือปลดล็อกบางชิ้นเพื่อทำงานต่อ")
                print("=======================================================\n")
                
                # กดออกจากหน้าย่อยก่อนออก
                click_bg_point(hwnd, 700, 60, label="กดออกจากหน้าย่อย")
                return

        # 11. กดออกจากหน้าย่อย (x=700, y=60)
        click_bg_point(hwnd, 700, 60, label="11. กดออกจากหน้าย่อย")
        if interruptible_sleep(1.8, stop_checker): return
        
        print(f"🎉 เสร็จสิ้นรอบย่อยสมบัติที่ {loop_count}! กำลังเตรียมวนกลับไปซื้อสมบัติ...")

# ----------------- หน้าต่าง UI ตั้งค่าเว้นสมบัติ (CustomTkinter) -----------------
class TreasureConfigWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("💎 ตั้งค่าการเว้นสมบัติ (Smart Keep Settings)")
        self.geometry("640x620")
        self.resizable(False, False)
        self.configure(fg_color="#0f1219")
        self.attributes("-topmost", True)
        
        self.config = load_treasure_config()
        self.selected_keeps = set(self.config.get("keep_list", []))
        self.check_vars = {}
        self.pil_images = {}
        
        self.create_widgets()
        
    def create_widgets(self):
        # Header
        lbl_title = ctk.CTkLabel(
            self, text="💎 ตั้งค่าสมบัติที่ไม่ต้องการย่อย (Keep List)", 
            font=("Arial", 15, "bold"), text_color="#38bdf8"
        )
        lbl_title.pack(pady=(12, 2))
        
        lbl_desc = ctk.CTkLabel(
            self, text="ติ๊กถูก [✓] สมบัติที่ต้องการ 'เว้นไว้' (บอทจะสแกนและข้ามไม่ย่อยชิ้นที่เลือก)", 
            font=("Arial", 11), text_color="#94a3b8"
        )
        lbl_desc.pack(pady=(0, 10))
        
        # Toolbar (เลือกทั้งหมด / ล้างทั้งหมด / เปิดโฟลเดอร์)
        toolbar_frame = ctk.CTkFrame(self, fg_color="transparent")
        toolbar_frame.pack(fill="x", padx=18, pady=(0, 8))
        
        btn_select_all = ctk.CTkButton(
            toolbar_frame, text="✅ เลือกทั้งหมด", width=110, height=28,
            font=("Arial", 10, "bold"), fg_color="#1e293b", hover_color="#334155",
            command=self.select_all
        )
        btn_select_all.pack(side="left", padx=(0, 6))
        
        btn_clear_all = ctk.CTkButton(
            toolbar_frame, text="⬜ ล้างทั้งหมด", width=110, height=28,
            font=("Arial", 10, "bold"), fg_color="#1e293b", hover_color="#334155",
            command=self.clear_all
        )
        btn_clear_all.pack(side="left", padx=6)
        
        btn_open_folder = ctk.CTkButton(
            toolbar_frame, text="📁 เปิดโฟลเดอร์รูปภาพ", width=140, height=28,
            font=("Arial", 10, "bold"), fg_color="#0284c7", hover_color="#0369a1",
            command=self.open_folder
        )
        btn_open_folder.pack(side="right")
        
        # Scrollable Area for Treasures
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, fg_color="#181c26", corner_radius=10, 
            border_width=1, border_color="#262b3a", height=400
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=18, pady=(0, 12))
        
        self.populate_treasures()
        
        # Bottom Action Bar
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=18, pady=(0, 14))
        
        self.lbl_count = ctk.CTkLabel(
            bottom_frame, text=f"เลือกเว้นไว้: {len(self.selected_keeps)} ชิ้น", 
            font=("Arial", 11, "bold"), text_color="#34d399"
        )
        self.lbl_count.pack(side="left")
        
        btn_save = ctk.CTkButton(
            bottom_frame, text="💾 บันทึกการตั้งค่า", width=140, height=34,
            font=("Arial", 12, "bold"), fg_color="#10b981", hover_color="#059669",
            command=self.save_and_close
        )
        btn_save.pack(side="right")
        
    def populate_treasures(self):
        image_files = sorted(glob.glob(os.path.join(TREASURES_DB_DIR, "*.*")))
        valid_files = [f for f in image_files if f.lower().endswith((".png", ".jpg", ".jpeg"))]
        
        if not valid_files:
            lbl_empty = ctk.CTkLabel(
                self.scroll_frame, 
                text="📂 ยังไม่มีรูปภาพในโฟลเดอร์ treasures_db\n\nผู้พัฒนาหรือผู้ใช้สามารถนำรูปไอคอนสมบัติ (.png)\nมาใส่ในโฟลเดอร์ treasures_db ได้เลยครับ",
                font=("Arial", 12), text_color="#64748b"
            )
            lbl_empty.pack(pady=60)
            return
            
        columns = 3
        for idx, img_path in enumerate(valid_files):
            filename = os.path.basename(img_path)
            name_display = os.path.splitext(filename)[0].replace("_", " ").title()
            
            row = idx // columns
            col = idx % columns
            
            card = ctk.CTkFrame(self.scroll_frame, fg_color="#202534", corner_radius=8, border_width=1, border_color="#2a3144")
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            self.scroll_frame.columnconfigure(col, weight=1)
            
            try:
                pil_img = Image.open(img_path)
                pil_img = pil_img.resize((48, 48), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(48, 48))
                self.pil_images[filename] = ctk_img
                
                img_label = ctk.CTkLabel(card, text="", image=ctk_img)
                img_label.pack(pady=(6, 2))
            except Exception:
                pass
                
            is_checked = filename in self.selected_keeps
            var = ctk.BooleanVar(value=is_checked)
            self.check_vars[filename] = var
            
            def make_toggle(fn=filename, v=var):
                return lambda: self.on_check_toggle(fn, v.get())
                
            chk = ctk.CTkCheckBox(
                card, text=name_display, variable=var, 
                font=("Arial", 10, "bold"), text_color="#e2e8f0",
                fg_color="#38bdf8", hover_color="#0284c7",
                command=make_toggle(filename, var)
            )
            chk.pack(pady=(2, 8), padx=6)
            
    def on_check_toggle(self, filename, is_checked):
        if is_checked:
            self.selected_keeps.add(filename)
        else:
            self.selected_keeps.discard(filename)
        self.lbl_count.configure(text=f"เลือกเว้นไว้: {len(self.selected_keeps)} ชิ้น")
        
    def select_all(self):
        for fn, var in self.check_vars.items():
            var.set(True)
            self.selected_keeps.add(fn)
        self.lbl_count.configure(text=f"เลือกเว้นไว้: {len(self.selected_keeps)} ชิ้น")
        
    def clear_all(self):
        for fn, var in self.check_vars.items():
            var.set(False)
            self.selected_keeps.discard(fn)
        self.lbl_count.configure(text=f"เลือกเว้นไว้: {len(self.selected_keeps)} ชิ้น")
        
    def open_folder(self):
        try:
            os.startfile(TREASURES_DB_DIR)
        except Exception as e:
            print(f"❌ ไม่สามารถเปิดโฟลเดอร์ได้: {e}")
            
    def save_and_close(self):
        self.config["keep_list"] = sorted(list(self.selected_keeps))
        save_treasure_config(self.config)
        print(f"💾 บันทึกรายการเว้นสมบัติสำเร็จ ({len(self.selected_keeps)} ชิ้น)")
        self.destroy()

def open_treasure_config_window(parent):
    """ฟังก์ชันเปิดหน้าต่าง UI ตั้งค่าเว้นสมบัติ"""
    win = TreasureConfigWindow(parent)
    win.focus()
    return win

# ----------------- ทดสอบรันเดี่ยว (CLI Standalone) -----------------
def main():
    from auto_extract_treasure import get_mumu_hwnd
    hwnd = get_mumu_hwnd()
    if not hwnd:
        print("❌ ไม่พบหน้าต่าง Emulator! กรุณาเปิด Emulator ก่อนรัน")
        return
        
    print(f"✅ ตรวจพบ Emulator (HWND: {hwnd})")
    run_smart_extract_loop(hwnd)

if __name__ == "__main__":
    main()
