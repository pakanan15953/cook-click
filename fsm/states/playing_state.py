# -*- coding: utf-8 -*-
import time
import random
from ..base_state import BaseState
from window_manager import (
    human_click_bg, human_press_bg,
    VK_LSHIFT, SCAN_SHIFT, VK_SPACE, SCAN_SPACE, VK_ALT, SCAN_ALT
)
from template_matcher import find_template_match, find_best_template_match

class PlayingState(BaseState):
    def __init__(self, context, is_loading=False):
        super().__init__(context, timeout_seconds=360.0) # Up to 6 mins per run
        self.is_loading = is_loading
        self.loading_start_time = time.time()
        self.last_endgame_check_time = 0
        self.last_switch_check_time = 0
        self.last_jump_time = 0
        self.last_slide_time = 0
        self.last_action_time = time.time()

    def on_enter(self):
        super().on_enter()
        if self.is_loading:
            self.ctx.update_ui_status("สถานะ: กำลังโหลดเข้าเกม...", text_color="#f39c12")
        else:
            self.ctx.update_ui_status("สถานะ: กำลังวิ่ง (PLAYING)", text_color="#2ecc71")

    def execute(self, frame) -> BaseState:
        now = time.time()

        # ----------------- 1. Loading Phase -----------------
        if self.is_loading:
            if now - self.loading_start_time > 4.0:
                self.is_loading = False
                self.ctx.update_ui_status("สถานะ: กำลังวิ่ง (PLAYING)", text_color="#2ecc71")
                self.last_action_time = now
            return self

        # ----------------- 2. Game Over (OK Button) Check -----------------
        if now - self.last_endgame_check_time > 0.35:
            self.last_endgame_check_time = now
            found_ok = False
            cx_ok, cy_ok = 285, 386

            if "ok" in self.ctx.autostart_templates:
                f_ok, tx_ok, ty_ok = find_template_match(
                    self.ctx.hwnd, frame, self.ctx.autostart_templates["ok"], threshold=0.48
                )
                if f_ok and (220 <= tx_ok <= 350) and (340 <= ty_ok <= 430):
                    found_ok = True
                    cx_ok, cy_ok = tx_ok, ty_ok

            if found_ok:
                rest_enabled = self.ctx.get_config("rest_breaks_enabled", True)
                curr_runs = self.ctx.get_config("current_session_runs", 0)
                target_runs = self.ctx.get_config("target_session_runs", 10)

                if rest_enabled and curr_runs >= target_runs:
                    from .resting_state import RestingState
                    return RestingState(self.ctx)
                else:
                    human_click_bg(self.ctx.hwnd, cx_ok, cy_ok, "OK (Game Over)")
                    from .gameover_state import GameOverState
                    return GameOverState(self.ctx)

        # ----------------- 3. Relay (Character Switch) Check -----------------
        use_relay = self.ctx.get_config("use_relay", True)
        if use_relay and (now - self.last_action_time > 10.0) and self.ctx.relay_templates:
            if now - self.last_switch_check_time > 0.4:
                self.last_switch_check_time = now
                found_relay, rx, ry, rscore, rname = find_best_template_match(
                    self.ctx.hwnd, frame, self.ctx.relay_templates, threshold=0.52
                )
                if found_relay and (rx >= 420 or ry <= 240):
                    print(f"[{time.strftime('%H:%M:%S')}] 👥 สลับตัวผลัด 2")
                    human_press_bg(self.ctx.hwnd, VK_ALT, SCAN_ALT, duration_min=0.08, duration_max=0.15)
                    self.last_action_time = now

        # ----------------- 4. YOLO AI Detection & Obstacle Avoidance -----------------
        model = self.ctx.model
        auto_jump = self.ctx.get_config("auto_jump", True)
        auto_slide = self.ctx.get_config("auto_slide", True)

        if model is not None and (auto_jump or auto_slide):
            self._process_yolo_gameplay(frame, model, now)

        if self.is_timed_out():
            from .recovery_state import RecoveryState
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ [Timeout] วิ่งนานเกิน ➔ Recovery")
            return RecoveryState(self.ctx)

        return self

    def _process_yolo_gameplay(self, frame, model, now):
        conf_val = self.ctx.get_config("conf_val", 0.35)
        trigger_dist = self.ctx.get_config("trigger_dist", 185)
        slide_hold_ms = self.ctx.get_config("slide_hold_ms", 350)
        device_str = self.ctx.get_config("device_str", "cpu")

        is_pt = str(getattr(model, "ckpt_path", "")).endswith(".pt") or str(getattr(model, "model_name", "")).endswith(".pt")
        dev = device_str if is_pt else "cpu"

        results = model(frame, conf=conf_val, device=dev, verbose=False)

        cookie_box = None
        detected_objects = []

        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls_id = int(box.cls[0].item())
                c_name = model.names[cls_id]
                conf = float(box.conf[0].item())
                coords = [int(v) for v in box.xyxy[0].tolist()]

                if c_name == "cookie":
                    cookie_box = coords
                else:
                    detected_objects.append((coords[0], coords[1], coords[2], coords[3], c_name, conf))

        cookie_right_x = cookie_box[2] if cookie_box else self.ctx.get_config("FALLBACK_COOKIE_X", 220)

        # Dynamic Speed Estimation
        last_obs_x = self.ctx.get_config("last_obstacle_x", None)
        last_obs_time = self.ctx.get_config("last_obstacle_time", None)
        estimated_speed = self.ctx.get_config("estimated_speed", 350.0)

        moving_obstacles = [obj for obj in detected_objects if obj[4] in ["jump_obs", "slide_obs", "double_jump_obs", "jump_potato"]]
        if moving_obstacles:
            closest_obs = min(moving_obstacles, key=lambda o: o[0])
            current_obs_x = closest_obs[0]
            if last_obs_x is not None and last_obs_time is not None:
                dt = now - last_obs_time
                dx = last_obs_x - current_obs_x
                if 0.015 < dt < 0.15 and 0 < dx < 200:
                    inst_speed = dx / dt
                    estimated_speed = 0.82 * estimated_speed + 0.18 * inst_speed
                    self.ctx.set_config("estimated_speed", estimated_speed)

            self.ctx.set_config("last_obstacle_x", current_obs_x)
            self.ctx.set_config("last_obstacle_time", now)

        trigger_ttc = trigger_dist / 350.0

        jump_obstacles = []
        closest_obstacle_info = None
        min_dist = float('inf')

        for x1, y1, x2, y2, c_name, conf in detected_objects:
            if c_name in ["jump_obs", "slide_obs", "double_jump_obs", "jump_potato", "raised_floor", "coin"]:
                dist = x1 - cookie_right_x
                if 0 < dist < min_dist:
                    min_dist = dist
                    closest_obstacle_info = (x1, y1, x2, y2, c_name, dist)
                if c_name in ["jump_obs", "jump_potato", "double_jump_obs"] and dist > 0:
                    jump_obstacles.append((x1, x2))

        jump_obstacles.sort(key=lambda o: o[0])

        found_jump = False
        found_double_jump = False
        found_slide = False

        if closest_obstacle_info is not None:
            obs_x1, obs_y1, obs_x2, obs_y2, obs_name, dist = closest_obstacle_info
            obs_ttc = dist / max(estimated_speed, 1.0)

            if obs_ttc <= trigger_ttc:
                if obs_name in ["jump_obs", "jump_potato", "double_jump_obs", "raised_floor", "coin"]:
                    if obs_name == "double_jump_obs":
                        found_double_jump = True
                    elif len(jump_obstacles) >= 2:
                        gap_px = jump_obstacles[1][0] - jump_obstacles[0][1]
                        if (gap_px / max(estimated_speed, 1.0)) < 0.35:
                            found_double_jump = True
                        else:
                            found_jump = True
                    else:
                        found_jump = True
                elif obs_name == "slide_obs":
                    found_slide = True

        # Cliff radar detection
        ground_boxes = [(x1, x2, y1, y2) for x1, y1, x2, y2, c_name, conf in detected_objects if c_name == "ground"]
        for x1, x2, y1, y2 in ground_boxes:
            if x1 <= 220 and x2 >= 180:
                dist_to_cliff = x2 - 220
                cliff_ttc = dist_to_cliff / max(estimated_speed, 1.0)
                if 0.03 < cliff_ttc <= 0.45:
                    has_cont = any(0 <= (nx1 - x2) < 45 for nx1, nx2, ny1, ny2 in ground_boxes)
                    if not has_cont:
                        has_cont = any(0 <= (rx1 - x2) < 45 for rx1, ry1, rx2, ry2, rc_name, rconf in detected_objects if rc_name == "raised_floor")
                    if not has_cont:
                        found_jump = True
                        break

        # Execute Actions
        if found_double_jump and (now - self.last_jump_time > 0.48):
            print(f"[{time.strftime('%H:%M:%S')}] 🦘 Jump (Double)")
            human_press_bg(self.ctx.hwnd, VK_LSHIFT, SCAN_SHIFT, duration_min=0.05, duration_max=0.08)
            self.ctx.schedule_callback(170, lambda: human_press_bg(self.ctx.hwnd, VK_LSHIFT, SCAN_SHIFT, duration_min=0.05, duration_max=0.08))
            self.last_jump_time = now

        elif found_jump and (now - self.last_jump_time > 0.35):
            print(f"[{time.strftime('%H:%M:%S')}] 🦘 Jump (Single)")
            human_press_bg(self.ctx.hwnd, VK_LSHIFT, SCAN_SHIFT, duration_min=0.06, duration_max=0.10)
            self.last_jump_time = now

        elif found_slide and (now - self.last_slide_time > 0.32):
            print(f"[{time.strftime('%H:%M:%S')}] 🛹 Slide")
            human_press_bg(self.ctx.hwnd, VK_SPACE, SCAN_SPACE, duration_min=slide_hold_ms / 1000.0, duration_max=(slide_hold_ms + 100) / 1000.0)
            self.last_slide_time = now
