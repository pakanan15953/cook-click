# -*- coding: utf-8 -*-
import time
import random
from ..base_state import BaseState
from window_manager import human_click_bg
from template_matcher import find_template_match

class RewardState(BaseState):
    PHASE_OPENALL = "OPENALL"
    PHASE_CONFIRM = "CONFIRM"

    def __init__(self, context):
        super().__init__(context, timeout_seconds=30.0)
        self.phase = self.PHASE_OPENALL
        self.confirm_clicks = 0
        self.last_action_time = 0

    def on_enter(self):
        super().on_enter()
        self.ctx.update_ui_status("สถานะ: เปิดกล่องสมบัติ (Reward)", text_color="#f39c12")
        self.last_action_time = time.time()

    def execute(self, frame) -> BaseState:
        now = time.time()

        found_openall, cx_o, cy_o = find_template_match(
            self.ctx.hwnd, frame, self.ctx.autostart_templates.get("openall", None), threshold=0.48
        )
        found_confirm, cx_c, cy_c = find_template_match(
            self.ctx.hwnd, frame, self.ctx.autostart_templates.get("confirmafteropenall", None), threshold=0.48
        )
        found_lobby, rx, ry = find_template_match(
            self.ctx.hwnd, frame, self.ctx.autostart_templates.get("playlobby", None), threshold=0.56
        )

        if self.phase == self.PHASE_OPENALL:
            if found_openall:
                print(f"[{time.strftime('%H:%M:%S')}] 🎁 [FSM] คลิกเปิดกล่องสมบัติ (Open All)...")
                human_click_bg(self.ctx.hwnd, cx_o, cy_o, "Open All Chests Button")
                self.last_action_time = now
                self.phase = self.PHASE_CONFIRM
                self.confirm_clicks = 0
            elif found_confirm:
                self.phase = self.PHASE_CONFIRM
            elif (found_lobby and (560 <= rx <= 720) and (360 <= ry <= 430)) or (now - self.last_action_time > 3.0):
                return self._return_to_lobby(now)

        elif self.phase == self.PHASE_CONFIRM:
            if found_confirm and (now - self.last_action_time > 0.8):
                self.confirm_clicks += 1
                print(f"[{time.strftime('%H:%M:%S')}] 🎁 [FSM] ยืนยันหลังเปิดกล่อง (รอบที่ {self.confirm_clicks}) -> ({cx_c}, {cy_c})")
                human_click_bg(self.ctx.hwnd, cx_c, cy_c, f"Confirm After Open All ({self.confirm_clicks})")
                self.last_action_time = now
                if self.confirm_clicks >= 2:
                    return self._return_to_lobby(now)

            elif self.confirm_clicks >= 1 and (now - self.last_action_time > 1.2) and not found_lobby:
                print(f"[{time.strftime('%H:%M:%S')}] 🎁 [FSM] ยืนยันหลังเปิดกล่อง (รอบที่ 2 สำรอง) -> (400, 400)")
                human_click_bg(self.ctx.hwnd, 400, 400, "Confirm After Open All (Fallback)")
                self.last_action_time = now
                self.confirm_clicks = 2
                return self._return_to_lobby(now)

            elif (found_lobby and (560 <= rx <= 720) and (360 <= ry <= 430)) or (now - self.last_action_time > 3.5):
                return self._return_to_lobby(now)

        if self.is_timed_out():
            from .recovery_state import RecoveryState
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ [FSM] เปิดกล่องนานเกินกำหนด -> เข้าสู่ Recovery Mode")
            return RecoveryState(self.ctx)

        return self

    def _return_to_lobby(self, now) -> BaseState:
        wait_sec = random.uniform(15.0, 20.0)
        print(f"[{time.strftime('%H:%M:%S')}] 🏠 [FSM] จบการเปิดกล่อง -> พักรอหน้าหลัก {wait_sec:.0f} วินาทีก่อนเริ่มรอบถัดไป...")
        self.ctx.set_config("lobby_cooldown_end", now + wait_sec)
        from .lobby_state import LobbyState
        return LobbyState(self.ctx)
