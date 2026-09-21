# -*- coding: utf-8 -*-
import cv2
import numpy as np
import time
import random
from window_manager import human_click_bg
from template_matcher import find_template_match

class GlobalInterceptor:
    """
    Monitors global edge-cases that can happen at any state:
    - Level Up popup dismissal
    - Freeze detection (static frames for >15s)
    - Black/White screen detection
    """
    def __init__(self, context):
        self.ctx = context
        self.last_frame = None
        self.frozen_start_time = None
        self.last_levelup_click = 0

    def intercept(self, frame) -> bool:
        """
        Runs global checks. Returns True if an interceptor handled an event
        and the state machine should skip normal state execution for this tick.
        """
        if frame is None or self.ctx.hwnd is None:
            return False

        now = time.time()

        # 1. Level-Up Popup Detection
        if "confirmlevelup" in self.ctx.autostart_templates:
            found_lv, cx_lv, cy_lv = find_template_match(
                self.ctx.hwnd, frame, self.ctx.autostart_templates["confirmlevelup"], threshold=0.60
            )
            if found_lv and (now - self.last_levelup_click > 2.0):
                print(f"[{time.strftime('%H:%M:%S')}] ⭐ [Interceptor] ตรวจพบป๊อปอัป Level Up! ทำการคลิกปิดเพื่อไปต่อ...")
                human_click_bg(self.ctx.hwnd, cx_lv, cy_lv, "Level Up Close Button")
                self.last_levelup_click = now
                time.sleep(random.uniform(1.0, 2.0))
                return True

        # 1.1 League / Notice Modal Popup Detection (Green Confirm Button)
        if "popup_confirm_green" in self.ctx.autostart_templates:
            found_pop, cx_pop, cy_pop = find_template_match(
                self.ctx.hwnd, frame, self.ctx.autostart_templates["popup_confirm_green"], threshold=0.55
            )
            if found_pop and (now - getattr(self, "last_popup_click", 0) > 1.5):
                print(f"[{time.strftime('%H:%M:%S')}] 📢 [Interceptor] ตรวจพบป๊อปอัปแจ้งเตือน (League / Notice)! ทำการกดปุ่ม Confirm (X: {cx_pop}, Y: {cy_pop})...")
                human_click_bg(self.ctx.hwnd, cx_pop, cy_pop, "Popup Confirm Button")
                self.last_popup_click = now
                time.sleep(random.uniform(0.5, 1.0))
                return True

        # 2. Freeze Detection (Frame Difference)
        if self.last_frame is not None and self.last_frame.shape == frame.shape:
            try:
                gray1 = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2GRAY)
                gray2 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                diff = cv2.absdiff(gray1, gray2)
                non_zero = np.count_nonzero(diff > 8)
                total_pixels = frame.shape[0] * frame.shape[1]
                
                # If less than 0.05% of pixels changed, frame is stationary
                if non_zero < (total_pixels * 0.0005):
                    if self.frozen_start_time is None:
                        self.frozen_start_time = now
                else:
                    self.frozen_start_time = None
            except Exception:
                self.frozen_start_time = None

        self.last_frame = frame.copy()
        return False

    def is_screen_frozen(self, max_seconds=18.0) -> bool:
        if self.frozen_start_time is not None:
            return (time.time() - self.frozen_start_time) > max_seconds
        return False

    def reset_freeze_timer(self):
        self.frozen_start_time = None
