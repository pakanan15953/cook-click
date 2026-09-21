# -*- coding: utf-8 -*-
import time
import random
from ..base_state import BaseState
from window_manager import human_click_bg
from template_matcher import find_template_match

class GameOverState(BaseState):
    def __init__(self, context):
        super().__init__(context, timeout_seconds=25.0)
        self.ok_clicks = 0
        self.last_action_time = 0

    def on_enter(self):
        super().on_enter()
        self.ctx.update_ui_status("สถานะ: สรุปผลคะแนน (Game Over)", text_color="#f39c12")
        self.last_action_time = time.time()

    def execute(self, frame) -> BaseState:
        now = time.time()

        found_openall, _, _ = find_template_match(
            self.ctx.hwnd, frame, self.ctx.autostart_templates.get("openall", None), threshold=0.48
        )
        found_confirm, _, _ = find_template_match(
            self.ctx.hwnd, frame, self.ctx.autostart_templates.get("confirmafteropenall", None), threshold=0.48
        )
        found_lobby, rx, ry = find_template_match(
            self.ctx.hwnd, frame, self.ctx.autostart_templates.get("playlobby", None), threshold=0.56
        )

        if found_openall or found_confirm:
            from .reward_state import RewardState
            return RewardState(self.ctx)

        elif found_lobby and (560 <= rx <= 720) and (360 <= ry <= 430):
            wait_sec = random.uniform(15.0, 20.0)
            print(f"[{time.strftime('%H:%M:%S')}] 🏠 พัก {wait_sec:.0f}s ก่อนเริ่มรอบใหม่")
            self.ctx.set_config("lobby_cooldown_end", now + wait_sec)
            from .lobby_state import LobbyState
            return LobbyState(self.ctx)

        else:
            if self.ok_clicks < 2 and (now - self.last_action_time > 1.2):
                human_click_bg(self.ctx.hwnd, 285, 386, "OK")
                self.ok_clicks += 1
                self.last_action_time = now
            elif now - self.last_action_time > 2.5:
                wait_sec = random.uniform(15.0, 20.0)
                print(f"[{time.strftime('%H:%M:%S')}] 🏠 พัก {wait_sec:.0f}s ก่อนเริ่มรอบใหม่")
                self.ctx.set_config("lobby_cooldown_end", now + wait_sec)
                from .lobby_state import LobbyState
                return LobbyState(self.ctx)

        if self.is_timed_out():
            from .recovery_state import RecoveryState
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ [Timeout] ค้างหน้าสรุปผล ➔ Recovery")
            return RecoveryState(self.ctx)

        return self
