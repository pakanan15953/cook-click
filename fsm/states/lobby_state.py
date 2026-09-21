# -*- coding: utf-8 -*-
import time
import cv2
from ..base_state import BaseState
from window_manager import human_click_bg
from template_matcher import find_template_match

class LobbyState(BaseState):
    def __init__(self, context):
        super().__init__(context, timeout_seconds=60.0)
        self.last_click_time = 0
        self.relic_checked = False
        self.relic_sub_step = 0
        self.relic_action_time = 0

    def on_enter(self):
        super().on_enter()
        self.ctx.update_ui_status("สถานะ: หน้าหลัก (Lobby)", text_color="#3498db")
        self.relic_checked = False
        self.relic_sub_step = 0
        self.relic_action_time = 0

    def execute(self, frame) -> BaseState:
        now = time.time()

        # ----------------- RELIC AUTO-OPEN SEQUENCE -----------------
        if self.relic_sub_step == 1:
            # ขั้นตอนที่ 3 & 4: รอหน้าต่าง Relic โหลด 1.5 วินาที แล้วอ่านคำที่ตำแหน่ง (396, 361)
            self.ctx.update_ui_status("🏺 กำลังตรวจสอบปุ่ม Claim ในหน้าต่าง Relic...", text_color="#fbbf24")
            self.start_time = now # รีเซ็ต timeout
            if now - self.relic_action_time >= 1.5:
                roi = frame[335:385, 330:465]
                has_claim = False
                ocr_engine = getattr(self.ctx.app, "ocr_engine", None)
                if ocr_engine is None and hasattr(self.ctx.app, "_init_ocr"):
                    self.ctx.app._init_ocr()
                    ocr_engine = getattr(self.ctx.app, "ocr_engine", None)
                
                raw_txt = ""
                if ocr_engine:
                    roi_big = cv2.resize(roi, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
                    res, _ = ocr_engine(roi_big)
                    if res:
                        raw_txt = " ".join(item[1] for item in res).strip().upper()
                        print(f"[{time.strftime('%H:%M:%S')}] 🏺 [Relic] ข้อความปุ่ม: '{raw_txt}'")
                        if any(k in raw_txt for k in ["CLAIM", "CLALM", "CLAM", "C1AIM", "LAIM", "AIM", "เคลม"]):
                            has_claim = True

                if has_claim:
                    # ขั้นตอนที่ 5: เจอคำว่า Claim -> คลิกที่ (396, 361) ครั้งที่ 1 แล้วรอ 10 วิ
                    print(f"[{time.strftime('%H:%M:%S')}] 🏺 [Relic] ✨ ตรวจพบปุ่ม 'Claim'! -> กดเปิดชิ้นส่วน (396, 361)")
                    human_click_bg(self.ctx.hwnd, 396, 361, "กดปุ่ม Claim (Relic)")
                    self.relic_action_time = now
                    self.relic_sub_step = 2
                else:
                    # ขั้นตอนที่ 4: ไม่พบคำว่า Claim -> กดปิดที่ (671, 98) จบไป แล้วนับเวลาเริ่มเกมใหม่
                    print(f"[{time.strftime('%H:%M:%S')}] 🏺 [Relic] ❌ ไม่พบปุ่ม Claim (ชิ้นส่วนยังไม่ครบ) -> กดปิดหน้าต่าง (671, 98)")
                    human_click_bg(self.ctx.hwnd, 671, 98, "ปิดหน้าต่าง Relic (X)")
                    self.relic_sub_step = 0
                    self.relic_checked = True
                    self.last_click_time = now
                    if hasattr(self.ctx.app, "lobby_cooldown_end"):
                        self.ctx.app.lobby_cooldown_end = min(self.ctx.app.lobby_cooldown_end, now + 1.5)
            return self

        elif self.relic_sub_step == 2:
            # ขั้นตอนที่ 5 ต่อเนื่อง: รอ 10 วิ แล้วคลิกตำแหน่งเดิม (396, 361) 1 ครั้ง
            self.ctx.update_ui_status("🏺 กำลังเปิดชิ้นส่วน Relic... (รอ 10 วิ)", text_color="#fbbf24")
            self.start_time = now # รีเซ็ต timeout
            if now - self.relic_action_time >= 10.0:
                print(f"[{time.strftime('%H:%M:%S')}] 🏺 [Relic] ครบ 10 วิ -> กดยืนยันรับรางวัล (396, 361)")
                human_click_bg(self.ctx.hwnd, 396, 361, "รับรางวัล Relic (ยืนยัน)")
                self.relic_action_time = now
                self.relic_sub_step = 3
            return self

        elif self.relic_sub_step == 3:
            # ขั้นตอนที่ 5 จบ: รอ 1.5 วิ แล้วกดปิดที่ (671, 98) นับเวลาเข้าลูปเริ่มเกมรอบใหม่
            self.ctx.update_ui_status("🏺 กำลังปิดหน้าต่าง Relic...", text_color="#fbbf24")
            self.start_time = now # รีเซ็ต timeout
            if now - self.relic_action_time >= 1.5:
                print(f"[{time.strftime('%H:%M:%S')}] 🏺 [Relic] ปิดหน้าต่าง Relic (671, 98) สำเร็จ! เริ่มนับเวลาเพื่อเริ่มเกมรอบใหม่")
                human_click_bg(self.ctx.hwnd, 671, 98, "ปิดหน้าต่าง Relic (X)")
                self.relic_sub_step = 0
                self.relic_checked = True
                self.last_click_time = now
                if hasattr(self.ctx.app, "lobby_cooldown_end"):
                    self.ctx.app.lobby_cooldown_end = now + 1.5
            return self

        # ----------------- Check lobby rest cooldown -----------------
        cooldown_end = getattr(self.ctx.app, "lobby_cooldown_end", 0)
        if now < cooldown_end:
            remaining_sec = int(cooldown_end - now)
            self.ctx.update_ui_status(f"สถานะ: พักในหน้าหลัก ({remaining_sec}s)", text_color="#f39c12")

            # เช็ค Relic เมื่ออยู่ในช่วงพักหน้าหลัก (รอ 7 วิ ให้อนิเมชั่นหน้าหลักจบก่อนกดเปิด)
            if self.ctx.get_config("auto_relic", True) and not self.relic_checked and (self.elapsed_time() >= 7.0) and (now - self.last_click_time > 1.5):
                self._start_relic_check(now)

            return self

        self.ctx.update_ui_status("สถานะ: หน้าหลัก (Lobby)", text_color="#3498db")

        # หากเปิดฟังก์ชัน Auto Relic และยังไม่ได้เช็คในรอบนี้ ให้รอครบ 7 วิแล้วกดเช็ค Relic ก่อนกดเริ่มเกม
        if self.ctx.get_config("auto_relic", True) and not self.relic_checked:
            if self.elapsed_time() >= 7.0 and (now - self.last_click_time > 1.5):
                self._start_relic_check(now)
            return self

        found_match = False
        cx, cy = 647, 400

        if "playlobby" in self.ctx.autostart_templates:
            found, tx, ty = find_template_match(
                self.ctx.hwnd, frame, self.ctx.autostart_templates["playlobby"], threshold=0.50
            )
            if found and (560 <= tx <= 720) and (360 <= ty <= 430):
                found_match = True
                cx, cy = tx, ty

        # Click Play button
        if found_match and (now - self.last_click_time > 1.0):
            human_click_bg(self.ctx.hwnd, cx, cy, "Play (Lobby)")
            self.last_click_time = now
            return self._next_state()

        elif not found_match and (self.elapsed_time() > 6.0) and (now - self.last_click_time > 3.0):
            human_click_bg(self.ctx.hwnd, cx, cy, "Play (Fallback)")
            self.last_click_time = now
            return self._next_state()

        if self.is_timed_out():
            from .recovery_state import RecoveryState
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ [Timeout] ค้างหน้า Lobby ➔ Recovery")
            return RecoveryState(self.ctx)

        return self

    def _start_relic_check(self, now):
        """ขั้นตอนที่ 1 & 2: หยุดนับเวลาเริ่มเกมใหม่ชั่วคราว แล้วกดเปิดขวด Relic ที่ (325, 64)"""
        if hasattr(self.ctx.app, "lobby_cooldown_end"):
            self.ctx.app.lobby_cooldown_end = max(self.ctx.app.lobby_cooldown_end, now) + 25.0

        print(f"[{time.strftime('%H:%M:%S')}] 🏺 [Relic] กดเปิดหน้าต่าง Relic -> พิกัด (325, 64)")
        human_click_bg(self.ctx.hwnd, 325, 64, "เปิดหน้าต่าง Relic")
        self.relic_action_time = now
        self.relic_sub_step = 1

    def _next_state(self) -> BaseState:
        if self.ctx.get_config("buy_random_boost", False):
            from .buff_state import BuffState
            return BuffState(self.ctx)
        else:
            from .stage_start_state import StageStartState
            return StageStartState(self.ctx)
