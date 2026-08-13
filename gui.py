# -*- coding: utf-8 -*-
import os
import sys
import time
import random
import json
import traceback
import cv2
import numpy as np
import win32gui
import win32con
import customtkinter as ctk

from window_manager import (
    human_click_bg, human_press_bg, capture_window_bg,
    VK_ALT, SCAN_ALT, VK_LSHIFT, SCAN_SHIFT, VK_SPACE, SCAN_SPACE
)
from template_matcher import (
    find_template_match, find_best_template_match, set_show_debug_logs
)
from gameplay_controller import GameplayControllerCore, get_hwid, check_license_online

class StdoutRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.enabled = True

    def write(self, string):
        if not getattr(self, "enabled", True):
            return
        try:
            self.text_widget.configure(state="normal")
            self.text_widget.insert("end", string)
            # Automatic Log Trimming: Limit log memory usage to prevent RAM leak
            num_lines = int(float(self.text_widget.index('end-1c').split('.')[0]))
            if num_lines > 500:
                self.text_widget.delete("1.0", "100.0")
            self.text_widget.see("end")
            self.text_widget.configure(state="disabled")
        except Exception:
            pass

    def flush(self):
        pass

class CookieRunAIApp(ctk.CTk, GameplayControllerCore):
    def __init__(self):
        ctk.CTk.__init__(self)
        GameplayControllerCore.__init__(self)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.title("Cookie Clicker 💀 (ระบบบอทอัตโนมัติ)")
        self.geometry("780x520")
        self.resizable(False, False)
        
        self.init_resources()
        self.create_layout()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(100, self.update_loop)

    def on_closing(self):
        self.bot_active = False
        self.destroy()

    def open_buff_config_window(self):
        if hasattr(self, 'buff_win') and self.buff_win is not None and self.buff_win.winfo_exists():
            self.buff_win.focus()
            return
        
        self.buff_win = ctk.CTkToplevel(self)
        self.buff_win.title("🎯 ตั้งค่าบัฟเป้าหมาย (RapidOCR)")
        self.buff_win.geometry("520x490")
        self.buff_win.resizable(False, False)
        self.buff_win.attributes("-topmost", True)

        lbl_title = ctk.CTkLabel(self.buff_win, text="🎯 เลือกบัฟเป้าหมายหลัก", font=("Arial", 16, "bold"), text_color="#7d5fff")
        lbl_title.pack(pady=(15, 2))

        lbl_desc = ctk.CTkLabel(self.buff_win, text="คลิกเลือกบัฟที่ต้องการเพียง 1 ชนิด (บอทจะสุ่มหาจนกว่าจะเจอบัฟนี้)", font=("Arial", 11), text_color="#a29bfe")
        lbl_desc.pack(pady=(0, 10))

        frame_grid = ctk.CTkFrame(self.buff_win, fg_color="#18181c", corner_radius=12)
        frame_grid.pack(fill="both", expand=True, padx=15, pady=(0, 8))

        buff_items = [
            ("🪙 Coins x2 (เหรียญ 2 เท่า)", "buy_double_coin", 0, 0),
            ("💖 Revive (คืนชีพ)", "buy_revive", 0, 1),
            ("🧲 Magnetic (พลังแม่เหล็ก)", "buy_magnetic_aura", 1, 0),
            ("⚡ Base Speed +17%", "buy_base_speed", 1, 1),
            ("🧪 -15% HP Drain (ลดเลือดช้า)", "buy_hp_drain", 2, 0),
            ("🚑 Collision -30% (ลดแรงชน)", "buy_collision_damage", 2, 1),
            ("🛡️ Crush 70% (ชนทำลาย)", "buy_crush_chance", 3, 0),
            ("🍷 Potion +20% (กินยาขวด)", "buy_hp_potions", 3, 1),
            ("🎁 Gold Coin Magic", "buy_gold_coin_magic", 4, 0),
            ("🏆 Score +15% (เพิ่มคะแนน)", "buy_score_bonus", 4, 1),
            ("🛟 Pit Lifts x2 (ช่วยตกเหว)", "buy_pit_lifts", 5, 0),
        ]

        current_selected = "buy_double_coin"
        for _, var_name, _, _ in buff_items:
            if getattr(self, var_name, False):
                current_selected = var_name
                break

        lbl_status = ctk.CTkLabel(self.buff_win, text="", font=("Arial", 12, "bold"), text_color="#00cec9")
        lbl_status.pack(pady=(4, 12))

        btn_dict = {}

        def select_buff(target_vn, target_text):
            for _, vn, _, _ in buff_items:
                setattr(self, vn, (vn == target_vn))
            print(f"⚙️ เปลี่ยนบัฟเป้าหมายหลักเป็น: '{target_vn}'")
            lbl_status.configure(text=f"✅ เลือกบัฟเป้าหมาย: {target_text}")

            for vn, btn in btn_dict.items():
                if vn == target_vn:
                    btn.configure(fg_color="#7d5fff", hover_color="#6c5ce7", text_color="#ffffff", border_width=2, border_color="#a29bfe")
                else:
                    btn.configure(fg_color="#282830", hover_color="#3a3a46", text_color="#dcdde1", border_width=0)

        frame_grid.columnconfigure(0, weight=1)
        frame_grid.columnconfigure(1, weight=1)

        for text, var_name, row, col in buff_items:
            def make_handler(vn=var_name, txt=text):
                return lambda: select_buff(vn, txt)

            btn = ctk.CTkButton(
                frame_grid, text=text, font=("Arial", 11, "bold"), height=42, corner_radius=8, command=make_handler(var_name, text)
            )
            btn.grid(row=row, column=col, padx=8, pady=6, sticky="ew")
            btn_dict[var_name] = btn

        initial_text = next((t for t, vn, _, _ in buff_items if vn == current_selected), "Coins x2")
        select_buff(current_selected, initial_text)

    def create_layout(self):
        self.tabview = ctk.CTkTabview(
            self,
            segmented_button_selected_color="#7d5fff",
            segmented_button_selected_hover_color="#6c5ce7",
            segmented_button_unselected_color="#2c2c35",
            text_color="#ffffff",
            fg_color="#1e1e24"
        )
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_autorun = self.tabview.add("ระบบวิ่งอัตโนมัติ")
        self.tab_autoclaim = self.tabview.add("ระบบรับของรางวัล")
        self.tab_settings = self.tabview.add("ตั้งค่าระบบ")
        self.tab_license = self.tabview.add("ยืนยัน License")
        
        self.setup_autorun_tab()
        self.setup_autoclaim_tab()
        self.setup_settings_tab()
        self.setup_license_tab()

    def setup_autorun_tab(self):
        self.autorun_left = ctk.CTkFrame(self.tab_autorun, fg_color="transparent")
        self.autorun_left.pack(side="left", fill="both", expand=False, padx=(10, 5), pady=10)
        
        self.autorun_right = ctk.CTkFrame(self.tab_autorun, fg_color="#121212", corner_radius=8)
        self.autorun_right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)
        
        lbl_title = ctk.CTkLabel(self.autorun_left, text="ตั้งค่าระบบวิ่งอัตโนมัติ (Auto-Run)", font=("Arial", 13, "bold"), text_color="#a29bfe")
        lbl_title.pack(anchor="w", pady=(5, 10))

        lbl_win_select = ctk.CTkLabel(self.autorun_left, text="หน้าต่างโปรแกรมจำลอง MuMu:", font=("Arial", 11, "bold"), text_color="#dcdde1")
        lbl_win_select.pack(anchor="w", pady=(0, 2))
        
        win_frame = ctk.CTkFrame(self.autorun_left, fg_color="transparent")
        win_frame.pack(fill="x", pady=(0, 10))
        
        init_options = list(self.mumu_windows.keys()) if hasattr(self, 'mumu_windows') and self.mumu_windows else ["ไม่พบหน้าต่าง MuMu Player"]
        self.window_option_menu = ctk.CTkOptionMenu(
            win_frame, values=init_options, command=self.on_select_mumu_window,
            width=150, fg_color="#2f3542", button_color="#7d5fff", button_hover_color="#6c5ce7"
        )
        self.window_option_menu.pack(side="left", fill="x", expand=True, padx=(0, 4))
        if init_options and init_options[0] != "ไม่พบหน้าต่าง MuMu Player":
            self.window_option_menu.set(init_options[0])

        self.btn_hide_mumu = ctk.CTkButton(
            win_frame, text="🙈 ซ่อนจอ", width=65, fg_color="#2f3542", hover_color="#7d5fff", font=("Arial", 11, "bold"), command=self.toggle_hide_mumu_window
        )
        self.btn_hide_mumu.pack(side="right", padx=(4, 0))

        self.btn_grid_capture = ctk.CTkButton(
            win_frame, text="📸 ตาราง", width=65, fg_color="#2f3542", hover_color="#00cec9", font=("Arial", 11, "bold"), command=self.capture_and_show_grid_overlay
        )
        self.btn_grid_capture.pack(side="right", padx=(4, 0))

        btn_refresh_win = ctk.CTkButton(
            win_frame, text="🔄", width=35, fg_color="#2f3542", hover_color="#7d5fff", command=self.refresh_mumu_windows
        )
        btn_refresh_win.pack(side="right")
        
        self.switch_frame = ctk.CTkFrame(self.autorun_left, fg_color="transparent")
        self.switch_frame.pack(fill="both", expand=True)
        
        lbl_yolo = ctk.CTkLabel(self.switch_frame, text="YOLO AI Bot (หลบสิ่งกีดขวาง ด่าน 1)", font=("Arial", 11, "bold"), text_color="#dcdde1")
        lbl_yolo.grid(row=0, column=0, columnspan=2, padx=15, pady=(5, 2), sticky="w")
        self.switch_yolo = ctk.CTkSwitch(self.switch_frame, text="", progress_color="#7d5fff", fg_color="#2f3542", width=40, command=self.on_toggle_yolo)
        self.switch_yolo.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="w")
        self.switch_yolo.select()
        
        lbl_rest = ctk.CTkLabel(self.switch_frame, text="ระบบพักสายตา (Auto-Rest)", font=("Arial", 11, "bold"), text_color="#dcdde1")
        lbl_rest.grid(row=2, column=0, padx=15, pady=(5, 2), sticky="w")
        self.switch_rest = ctk.CTkSwitch(self.switch_frame, text="", progress_color="#7d5fff", fg_color="#2f3542", width=40, command=self.on_toggle_rest)
        self.switch_rest.grid(row=3, column=0, padx=15, pady=(0, 10))
        if self.rest_breaks_enabled:
            self.switch_rest.select()
        
        lbl_buffs = ctk.CTkLabel(self.switch_frame, text="ซื้อบัฟอัตโนมัติ (Buy Buffs)", font=("Arial", 11, "bold"), text_color="#dcdde1")
        lbl_buffs.grid(row=2, column=1, padx=15, pady=(5, 2), sticky="w")
        
        buff_frame = ctk.CTkFrame(self.switch_frame, fg_color="transparent")
        buff_frame.grid(row=3, column=1, padx=15, pady=(0, 10), sticky="w")

        self.switch_buffs = ctk.CTkSwitch(buff_frame, text="", progress_color="#7d5fff", fg_color="#2f3542", width=40, command=self.on_toggle_buy_random_boost)
        self.switch_buffs.pack(side="left")
        if self.buy_random_boost:
            self.switch_buffs.select()

        self.btn_buff_cfg = ctk.CTkButton(
            buff_frame, text="⚙️ บัฟ", font=("Arial", 10, "bold"), width=58, height=22, fg_color="#2f3542", hover_color="#7d5fff", text_color="#ffffff", command=self.open_buff_config_window
        )
        self.btn_buff_cfg.pack(side="left", padx=(5, 0))
        
        lbl_fast_start = ctk.CTkLabel(self.switch_frame, text="เริ่มเกมเร็ว (Fast Start)", font=("Arial", 11, "bold"), text_color="#dcdde1")
        lbl_fast_start.grid(row=4, column=0, padx=15, pady=(5, 2), sticky="w")
        self.switch_fast_start = ctk.CTkSwitch(self.switch_frame, text="", progress_color="#7d5fff", fg_color="#2f3542", width=40, command=self.on_toggle_boost_start)
        self.switch_fast_start.grid(row=5, column=0, padx=15, pady=(0, 10))
        if self.use_boost_start:
            self.switch_fast_start.select()
        
        lbl_relay = ctk.CTkLabel(self.switch_frame, text="ผลัดสอง (Auto Relay)", font=("Arial", 11, "bold"), text_color="#dcdde1")
        lbl_relay.grid(row=4, column=1, padx=15, pady=(5, 2), sticky="w")
        self.switch_relay = ctk.CTkSwitch(self.switch_frame, text="", progress_color="#7d5fff", fg_color="#2f3542", width=40, command=self.on_toggle_relay)
        self.switch_relay.grid(row=5, column=1, padx=15, pady=(0, 10))
        if self.use_relay:
            self.switch_relay.select()

        lbl_debug = ctk.CTkLabel(self.switch_frame, text="แสดง Debug Logs", font=("Arial", 11, "bold"), text_color="#dcdde1")
        lbl_debug.grid(row=6, column=0, padx=15, pady=(5, 2), sticky="w")
        self.switch_debug = ctk.CTkSwitch(self.switch_frame, text="", progress_color="#7d5fff", fg_color="#2f3542", width=40, command=self.on_toggle_debug)
        self.switch_debug.grid(row=7, column=0, padx=15, pady=(0, 10))

        # สวิตช์เปิด/ปิดแสดงผล GUI Logs (เพื่อประหยัดสเปคเครื่อง)
        lbl_gui_logs = ctk.CTkLabel(self.switch_frame, text="แสดง GUI Logs", font=("Arial", 11, "bold"), text_color="#dcdde1")
        lbl_gui_logs.grid(row=6, column=1, padx=15, pady=(5, 2), sticky="w")
        self.switch_gui_logs = ctk.CTkSwitch(self.switch_frame, text="", progress_color="#7d5fff", fg_color="#2f3542", width=40, command=self.on_toggle_gui_logs)
        self.switch_gui_logs.grid(row=7, column=1, padx=15, pady=(0, 10))
        self.switch_gui_logs.select()

        # Log Text Box
        lbl_logs = ctk.CTkLabel(self.autorun_right, text="บันทึกการทำงาน (Execution Logs):", font=("Arial", 12, "bold"), text_color="#a29bfe")
        lbl_logs.pack(anchor="w", padx=10, pady=(10, 5))
        
        self.log_textbox = ctk.CTkTextbox(self.autorun_right, font=("Consolas", 10), fg_color="#0c0d12", text_color="#00d2d3")
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        self.log_textbox.configure(state="disabled")

        self.stdout_redirector = StdoutRedirector(self.log_textbox)
        sys.stdout = self.stdout_redirector

        btn_control_frame = ctk.CTkFrame(self.autorun_right, fg_color="transparent")
        btn_control_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.btn_start = ctk.CTkButton(
            btn_control_frame, text="▶️ เริ่มบอท (START)", fg_color="#2ecc71", hover_color="#27ae60", font=("Arial", 12, "bold"), command=self.start_bot
        )
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_stop = ctk.CTkButton(
            btn_control_frame, text="⏹️ หยุดบอท (STOP)", fg_color="#e74c3c", hover_color="#c0392b", font=("Arial", 12, "bold"), command=self.stop_bot
        )
        self.btn_stop.pack(side="right", fill="x", expand=True, padx=(5, 0))

        self.status_label = ctk.CTkLabel(self.autorun_right, text="ตัวจำลอง: ยังไม่เชื่อมต่อ", font=("Arial", 11, "bold"), text_color="#e74c3c")
        self.status_label.pack(side="left", padx=10, pady=(0, 10))

        self.bot_status_label = ctk.CTkLabel(self.autorun_right, text="สถานะ: หยุดทำงาน", font=("Arial", 11, "bold"), text_color="#e74c3c")
        self.bot_status_label.pack(side="right", padx=10, pady=(0, 10))

    def setup_autoclaim_tab(self):
        scroll_frame = ctk.CTkScrollableFrame(self.tab_autoclaim, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=10)

        lbl_title = ctk.CTkLabel(scroll_frame, text="🎁 ศูนย์รวมฟังก์ชันอัตโนมัติ (Automation Suite)", font=("Arial", 15, "bold"), text_color="#a29bfe")
        lbl_title.pack(anchor="w", pady=(5, 10))

        # --- CARD 1: Send Hearts ---
        card_hearts = ctk.CTkFrame(scroll_frame, fg_color="#18181c", corner_radius=10)
        card_hearts.pack(fill="x", pady=6, padx=5)

        h_title = ctk.CTkLabel(card_hearts, text="💌 ระบบส่งหัวใจอัตโนมัติ (Auto Send Hearts)", font=("Arial", 12, "bold"), text_color="#ff7675")
        h_title.pack(anchor="w", padx=12, pady=(10, 2))
        
        h_desc = ctk.CTkLabel(card_hearts, text="สแกนรายชื่อเพื่อน เลื่อนตาราง และกดส่งหัวใจให้เพื่อนทุกคนในรายชื่อโดยอัตโนมัติ", font=("Arial", 10), text_color="#a4b0be")
        h_desc.pack(anchor="w", padx=12, pady=(0, 8))

        btn_box1 = ctk.CTkFrame(card_hearts, fg_color="transparent")
        btn_box1.pack(fill="x", padx=12, pady=(0, 10))

        btn_send_hearts = ctk.CTkButton(
            btn_box1, text="▶️ เริ่มส่งหัวใจ (Start)", fg_color="#e84393", hover_color="#d63031", font=("Arial", 11, "bold"),
            command=self.start_send_hearts_task
        )
        btn_send_hearts.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_stop_hearts = ctk.CTkButton(
            btn_box1, text="⏹️ หยุด (Stop)", width=90, fg_color="#2f3542", hover_color="#e74c3c", font=("Arial", 11, "bold"),
            command=self.stop_autoclaim_task
        )
        btn_stop_hearts.pack(side="right")

        # --- CARD 2: Extract Treasure ---
        card_extract = ctk.CTkFrame(scroll_frame, fg_color="#18181c", corner_radius=10)
        card_extract.pack(fill="x", pady=6, padx=5)

        e_title = ctk.CTkLabel(card_extract, text="🪙 ระบบสุ่มและย่อยสมบัติ (Auto Extract Treasure)", font=("Arial", 12, "bold"), text_color="#fdcb6e")
        e_title.pack(anchor="w", padx=12, pady=(10, 2))
        
        e_desc = ctk.CTkLabel(card_extract, text="สุ่มซื้อสมบัติ 12 ครั้ง และเข้าคลังกดย่อยเป็นผงเวทมนตร์อัตโนมัติแบบต่อเนื่อง", font=("Arial", 10), text_color="#a4b0be")
        e_desc.pack(anchor="w", padx=12, pady=(0, 8))

        btn_box2 = ctk.CTkFrame(card_extract, fg_color="transparent")
        btn_box2.pack(fill="x", padx=12, pady=(0, 10))

        btn_extract = ctk.CTkButton(
            btn_box2, text="▶️ เริ่มย่อยสมบัติ (Start)", fg_color="#fdcb6e", hover_color="#e1b12c", text_color="#2d3436", font=("Arial", 11, "bold"),
            command=self.start_extract_treasure_task
        )
        btn_extract.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_stop_extract = ctk.CTkButton(
            btn_box2, text="⏹️ หยุด (Stop)", width=90, fg_color="#2f3542", hover_color="#e74c3c", font=("Arial", 11, "bold"),
            command=self.stop_autoclaim_task
        )
        btn_stop_extract.pack(side="right")

        # --- CARD 3: Open Gift Box ---
        card_gift = ctk.CTkFrame(scroll_frame, fg_color="#18181c", corner_radius=10)
        card_gift.pack(fill="x", pady=6, padx=5)

        g_title = ctk.CTkLabel(card_gift, text="🎁 ระบบเปิดกล่องของขวัญอัตโนมัติ (Auto Claim Gift)", font=("Arial", 12, "bold"), text_color="#74b9ff")
        g_title.pack(anchor="w", padx=12, pady=(10, 2))
        
        g_desc = ctk.CTkLabel(card_gift, text="สุ่มเปิดกล่องของขวัญและกดเปิดอีกครั้งอัตโนมัติจนกว่าจะได้รับของครบ", font=("Arial", 10), text_color="#a4b0be")
        g_desc.pack(anchor="w", padx=12, pady=(0, 8))

        btn_box3 = ctk.CTkFrame(card_gift, fg_color="transparent")
        btn_box3.pack(fill="x", padx=12, pady=(0, 10))

        btn_claim = ctk.CTkButton(
            btn_box3, text="▶️ เริ่มเปิดกล่อง (Start)", fg_color="#0984e3", hover_color="#74b9ff", font=("Arial", 11, "bold"),
            command=self.start_claim_gift_task
        )
        btn_claim.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_stop_claim = ctk.CTkButton(
            btn_box3, text="⏹️ หยุด (Stop)", width=90, fg_color="#2f3542", hover_color="#e74c3c", font=("Arial", 11, "bold"),
            command=self.stop_autoclaim_task
        )
        btn_stop_claim.pack(side="right")

    def start_send_hearts_task(self):
        if getattr(self, "autoclaim_running", False):
            print("⚠️ มีระบบอัตโนมัติกำลังทำงานอยู่แล้ว! กรุณากดหยุดระบบเดิมก่อน")
            return
        if not self.hwnd:
            print("❌ ไม่พบหน้าต่าง Emulator!")
            return
        
        self.autoclaim_running = True
        print(f"[{time.strftime('%H:%M:%S')}] 💌 เริ่มทำงานระบบส่งหัวใจอัตโนมัติ...")
        
        def worker():
            try:
                from auto_send_hearts import run_auto_send_hearts_loop
                run_auto_send_hearts_loop(self.hwnd, max_scrolls=300, stop_checker=lambda: not getattr(self, "autoclaim_running", False))
            except Exception as e:
                print(f"❌ เกิดข้อผิดพลาดในระบบส่งหัวใจ: {e}")
            finally:
                self.autoclaim_running = False
                print(f"[{time.strftime('%H:%M:%S')}] ⏹️ หยุดทำงานระบบส่งหัวใจ")
        
        import threading
        threading.Thread(target=worker, daemon=True).start()

    def start_extract_treasure_task(self):
        if getattr(self, "autoclaim_running", False):
            print("⚠️ มีระบบอัตโนมัติกำลังทำงานอยู่แล้ว! กรุณากดหยุดระบบเดิมก่อน")
            return
        if not self.hwnd:
            print("❌ ไม่พบหน้าต่าง Emulator!")
            return
        
        self.autoclaim_running = True
        print(f"[{time.strftime('%H:%M:%S')}] 🪙 เริ่มทำงานระบบสุ่มและย่อยสมบัติอัตโนมัติ...")
        
        def worker():
            try:
                from auto_extract_treasure import run_auto_extract_loop
                run_auto_extract_loop(self.hwnd, max_loops=None, stop_checker=lambda: not getattr(self, "autoclaim_running", False))
            except Exception as e:
                print(f"❌ เกิดข้อผิดพลาดในระบบย่อยสมบัติ: {e}")
            finally:
                self.autoclaim_running = False
                print(f"[{time.strftime('%H:%M:%S')}] ⏹️ หยุดทำงานระบบย่อยสมบัติ")
        
        import threading
        threading.Thread(target=worker, daemon=True).start()

    def start_claim_gift_task(self):
        if getattr(self, "autoclaim_running", False):
            print("⚠️ มีระบบอัตโนมัติกำลังทำงานอยู่แล้ว! กรุณากดหยุดระบบเดิมก่อน")
            return
        if not self.hwnd:
            print("❌ ไม่พบหน้าต่าง Emulator!")
            return
        
        self.autoclaim_running = True
        print(f"[{time.strftime('%H:%M:%S')}] 🎁 เริ่มทำงานระบบเปิดกล่องของขวัญอัตโนมัติ...")
        
        def worker():
            try:
                from auto_claim_gift import run_auto_gift_loop
                run_auto_gift_loop(self.hwnd, max_rounds=None, stop_checker=lambda: not getattr(self, "autoclaim_running", False))
            except Exception as e:
                print(f"❌ เกิดข้อผิดพลาดในระบบเปิดกล่อง: {e}")
            finally:
                self.autoclaim_running = False
                print(f"[{time.strftime('%H:%M:%S')}] ⏹️ หยุดทำงานระบบเปิดกล่อง")
        
        import threading
        threading.Thread(target=worker, daemon=True).start()

    def stop_autoclaim_task(self):
        if getattr(self, "autoclaim_running", False):
            self.autoclaim_running = False
            print(f"[{time.strftime('%H:%M:%S')}] 🛑 ส่งสัญญาณหยุดระบบส่งหัวใจ/ย่อยสมบัติ/เปิดกล่อง...")

    def setup_settings_tab(self):
        self.settings_left = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        self.settings_left.pack(side="left", fill="both", expand=True, padx=15, pady=15)

        self.settings_right = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        self.settings_right.pack(side="right", fill="both", expand=True, padx=15, pady=15)

        lbl_profile = ctk.CTkLabel(self.settings_left, text="โปรไฟล์ตั้งค่าด่านด่วน (Quick Profile)", font=("Arial", 12, "bold"), text_color="#a29bfe")
        lbl_profile.pack(anchor="w", pady=(5, 5))

        self.profile_option_menu = ctk.CTkOptionMenu(
            self.settings_left, values=["Stage 1 (ฟาร์มเงิน)", "Stage 3 (ฟาร์มสปีด)"], command=self.on_profile_change,
            fg_color="#2f3542", button_color="#7d5fff"
        )
        self.profile_option_menu.pack(fill="x", pady=(0, 15))

        self.session_runs_label = ctk.CTkLabel(self.settings_left, text="จำนวนรอบในเซสชัน: 0/12 รอบ", font=("Arial", 11, "bold"), text_color="#ffffff")
        self.session_runs_label.pack(anchor="w", pady=5)

        self.session_limit_title = ctk.CTkLabel(self.settings_right, text=f"ขีดจำกัดรอบการเล่นสูงสุดต่อเซสชัน: {self.max_session_runs_limit} รอบ", font=("Arial", 10, "bold"), text_color="#ffffff")
        self.session_limit_title.pack(anchor="w", pady=(5, 1))

        self.session_limit_slider = ctk.CTkSlider(
            self.settings_right, from_=5, to=30, number_of_steps=25, progress_color="#7d5fff", fg_color="#2c2c35", command=self.on_session_limit_change
        )
        self.session_limit_slider.set(self.max_session_runs_limit)
        self.session_limit_slider.pack(fill="x", pady=(0, 10))

        self.dist_title = ctk.CTkLabel(self.settings_right, text=f"ระยะทางทริกเกอร์หลบสิ่งกีดขวาง: {self.trigger_dist} px", font=("Arial", 10, "bold"), text_color="#ffffff")
        self.dist_title.pack(anchor="w", pady=(5, 1))
        self.dist_slider = ctk.CTkSlider(
            self.settings_right, from_=50, to=300, number_of_steps=250, progress_color="#7d5fff", fg_color="#2c2c35", command=self.on_dist_change
        )
        self.dist_slider.set(self.trigger_dist)
        self.dist_slider.pack(fill="x", pady=(0, 10))

        self.slide_title = ctk.CTkLabel(self.settings_right, text=f"เวลากดสไลด์ค้าง: {self.slide_hold_ms} ms", font=("Arial", 10, "bold"), text_color="#ffffff")
        self.slide_title.pack(anchor="w", pady=(5, 1))
        self.slide_slider = ctk.CTkSlider(
            self.settings_right, from_=100, to=1500, number_of_steps=140, progress_color="#7d5fff", fg_color="#2c2c35", command=self.on_slide_change
        )
        self.slide_slider.set(self.slide_hold_ms)
        self.slide_slider.pack(fill="x", pady=(0, 10))

        self.conf_title = ctk.CTkLabel(self.settings_right, text=f"ความเข้มงวด YOLO (Threshold): {int(self.conf_val * 100)}%", font=("Arial", 10, "bold"), text_color="#ffffff")
        self.conf_title.pack(anchor="w", pady=(5, 1))
        self.conf_slider = ctk.CTkSlider(
            self.settings_right, from_=0.10, to=0.85, number_of_steps=75, progress_color="#7d5fff", fg_color="#2c2c35", command=self.on_conf_change
        )
        self.conf_slider.set(self.conf_val)
        self.conf_slider.pack(fill="x", pady=(0, 10))

    def setup_license_tab(self):
        card_frame = ctk.CTkFrame(self.tab_license, fg_color="#121212", corner_radius=12)
        card_frame.pack(fill="both", expand=True, padx=20, pady=20)

        lbl_title = ctk.CTkLabel(card_frame, text="🔑 ระบบตรวจสอบและยืนยันสิทธิ์ใช้งาน (License Key)", font=("Arial", 15, "bold"), text_color="#7d5fff")
        lbl_title.pack(pady=(20, 10))

        hwid_frame = ctk.CTkFrame(card_frame, fg_color="#1e1e24", corner_radius=8)
        hwid_frame.pack(fill="x", padx=25, pady=(5, 12))

        current_hwid = get_hwid()
        lbl_hwid_tag = ctk.CTkLabel(hwid_frame, text="รหัสประจำเครื่องของคุณ (HWID):", font=("Arial", 11, "bold"), text_color="#a29bfe")
        lbl_hwid_tag.pack(anchor="w", padx=12, pady=(8, 2))

        hwid_sub_frame = ctk.CTkFrame(hwid_frame, fg_color="transparent")
        hwid_sub_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.entry_hwid = ctk.CTkEntry(hwid_sub_frame, font=("Courier New", 11, "bold"), fg_color="#0c0d12", text_color="#00d2d3")
        self.entry_hwid.insert(0, current_hwid)
        self.entry_hwid.configure(state="readonly")
        self.entry_hwid.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_copy_hwid = ctk.CTkButton(
            hwid_sub_frame, text="📋 คัดลอก HWID", width=95, height=28, fg_color="#2f3542", hover_color="#7d5fff", font=("Arial", 10, "bold"), command=self.copy_hwid_to_clipboard
        )
        btn_copy_hwid.pack(side="right")

        key_frame = ctk.CTkFrame(card_frame, fg_color="#1e1e24", corner_radius=8)
        key_frame.pack(fill="x", padx=25, pady=5)

        lbl_key_tag = ctk.CTkLabel(key_frame, text="กรอก License Key ของคุณ:", font=("Arial", 11, "bold"), text_color="#a29bfe")
        lbl_key_tag.pack(anchor="w", padx=12, pady=(8, 2))

        key_sub_frame = ctk.CTkFrame(key_frame, fg_color="transparent")
        key_sub_frame.pack(fill="x", padx=12, pady=(0, 10))

        saved_key = self.load_saved_license()
        self.entry_license_key = ctk.CTkEntry(
            key_sub_frame, placeholder_text="ตัวอย่าง: CRBOT-VIP-1111", font=("Arial", 12), fg_color="#0c0d12", text_color="#ffffff"
        )
        if saved_key:
            self.entry_license_key.insert(0, saved_key)
        self.entry_license_key.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_verify = ctk.CTkButton(
            key_sub_frame, text="⚡ ตรวจสอบคีย์", width=110, height=32, fg_color="#7d5fff", hover_color="#6c5ce7", font=("Arial", 11, "bold"), command=self.on_verify_key_clicked
        )
        btn_verify.pack(side="right")

        self.license_status_label = ctk.CTkLabel(card_frame, text="สถานะ: 🔒 รอการตรวจสอบสิทธิ์", font=("Arial", 12, "bold"), text_color="#f39c12")
        self.license_status_label.pack(pady=15)

        if saved_key:
            self.after(600, self.auto_check_saved_license)

    def on_select_mumu_window(self, selected_label):
        if hasattr(self, 'mumu_windows') and selected_label in self.mumu_windows:
            self.hwnd = self.mumu_windows[selected_label]
            print(f"[{time.strftime('%H:%M:%S')}] 🎯 สลับไปใช้หน้าต่าง Emulator: {selected_label}")

    def refresh_mumu_windows(self):
        self.mumu_windows = self.scan_mumu_windows()
        options = list(self.mumu_windows.keys())
        if not options:
            options = ["ไม่พบหน้าต่าง MuMu Player"]
            self.hwnd = None
        else:
            current_sel = self.window_option_menu.get() if hasattr(self, 'window_option_menu') else None
            if current_sel in self.mumu_windows:
                self.hwnd = self.mumu_windows[current_sel]
            else:
                first_label = options[0]
                self.hwnd = self.mumu_windows[first_label]
                if hasattr(self, 'window_option_menu'):
                    self.window_option_menu.set(first_label)

        if hasattr(self, 'window_option_menu'):
            self.window_option_menu.configure(values=options)
        print(f"[{time.strftime('%H:%M:%S')}] 🔄 รีเฟรชรายชื่อหน้าต่าง MuMu เรียบร้อย พบ {len(self.mumu_windows)} จอ")

    def toggle_hide_mumu_window(self):
        if not self.hwnd:
            print("❌ ไม่พบหน้าต่าง Emulator!")
            return
        try:
            is_visible = win32gui.IsWindowVisible(self.hwnd)
            if is_visible:
                win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
                self.btn_hide_mumu.configure(text="👁️ แสดงจอ", fg_color="#e74c3c")
                print(f"[{time.strftime('%H:%M:%S')}] 🙈 ซ่อนหน้าต่าง Emulator เรียบร้อย!")
            else:
                win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
                win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
                self.btn_hide_mumu.configure(text="🙈 ซ่อนจอ", fg_color="#2f3542")
                print(f"[{time.strftime('%H:%M:%S')}] 👁️ แสดงหน้าต่าง Emulator เรียบร้อย!")
        except Exception as e:
            print(f"❌ ไม่สามารถเปลี่ยนสถานะแสดง/ซ่อนหน้าต่างได้: {e}")

    def capture_and_show_grid_overlay(self):
        if not self.hwnd:
            print("❌ ไม่พบหน้าต่าง Emulator!")
            return
        frame = capture_window_bg(self.hwnd)
        if frame is None:
            print("❌ ไม่สามารถดึงภาพหน้าจอได้!")
            return
        
        h, w = frame.shape[:2]
        for x in range(0, w, 50):
            cv2.line(frame, (x, 0), (x, h), (100, 100, 100), 1)
            cv2.putText(frame, str(x), (x + 2, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)
        for y in range(0, h, 50):
            cv2.line(frame, (0, y), (w, y), (100, 100, 100), 1)
            cv2.putText(frame, str(y), (5, y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)
        
        cv2.imwrite("captured_grid.png", frame)
        print(f"[{time.strftime('%H:%M:%S')}] 📸 บันทึกภาพพร้อมตารางพิกัดเรียบร้อย -> 'captured_grid.png'")

    def copy_hwid_to_clipboard(self):
        hwid = get_hwid()
        self.clipboard_clear()
        self.clipboard_append(hwid)
        print(f"[{time.strftime('%H:%M:%S')}] 📋 คัดลอก HWID ({hwid}) ลงคลิบบอร์ดเรียบร้อย!")

    def load_saved_license(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        lic_file = os.path.join(script_dir, "license.json")
        if os.path.exists(lic_file):
            try:
                with open(lic_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("license_key", "")
            except Exception:
                pass
        return ""

    def save_saved_license(self, key_str):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        lic_file = os.path.join(script_dir, "license.json")
        try:
            with open(lic_file, "w", encoding="utf-8") as f:
                json.dump({"license_key": key_str}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def on_verify_key_clicked(self):
        user_key = self.entry_license_key.get().strip()
        if not user_key:
            self.license_status_label.configure(text="สถานะ: ❌ กรุณากรอก License Key", text_color="#e74c3c")
            return

        valid, msg, exp = check_license_online(user_key)
        if valid:
            self.save_saved_license(user_key)
            self.license_status_label.configure(text=f"สถานะ: {msg}", text_color="#2ecc71")
            print(f"[{time.strftime('%H:%M:%S')}] {msg}")
        else:
            self.license_status_label.configure(text=f"สถานะ: {msg}", text_color="#e74c3c")
            print(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def auto_check_saved_license(self):
        saved_key = self.load_saved_license()
        if saved_key:
            valid, msg, exp = check_license_online(saved_key)
            if valid:
                self.license_status_label.configure(text=f"สถานะ: {msg}", text_color="#2ecc71")
                print(f"[{time.strftime('%H:%M:%S')}] 🔒 [Auto Check] {msg}")
            else:
                self.license_status_label.configure(text=f"สถานะ: {msg}", text_color="#e74c3c")
                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ [Auto Check] {msg}")

    def start_bot(self):
        saved_key = self.load_saved_license()
        if not saved_key and hasattr(self, 'entry_license_key'):
            saved_key = self.entry_license_key.get().strip()

        valid, msg, exp = check_license_online(saved_key)
        if not valid:
            print(f"[{time.strftime('%H:%M:%S')}] ⛔ ไม่สามารถเริ่มรันบอทได้: {msg}")
            self.bot_status_label.configure(text="สถานะ: LICENSE ERROR", text_color="#e74c3c")
            return

        if not self.bot_active:
            self.bot_active = True
            self.current_state = self.STATE_WAIT_PLAYLOBBY if self.autostart_enabled else self.STATE_PLAYING
            self.last_action_time = time.time()
            self.bot_status_label.configure(text="สถานะ: กำลังทำงาน", text_color="#2ecc71")
            print(f"[{time.strftime('%H:%M:%S')}] ▶️ เริ่มทำงานบอท (START BOT)")

    def stop_bot(self):
        if self.bot_active:
            self.bot_active = False
            self.bot_status_label.configure(text="สถานะ: หยุดทำงาน", text_color="#e74c3c")
            print(f"[{time.strftime('%H:%M:%S')}] ⏸️ หยุดทำงานบอท (STOP BOT)")

    def on_profile_change(self, selected=None):
        if "Stage 1" in selected:
            self.buy_random_boost = True
            self.use_boost_start = False
            self.use_relay = True
            if hasattr(self, 'switch_buffs'): self.switch_buffs.select()
            if hasattr(self, 'switch_fast_start'): self.switch_fast_start.deselect()
            if hasattr(self, 'switch_relay'): self.switch_relay.select()
            self.trigger_dist = 140
            if hasattr(self, 'dist_slider'): self.dist_slider.set(140)
        elif "Stage 3" in selected:
            self.buy_random_boost = False
            self.use_boost_start = True
            self.use_relay = False
            if hasattr(self, 'switch_buffs'): self.switch_buffs.deselect()
            if hasattr(self, 'switch_fast_start'): self.switch_fast_start.select()
            if hasattr(self, 'switch_relay'): self.switch_relay.deselect()
            self.trigger_dist = 165
            if hasattr(self, 'dist_slider'): self.dist_slider.set(165)
        self.update_session_label()

    def on_toggle_yolo(self):
        val = self.switch_yolo.get() == 1
        self.auto_jump = val
        self.auto_slide = val
        status = "เปิดใช้งาน" if val else "ปิดใช้งาน"
        print(f"⚙️ YOLO AI Bot Toggled: {status}")

    def update_session_label(self):
        if self.rest_breaks_enabled:
            if self.current_state == self.STATE_RESTING:
                self.session_runs_label.configure(text=f"เซสชัน: {self.current_session_runs}/{self.target_session_runs} (กำลังพักผ่อน)")
            else:
                self.session_runs_label.configure(text=f"เซสชัน: {self.current_session_runs}/{self.target_session_runs} รอบ")
        else:
            self.session_runs_label.configure(text=f"รอบสะสม: {self.current_session_runs} รอบ (ไม่มีพักเบรก)")

    def on_toggle_rest(self):
        self.rest_breaks_enabled = self.switch_rest.get() == 1
        status = "เปิดใช้งาน" if self.rest_breaks_enabled else "ปิดใช้งาน"
        print(f"⚙️ Auto-Rest Breaks Toggled: {status}")
        self.update_session_label()

    def on_toggle_boost_start(self):
        self.use_boost_start = self.switch_fast_start.get() == 1
        status = "เปิดใช้งาน" if self.use_boost_start else "ปิดใช้งาน"
        print(f"⚙️ Boost Start Clicker Toggled: {status}")

    def on_toggle_buy_random_boost(self):
        self.buy_random_boost = self.switch_buffs.get() == 1
        status = "เปิดใช้งาน" if self.buy_random_boost else "ปิดใช้งาน"
        print(f"⚙️ Buy Random Boost Toggled: {status}")

    def on_toggle_relay(self):
        self.use_relay = self.switch_relay.get() == 1
        status = "เปิดใช้งาน" if self.use_relay else "ปิดใช้งาน"
        print(f"⚙️ Use Relay Toggled: {status}")

    def on_toggle_debug(self):
        val = self.switch_debug.get() == 1
        set_show_debug_logs(val)
        status = "เปิดใช้งาน" if val else "ปิดใช้งาน"
        print(f"⚙️ Debug Logs Toggled: {status}")

    def on_toggle_gui_logs(self):
        enabled = self.switch_gui_logs.get() == 1
        if hasattr(self, 'stdout_redirector'):
            self.stdout_redirector.enabled = enabled
        status = "เปิดใช้งาน" if enabled else "ปิดใช้งาน"
        if enabled:
            print(f"[{time.strftime('%H:%M:%S')}] 📋 แสดงผล GUI Logs: {status}")

    def on_session_limit_change(self, val):
        self.max_session_runs_limit = int(float(val))
        self.session_limit_title.configure(text=f"ขีดจำกัดรอบการเล่นสูงสุดต่อเซสชัน: {self.max_session_runs_limit} รอบ")

    def on_dist_change(self, val):
        self.trigger_dist = int(float(val))
        self.dist_title.configure(text=f"ระยะทางทริกเกอร์หลบสิ่งกีดขวาง: {self.trigger_dist} px")

    def on_slide_change(self, val):
        self.slide_hold_ms = int(float(val))
        self.slide_title.configure(text=f"เวลากดสไลด์ค้าง: {self.slide_hold_ms} ms")

    def on_conf_change(self, val):
        self.conf_val = float(val)
        self.conf_title.configure(text=f"ความเข้มงวด YOLO (Threshold): {int(self.conf_val * 100)}%")

    def process_scheduled_actions(self):
        if not self.hwnd:
            return
        now = time.time()
        remaining_actions = []
        self.scheduled_actions.sort(key=lambda x: x[0])
        for exec_time, vk_code, action in self.scheduled_actions:
            if now >= exec_time:
                try:
                    action()
                except Exception as e:
                    print(f"Error running scheduled action: {e}")
            else:
                remaining_actions.append((exec_time, vk_code, action))
        self.scheduled_actions = remaining_actions

    def schedule_next_loop(self, start_time):
        elapsed_ms = int((time.time() - start_time) * 1000)
        if self.eco_mode_enabled:
            delay = max(1, 50 - elapsed_ms)
        else:
            delay = max(12, 16 - elapsed_ms)
        self.after(delay, self.update_loop)

    def update_loop(self):
        try:
            self._update_loop_core()
        except Exception as e:
            print(f"❌ Exception in update_loop callback: {e}")
            traceback.print_exc()
            self.after(50, self.update_loop)

    def _update_loop_core(self):
        if not self.bot_active:
            self.bot_status_label.configure(text="สถานะ: หยุดทำงาน", text_color="#e74c3c")
            self.after(200, self.update_loop)
            return

        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            self.status_label.configure(text="ตัวจำลอง: ยังไม่เชื่อมต่อ", text_color="#e74c3c")
            self.bot_status_label.configure(text="สถานะ: OFFLINE", text_color="#e74c3c")
            self.refresh_mumu_windows()
            self.after(2000, self.update_loop)
            return

        self.status_label.configure(text="ตัวจำลอง: เชื่อมต่อแล้ว", text_color="#2ecc71")
        start_time = time.time()
        now = time.time()

        self.process_scheduled_actions()

        if self.current_state == self.STATE_RESTING:
            remaining = self.rest_end_time - now
            if remaining > 0:
                mins = int(remaining // 60)
                secs = int(remaining % 60)
                self.bot_status_label.configure(text=f"กำลังพัก ({mins:02d}:{secs:02d})", text_color="#f39c12")
                self.update_session_label()
                self.after(500, self.update_loop)
                return
            else:
                print(f"[{time.strftime('%H:%M:%S')}] ☀️ หมดเวลาพักผ่อนแล้ว! กำลังเริ่มเล่นเซสชันถัดไป...")
                self.current_session_runs = 0
                lower_limit = max(5, self.max_session_runs_limit - 3)
                self.target_session_runs = random.randint(lower_limit, self.max_session_runs_limit)
                self.current_state = self.STATE_WAIT_OK
                self.update_session_label()

        frame = capture_window_bg(self.hwnd)
        if frame is None:
            self.after(30, self.update_loop)
            return

        if self.autostart_enabled and self.current_state not in (self.STATE_PLAYING, self.STATE_RESTING, self.STATE_WAIT_LOADING):
            if self._watchdog_last_state != self.current_state:
                self._watchdog_last_state = self.current_state
                self._watchdog_state_since = now
            elif now - self._watchdog_state_since > 50.0:
                print(f"[{time.strftime('%H:%M:%S')}] 🛟 Watchdog: ค้างที่สเตท {self.current_state} นานเกิน 50 วินาที -> กดปิดสำรองและกู้คืนกลับ WAIT_PLAYLOBBY")
                try:
                    human_click_bg(self.hwnd, 607, 60, "Watchdog Recovery Close (X)")
                except Exception:
                    pass
                self.current_state = self.STATE_WAIT_PLAYLOBBY
                self.last_action_time = now
                self._watchdog_last_state = self.current_state
                self._watchdog_state_since = now
                self.schedule_next_loop(start_time)
                return

        if self.autostart_enabled:
            loading_grace = 9.0 if self.current_state == self.STATE_WAIT_LOADING else 6.0
            if (self.current_state == self.STATE_PLAYING or self.current_state == self.STATE_WAIT_LOADING) and (now - self.last_action_time > loading_grace):
                found_lobby_btn, rx, ry = find_template_match(self.hwnd, frame, self.autostart_templates.get("playlobby", None), threshold=0.72)
                is_lobby_match = found_lobby_btn and (580 <= rx <= 715) and (380 <= ry <= 420)
                if is_lobby_match:
                    if not hasattr(self, "_lobby_confirm_since") or self._lobby_confirm_since == 0:
                        self._lobby_confirm_since = now
                    elif now - self._lobby_confirm_since >= 2.5:
                        print(f"[{time.strftime('%H:%M:%S')}] 🔄 ตรวจพบปุ่มหน้าหลัก (Lobby) ต่อเนื่อง -> รีเซ็ตสเตทบอทเป็น WAIT_PLAYLOBBY")
                        self.current_state = self.STATE_WAIT_PLAYLOBBY
                        self.last_action_time = now
                        self._lobby_confirm_since = 0
                else:
                    self._lobby_confirm_since = 0

        if self.autostart_enabled and self.current_state != self.STATE_PLAYING:
            self.bot_status_label.configure(text=f"สถานะ: {self.current_state}", text_color="#f39c12")
            
            if "confirmlevelup" in self.autostart_templates:
                found_lv, cx_lv, cy_lv = find_template_match(self.hwnd, frame, self.autostart_templates["confirmlevelup"])
                if found_lv:
                    print(f"[{time.strftime('%H:%M:%S')}] ⭐ ตรวจพบป๊อปอัป Level Up! ทำการคลิกปิดเพื่อไปต่อ...")
                    human_click_bg(self.hwnd, cx_lv, cy_lv, "Level Up Close Button")
                    self.after(int(random.uniform(2000, 3500)), self.update_loop)
                    return

            if self.current_state == self.STATE_WAIT_OK:
                found_openall, cx_o, cy_o = find_template_match(self.hwnd, frame, self.autostart_templates.get("openall", None), threshold=0.48)
                found_confirm, cx_c, cy_c = find_template_match(self.hwnd, frame, self.autostart_templates.get("confirmafteropenall", None), threshold=0.48)
                found_lobby, rx, ry = find_template_match(self.hwnd, frame, self.autostart_templates.get("playlobby", None), threshold=0.56)
                
                if found_openall:
                    print(f"[{time.strftime('%H:%M:%S')}] 🎁 ตรวจพบกล่องสมบัติ (Open All)! -> สลับไปสเตทเปิดกล่อง")
                    self.current_state = self.STATE_WAIT_OPENALL
                    self.last_action_time = now
                elif found_confirm:
                    print(f"[{time.strftime('%H:%M:%S')}] 🎁 ตรวจพบปุ่มยืนยันหลังเปิดกล่อง -> สลับไปสเตทยืนยัน")
                    self.current_state = self.STATE_WAIT_CONFIRM_OPENALL
                    self.last_action_time = now
                elif found_lobby and (560 <= rx <= 720) and (360 <= ry <= 430):
                    wait_sec = random.uniform(15.0, 20.0)
                    print(f"[{time.strftime('%H:%M:%S')}] 🏠 ตรวจพบหน้าหลัก (ไม่มีกล่องสมบัติให้เปิด) -> พักรอ {wait_sec:.0f} วินาทีก่อนเริ่มรอบถัดไป...")
                    self.lobby_cooldown_end = now + wait_sec
                    self.current_state = self.STATE_WAIT_PLAYLOBBY
                    self.last_action_time = now
                else:
                    clicks = getattr(self, "ok_clicks", 0)
                    if clicks < 2 and (now - self.last_action_time > 1.2):
                        human_click_bg(self.hwnd, 285, 386, "OK Confirm Button")
                        self.ok_clicks = clicks + 1
                        self.last_action_time = now
                    elif now - self.last_action_time > 2.5:
                        wait_sec = random.uniform(15.0, 20.0)
                        print(f"[{time.strftime('%H:%M:%S')}] 🏠 ปิดหน้าคะแนนเรียบร้อย -> พักรอ {wait_sec:.0f} วินาทีก่อนเริ่มรอบถัดไป...")
                        self.lobby_cooldown_end = now + wait_sec
                        self.current_state = self.STATE_WAIT_PLAYLOBBY
                        self.last_action_time = now

            elif self.current_state == self.STATE_WAIT_OPENALL:
                found_openall, cx, cy = find_template_match(self.hwnd, frame, self.autostart_templates.get("openall", None), threshold=0.48)
                found_lobby, rx, ry = find_template_match(self.hwnd, frame, self.autostart_templates.get("playlobby", None), threshold=0.56)
                if found_openall:
                    human_click_bg(self.hwnd, cx, cy, "Open All Chests Button")
                    self.last_action_time = now
                    self.confirm_openall_clicks = 0
                    self.current_state = self.STATE_WAIT_CONFIRM_OPENALL
                elif (found_lobby and (560 <= rx <= 720) and (360 <= ry <= 430)) or (now - self.last_action_time > 2.5):
                    wait_sec = random.uniform(15.0, 20.0)
                    print(f"[{time.strftime('%H:%M:%S')}] 🏠 ไม่พบปุ่มเปิดกล่อง (ข้ามไปหน้าหลัก) -> พักรอ {wait_sec:.0f} วินาทีก่อนเริ่มรอบถัดไป...")
                    self.lobby_cooldown_end = now + wait_sec
                    self.current_state = self.STATE_WAIT_PLAYLOBBY
                    self.last_action_time = now

            elif self.current_state == self.STATE_WAIT_CONFIRM_OPENALL:
                found_confirm, cx, cy = find_template_match(self.hwnd, frame, self.autostart_templates.get("confirmafteropenall", None), threshold=0.48)
                found_lobby, rx, ry = find_template_match(self.hwnd, frame, self.autostart_templates.get("playlobby", None), threshold=0.56)
                
                confirm_clicks = getattr(self, "confirm_openall_clicks", 0)
                
                if found_confirm and (now - self.last_action_time > 0.8):
                    click_num = confirm_clicks + 1
                    print(f"[{time.strftime('%H:%M:%S')}] 🎁 ยืนยันหลังเปิดกล่อง (รอบที่ {click_num}) -> คลิกพิกัด ({cx}, {cy})")
                    human_click_bg(self.hwnd, cx, cy, f"Confirm After Open All Button ({click_num})")
                    self.last_action_time = now
                    self.confirm_openall_clicks = click_num
                    if click_num >= 2:
                        wait_sec = random.uniform(15.0, 20.0)
                        print(f"[{time.strftime('%H:%M:%S')}] 🏠 ยืนยันเปิดกล่องครบเรียบร้อย -> พักรอ {wait_sec:.0f} วินาทีก่อนเริ่มรอบถัดไป...")
                        self.lobby_cooldown_end = now + wait_sec
                        self.current_state = self.STATE_WAIT_PLAYLOBBY
                elif confirm_clicks >= 1 and (now - self.last_action_time > 1.2) and not found_lobby:
                    wait_sec = random.uniform(15.0, 20.0)
                    print(f"[{time.strftime('%H:%M:%S')}] 🎁 ยืนยันหลังเปิดกล่อง (รอบที่ 2 สำรอง) -> พักรอ {wait_sec:.0f} วินาทีก่อนเริ่มรอบถัดไป...")
                    human_click_bg(self.hwnd, 400, 400, "Confirm After Open All Button (2nd Fallback)")
                    self.last_action_time = now
                    self.confirm_openall_clicks = 2
                    self.lobby_cooldown_end = now + wait_sec
                    self.current_state = self.STATE_WAIT_PLAYLOBBY
                elif (found_lobby and (560 <= rx <= 720) and (360 <= ry <= 430)) or (now - self.last_action_time > 3.5):
                    wait_sec = random.uniform(15.0, 20.0)
                    print(f"[{time.strftime('%H:%M:%S')}] 🏠 ยืนยันเปิดกล่องครบเรียบร้อย -> พักรอ {wait_sec:.0f} วินาทีก่อนเริ่มรอบถัดไป...")
                    self.lobby_cooldown_end = now + wait_sec
                    self.current_state = self.STATE_WAIT_PLAYLOBBY
                    self.last_action_time = now

            elif self.current_state == self.STATE_WAIT_PLAYLOBBY:
                cooldown_end = getattr(self, "lobby_cooldown_end", 0)
                if now < cooldown_end:
                    remaining_sec = int(cooldown_end - now)
                    self.bot_status_label.configure(text=f"สถานะ: พักในหน้าหลัก ({remaining_sec}s)", text_color="#f39c12")
                    self.schedule_next_loop(start_time)
                    return

                found_match = False
                cx, cy = 647, 400
                if "playlobby" in self.autostart_templates:
                    found, tx, ty = find_template_match(self.hwnd, frame, self.autostart_templates["playlobby"], threshold=0.50)
                    if found and (560 <= tx <= 720) and (360 <= ty <= 430):
                        found_match = True
                        cx, cy = tx, ty

                if found_match and (now - self.last_action_time > 1.0):
                    print(f"[{time.strftime('%H:%M:%S')}] 🖱️ ตรวจพบปุ่ม Play หน้าหลัก -> คลิกปุ่ม Play ล็อบบี้ พิกัด ({cx}, {cy})")
                    human_click_bg(self.hwnd, cx, cy, "Play Lobby Button")
                    self.last_action_time = now
                    if self.buy_random_boost:
                        self.current_state = self.STATE_WAIT_SELECTBUFF_1
                    else:
                        self.current_state = self.STATE_WAIT_START
                        self.last_action_time = now
                elif not found_match and (now - self.last_action_time > 6.0):
                    print(f"[{time.strftime('%H:%M:%S')}] 🖱️ ไม่พบปุ่ม Play หน้าหลักเกิน 6 วินาที -> คลิกปุ่ม Fallback พิกัด ({cx}, {cy})")
                    human_click_bg(self.hwnd, cx, cy, "Play Lobby Button (Fallback)")
                    self.last_action_time = now
                    if self.buy_random_boost:
                        self.current_state = self.STATE_WAIT_SELECTBUFF_1
                    else:
                        self.current_state = self.STATE_WAIT_START
                        self.last_action_time = now

            elif self.current_state == self.STATE_WAIT_SELECTBUFF_1:
                if not self.buy_random_boost:
                    self.current_state = self.STATE_WAIT_START
                    self.schedule_next_loop(start_time)
                    return
                found = False
                cx, cy = 335, 375
                if "selectbuff_1" in self.autostart_templates:
                    found, tx, ty = find_template_match(self.hwnd, frame, self.autostart_templates["selectbuff_1"], threshold=0.55)
                    if found: cx, cy = tx, ty
                
                if found or (now - self.last_action_time > 2.5):
                    if now - self.last_action_time > 0.8:
                        human_click_bg(self.hwnd, cx, cy, "Select Random Boost Slot")
                        self.last_action_time = now
                        self.current_state = self.STATE_WAIT_SELECTBUFF_2

            elif self.current_state == self.STATE_WAIT_SELECTBUFF_2:
                found = False
                cx, cy = 666, 123
                if "selectbuff_2" in self.autostart_templates:
                    found, tx, ty = find_template_match(self.hwnd, frame, self.autostart_templates["selectbuff_2"], threshold=0.55)
                    if found: cx, cy = tx, ty
                
                if found or (now - self.last_action_time > 2.0):
                    if now - self.last_action_time > 0.8:
                        human_click_bg(self.hwnd, cx, cy, "Multi Random Boost Button")
                        self.last_action_time = now
                        self.current_state = self.STATE_WAIT_SELECTBUFF_3

            elif self.current_state == self.STATE_WAIT_SELECTBUFF_3:
                found = False
                cx, cy = 397, 367
                if "selectbuff_3" in self.autostart_templates:
                    found, tx, ty = find_template_match(self.hwnd, frame, self.autostart_templates["selectbuff_3"], threshold=0.55)
                    if found: cx, cy = tx, ty
                
                if found or (now - self.last_action_time > 2.0):
                    if now - self.last_action_time > 0.8:
                        human_click_bg(self.hwnd, cx, cy, "Multi-Buy Button")
                        self.last_action_time = now
                        if self.buff_spin_start_time == 0:
                            self.buff_spin_start_time = now
                        self.current_state = self.STATE_WAIT_BUFF_RESULT
                        self._last_logged_ocr = ""
                        self._ocr_scanned_this_result = False
                        self._prev_buff_roi = None

            elif self.current_state == self.STATE_WAIT_BUFF_RESULT:
                if now - self.last_action_time >= 1.0:
                    roi_buff_area = frame[100:380, 200:600]
                    is_moving = True
                    if hasattr(self, "_prev_buff_roi") and self._prev_buff_roi is not None:
                        if self._prev_buff_roi.shape == roi_buff_area.shape:
                            diff = cv2.absdiff(cv2.cvtColor(roi_buff_area, cv2.COLOR_BGR2GRAY), cv2.cvtColor(self._prev_buff_roi, cv2.COLOR_BGR2GRAY))
                            if np.mean(diff) < 2.0:
                                is_moving = False
                    self._prev_buff_roi = roi_buff_area.copy()

                    if is_moving:
                        self.schedule_next_loop(start_time)
                        return

                    if not getattr(self, "_ocr_scanned_this_result", False):
                        self._ocr_scanned_this_result = True
                        roi_big = cv2.resize(roi_buff_area, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
                        self.trigger_async_ocr(roi_big)

                    found_acceptable_buff = False
                    matched_buff_name = ""

                    ocr_text = getattr(self, "_async_ocr_text", "")
                    self._last_ocr_text = ocr_text

                    txt_lower = ocr_text.lower()
                    if any(k in txt_lower for k in ["tap multi-buy", "keep spending", "firstbuy", "repeatbuy"]):
                        ocr_text = ""
                        txt_lower = ""

                    if ocr_text and ocr_text != getattr(self, "_last_logged_ocr", ""):
                        self._last_logged_ocr = ocr_text
                        print(f"[{time.strftime('%H:%M:%S')}] 🎲 ผลการอ่านบัฟ: '{ocr_text}'")

                    if not ocr_text and (now - self.last_action_time < 3.0):
                        self.schedule_next_loop(start_time)
                        return

                    if self.buy_double_coin and ("doubl" in txt_lower or "double" in txt_lower) and "gold" not in txt_lower:
                        found_acceptable_buff = True
                        matched_buff_name = "Double Coins (เหรียญ 2 เท่า)"
                    elif self.buy_hp_drain and "drain" in txt_lower:
                        found_acceptable_buff = True
                        matched_buff_name = "-15% HP Drain"
                    elif self.buy_crush_chance and ("crush" in txt_lower or "70%" in txt_lower or "70" in txt_lower):
                        found_acceptable_buff = True
                        matched_buff_name = "70% Crush Chance"
                    elif self.buy_gold_coin_magic and ("gold" in txt_lower or "magic" in txt_lower):
                        found_acceptable_buff = True
                        matched_buff_name = "Gold Coin Magic"
                    elif self.buy_hp_potions and ("potion" in txt_lower or "+20%" in txt_lower or "20%" in txt_lower):
                        found_acceptable_buff = True
                        matched_buff_name = "+20% HP Potions"
                    elif self.buy_pit_lifts and ("pit" in txt_lower or "lift" in txt_lower):
                        found_acceptable_buff = True
                        matched_buff_name = "2 Pit Lifts"
                    elif self.buy_score_bonus and ("score" in txt_lower or "bonus" in txt_lower):
                        found_acceptable_buff = True
                        matched_buff_name = "+15% Score Bonus"
                    elif self.buy_revive and ("reviv" in txt_lower or "80" in txt_lower):
                        found_acceptable_buff = True
                        matched_buff_name = "Revive once (คืนชีพ)"
                    elif self.buy_base_speed and ("speed" in txt_lower or "+17%" in txt_lower or "17%" in txt_lower or "17" in txt_lower):
                        found_acceptable_buff = True
                        matched_buff_name = "+17% Base Speed"
                    elif self.buy_collision_damage and ("collis" in txt_lower or "damage" in txt_lower or "-30%" in txt_lower or "30%" in txt_lower):
                        found_acceptable_buff = True
                        matched_buff_name = "-30% Collision Damage"
                    elif self.buy_magnetic_aura and ("magnet" in txt_lower or "aura" in txt_lower):
                        found_acceptable_buff = True
                        matched_buff_name = "Magnetic Aura (แม่เหล็ก)"

                    if found_acceptable_buff:
                        print(f"[{time.strftime('%H:%M:%S')}] 🔍 RapidOCR อ่านป้ายบัฟได้: '{ocr_text}' -> ตรงกับ {matched_buff_name}!")
                        print(f"[{time.strftime('%H:%M:%S')}] 🌟 เจอบัฟเป้าหมายแล้ว! รอ 1.5 วินาทีแล้วกดเริ่มเล่น...")
                        time.sleep(1.5)
                        human_click_bg(self.hwnd, 610, 400, "Play Buff Button")
                        self.last_action_time = now
                        self.buff_spin_start_time = 0
                        self._async_ocr_text = ""
                        self._ocr_scanned_this_result = False
                        self.current_state = self.STATE_WAIT_LOADING
                        self.loading_start_time = now
                        self.schedule_next_loop(start_time)
                        return
                    else:
                        self._ocr_scanned_this_result = False
                        self.schedule_next_loop(start_time)
                        return

            elif self.current_state == self.STATE_WAIT_START:
                if now - self.last_action_time >= 2.0:
                    found_start = False
                    cx_s, cy_s = 670, 390
                    if "playlobby" in self.autostart_templates:
                        found, tx, ty = find_template_match(self.hwnd, frame, self.autostart_templates["playlobby"], threshold=0.48)
                        if found and (600 <= tx <= 740) and (350 <= ty <= 430):
                            found_start = True
                            cx_s, cy_s = tx, ty
                    
                    name = "Start Game Button" if found_start else "Start Game Button (Fixed Pos)"
                    print(f"[{time.strftime('%H:%M:%S')}] 🎮 คลิกปุ่มเริ่มวิ่งเตรียมเข้าเกมด้วยพิกัด: ({cx_s}, {cy_s}) [{name}]")
                    human_click_bg(self.hwnd, cx_s, cy_s, name)
                    self.current_session_runs += 1
                    self.update_session_label()
                    self.current_state = self.STATE_WAIT_LOADING
                    self.loading_start_time = now
                    self.last_action_time = now

            elif self.current_state == self.STATE_WAIT_LOADING:
                if now - self.loading_start_time > 4.0:
                    print(f"[{time.strftime('%H:%M:%S')}] 🎮 โหลดเข้าเกมเรียบร้อย! เปลี่ยนสถานะเป็น PLAYING (กำลังวิ่ง)...")
                    self.current_state = self.STATE_PLAYING
                    self.last_action_time = now
            self.schedule_next_loop(start_time)
            return

        # NORMAL GAMEPLAY: YOLO Run Controls
        self.bot_status_label.configure(text="สถานะ: กำลังทำงาน", text_color="#2ecc71")
        self.update_session_label()
        
        if self.autostart_enabled and self.current_state == self.STATE_PLAYING:
            if now - self.last_endgame_check_time > 0.4:
                self.last_endgame_check_time = now
                found_ok = False
                cx_ok, cy_ok = 285, 386
                if "ok" in self.autostart_templates:
                    f_ok, tx_ok, ty_ok = find_template_match(self.hwnd, frame, self.autostart_templates["ok"], threshold=0.48)
                    if f_ok and (220 <= tx_ok <= 350) and (340 <= ty_ok <= 430):
                        found_ok = True
                        cx_ok, cy_ok = tx_ok, ty_ok

                if found_ok:
                    if self.rest_breaks_enabled and self.current_session_runs >= self.target_session_runs:
                        self.current_state = self.STATE_RESTING
                        rest_duration = random.uniform(480, 1080)
                        self.rest_end_time = time.time() + rest_duration
                        print(f"[{time.strftime('%H:%M:%S')}] 💤 ครบเซสชันการเล่น -> พักเบรก {rest_duration/60:.1f} นาที")
                        self.update_session_label()
                        self.schedule_next_loop(start_time)
                        return
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] 🏁 วิ่งจบเกม (ตรวจพบปุ่ม OK)! -> คลิกตกลงปิดหน้าผลคะแนน...")
                        human_click_bg(self.hwnd, cx_ok, cy_ok, "OK Confirm Button")
                        self.current_state = self.STATE_WAIT_OK
                        self.last_action_time = now
                        self.ok_clicks = 1
                        self.schedule_next_loop(start_time)
                        return

        # Check character switch player template (ผลัดสอง)
        if self.current_state == self.STATE_PLAYING and (now - self.last_action_time > 10.0) and self.use_relay and getattr(self, "relay_templates", None):
            if now - self.last_switch_check_time > 0.4:
                self.last_switch_check_time = now
                found_relay, rx, ry, rscore, rname = find_best_template_match(self.hwnd, frame, self.relay_templates, threshold=0.52)
                if found_relay:
                    print(f"[{time.strftime('%H:%M:%S')}] 🔍 ตรวจพบปุ่มผลัดสอง! ('{rname}') -> กดเปลี่ยนตัวผลัดสอง!")
                    human_press_bg(self.hwnd, VK_ALT, SCAN_ALT, duration_min=0.08, duration_max=0.15)
                    self.last_action_time = now

        # YOLO AI Detection Engine (Ported from Main Project: TTC Speed Estimation, Cliff Radar, Double Jump)
        if self.model is not None and (self.auto_jump or self.auto_slide):
            is_pt = str(getattr(self.model, "ckpt_path", "")).endswith(".pt") or str(getattr(self.model, "model_name", "")).endswith(".pt")
            dev = getattr(self, "device_str", "cpu") if is_pt else "cpu"
            results = self.model(frame, conf=self.conf_val, device=dev, verbose=False)
            
            cookie_box = None
            detected_objects = []

            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    score = box.conf[0].cpu().numpy()
                    cls = int(box.cls[0].cpu().numpy())
                    class_name = self.model.names[cls].lower()

                    detected_objects.append((int(x1), int(y1), int(x2), int(y2), class_name, score))
                    if class_name == "cookie":
                        cookie_box = (int(x1), int(y1), int(x2), int(y2))

            fallback_x = getattr(self, "FALLBACK_COOKIE_X", 220)
            if not hasattr(self, "smoothed_cookie_x"):
                self.smoothed_cookie_x = fallback_x

            if cookie_box is not None:
                self.smoothed_cookie_x = self.smoothed_cookie_x * 0.8 + cookie_box[2] * 0.2
            else:
                self.smoothed_cookie_x = self.smoothed_cookie_x * 0.95 + fallback_x * 0.05

            cookie_front_x = self.smoothed_cookie_x

            # Distance & obstacle sorting
            jump_obstacles = []
            slide_obstacles = []
            closest_obstacle_info = None
            closest_obstacle_distance = 9999

            for x1, y1, x2, y2, c_name, conf in detected_objects:
                if x1 > cookie_front_x:
                    distance = x1 - cookie_front_x
                    if distance < 400:
                        if c_name in ["jump_obs", "jump_potato", "double_jump_obs", "raised_floor", "coin"]:
                            jump_obstacles.append((int(x1), int(x2), int(y1), int(y2), c_name, distance))
                        elif c_name == "slide_obs":
                            slide_obstacles.append((int(x1), int(x2), int(y1), int(y2), c_name, distance))
                        
                        if distance < closest_obstacle_distance:
                            closest_obstacle_distance = distance
                            closest_obstacle_info = (int(x1), int(y1), int(x2), int(y2), c_name, distance)

            jump_obstacles.sort(key=lambda o: o[5])
            slide_obstacles.sort(key=lambda o: o[5])

            if not hasattr(self, "estimated_speed"):
                self.estimated_speed = 350.0

            # Dynamic speed tracking
            if closest_obstacle_info is not None:
                obs_x1, obs_y1, obs_x2, obs_y2, obs_name, dist = closest_obstacle_info
                
                if not hasattr(self, "last_closest_dist"):
                    self.last_closest_dist = 0
                    self.current_jitter = 0.0
                    self.last_obstacle_x = None
                    self.last_obstacle_time = None

                if self.last_closest_dist == 0 or dist > self.last_closest_dist + 50:
                    self.current_jitter = random.uniform(-0.04, 0.04)
                self.last_closest_dist = dist
                
                if getattr(self, "last_obstacle_x", None) is not None and getattr(self, "last_obstacle_time", None) is not None:
                    dt = now - self.last_obstacle_time
                    dx = self.last_obstacle_x - obs_x1
                    if 0.015 < dt < 0.200 and 0 < dx < 200:
                        measured_speed = dx / dt
                        self.estimated_speed = self.estimated_speed * 0.85 + measured_speed * 0.15
                        self.estimated_speed = max(150.0, min(self.estimated_speed, 900.0))
                
                self.last_obstacle_x = obs_x1
                self.last_obstacle_time = now
            else:
                self.last_obstacle_x = None
                self.last_obstacle_time = None
                self.last_closest_dist = 0
                self.current_jitter = 0.0

            # Time-To-Collision (TTC) Calculation
            trigger_ttc = (self.trigger_dist / max(self.estimated_speed, 1.0)) + getattr(self, "current_jitter", 0.0)
            trigger_ttc = max(0.12, min(trigger_ttc, 0.80))

            found_jump_obstacle = False
            found_double_jump_obstacle = False
            found_slide_obstacle = False

            if closest_obstacle_info is not None:
                obs_x1, obs_y1, obs_x2, obs_y2, obs_name, dist = closest_obstacle_info
                obs_ttc = dist / max(self.estimated_speed, 1.0)

                if obs_ttc <= trigger_ttc:
                    if obs_name in ["jump_obs", "jump_potato", "double_jump_obs", "raised_floor", "coin"]:
                        is_double_jump = False
                        if obs_name == "double_jump_obs":
                            is_double_jump = True
                        elif len(jump_obstacles) >= 2:
                            first_obs = jump_obstacles[0]
                            second_obs = jump_obstacles[1]
                            gap_px = second_obs[0] - first_obs[1]
                            gap_time = gap_px / max(self.estimated_speed, 1.0)
                            if gap_time < 0.35:
                                is_double_jump = True
                                
                        if is_double_jump:
                            found_double_jump_obstacle = True
                        else:
                            found_jump_obstacle = True
                            
                    elif obs_name == "slide_obs":
                        found_slide_obstacle = True

            # Cliff detection radar
            ground_boxes = [(x1, x2, y1, y2) for x1, y1, x2, y2, c_name, conf in detected_objects if c_name == "ground"]
            for x1, x2, y1, y2 in ground_boxes:
                if x1 <= 220 and x2 >= 180:
                    dist_to_cliff = x2 - 220
                    cliff_ttc = dist_to_cliff / max(self.estimated_speed, 1.0)
                    if 0.03 < cliff_ttc <= 0.45:
                        has_continuation = any(0 <= (nx1 - x2) < 45 for nx1, nx2, ny1, ny2 in ground_boxes)
                        if not has_continuation:
                            has_continuation = any(0 <= (rx1 - x2) < 45 for rx1, ry1, rx2, ry2, rc_name, rconf in detected_objects if rc_name == "raised_floor")
                        if not has_continuation:
                            found_jump_obstacle = True
                            break

            # Execute Actions
            if found_double_jump_obstacle and (now - self.last_jump_time > 0.48):
                print(f"[{time.strftime('%H:%M:%S')}] 🦘 [AI Smart Engine] ดับเบิ้ลจัมพ์ (Speed: {self.estimated_speed:.0f} px/s, TTC: {trigger_ttc:.3f}s)")
                human_press_bg(self.hwnd, VK_LSHIFT, SCAN_SHIFT, duration_min=0.05, duration_max=0.08)
                self.after(170, lambda: human_press_bg(self.hwnd, VK_LSHIFT, SCAN_SHIFT, duration_min=0.05, duration_max=0.08))
                self.last_jump_time = now
            elif found_jump_obstacle and (now - self.last_jump_time > 0.35):
                print(f"[{time.strftime('%H:%M:%S')}] 🦘 [AI Smart Engine] กระโดด (Speed: {self.estimated_speed:.0f} px/s, TTC: {trigger_ttc:.3f}s)")
                human_press_bg(self.hwnd, VK_LSHIFT, SCAN_SHIFT, duration_min=0.06, duration_max=0.10)
                self.last_jump_time = now
            elif found_slide_obstacle and (now - self.last_slide_time > 0.32):
                print(f"[{time.strftime('%H:%M:%S')}] 🛹 [AI Smart Engine] สไลด์ (Speed: {self.estimated_speed:.0f} px/s, TTC: {trigger_ttc:.3f}s)")
                human_press_bg(self.hwnd, VK_SPACE, SCAN_SPACE, duration_min=self.slide_hold_ms / 1000.0, duration_max=(self.slide_hold_ms + 100) / 1000.0)
                self.last_slide_time = now

        self.schedule_next_loop(start_time)
