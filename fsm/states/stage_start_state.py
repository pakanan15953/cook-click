# -*- coding: utf-8 -*-
import time
from ..base_state import BaseState
from window_manager import human_click_bg
from template_matcher import find_template_match

class StageStartState(BaseState):
    def __init__(self, context):
        super().__init__(context, timeout_seconds=20.0)

    def on_enter(self):
        super().on_enter()
        self.ctx.update_ui_status("สถานะ: หน้าเตรียมตัวก่อนวิ่ง", text_color="#3498db")

    def execute(self, frame) -> BaseState:
        now = time.time()

        if self.elapsed_time() >= 1.5:
            found_start = False
            cx_s, cy_s = 670, 390

            if "playlobby" in self.ctx.autostart_templates:
                found, tx, ty = find_template_match(
                    self.ctx.hwnd, frame, self.ctx.autostart_templates["playlobby"], threshold=0.48
                )
                if found and (600 <= tx <= 740) and (350 <= ty <= 430):
                    found_start = True
                    cx_s, cy_s = tx, ty

            human_click_bg(self.ctx.hwnd, cx_s, cy_s, "Start Game")

            current_runs = self.ctx.get_config("current_session_runs", 0) + 1
            self.ctx.set_config("current_session_runs", current_runs)
            self.ctx.update_session_label()

            from .playing_state import PlayingState
            return PlayingState(self.ctx, is_loading=True)

        if self.is_timed_out():
            from .recovery_state import RecoveryState
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ [Timeout] ค้างหน้า Start ➔ Recovery")
            return RecoveryState(self.ctx)

        return self
