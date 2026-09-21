# -*- coding: utf-8 -*-
import time
from .context import BotContext
from .global_interceptor import GlobalInterceptor
from .states.lobby_state import LobbyState
from .states.playing_state import PlayingState
from .states.recovery_state import RecoveryState

class FSMEngine:
    """
    Finite State Machine Engine for Cookie Run Bot.
    Coordinates state transitions, runs global interceptors (freeze/popups),
    and ensures zero-crash execution.
    """
    def __init__(self, app_controller):
        self.ctx = BotContext(app_controller)
        self.interceptor = GlobalInterceptor(self.ctx)
        self.current_state = None
        self.reset()

    def reset(self):
        autostart = self.ctx.get_config("autostart_enabled", True)
        if autostart:
            self.current_state = LobbyState(self.ctx)
        else:
            self.current_state = PlayingState(self.ctx)
        self.current_state.on_enter()
        self.interceptor.reset_freeze_timer()

    def change_state(self, new_state):
        if new_state is not None and new_state != self.current_state:
            try:
                self.current_state.on_exit()
            except Exception as e:
                print(f"⚠️ [FSM] on_exit error in {self.current_state.state_name}: {e}")

            old_name = self.current_state.state_name.replace("State", "")
            new_name = new_state.state_name.replace("State", "")
            self.current_state = new_state
            print(f"🔄 [State] {old_name} ➔ {new_name}")

            try:
                self.current_state.on_enter()
            except Exception as e:
                print(f"⚠️ [FSM] on_enter error in {new_state.state_name}: {e}")

    def update(self, frame):
        """Processes one frame tick with error boundary."""
        if frame is None or self.ctx.hwnd is None:
            return

        try:
            # 1. Check Global Interceptors (Level Up popup, etc.)
            if self.interceptor.intercept(frame):
                return

            # 2. Check Screen Freeze (>18s static frame)
            # Only trigger freeze recovery if not resting or loading
            is_playing = isinstance(self.current_state, PlayingState)
            if self.interceptor.is_screen_frozen(max_seconds=18.0) and not is_playing:
                print(f"[{time.strftime('%H:%M:%S')}] 🚨 [FSM Engine] ตรวจพบหน้าจอค้างนิ่งเกิน 18 วินาที -> เข้าสู่ Recovery Mode")
                self.interceptor.reset_freeze_timer()
                self.change_state(RecoveryState(self.ctx))
                return

            # 3. Execute Current State
            next_state = self.current_state.execute(frame)
            if next_state is not None and next_state != self.current_state:
                self.change_state(next_state)

        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ❌ [FSM Exception] เกิดข้อผิดพลาดใน {self.current_state.state_name}: {e}")
            self.change_state(RecoveryState(self.ctx))
