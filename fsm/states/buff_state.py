# -*- coding: utf-8 -*-
import cv2
import numpy as np
import time
from ..base_state import BaseState
from window_manager import human_click_bg
from template_matcher import find_template_match

class BuffState(BaseState):
    SUB_SLOT1 = "SLOT1"
    SUB_SLOT2 = "SLOT2"
    SUB_SLOT3 = "SLOT3"
    SUB_SCAN_RESULT = "SCAN_RESULT"
    SUB_CLICK_PLAY = "CLICK_PLAY"

    def __init__(self, context):
        super().__init__(context, timeout_seconds=60.0)
        self.sub_step = self.SUB_SLOT1
        self.last_action_time = 0
        self._prev_buff_roi = None
        self._ocr_scanned_this_result = False
        self._last_logged_ocr = ""
        self._play_click_count = 0
        self.consecutive_match_count = 0
        self.consecutive_target_name = ""
        self.consecutive_non_target_count = 0
        self.last_ocr_dispatch_time = 0

    def on_enter(self):
        super().on_enter()
        self.ctx.update_ui_status("สถานะ: สุ่มเลือกซื้อบัฟ", text_color="#f39c12")
        self.last_action_time = time.time()
        self.consecutive_match_count = 0
        self.consecutive_target_name = ""
        self.consecutive_non_target_count = 0
        self._last_logged_ocr = ""
        if hasattr(self.ctx.app, "_async_ocr_text"):
            self.ctx.app._async_ocr_text = ""

    def execute(self, frame) -> BaseState:
        now = time.time()

        if not self.ctx.get_config("buy_random_boost", False):
            from .stage_start_state import StageStartState
            return StageStartState(self.ctx)

        # ----------------- Step 1: Select Boost Slot -----------------
        if self.sub_step == self.SUB_SLOT1:
            found = False
            cx, cy = 335, 375
            if "selectbuff_1" in self.ctx.autostart_templates:
                found, tx, ty = find_template_match(
                    self.ctx.hwnd, frame, self.ctx.autostart_templates["selectbuff_1"], threshold=0.55
                )
                if found: cx, cy = tx, ty

            if (found or (now - self.last_action_time > 2.5)) and (now - self.last_action_time > 0.8):
                human_click_bg(self.ctx.hwnd, cx, cy, "เลือกสล็อตบัฟ")
                self.last_action_time = now
                self.sub_step = self.SUB_SLOT2

        # ----------------- Step 2: Multi Random Boost Button -----------------
        elif self.sub_step == self.SUB_SLOT2:
            found3 = False
            if "selectbuff_3" in self.ctx.autostart_templates:
                found3, _, _ = find_template_match(
                    self.ctx.hwnd, frame, self.ctx.autostart_templates["selectbuff_3"], threshold=0.55
                )
            if found3:
                self.sub_step = self.SUB_SLOT3
                self.last_action_time = now
                return self

            found = False
            cx, cy = 666, 123
            if "selectbuff_2" in self.ctx.autostart_templates:
                found, tx, ty = find_template_match(
                    self.ctx.hwnd, frame, self.ctx.autostart_templates["selectbuff_2"], threshold=0.55
                )
                if found: cx, cy = tx, ty

            if (found or (now - self.last_action_time > 2.0)) and (now - self.last_action_time > 0.8):
                human_click_bg(self.ctx.hwnd, cx, cy, "สุ่มบัฟต่อเนื่อง")
                self.last_action_time = now
                self.sub_step = self.SUB_SLOT3

        # ----------------- Step 3: Multi-Buy Button -----------------
        elif self.sub_step == self.SUB_SLOT3:
            found = False
            cx, cy = 397, 367
            if "selectbuff_3" in self.ctx.autostart_templates:
                found, tx, ty = find_template_match(
                    self.ctx.hwnd, frame, self.ctx.autostart_templates["selectbuff_3"], threshold=0.55
                )
                if found: cx, cy = tx, ty

            if (found or (now - self.last_action_time > 2.0)) and (now - self.last_action_time > 0.8):
                human_click_bg(self.ctx.hwnd, cx, cy, "ซื้อบัฟ")
                self.last_action_time = now
                self.sub_step = self.SUB_SCAN_RESULT
                self._last_logged_ocr = ""
                self.consecutive_match_count = 0
                self.consecutive_target_name = ""
                self.consecutive_non_target_count = 0
                self._prev_buff_roi = None
                if hasattr(self.ctx.app, "_async_ocr_text"):
                    self.ctx.app._async_ocr_text = ""

        # ----------------- Step 4: Scan and Verify Buff Result -----------------
        elif self.sub_step == self.SUB_SCAN_RESULT:
            # ต้องรอให้การกดซื้อบัฟผ่านไปอย่างน้อย 1.2 วินาทีเพื่อให้วงล้อเริ่มหมุนจริงก่อนอ่านผล
            if now - self.last_action_time >= 1.2:
                # ครอบคลุมป๊อปอัปสุ่มผล Multi-Buy ตรงกลางจอทั้งหมด (180:640, 90:380)
                roi_buff_area = frame[90:380, 180:640]

                # ส่งภาพเข้า Async OCR สตรีมต่อเนื่องทุก 150ms
                if now - self.last_ocr_dispatch_time >= 0.15:
                    self.last_ocr_dispatch_time = now
                    roi_big = cv2.resize(roi_buff_area, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
                    if hasattr(self.ctx.app, "trigger_async_ocr"):
                        self.ctx.app.trigger_async_ocr(roi_big)

                ocr_text = getattr(self.ctx.app, "_async_ocr_text", "")
                txt_lower = ocr_text.lower()

                if any(k in txt_lower for k in ["tap multi-buy", "keep spending", "firstbuy", "repeatbuy"]):
                    ocr_text = ""
                    txt_lower = ""

                detected_name = self._identify_buff_name(txt_lower)
                if detected_name and detected_name != self._last_logged_ocr:
                    self._last_logged_ocr = detected_name
                    print(f"[{time.strftime('%H:%M:%S')}] 🎲 บัฟ: {detected_name}")

                found_acceptable_buff, matched_name = self._check_buff_match(txt_lower)

                if found_acceptable_buff:
                    if matched_name == self.consecutive_target_name:
                        self.consecutive_match_count += 1
                    else:
                        self.consecutive_target_name = matched_name
                        self.consecutive_match_count = 1

                    # เมื่ออ่านเจอบัฟเป้าหมายซ้ำติดกัน 3 ครั้ง (ยืนยันว่าวงล้อหยุดนิ่งที่บัฟนี้จริง 100%)
                    if self.consecutive_match_count >= 3:
                        print(f"[{time.strftime('%H:%M:%S')}] ✨ ยืนยันเจอบัฟเป้าหมาย: {matched_name} (3/3)")
                        self.sub_step = self.SUB_CLICK_PLAY
                        self.last_action_time = 0
                        self._play_click_count = 0
                        self.ctx.set_config("_async_ocr_text", "")
                        self.ctx.set_config("current_session_runs", self.ctx.get_config("current_session_runs", 0) + 1)
                        self.ctx.update_session_label()
                else:
                    self.consecutive_match_count = 0
                    self.start_time = now # รีเซ็ต timeout ตลอดเวลาที่เกมกำลังสุ่มต่อเนื่อง

        # ----------------- Step 5: Click Play! & Verify Game Launch -----------------
        elif self.sub_step == self.SUB_CLICK_PLAY:
            if now - self.last_action_time >= 0.8:
                cx, cy = 675, 395
                if "playlobby" in self.ctx.autostart_templates:
                    found, tx, ty = find_template_match(
                        self.ctx.hwnd, frame, self.ctx.autostart_templates["playlobby"], threshold=0.48
                    )
                    if found and (580 <= tx <= 750) and (350 <= ty <= 430):
                        cx, cy = tx, ty

                human_click_bg(self.ctx.hwnd, cx, cy, "Start Game")
                self._play_click_count += 1
                self.last_action_time = now

                # If clicked twice or screen starts changing (loading screen), go to PlayingState
                if self._play_click_count >= 2:
                    from .playing_state import PlayingState
                    return PlayingState(self.ctx, is_loading=True)

        if self.is_timed_out():
            from .recovery_state import RecoveryState
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ [Timeout] สุ่มบัฟนานเกินไป ➔ Recovery")
            return RecoveryState(self.ctx)

        return self

    def _identify_buff_name(self, txt_lower: str) -> str:
        if not txt_lower: return ""
        if ("doubl" in txt_lower or "double" in txt_lower) and "gold" not in txt_lower:
            return "🪙 Coins x2"
        if "drain" in txt_lower:
            return "🧪 -15% HP Drain"
        if "crush" in txt_lower or "70%" in txt_lower:
            return "🛡️ 70% Crush Chance"
        if "gold" in txt_lower or "magic" in txt_lower:
            return "🎁 Gold Coin Magic"
        if "potion" in txt_lower or "+20%" in txt_lower:
            return "🍷 +20% HP Potions"
        if "pit" in txt_lower or "lift" in txt_lower:
            return "🛟 2 Pit Lifts"
        if "score" in txt_lower or "bonus" in txt_lower:
            return "🏆 +15% Score Bonus"
        if "reviv" in txt_lower:
            return "💖 Revive"
        if "speed" in txt_lower or "+17%" in txt_lower:
            return "⚡ +17% Base Speed"
        if "collis" in txt_lower or "-30%" in txt_lower:
            return "🚑 -30% Collision Damage"
        if "magnet" in txt_lower or "aura" in txt_lower:
            return "🧲 Magnetic Aura"
        return ""

    def _check_buff_match(self, txt_lower: str):
        c = self.ctx
        if c.get_config("buy_double_coin", False) and ("doubl" in txt_lower or "double" in txt_lower) and "gold" not in txt_lower:
            return True, "🪙 Coins x2"
        if c.get_config("buy_hp_drain", False) and "drain" in txt_lower:
            return True, "🧪 -15% HP Drain"
        if c.get_config("buy_crush_chance", False) and ("crush" in txt_lower or "70%" in txt_lower or "70" in txt_lower):
            return True, "🛡️ 70% Crush Chance"
        if c.get_config("buy_gold_coin_magic", False) and ("gold" in txt_lower or "magic" in txt_lower):
            return True, "🎁 Gold Coin Magic"
        if c.get_config("buy_hp_potions", False) and ("potion" in txt_lower or "+20%" in txt_lower or "20%" in txt_lower):
            return True, "🍷 +20% HP Potions"
        if c.get_config("buy_pit_lifts", False) and ("pit" in txt_lower or "lift" in txt_lower):
            return True, "🛟 2 Pit Lifts"
        if c.get_config("buy_score_bonus", False) and ("score" in txt_lower or "bonus" in txt_lower):
            return True, "🏆 +15% Score Bonus"
        if c.get_config("buy_revive", False) and ("reviv" in txt_lower or "80" in txt_lower):
            return True, "💖 Revive"
        if c.get_config("buy_base_speed", False) and ("speed" in txt_lower or "+17%" in txt_lower or "17%" in txt_lower or "17" in txt_lower):
            return True, "⚡ +17% Base Speed"
        if c.get_config("buy_collision_damage", False) and ("collis" in txt_lower or "damage" in txt_lower or "-30%" in txt_lower or "30%" in txt_lower):
            return True, "🚑 -30% Collision Damage"
        if c.get_config("buy_magnetic_aura", False) and ("magnet" in txt_lower or "aura" in txt_lower):
            return True, "🧲 Magnetic Aura"
        return False, ""
