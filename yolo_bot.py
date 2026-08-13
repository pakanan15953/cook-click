# -*- coding: utf-8 -*-
"""
Cookie Run AI Bot - Modular Launcher Wrapper
This file maintains backward compatibility with existing batch files (Run_Bot.bat).
All core functionality has been refactored into clean modular files:
  - main.py                : Application entry point & ONNX Sequential setup
  - gui.py                 : CustomTkinter UI layout & StdoutRedirector (with RAM leak protection)
  - gameplay_controller.py : State machine, YOLO inference, RapidOCR buff selection & Rest Breaks
  - window_manager.py      : Background window capture with safe GDI try...finally cleanup
  - template_matcher.py    : Template matching & multi-template helpers
"""
import main

if __name__ == "__main__":
    app = main.CookieRunAIApp()
    app.mainloop()
