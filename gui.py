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
        
        self.title("CR-BOT AI ⚡ v2.5 PRO")
        self.geometry("710x570")
        self.resizable(False, False)
        self.configure(fg_color="#0f1219")
        
        self.init_resources()
        self.create_layout()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(100, self.update_loop)

    def on_closing(self):
        self.bot_active = False
        self.destroy()

    def clear_logs(self):
        if hasattr(self, 'log_textbox'):
            self.log_textbox.configure(state="normal")
            self.log_textbox.delete("1.0", "end")
            self.log_textbox.configure(state="disabled")

    def open_buff_config_window(self):
        if hasattr(self, 'buff_win') and self.buff_win is not None and self.buff_win.winfo_exists():
            self.buff_win.focus()
            return
        
        self.buff_win = ctk.CTkToplevel(self)
        self.buff_win.title("🎯 ตั้งค่าบัฟเป้าหมาย (RapidOCR)")
        self.buff_win.geometry("490x480")
        self.buff_win.resizable(False, False)
        self.buff_win.configure(fg_color="#0f1219")
        self.buff_win.attributes("-topmost", True)

        lbl_title = ctk.CTkLabel(self.buff_win, text="🎯 เลือกบัฟเป้าหมายหลัก", font=("Arial", 14, "bold"), text_color="#818cf8")
        lbl_title.pack(pady=(12, 2))

        lbl_desc = ctk.CTkLabel(self.buff_win, text="คลิกเลือกบัฟที่ต้องการ 1 ชนิด (บอทจะสุ่มหาจนกว่าจะเจอบัฟนี้)", font=("Arial", 10), text_color="#94a3b8")
        lbl_desc.pack(pady=(0, 8))

        frame_grid = ctk.CTkFrame(self.buff_win, fg_color="#181c26", corner_radius=10, border_width=1, border_color="#262b3a")
        frame_grid.pack(fill="both", expand=True, padx=14, pady=(0, 8))

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

        lbl_status = ctk.CTkLabel(self.buff_win, text="", font=("Arial", 11, "bold"), text_color="#34d399")
        lbl_status.pack(pady=(2, 8))

        btn_dict = {}

        def select_buff(target_vn, target_text):
            for _, vn, _, _ in buff_items:
                setattr(self, vn, (vn == target_vn))
            print(f"⚙️ เปลี่ยนบัฟเป้าหมายหลักเป็น: '{target_vn}'")
            lbl_status.configure(text=f"✅ เลือก: {target_text}")

            for vn, btn in btn_dict.items():
                if vn == target_vn:
                    btn.configure(fg_color="#4f46e5", hover_color="#4338ca", text_color="#ffffff", border_width=1, border_color="#818cf8")
                else:
                    btn.configure(fg_color="#202534", hover_color="#2a3144", text_color="#cbd5e1", border_width=0)

        frame_grid.columnconfigure(0, weight=1)
        frame_grid.columnconfigure(1, weight=1)

        for text, var_name, row, col in buff_items:
            def make_handler(vn=var_name, txt=text):
                return lambda: select_buff(vn, txt)

            btn = ctk.CTkButton(
                frame_grid, text=text, font=("Arial", 10, "bold"), height=36, corner_radius=6, command=make_handler(var_name, text)
            )
            btn.grid(row=row, column=col, padx=6, pady=4, sticky="ew")
            btn_dict[var_name] = btn

        initial_text = next((t for t, vn, _, _ in buff_items if vn == current_selected), "Coins x2")
        select_buff(current_selected, initial_text)

    def create_layout(self):
        # ----------------- Top Header Bar -----------------
        header_frame = ctk.CTkFrame(self, fg_color="#181c26", corner_radius=10, height=48, border_width=1, border_color="#262b3a")
        header_frame.pack(fill="x", padx=10, pady=(8, 6))
        header_frame.pack_propagate(False)

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=12, pady=6)

        lbl_app_logo = ctk.CTkLabel(title_box, text="🍪 CR-BOT AI", font=("Arial", 14, "bold"), text_color="#f8fafc")
        lbl_app_logo.pack(side="left", padx=(0, 6))

        lbl_ver = ctk.CTkLabel(title_box, text="v2.5 PRO", font=("Arial", 10, "bold"), text_color="#94a3b8")
        lbl_ver.pack(side="left", padx=(0, 6))

        lbl_badge = ctk.CTkLabel(
            title_box, text="PRO", font=("Arial", 9, "bold"),
            fg_color="#4f46e5", text_color="#ffffff", corner_radius=4, padx=5, pady=1
        )
        lbl_badge.pack(side="left")

        # Top Live Status Indicator
        self.bot_status_label = ctk.CTkLabel(
            header_frame, text="● IDLE (หยุดทำงาน)", font=("Arial", 11, "bold"),
            text_color="#34d399"
        )
        self.bot_status_label.pack(side="right", padx=14, pady=8)

        # ----------------- Main Workspace (Sidebar + Content) -----------------
        workspace = ctk.CTkFrame(self, fg_color="transparent")
        workspace.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        # Left Sidebar Navigation
        self.sidebar_frame = ctk.CTkFrame(workspace, fg_color="#181c26", width=140, corner_radius=10, border_width=1, border_color="#262b3a")
        self.sidebar_frame.pack(side="left", fill="y", padx=(0, 6), pady=0)
        self.sidebar_frame.pack_propagate(False)

        self.sidebar_buttons = {}
        nav_items = [
            ("trainer", "🤖 AI Trainer"),
            ("autoclaim", "🎁 รับรางวัล"),
            ("settings", "⚙️ ตั้งค่า"),
            ("license", "🔑 License"),
        ]

        for view_key, label_text in nav_items:
            btn = ctk.CTkButton(
                self.sidebar_frame, text=label_text, font=("Arial", 11, "bold"), height=38, corner_radius=8,
                fg_color="transparent", text_color="#94a3b8", hover_color="#222736", anchor="w",
                command=lambda k=view_key: self.switch_view(k)
            )
            btn.pack(fill="x", padx=6, pady=4)
            self.sidebar_buttons[view_key] = btn

        # Right Content Container
        self.content_container = ctk.CTkFrame(workspace, fg_color="transparent")
        self.content_container.pack(side="right", fill="both", expand=True)

        self.views = {}
        self.views["trainer"] = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.views["autoclaim"] = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.views["settings"] = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.views["license"] = ctk.CTkFrame(self.content_container, fg_color="transparent")

        self.setup_trainer_view()
        self.setup_autoclaim_view()
        self.setup_settings_view()
        self.setup_license_view()

        self.switch_view("trainer")

    def switch_view(self, target_key):
        for key, view in self.views.items():
            if key == target_key:
                view.pack(fill="both", expand=True)
            else:
                view.pack_forget()

        for key, btn in self.sidebar_buttons.items():
            if key == target_key:
                btn.configure(fg_color="#2b3247", text_color="#818cf8")
            else:
                btn.configure(fg_color="transparent", text_color="#94a3b8")

    def setup_trainer_view(self):
        parent = self.views["trainer"]

        # 1. Top Emulator Connection Bar
        emu_bar = ctk.CTkFrame(parent, fg_color="#181c26", corner_radius=10, border_width=1, border_color="#262b3a", height=44)
        emu_bar.pack(fill="x", pady=(0, 6))
        emu_bar.pack_propagate(False)

        init_options = list(self.mumu_windows.keys()) if hasattr(self, 'mumu_windows') and self.mumu_windows else ["ไม่พบหน้าต่าง MuMu Player"]
        self.window_option_menu = ctk.CTkOptionMenu(
            emu_bar, values=init_options, command=self.on_select_mumu_window,
            width=260, height=30, fg_color="#202534", button_color="#2e3549", button_hover_color="#4f46e5",
            text_color="#f8fafc", dropdown_text_color="#f8fafc", font=("Arial", 10, "bold"),
            dropdown_fg_color="#181c26"
        )
        self.window_option_menu.pack(side="left", padx=(8, 4), pady=6, fill="x", expand=True)
        if init_options and init_options[0] != "ไม่พบหน้าต่าง MuMu Player":
            self.window_option_menu.set(init_options[0])

        btn_refresh_win = ctk.CTkButton(
            emu_bar, text="🔄 เชื่อมต่อ", width=80, height=30, fg_color="#202534", hover_color="#4f46e5",
            text_color="#818cf8", font=("Arial", 10, "bold"), corner_radius=6, command=self.refresh_mumu_windows
        )
        btn_refresh_win.pack(side="left", padx=3)

        self.btn_grid_capture = ctk.CTkButton(
            emu_bar, text="📸 Grid", width=62, height=30, fg_color="#202534", hover_color="#38bdf8",
            text_color="#38bdf8", font=("Arial", 10, "bold"), corner_radius=6, command=self.capture_and_show_grid_overlay
        )
        self.btn_grid_capture.pack(side="left", padx=3)

        self.btn_hide_mumu = ctk.CTkButton(
            emu_bar, text="🙈", width=34, height=30, fg_color="#202534", hover_color="#f59e0b",
            text_color="#cbd5e1", font=("Arial", 10, "bold"), corner_radius=6, command=self.toggle_hide_mumu_window
        )
        self.btn_hide_mumu.pack(side="left", padx=(3, 8))

        # 2. Card: Auto Trainer Controls
        toggles_card = ctk.CTkFrame(parent, fg_color="#181c26", corner_radius=10, border_width=1, border_color="#262b3a")
        toggles_card.pack(fill="x", pady=(0, 6))

        lbl_toggles_title = ctk.CTkLabel(toggles_card, text="⚡ AUTO TRAINER CONTROLS", font=("Arial", 10, "bold"), text_color="#818cf8")
        lbl_toggles_title.pack(anchor="w", padx=12, pady=(6, 2))

        self.switch_frame = ctk.CTkFrame(toggles_card, fg_color="transparent")
        self.switch_frame.pack(fill="x", padx=8, pady=(0, 6))
        self.switch_frame.columnconfigure(0, weight=1)
        self.switch_frame.columnconfigure(1, weight=1)

        # Row 0: YOLO & Auto Rest
        self.switch_yolo = ctk.CTkSwitch(self.switch_frame, text="AI YOLO Radar", font=("Arial", 11, "bold"), text_color="#e2e8f0", progress_color="#4f46e5", fg_color="#262b3a", width=40, command=self.on_toggle_yolo)
        self.switch_yolo.grid(row=0, column=0, padx=8, pady=3, sticky="w")
        self.switch_yolo.select()

        self.switch_rest = ctk.CTkSwitch(self.switch_frame, text="Auto-Rest พักสายตา", font=("Arial", 11, "bold"), text_color="#e2e8f0", progress_color="#4f46e5", fg_color="#262b3a", width=40, command=self.on_toggle_rest)
        self.switch_rest.grid(row=0, column=1, padx=8, pady=3, sticky="w")
        if self.rest_breaks_enabled:
            self.switch_rest.select()

        # Row 1: Relay & Fast Start
        self.switch_relay = ctk.CTkSwitch(self.switch_frame, text="สลับตัวผลัด", font=("Arial", 11, "bold"), text_color="#e2e8f0", progress_color="#4f46e5", fg_color="#262b3a", width=40, command=self.on_toggle_relay)
        self.switch_relay.grid(row=1, column=0, padx=8, pady=3, sticky="w")
        if self.use_relay:
            self.switch_relay.select()

        self.switch_fast_start = ctk.CTkSwitch(self.switch_frame, text="Fast Start", font=("Arial", 11, "bold"), text_color="#e2e8f0", progress_color="#4f46e5", fg_color="#262b3a", width=40, command=self.on_toggle_boost_start)
        self.switch_fast_start.grid(row=1, column=1, padx=8, pady=3, sticky="w")
        if self.use_boost_start:
            self.switch_fast_start.select()

        # Row 2: Buffs & FSM v2
        buff_box = ctk.CTkFrame(self.switch_frame, fg_color="transparent")
        buff_box.grid(row=2, column=0, padx=8, pady=3, sticky="w")

        self.switch_buffs = ctk.CTkSwitch(buff_box, text="สุ่มซื้อบัฟอัตโนมัติ", font=("Arial", 11, "bold"), text_color="#e2e8f0", progress_color="#4f46e5", fg_color="#262b3a", width=40, command=self.on_toggle_buy_random_boost)
        self.switch_buffs.pack(side="left")
        if self.buy_random_boost:
            self.switch_buffs.select()

        self.btn_buff_cfg = ctk.CTkButton(
            buff_box, text="⚙️", font=("Arial", 9, "bold"), width=24, height=20, fg_color="#202534", hover_color="#4f46e5", text_color="#818cf8", command=self.open_buff_config_window
        )
        self.btn_buff_cfg.pack(side="left", padx=(4, 0))

        self.switch_relic = ctk.CTkSwitch(self.switch_frame, text="เปิด Relic เมื่อครบ", font=("Arial", 11, "bold"), text_color="#e2e8f0", progress_color="#4f46e5", fg_color="#262b3a", width=40, command=self.on_toggle_relic)
        self.switch_relic.grid(row=2, column=1, padx=8, pady=3, sticky="w")
        if getattr(self, "auto_relic", True):
            self.switch_relic.select()

        # 3. Card: Mini Console
        console_card = ctk.CTkFrame(parent, fg_color="#181c26", corner_radius=10, border_width=1, border_color="#262b3a")
        console_card.pack(fill="both", expand=True, pady=(0, 6))

        c_head = ctk.CTkFrame(console_card, fg_color="transparent")
        c_head.pack(fill="x", padx=10, pady=(4, 2))

        lbl_console_title = ctk.CTkLabel(c_head, text="💧 MINI CONSOLE", font=("Arial", 10, "bold"), text_color="#818cf8")
        lbl_console_title.pack(side="left")

        self.status_label = ctk.CTkLabel(c_head, text="Emulator: พร้อมทำงาน", font=("Arial", 9, "bold"), text_color="#34d399")
        self.status_label.pack(side="left", padx=12)

        self.switch_gui_logs = ctk.CTkSwitch(c_head, text="", progress_color="#4f46e5", fg_color="#262b3a", width=28, command=self.on_toggle_gui_logs)
        self.switch_gui_logs.pack(side="right")
        self.switch_gui_logs.select()

        btn_clear = ctk.CTkButton(c_head, text="🧹", width=22, height=18, font=("Arial", 9), fg_color="#202534", hover_color="#475569", text_color="#94a3b8", command=self.clear_logs)
        btn_clear.pack(side="right", padx=4)

        self.btn_test_relic = ctk.CTkButton(
            c_head, text="🏺 Test Relic", width=75, height=18, font=("Arial", 9, "bold"),
            fg_color="#312e81", hover_color="#4338ca", text_color="#c7d2fe", command=self.test_read_relic_ocr
        )
        self.btn_test_relic.pack(side="right", padx=4)

        self.log_textbox = ctk.CTkTextbox(
            console_card, font=("Consolas", 9), fg_color="#0b0d13", text_color="#34d399",
            corner_radius=6, border_width=1, border_color="#202534", height=90
        )
        self.log_textbox.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self.log_textbox.configure(state="disabled")

        self.stdout_redirector = StdoutRedirector(self.log_textbox)
        sys.stdout = self.stdout_redirector

        # 4. Master Action Buttons Bar (START & STOP)
        btn_box = ctk.CTkFrame(parent, fg_color="transparent")
        btn_box.pack(fill="x", pady=(0, 2))

        self.btn_start = ctk.CTkButton(
            btn_box, text="▶ START BOT", height=38, fg_color="#4f46e5", hover_color="#4338ca",
            font=("Arial", 12, "bold"), corner_radius=6, command=self.start_bot
        )
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_stop = ctk.CTkButton(
            btn_box, text="⏹ STOP", height=38, fg_color="#201a24", hover_color="#331c26",
            text_color="#f87171", border_width=1.5, border_color="#f43f5e",
            font=("Arial", 12, "bold"), corner_radius=6, command=self.stop_bot
        )
        self.btn_stop.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def setup_autoclaim_view(self):
        parent = self.views["autoclaim"]
        scroll_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=2, pady=2)

        lbl_title = ctk.CTkLabel(scroll_frame, text="🎁 ศูนย์รวมฟังก์ชันอัตโนมัติ (Automation Suite)", font=("Arial", 12, "bold"), text_color="#818cf8")
        lbl_title.pack(anchor="w", padx=4, pady=(2, 6))

        # --- CARD 1: Send Hearts ---
        card_hearts = ctk.CTkFrame(scroll_frame, fg_color="#181c26", corner_radius=10, border_width=1, border_color="#262b3a")
        card_hearts.pack(fill="x", pady=4)

        h_title = ctk.CTkLabel(card_hearts, text="💌 ส่งหัวใจอัตโนมัติ (Auto Send Hearts)", font=("Arial", 11, "bold"), text_color="#f472b6")
        h_title.pack(anchor="w", padx=12, pady=(8, 2))
        
        btn_box1 = ctk.CTkFrame(card_hearts, fg_color="transparent")
        btn_box1.pack(fill="x", padx=12, pady=(0, 8))

        btn_send_hearts = ctk.CTkButton(
            btn_box1, text="▶️ เริ่มส่งหัวใจ", height=30, fg_color="#ec4899", hover_color="#db2777", font=("Arial", 10, "bold"), corner_radius=6,
            command=self.start_send_hearts_task
        )
        btn_send_hearts.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_stop_hearts = ctk.CTkButton(
            btn_box1, text="⏹️ หยุด", width=70, height=30, fg_color="#202534", hover_color="#f43f5e", text_color="#f87171", font=("Arial", 10, "bold"), corner_radius=6,
            command=self.stop_autoclaim_task
        )
        btn_stop_hearts.pack(side="right")

        # --- CARD 2: Extract Treasure ---
        card_extract = ctk.CTkFrame(scroll_frame, fg_color="#181c26", corner_radius=10, border_width=1, border_color="#262b3a")
        card_extract.pack(fill="x", pady=4)

        header_extract = ctk.CTkFrame(card_extract, fg_color="transparent")
        header_extract.pack(fill="x", padx=12, pady=(8, 2))

        e_title = ctk.CTkLabel(header_extract, text="🪙 สุ่มและย่อยสมบัติ (Smart Extract)", font=("Arial", 11, "bold"), text_color="#fbbf24")
        e_title.pack(side="left")

        btn_cfg_extract = ctk.CTkButton(
            header_extract, text="⚙️ เว้นสมบัติ", width=85, height=22, fg_color="#202534", hover_color="#334155", text_color="#38bdf8", font=("Arial", 9, "bold"), corner_radius=4,
            command=self.open_treasure_config_window
        )
        btn_cfg_extract.pack(side="right")

        btn_box2 = ctk.CTkFrame(card_extract, fg_color="transparent")
        btn_box2.pack(fill="x", padx=12, pady=(0, 8))

        btn_extract = ctk.CTkButton(
            btn_box2, text="▶️ เริ่มย่อยสมบัติ", height=30, fg_color="#f59e0b", hover_color="#d97706", text_color="#ffffff", font=("Arial", 10, "bold"), corner_radius=6,
            command=self.start_extract_treasure_task
        )
        btn_extract.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_stop_extract = ctk.CTkButton(
            btn_box2, text="⏹️ หยุด", width=70, height=30, fg_color="#202534", hover_color="#f43f5e", text_color="#f87171", font=("Arial", 10, "bold"), corner_radius=6,
            command=self.stop_autoclaim_task
        )
        btn_stop_extract.pack(side="right")

        # --- CARD 3: Open Gift Box ---
        card_gift = ctk.CTkFrame(scroll_frame, fg_color="#181c26", corner_radius=10, border_width=1, border_color="#262b3a")
        card_gift.pack(fill="x", pady=4)

        g_title = ctk.CTkLabel(card_gift, text="🎁 เปิดกล่องของขวัญ (Auto Claim Gift)", font=("Arial", 11, "bold"), text_color="#38bdf8")
        g_title.pack(anchor="w", padx=12, pady=(8, 2))

        btn_box3 = ctk.CTkFrame(card_gift, fg_color="transparent")
        btn_box3.pack(fill="x", padx=12, pady=(0, 8))

        btn_claim = ctk.CTkButton(
            btn_box3, text="▶️ เริ่มเปิดกล่อง", height=30, fg_color="#0284c7", hover_color="#0369a1", font=("Arial", 10, "bold"), corner_radius=6,
            command=self.start_claim_gift_task
        )
        btn_claim.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_stop_claim = ctk.CTkButton(
            btn_box3, text="⏹️ หยุด", width=70, height=30, fg_color="#202534", hover_color="#f43f5e", text_color="#f87171", font=("Arial", 10, "bold"), corner_radius=6,
            command=self.stop_autoclaim_task
        )
        btn_stop_claim.pack(side="right")

    def run_autoclaim_worker(self, task_name, run_func):
        if getattr(self, "autoclaim_running", False):
            print("⚠️ มีระบบอัตโนมัติกำลังทำงานอยู่แล้ว! กรุณากดหยุดระบบเดิมก่อน")
            return
        if not self.hwnd:
            print("❌ ไม่พบหน้าต่าง Emulator!")
            return
        
        self.autoclaim_running = True
        if not hasattr(self, "autoclaim_stop_event"):
            import threading
            self.autoclaim_stop_event = threading.Event()
        self.autoclaim_stop_event.clear()
        
        print(f"[{time.strftime('%H:%M:%S')}] 🚀 เริ่มทำงาน: {task_name}...")
        
        def worker():
            try:
                run_func(self.hwnd, self.autoclaim_stop_event)
            except Exception as e:
                print(f"❌ เกิดข้อผิดพลาดใน {task_name}: {e}")
            finally:
                self.autoclaim_running = False
                print(f"[{time.strftime('%H:%M:%S')}] ⏹️ หยุดทำงาน: {task_name}")
        
        import threading
        threading.Thread(target=worker, daemon=True).start()

    def start_send_hearts_task(self):
        from auto_send_hearts import run_auto_send_hearts_loop
        self.run_autoclaim_worker("ส่งหัวใจอัตโนมัติ", lambda hwnd, stop_ev: run_auto_send_hearts_loop(hwnd, stop_checker=stop_ev.is_set))

    def start_extract_treasure_task(self):
        from smart_extract_treasure import run_smart_extract_loop
        self.run_autoclaim_worker("ย่อยสมบัติ", lambda hwnd, stop_ev: run_smart_extract_loop(hwnd, stop_checker=stop_ev.is_set))

    def start_claim_gift_task(self):
        from auto_claim_gift import run_auto_gift_loop
        self.run_autoclaim_worker("เปิดกล่องของขวัญ", lambda hwnd, stop_ev: run_auto_gift_loop(hwnd, stop_checker=stop_ev.is_set))

    def stop_autoclaim_task(self):
        if hasattr(self, "autoclaim_stop_event"):
            self.autoclaim_stop_event.set()
        self.autoclaim_running = False
        print(f"[{time.strftime('%H:%M:%S')}] 🛑 ส่งสัญญาณหยุดระบบอัตโนมัติ...")

    def open_treasure_config_window(self):
        try:
            from smart_extract_treasure import open_treasure_config_window
            open_treasure_config_window(self)
        except Exception as e:
            print(f"❌ ไม่สามารถเปิดหน้าต่างตั้งค่าเว้นสมบัติได้: {e}")

    def setup_settings_view(self):
        parent = self.views["settings"]
        scroll_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=2, pady=2)

        card_p = ctk.CTkFrame(scroll_frame, fg_color="#181c26", corner_radius=10, border_width=1, border_color="#262b3a")
        card_p.pack(fill="x", pady=4)

        lbl_profile = ctk.CTkLabel(card_p, text="🎯 โปรไฟล์ด่านด่วน (Quick Profile)", font=("Arial", 11, "bold"), text_color="#818cf8")
        lbl_profile.pack(anchor="w", padx=12, pady=(8, 2))

        self.profile_option_menu = ctk.CTkOptionMenu(
            card_p, values=["Stage 1 (ฟาร์มเงิน)", "Stage 3 (ฟาร์มสปีด)"], command=self.on_profile_change,
            fg_color="#202534", button_color="#2e3549", button_hover_color="#4f46e5", text_color="#f8fafc",
            dropdown_text_color="#f8fafc", height=28, font=("Arial", 10, "bold"),
            dropdown_fg_color="#181c26"
        )
        self.profile_option_menu.pack(fill="x", padx=12, pady=(0, 8))

        self.session_runs_label = ctk.CTkLabel(card_p, text="📊 จำนวนรอบในเซสชัน: 0/12 รอบ", font=("Arial", 10, "bold"), text_color="#34d399")
        self.session_runs_label.pack(anchor="w", padx=12, pady=(0, 8))

        card_sliders = ctk.CTkFrame(scroll_frame, fg_color="#181c26", corner_radius=10, border_width=1, border_color="#262b3a")
        card_sliders.pack(fill="x", pady=4)

        lbl_tune = ctk.CTkLabel(card_sliders, text="⚙️ AI PARAMETERS TUNING", font=("Arial", 10, "bold"), text_color="#818cf8")
        lbl_tune.pack(anchor="w", padx=12, pady=(8, 4))

        self.session_limit_title = ctk.CTkLabel(card_sliders, text=f"ขีดจำกัดรอบสูงสุด/เซสชัน: {self.max_session_runs_limit} รอบ", font=("Arial", 10, "bold"), text_color="#f8fafc")
        self.session_limit_title.pack(anchor="w", padx=12, pady=(2, 1))

        self.session_limit_slider = ctk.CTkSlider(
            card_sliders, from_=5, to=30, number_of_steps=25, progress_color="#6366f1", fg_color="#262b3a", command=self.on_session_limit_change
        )
        self.session_limit_slider.set(self.max_session_runs_limit)
        self.session_limit_slider.pack(fill="x", padx=12, pady=(0, 6))

        self.dist_title = ctk.CTkLabel(card_sliders, text=f"ระยะทริกเกอร์หลบสิ่งกีดขวาง: {self.trigger_dist} px", font=("Arial", 10, "bold"), text_color="#f8fafc")
        self.dist_title.pack(anchor="w", padx=12, pady=(2, 1))
        self.dist_slider = ctk.CTkSlider(
            card_sliders, from_=50, to=300, number_of_steps=250, progress_color="#6366f1", fg_color="#262b3a", command=self.on_dist_change
        )
        self.dist_slider.set(self.trigger_dist)
        self.dist_slider.pack(fill="x", padx=12, pady=(0, 6))

        self.slide_title = ctk.CTkLabel(card_sliders, text=f"เวลากดสไลด์ค้าง: {self.slide_hold_ms} ms", font=("Arial", 10, "bold"), text_color="#f8fafc")
        self.slide_title.pack(anchor="w", padx=12, pady=(2, 1))
        self.slide_slider = ctk.CTkSlider(
            card_sliders, from_=100, to=1500, number_of_steps=140, progress_color="#6366f1", fg_color="#262b3a", command=self.on_slide_change
        )
        self.slide_slider.set(self.slide_hold_ms)
        self.slide_slider.pack(fill="x", padx=12, pady=(0, 6))

        self.conf_title = ctk.CTkLabel(card_sliders, text=f"ความเข้มงวด YOLO: {int(self.conf_val * 100)}%", font=("Arial", 10, "bold"), text_color="#f8fafc")
        self.conf_title.pack(anchor="w", padx=12, pady=(2, 1))
        self.conf_slider = ctk.CTkSlider(
            card_sliders, from_=0.10, to=0.85, number_of_steps=75, progress_color="#6366f1", fg_color="#262b3a", command=self.on_conf_change
        )
        self.conf_slider.set(self.conf_val)
        self.conf_slider.pack(fill="x", padx=12, pady=(0, 8))

    def setup_license_view(self):
        parent = self.views["license"]
        card_frame = ctk.CTkFrame(parent, fg_color="#181c26", corner_radius=10, border_width=1, border_color="#262b3a")
        card_frame.pack(fill="both", expand=True, padx=2, pady=2)

        lbl_title = ctk.CTkLabel(card_frame, text="🔑 ยืนยันสิทธิ์ใช้งาน (License Key)", font=("Arial", 12, "bold"), text_color="#818cf8")
        lbl_title.pack(pady=(14, 8))

        current_hwid = get_hwid()
        lbl_hwid_tag = ctk.CTkLabel(card_frame, text="HWID ของคุณ:", font=("Arial", 10, "bold"), text_color="#94a3b8")
        lbl_hwid_tag.pack(anchor="w", padx=12, pady=(2, 1))

        hwid_sub = ctk.CTkFrame(card_frame, fg_color="transparent")
        hwid_sub.pack(fill="x", padx=12, pady=(0, 8))

        self.entry_hwid = ctk.CTkEntry(hwid_sub, font=("Courier New", 10, "bold"), fg_color="#0b0d13", text_color="#38bdf8", border_color="#262b3a", height=28)
        self.entry_hwid.insert(0, current_hwid)
        self.entry_hwid.configure(state="readonly")
        self.entry_hwid.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_copy_hwid = ctk.CTkButton(
            hwid_sub, text="📋", width=32, height=28, fg_color="#202534", hover_color="#4f46e5", text_color="#818cf8", command=self.copy_hwid_to_clipboard
        )
        btn_copy_hwid.pack(side="right")

        lbl_key_tag = ctk.CTkLabel(card_frame, text="License Key:", font=("Arial", 10, "bold"), text_color="#94a3b8")
        lbl_key_tag.pack(anchor="w", padx=12, pady=(2, 1))

        key_sub = ctk.CTkFrame(card_frame, fg_color="transparent")
        key_sub.pack(fill="x", padx=12, pady=(0, 8))

        saved_key = self.load_saved_license()
        self.entry_license_key = ctk.CTkEntry(
            key_sub, placeholder_text="CRBOT-VIP-XXXX", font=("Arial", 10), fg_color="#0b0d13", text_color="#f8fafc", border_color="#262b3a", height=28
        )
        if saved_key:
            self.entry_license_key.insert(0, saved_key)
        self.entry_license_key.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_verify = ctk.CTkButton(
            key_sub, text="⚡ เช็คคีย์", width=65, height=28, fg_color="#4f46e5", hover_color="#4338ca", font=("Arial", 10, "bold"), command=self.on_verify_key_clicked
        )
        btn_verify.pack(side="right")

        self.license_status_label = ctk.CTkLabel(card_frame, text="สถานะ: 🔒 รอตรวจสอบ", font=("Arial", 10, "bold"), text_color="#f59e0b")
        self.license_status_label.pack(pady=8)

        if saved_key:
            self.after(600, self.auto_check_saved_license)

    def on_select_mumu_window(self, selected_label):
        if hasattr(self, 'mumu_windows') and selected_label in self.mumu_windows:
            self.hwnd = self.mumu_windows[selected_label]
            print(f"[{time.strftime('%H:%M:%S')}] 🎯 เลือกหน้าต่าง: {selected_label}")

    def refresh_mumu_windows(self):
        self.mumu_windows = self.scan_mumu_windows()
        options = list(self.mumu_windows.keys())
        if not options:
            options = ["ไม่พบหน้าต่าง Emulator"]
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
        print(f"[{time.strftime('%H:%M:%S')}] 🔄 รีเฟรชพบ {len(self.mumu_windows)} หน้าต่าง")

    def toggle_hide_mumu_window(self):
        if not self.hwnd:
            print("❌ ไม่พบหน้าต่าง Emulator!")
            return
        try:
            is_visible = win32gui.IsWindowVisible(self.hwnd)
            if is_visible:
                win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
                self.btn_hide_mumu.configure(text="👁️", fg_color="#e74c3c")
                print(f"[{time.strftime('%H:%M:%S')}] 🙈 ซ่อนหน้าต่าง Emulator")
            else:
                win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
                win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
                self.btn_hide_mumu.configure(text="🙈", fg_color="#202534")
                print(f"[{time.strftime('%H:%M:%S')}] 👁️ แสดงหน้าต่าง Emulator")
        except Exception as e:
            print(f"❌ ไม่สามารถเปลี่ยนสถานะหน้าต่างได้: {e}")

    def capture_and_show_grid_overlay(self):
        if not self.hwnd:
            print("❌ ไม่พบหน้าต่าง Emulator! กรุณาเลือกหน้าต่างก่อน")
            return
        
        raw_frame = capture_window_bg(self.hwnd)
        if raw_frame is None:
            print("❌ ไม่สามารถดึงภาพหน้าจอได้!")
            return

        # เปิดหน้าต่าง Grid Inspector Window
        if hasattr(self, 'grid_win') and self.grid_win is not None and self.grid_win.winfo_exists():
            self.grid_win.focus()
            self._update_grid_view(raw_frame)
            return

        self.grid_win = ctk.CTkToplevel(self)
        self.grid_win.title("🎯 ตรวจสอบพิกัดหน้าจอ (Screen Grid Inspector)")
        self.grid_win.geometry("830x530")
        self.grid_win.resizable(False, False)
        self.grid_win.configure(fg_color="#0f1219")
        self.grid_win.attributes("-topmost", True)

        # Header bar
        header = ctk.CTkFrame(self.grid_win, fg_color="#181c26", height=42, corner_radius=0)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        self.lbl_grid_coord = ctk.CTkLabel(
            header, text="📍 เลื่อนเมาส์บนภาพเพื่อดูพิกัด | คลิกเพื่อคัดลอก (X, Y)",
            font=("Arial", 11, "bold"), text_color="#38bdf8"
        )
        self.lbl_grid_coord.pack(side="left", padx=14)

        btn_save = ctk.CTkButton(
            header, text="💾 บันทึกรูป", width=80, height=28,
            fg_color="#202534", hover_color="#334155", font=("Arial", 10, "bold"), corner_radius=6,
            command=self._save_current_grid_image
        )
        btn_save.pack(side="right", padx=(4, 10), pady=6)

        btn_recap = ctk.CTkButton(
            header, text="🔄 แคปใหม่", width=80, height=28,
            fg_color="#4f46e5", hover_color="#4338ca", font=("Arial", 10, "bold"), corner_radius=6,
            command=self._refresh_grid_view
        )
        btn_recap.pack(side="right", padx=4, pady=6)

        # Canvas container for 800x450 image
        img_container = ctk.CTkFrame(self.grid_win, fg_color="#000000", corner_radius=0)
        img_container.pack(fill="both", expand=True, padx=15, pady=(10, 15))

        import tkinter as tk
        self.grid_canvas = tk.Canvas(img_container, width=800, height=450, bg="#000000", highlightthickness=0)
        self.grid_canvas.pack(expand=True)

        def on_mouse_move(event):
            x, y = event.x, event.y
            if 0 <= x <= 800 and 0 <= y <= 450:
                self.lbl_grid_coord.configure(text=f"📍 พิกัด: X={x}, Y={y}  (คลิกซ้ายเพื่อคัดลอก)")

        def on_mouse_click(event):
            x, y = event.x, event.y
            if 0 <= x <= 800 and 0 <= y <= 450:
                coord_str = f"({x}, {y})"
                self.clipboard_clear()
                self.clipboard_append(coord_str)
                self.lbl_grid_coord.configure(text=f"✅ คัดลอกพิกัด {coord_str} ลงคลิปบอร์ดแล้ว!")
                print(f"[{time.strftime('%H:%M:%S')}] 📋 คัดลอกพิกัด: {coord_str}")

        self.grid_canvas.bind("<Motion>", on_mouse_move)
        self.grid_canvas.bind("<Button-1>", on_mouse_click)

        self._update_grid_view(raw_frame)

    def _draw_grid_on_frame(self, frame):
        h, w = frame.shape[:2]
        grid_frame = frame.copy()
        
        # เส้นย่อย 25px
        for x in range(0, w, 25):
            if x % 50 != 0:
                cv2.line(grid_frame, (x, 0), (x, h), (40, 40, 50), 1)
        for y in range(0, h, 25):
            if y % 50 != 0:
                cv2.line(grid_frame, (0, y), (w, y), (40, 40, 50), 1)
                
        # เส้นหลัก 50px พร้อมตัวเลข
        for x in range(0, w, 50):
            cv2.line(grid_frame, (x, 0), (x, h), (70, 80, 100), 1)
            cv2.putText(grid_frame, str(x), (x + 2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(grid_frame, str(x), (x + 2, h - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 255, 255), 1, cv2.LINE_AA)
            
        for y in range(0, h, 50):
            cv2.line(grid_frame, (0, y), (w, y), (70, 80, 100), 1)
            cv2.putText(grid_frame, str(y), (4, y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(grid_frame, str(y), (w - 30, y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 255, 255), 1, cv2.LINE_AA)
            
        return grid_frame

    def _update_grid_view(self, raw_frame):
        if raw_frame is None:
            return
        grid_frame = self._draw_grid_on_frame(raw_frame)
        self._current_grid_cv_image = grid_frame
        
        # แปลง BGR เป็น RGB และทำ PhotoImage
        rgb_frame = cv2.cvtColor(grid_frame, cv2.COLOR_BGR2RGB)
        if rgb_frame.shape[1] != 800 or rgb_frame.shape[0] != 450:
            rgb_frame = cv2.resize(rgb_frame, (800, 450))
            
        from PIL import ImageTk, Image
        pil_img = Image.fromarray(rgb_frame)
        self._grid_photo = ImageTk.PhotoImage(pil_img)
        
        if hasattr(self, 'grid_canvas') and self.grid_canvas.winfo_exists():
            self.grid_canvas.delete("all")
            self.grid_canvas.create_image(0, 0, anchor="nw", image=self._grid_photo)

    def _refresh_grid_view(self):
        if not self.hwnd:
            return
        frame = capture_window_bg(self.hwnd)
        if frame is not None:
            self._update_grid_view(frame)
            if hasattr(self, 'lbl_grid_coord'):
                self.lbl_grid_coord.configure(text="🔄 แคปภาพหน้าจอใหม่เรียบร้อย!")

    def _save_current_grid_image(self):
        if hasattr(self, '_current_grid_cv_image') and self._current_grid_cv_image is not None:
            cv2.imwrite("captured_grid.png", self._current_grid_cv_image)
            if hasattr(self, 'lbl_grid_coord'):
                self.lbl_grid_coord.configure(text="💾 บันทึกรูปภาพ 'captured_grid.png' สำเร็จ!")
            print(f"[{time.strftime('%H:%M:%S')}] 📸 บันทึกตารางพิกัด -> 'captured_grid.png'")

    def copy_hwid_to_clipboard(self):
        hwid = get_hwid()
        self.clipboard_clear()
        self.clipboard_append(hwid)
        print(f"[{time.strftime('%H:%M:%S')}] 📋 คัดลอก HWID เรียบร้อย")

    def load_saved_license(self):
        if getattr(sys, 'frozen', False):
            script_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
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
        if getattr(sys, 'frozen', False):
            script_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
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
            self.last_action_time = time.time()
            if getattr(self, "fsm_engine", None):
                self.fsm_engine.reset()
            self.bot_status_label.configure(text="กำลังเล่น (PLAYING)", text_color="#34d399")
            print(f"[{time.strftime('%H:%M:%S')}] ▶️ Start Bot")

    def stop_bot(self):
        if self.bot_active:
            self.bot_active = False
            self.bot_status_label.configure(text="● IDLE (หยุดทำงาน)", text_color="#f87171")
            print(f"[{time.strftime('%H:%M:%S')}] ⏹️ Stop Bot")

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
        status = "เปิด" if val else "ปิด"
        print(f"🤖 YOLO Radar: {status}")

    def update_session_label(self):
        if self.rest_breaks_enabled:
            is_resting = False
            if getattr(self, "fsm_engine", None) and hasattr(self.fsm_engine.current_state, "__class__"):
                is_resting = self.fsm_engine.current_state.__class__.__name__ == "RestingState"
            if is_resting:
                self.session_runs_label.configure(text=f"เซสชัน: {self.current_session_runs}/{self.target_session_runs} (กำลังพักผ่อน)")
            else:
                self.session_runs_label.configure(text=f"เซสชัน: {self.current_session_runs}/{self.target_session_runs} รอบ")
        else:
            self.session_runs_label.configure(text=f"รอบสะสม: {self.current_session_runs} รอบ (ไม่มีพักเบรก)")

    def on_toggle_rest(self):
        self.rest_breaks_enabled = self.switch_rest.get() == 1
        status = "เปิด" if self.rest_breaks_enabled else "ปิด"
        print(f"☕ Auto-Rest: {status}")
        self.update_session_label()

    def on_toggle_boost_start(self):
        self.use_boost_start = self.switch_fast_start.get() == 1
        status = "เปิด" if self.use_boost_start else "ปิด"
        print(f"⚡ Fast Start: {status}")

    def on_toggle_buy_random_boost(self):
        self.buy_random_boost = self.switch_buffs.get() == 1
        status = "เปิด" if self.buy_random_boost else "ปิด"
        print(f"🎲 Auto Buffs: {status}")

    def on_toggle_relay(self):
        self.use_relay = self.switch_relay.get() == 1
        status = "เปิด" if self.use_relay else "ปิด"
        print(f"👥 Relay Cookie: {status}")

    def on_toggle_relic(self):
        self.auto_relic = self.switch_relic.get() == 1
        status = "เปิด" if self.auto_relic else "ปิด"
        print(f"🏺 Auto Relic: {status}")

    def on_toggle_debug(self):
        val = self.switch_debug.get() == 1
        set_show_debug_logs(val)
        status = "เปิด" if val else "ปิด"
        print(f"🔍 Debug: {status}")

    def test_read_relic_ocr(self):
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ กรุณาเลือกหน้าต่างเกม (HWND) จากเมนูด้านบนก่อนกดทดสอบ")
            return

        frame = capture_window_bg(self.hwnd)
        if frame is None:
            print(f"[{time.strftime('%H:%M:%S')}] ❌ ไม่สามารถดึงภาพจากหน้าต่างเป้าหมายได้ (กรุณาเช็คว่าหน้าต่างเปิดอยู่)")
            return

        # พิกัดตามที่ระบุ: x 300 - 350, y 50 - 80 (บนสเกล 800x450)
        roi_exact = frame[50:80, 300:350]
        roi_wide = frame[40:90, 280:365]

        os.makedirs("scratch", exist_ok=True)
        cv2.imwrite("scratch/relic_exact.png", roi_exact)
        cv2.imwrite("scratch/relic_wide.png", roi_wide)
        cv2.imwrite("scratch/test_lobby.png", frame)

        if self.ocr_engine is None:
            self._init_ocr()

        if self.ocr_engine is None:
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ ระบบ RapidOCR ยังไม่พร้อมใช้งาน")
            return

        roi_big = cv2.resize(roi_exact, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        res_exact, _ = self.ocr_engine(roi_big)
        raw_exact = " ".join(item[1] for item in res_exact).strip() if res_exact else ""
        txt_exact = raw_exact.upper().replace("LA", "5").replace("IA", "5").replace("SA", "5").replace("LO", "5").replace("\\", "/").replace("|", "/")

        print(f"[{time.strftime('%H:%M:%S')}] 🏺 [Test Relic 300-350, 50-80]: '{raw_exact}' ➔ แปลงเป็น: '{txt_exact}'")

        roi_wide_big = cv2.resize(roi_wide, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        res_wide, _ = self.ocr_engine(roi_wide_big)
        raw_wide = " ".join(item[1] for item in res_wide).strip() if res_wide else ""
        txt_wide = raw_wide.upper().replace("LA", "5").replace("IA", "5").replace("SA", "5").replace("LO", "5").replace("\\", "/").replace("|", "/")
        print(f"[{time.strftime('%H:%M:%S')}] 🔍 [Test Relic ขอบกว้าง 280-365, 40-90]: '{raw_wide}' ➔ แปลงเป็น: '{txt_wide}'")
        print(f"[{time.strftime('%H:%M:%S')}] 💾 บันทึกภาพตัดครอปไว้ที่ scratch/relic_exact.png และ relic_wide.png")

    def on_toggle_gui_logs(self):
        enabled = self.switch_gui_logs.get() == 1
        if hasattr(self, 'stdout_redirector'):
            self.stdout_redirector.enabled = enabled

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

        frame = capture_window_bg(self.hwnd)
        if frame is None:
            self.after(30, self.update_loop)
            return

        # ----------------- FSM v2 Engine -----------------
        if getattr(self, "fsm_engine", None):
            self.fsm_engine.update(frame)

        self.schedule_next_loop(start_time)
