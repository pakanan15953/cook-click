# -*- coding: utf-8 -*-
import os
import sys
import cv2
import numpy as np
import time
import random
import ctypes
import win32gui
import win32con
import win32ui
import requests
import hashlib
import subprocess
import json
from datetime import datetime
import traceback
from ultralytics import YOLO

from window_manager import (
    find_render_hwnd, human_click_bg, human_press_bg,
    _printwindow_capture, capture_window_bg,
    VK_ALT, SCAN_ALT, VK_LSHIFT, SCAN_SHIFT, VK_SPACE, SCAN_SPACE
)
from template_matcher import (
    load_multi_templates, find_template_match, find_best_template_match,
    set_show_debug_logs
)

SHOW_DEBUG_LOGS = False
GIST_RAW_URL = "https://gist.githubusercontent.com/pakanan15953/692044c8cfd47739366bebfd14d2e0cf/raw/keys.json"

def get_hwid():
    """ดึงค่า HWID ประจำเครื่องผู้ใช้ผ่าน Windows Registry (MachineGuid) รองรับ Windows 10/11 100%"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        guid, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        if guid:
            return hashlib.sha256(guid.encode()).hexdigest()[:16].upper()
    except Exception:
        pass
    
    try:
        cmd = 'wmic csproduct get uuid'
        uuid_out = subprocess.check_output(cmd, shell=True, errors='ignore', stderr=subprocess.DEVNULL).split('\n')[1].strip()
        if uuid_out and "uuid" not in uuid_out.lower():
            return hashlib.sha256(uuid_out.encode()).hexdigest()[:16].upper()
    except Exception:
        pass

    try:
        import platform
        node = platform.node() + platform.processor()
        return hashlib.sha256(node.encode()).hexdigest()[:16].upper()
    except Exception:
        return "CRBOT-DEFAULT-HWID"

def get_cpu_name():
    """ตรวจจับชื่อรุ่น CPU ของเครื่องผู้ใช้ผ่าน Windows Registry หรือ Platform"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        winreg.CloseKey(key)
        if cpu_name:
            return cpu_name.strip()
    except Exception:
        pass
    try:
        import platform
        return platform.processor() or "AMD / Intel Processor"
    except Exception:
        return "Unknown CPU Processor"

def check_license_online(user_key):
    """ตรวจสอบ License Key กับ GitHub Gist ล่าสุดแบบ Real-time"""
    if not user_key or not str(user_key).strip():
        return False, "❌ กรุณากรอก License Key ในแท็บ License", ""
    
    key_clean = str(user_key).strip()
    try:
        url_with_cache = f"{GIST_RAW_URL}?t={int(time.time())}"
        resp = requests.get(url_with_cache, timeout=6)
        if resp.status_code != 200:
            return False, "❌ ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์เช็คคีย์ได้", ""
        
        db = resp.json()
        if key_clean not in db:
            return False, f"❌ ไม่พบ License Key '{key_clean}' ในระบบ", ""
        
        key_data = db[key_clean]
        status = key_data.get("status", "active")
        if status != "active":
            return False, "❌ License Key นี้ถูกระงับการใช้งาน (Banned)", ""
        
        expiry_str = key_data.get("expiry", "2000-01-01")
        try:
            exp_date = datetime.strptime(expiry_str, "%Y-%m-%d")
            if datetime.now() > exp_date:
                return False, f"❌ License Key หมดอายุแล้วเมื่อ ({expiry_str})", expiry_str
        except Exception:
            pass
        
        saved_hwid = key_data.get("hwid", "")
        current_hwid = get_hwid()
        if saved_hwid and saved_hwid != current_hwid:
            return False, f"❌ Key นี้ถูกผูกใช้งานกับเครื่องอื่นอยู่แล้ว (HWID ไม่ตรง)", expiry_str
        
        return True, f"✅ License Key ถูกต้อง! (หมดอายุ: {expiry_str})", expiry_str
    except Exception as e:
        return False, f"❌ เกิดข้อผิดพลาดในการตรวจสอบคีย์: {e}", ""

class GameplayControllerCore:
    """แกนหลักของระบบบอทควบคุมเกม การโหลดโมเดล สเตทแมชชีน และการทำงานเบื้องหลัง"""
    def __init__(self):
        self.hwnd = None
        self.model = None
        self.template_btn = None
        self.relay_templates = []
        self.boost_start_templates = []
        self.bot_active = False
        
        self.auto_jump = True
        self.auto_slide = True
        self.auto_relic = False
        
        self.trigger_dist = 140
        self.slide_hold_ms = 850
        self.conf_val = 0.28
        self.autostart_enabled = True
        self.use_boost_start = False
        self.buy_random_boost = True
        self.use_relay = True
        self.auto_open_chest = True
        self.loading_start_time = 0
        self.dismiss_clicks = 0
        self.openall_fallback_clicks = 0
        self.confirm_fallback_clicks = 0
        self._watchdog_last_state = None
        self._watchdog_state_since = 0
        self._lobby_confirm_since = 0

        # RapidOCR Buff Options
        self.buy_double_coin = True
        self.buy_magnetic_aura = False
        self.buy_hp_drain = False
        self.buy_crush_chance = False
        self.buy_gold_coin_magic = False
        self.buy_hp_potions = False
        self.buy_pit_lifts = False
        self.buy_score_bonus = False
        self.buy_revive = False
        self.buy_base_speed = False
        self.buy_collision_damage = False

        self.ocr_engine = None
        self._last_ocr_text = ""
        self._async_ocr_text = ""
        self._ocr_running = False
        self.buff_spin_start_time = 0
        self._init_ocr()

        self.eco_mode_enabled = False
        
        # Rest Break Configs
        self.rest_breaks_enabled = True
        self.current_session_runs = 0
        self.max_session_runs_limit = 12
        self.target_session_runs = random.randint(9, 12)
        self.rest_end_time = 0
        
        # Game Flow States
        self.STATE_PLAYING = "PLAYING"
        self.STATE_WAIT_OK = "WAIT_OK"
        self.STATE_WAIT_OPENALL = "WAIT_OPENALL"
        self.STATE_WAIT_CONFIRM_OPENALL = "WAIT_CONFIRM_OPENALL"
        self.STATE_WAIT_PLAYLOBBY = "WAIT_PLAYLOBBY"
        self.STATE_WAIT_SELECTBUFF_1 = "WAIT_SELECTBUFF_1"
        self.STATE_WAIT_SELECTBUFF_2 = "WAIT_SELECTBUFF_2"
        self.STATE_WAIT_SELECTBUFF_3 = "WAIT_SELECTBUFF_3"
        self.STATE_WAIT_BUFF_RESULT = "WAIT_BUFF_RESULT"
        self.STATE_WAIT_START = "WAIT_START"
        self.STATE_WAIT_LOADING = "WAIT_LOADING"
        self.STATE_RESTING = "RESTING"
        
        self.current_state = self.STATE_PLAYING
        self.last_action_time = 0
        self.last_random_jump_check_time = 0
        self.last_switch_check_time = 0
        self.last_endgame_check_time = 0
        self.action_cooldown = 0.30
        self.scheduled_actions = []
        self.last_jump_time = 0
        self.last_slide_time = 0
        self.last_switch_time = 0
        
        self.cached_switch_status = False
        self.cached_switch_rect = None
        self.cached_switch_val = 0.0
        self.FALLBACK_COOKIE_X = 220
        
        self.last_obstacle_x = None
        self.last_obstacle_time = None
        self.estimated_speed = 350.0
        self.autostart_templates = {}

    def scan_mumu_windows(self):
        """สแกนหาหน้าต่าง MuMu Player ทั้งหมดที่เปิดอยู่"""
        windows = {}
        def enum_cb(h, extra):
            if win32gui.IsWindowVisible(h):
                t = win32gui.GetWindowText(h)
                c = win32gui.GetClassName(h)
                if t and ("android device" in t.lower() or "mumuplayer" in t.lower() or "mumu" in c.lower() or "mumu" in t.lower()):
                    label = f"{t} (HWND: {h})"
                    windows[label] = h
            return True
        try:
            win32gui.EnumWindows(enum_cb, None)
        except Exception:
            pass
        return windows

    def init_resources(self):
        print("=== บอท Cookie Run (โหมด Dashboard GUI) กำลังเตรียมทรัพยากร ===")
        self.mumu_windows = self.scan_mumu_windows()
        if self.mumu_windows:
            first_label = list(self.mumu_windows.keys())[0]
            self.hwnd = self.mumu_windows[first_label]
            print(f"✅ เชื่อมต่อหน้าต่าง Emulator สำเร็จ! ({first_label})")
        else:
            self.hwnd = None
            print("❌ ไม่พบหน้าต่างโปรแกรมจำลอง MuMu Player! กรุณาเปิดโปรแกรมจำลองขึ้นมาก่อนรันบอท")

        if getattr(sys, 'frozen', False):
            script_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))

        onnx_path = os.path.join(script_dir, "best.onnx")
        pt_path = os.path.join(script_dir, "best.pt")

        import torch
        self.device_str = "cuda" if torch.cuda.is_available() else "cpu"

        if self.device_str == "cuda" and os.path.exists(pt_path):
            print(f"📥 [GPU Accelerator] โหลดโมเดล PyTorch CUDA 'best.pt' บน {torch.cuda.get_device_name(0)}...")
            self.model = YOLO(pt_path, task="detect")
            print("✅ โหลดโมเดล PyTorch CUDA สำเร็จ! (Ultra-low latency)")
        elif os.path.exists(onnx_path):
            print("📥 กำลังโหลดโมเดล YOLOv8 'best.onnx' (ONNX Runtime)...")
            self.model = YOLO(onnx_path, task="detect")
            print("✅ โหลดโมเดล YOLOv8 (ONNX) สำเร็จ!")
        elif os.path.exists(pt_path):
            print("📥 กำลังโหลดโมเดล YOLOv8 'best.pt'...")
            self.model = YOLO(pt_path, task="detect")
            print("✅ โหลดโมเดล YOLOv8 สำเร็จ!")
        else:
            print("❌ ไม่พบโมเดล 'best.onnx' หรือ 'best.pt' ในโฟลเดอร์บอท!")

        self.relay_templates = load_multi_templates(os.path.join(script_dir, "autostart", "relay_btn"))
        self.template_btn = self.relay_templates[0][1] if self.relay_templates else None
        
        switch_template_path = os.path.join(script_dir, "autochangeplayer.png")
        if self.template_btn is None and os.path.exists(switch_template_path):
            self.template_btn = cv2.imread(switch_template_path, cv2.IMREAD_GRAYSCALE)
            self.relay_templates = [("autochangeplayer.png", self.template_btn)]

        self.boost_start_templates = load_multi_templates(os.path.join(script_dir, "autostart", "boost_start_btn"))
        
        autostart_dir = os.path.join(script_dir, "autostart")
        autostart_files = {
            "ok": "ok_1.png",
            "openall": "openall_2.png",
            "confirmafteropenall": "confirmafteropenall_1.png",
            "playlobby": "playlobby_1.png",
            "selectbuff_1": "selectbuff_1.png",
            "selectbuff_2": "selectbuff_2.png",
            "selectbuff_3": "selectbuff_3.png",
            "affterselectbuff": "affterselectbuff_1.png",
            "confirmlevelup": "confirmlevelup1.png"
        }
        
        for name, filename in autostart_files.items():
            filepath = os.path.join(autostart_dir, filename)
            if os.path.exists(filepath):
                img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    if name in ["openall", "confirmafteropenall"]:
                        h, w = img.shape[:2]
                        img = cv2.resize(img, (int(w * 0.85), int(h * 0.85)))
                    self.autostart_templates[name] = img

    def _init_ocr(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
            self.ocr_engine = RapidOCR()
            print("✅ RapidOCR Engine โหลดสำเร็จพร้อมใช้งานสำหรับการสแกนบัฟ!")
        except Exception as e:
            print(f"⚠️ ไม่สามารถเริ่มระบบ RapidOCR ได้: {e}")
            self.ocr_engine = None

    def trigger_async_ocr(self, roi_big):
        if getattr(self, "_ocr_running", False) or self.ocr_engine is None:
            return
        self._ocr_running = True

        def worker():
            try:
                res, _ = self.ocr_engine(roi_big)
                text = " ".join(item[1] for item in res) if res else ""
                self._async_ocr_text = text
            except Exception:
                self._async_ocr_text = ""
            finally:
                self._ocr_running = False

        import threading
        t = threading.Thread(target=worker, daemon=True)
        t.start()
