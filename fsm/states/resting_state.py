# -*- coding: utf-8 -*-
import time
import random
from ..base_state import BaseState

class RestingState(BaseState):
    def __init__(self, context):
        rest_duration = random.uniform(480, 1080) # 8 to 18 minutes
        super().__init__(context, timeout_seconds=rest_duration + 60.0)
        self.rest_end_time = time.time() + rest_duration
        self.rest_duration_mins = rest_duration / 60.0

    def on_enter(self):
        super().on_enter()
        print(f"[{time.strftime('%H:%M:%S')}] 💤 [FSM] ครบเซสชันการเล่น -> พักเบรก {self.rest_duration_mins:.1f} นาที")
        self.ctx.set_config("rest_end_time", self.rest_end_time)
        self.ctx.update_session_label()

    def execute(self, frame) -> BaseState:
        now = time.time()
        remaining = self.rest_end_time - now

        if remaining > 0:
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            self.ctx.update_ui_status(f"กำลังพัก ({mins:02d}:{secs:02d})", text_color="#f39c12")
            return self
        else:
            print(f"[{time.strftime('%H:%M:%S')}] ☀️ [FSM] หมดเวลาพักผ่อนแล้ว! กำลังเริ่มเล่นเซสชันถัดไป...")
            self.ctx.set_config("current_session_runs", 0)
            limit = self.ctx.get_config("max_session_runs_limit", 12)
            lower = max(5, limit - 3)
            self.ctx.set_config("target_session_runs", random.randint(lower, limit))
            self.ctx.update_session_label()

            from .lobby_state import LobbyState
            return LobbyState(self.ctx)
