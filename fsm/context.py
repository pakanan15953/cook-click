# -*- coding: utf-8 -*-
import time
import random

class BotContext:
    """
    Shared Context holds common resources, configurations, helper methods,
    and runtime metrics shared across all FSM states.
    """
    def __init__(self, app_controller):
        self.app = app_controller

    @property
    def hwnd(self):
        return self.app.hwnd

    @property
    def autostart_templates(self):
        return getattr(self.app, "autostart_templates", {})

    @property
    def relay_templates(self):
        return getattr(self.app, "relay_templates", [])

    @property
    def boost_start_templates(self):
        return getattr(self.app, "boost_start_templates", [])

    @property
    def model(self):
        return getattr(self.app, "model", None)

    @property
    def ocr_engine(self):
        return getattr(self.app, "ocr_engine", None)

    def update_ui_status(self, text, text_color="#f39c12", color=None):
        """Safely update UI status label."""
        final_color = color if color is not None else text_color
        if hasattr(self.app, "bot_status_label") and self.app.bot_status_label:
            try:
                self.app.bot_status_label.configure(text=text, text_color=final_color)
            except Exception:
                pass

    def update_session_label(self):
        if hasattr(self.app, "update_session_label"):
            try:
                self.app.update_session_label()
            except Exception:
                pass

    def schedule_callback(self, delay_ms, callback):
        """Schedule a delayed callback on the Tkinter main thread."""
        if hasattr(self.app, "after"):
            self.app.after(delay_ms, callback)
        else:
            time.sleep(delay_ms / 1000.0)
            callback()

    def get_config(self, key, default=None):
        return getattr(self.app, key, default)

    def set_config(self, key, value):
        setattr(self.app, key, value)
