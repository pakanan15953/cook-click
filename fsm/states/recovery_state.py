# -*- coding: utf-8 -*-
import time
from ..base_state import BaseState
from window_manager import human_click_bg

class RecoveryState(BaseState):
    def __init__(self, context):
        super().__init__(context, timeout_seconds=12.0)
        self.recovery_attempts = 0

    def on_enter(self):
        super().on_enter()
        self.ctx.update_ui_status("สถานะ: กำลังกู้คืนระบบ (Recovery)", text_color="#e74c3c")
        print(f"[{time.strftime('%H:%M:%S')}] 🛟 [FSM Recovery] กำลังเคลียร์หน้าต่างป๊อปอัปและรีเซ็ตหน้าจอ...")

    def execute(self, frame) -> BaseState:
        # Common close / dismiss coordinates: top-right X, modal close, center dismiss
        close_targets = [
            (607, 60, "Watchdog Close (X)"),
            (740, 50, "Top-Right Close (X)"),
            (400, 400, "Center Dismiss Click"),
            (285, 386, "Fallback Confirm Button")
        ]

        for cx, cy, name in close_targets:
            try:
                human_click_bg(self.ctx.hwnd, cx, cy, name)
                time.sleep(0.4)
            except Exception:
                pass

        print(f"[{time.strftime('%H:%M:%S')}] ✅ [FSM Recovery] ดำเนินการเคลียร์หน้าจอเสร็จสิ้น -> กลับสู่ Lobby")
        
        from .lobby_state import LobbyState
        return LobbyState(self.ctx)
