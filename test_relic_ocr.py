# -*- coding: utf-8 -*-
"""
สคริปต์ทดสอบ RapidOCR สำหรับอ่านข้อความปุ่มเปิด Relic ที่พิกัด (X: 396, Y: 361)
รองรับการเลือกหน้าต่าง Emulator แบบระบุหมายเลข (1, 2, 3...)
"""
import os
import sys
import cv2
import numpy as np
import time

from window_manager import capture_window_bg, find_render_hwnd
from gameplay_controller import GameplayControllerCore
from rapidocr_onnxruntime import RapidOCR

def test_relic_claim_button_ocr(target_hwnd=None):
    print("=" * 65)
    print("  🏺 เครื่องมือทดสอบ OCR ปุ่ม Relic (X: 396, Y: 361)")
    print("=" * 65)

    ocr = RapidOCR()
    core = GameplayControllerCore()
    
    hwnd = target_hwnd
    target_title = ""

    if hwnd is None:
        windows = core.scan_mumu_windows()
        if not windows:
            print("\n❌ ไม่พบหน้าต่างโปรแกรมจำลอง (MuMu Player / LDPlayer) ในระบบ!")
            print("👉 กรุณาเปิดโปรแกรมจำลองขึ้นมาก่อน แล้วลองใหม่อีกครั้งครับ\n")
            return

        win_list = list(windows.items())
        
        print("\n🖥️  พบหน้าต่างโปรแกรมจำลองในระบบ ดังนี้:")
        for idx, (title, h) in enumerate(win_list, 1):
            print(f"  [{idx}] {title} (HWND: {h})")
        print("-" * 65)

        if len(win_list) == 1:
            target_title, hwnd = win_list[0]
            print(f"👉 ตรวจพบ 1 หน้าต่าง -> เลือก: '{target_title}' อัตโนมัติ")
        else:
            try:
                choice = input(f"\n👉 กรุณาพิมพ์หมายเลขหน้าต่างที่ต้องการ [1-{len(win_list)}] (กด Enter เพื่อเลือก 1): ").strip()
                if not choice:
                    selected_idx = 0
                else:
                    selected_idx = int(choice) - 1
                    if selected_idx < 0 or selected_idx >= len(win_list):
                        print("⚠️ หมายเลขไม่ถูกต้อง -> เลือกหน้าต่างที่ 1 เป็นค่าเริ่มต้น")
                        selected_idx = 0
            except Exception:
                selected_idx = 0

            target_title, hwnd = win_list[selected_idx]

    print(f"\n🎯 กำลังจับภาพจากหน้าต่าง: '{target_title}' (HWND: {hwnd})")
    frame = capture_window_bg(hwnd)
    if frame is None:
        print("❌ ไม่สามารถดึงภาพหน้าจอได้! กรุณาตรวจสอบว่าหน้าต่างไม่ได้ถูก Minimize ย่อไว้")
        return

    h_frame, w_frame = frame.shape[:2]
    print(f"🖼️ ขนาดภาพหน้าจอ: {w_frame}x{h_frame}")

    # กำหนดกรอบรอบตำแหน่ง (396, 361)
    y1, y2 = 335, 385
    x1, x2 = 330, 465

    roi = frame[y1:y2, x1:x2]
    roi_big = cv2.resize(roi, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)

    os.makedirs("scratch", exist_ok=True)
    cv2.imwrite("scratch/relic_claim_crop.png", roi)
    cv2.imwrite("scratch/relic_claim_crop_big.png", roi_big)
    
    # วาดกรอบสี่เหลี่ยมสีแดงบนภาพเต็มเพื่อดูตำแหน่งจริง
    debug_full = frame.copy()
    cv2.rectangle(debug_full, (x1, y1), (x2, y2), (0, 0, 255), 2)
    cv2.circle(debug_full, (396, 361), 5, (0, 255, 0), -1)
    cv2.putText(debug_full, "(396, 361)", (405, 365), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
    cv2.imwrite("scratch/relic_screen_marked.png", debug_full)

    print(f"\n🔍 กำลังรัน RapidOCR ในกรอบพิกัด Y:[{y1}:{y2}], X:[{x1}:{x2}]...")
    res, elapse = ocr(roi_big)

    raw_txt = ""
    print("\n--- 📋 ผลลัพธ์การตรวจจับข้อความ ---")
    if res:
        for idx, item in enumerate(res, 1):
            box, text, score = item[0], item[1], item[2]
            print(f"  [{idx}] ข้อความ: '{text}'  |  ความมั่นใจ: {score:.2f} ({score*100:.1f}%)")
            raw_txt += " " + text
        raw_txt = raw_txt.strip().upper()
    else:
        print("  ⚠️ RapidOCR ตรวจไม่พบตัวหนังสือในบริเวณนี้")

    print("\n--- 🎯 การวิเคราะห์เงื่อนไข ---")
    has_claim = False
    if any(k in raw_txt for k in ["CLAIM", "CLALM", "CLAM", "C1AIM", "LAIM", "AIM", "เคลม"]):
        has_claim = True
        print(f"  ✅ สรุป: ตรวจพบคำว่า 'CLAIM' สำเร็จ! 🎉 (ข้อความที่อ่าน: '{raw_txt}')")
        print("  👉 บอทจะทำการกดคลิก (396, 361) เพื่อเปิดรับรางวัลทันที")
    else:
        print(f"  ❌ สรุป: ไม่พบคำว่า 'CLAIM' (ข้อความที่อ่านได้: '{raw_txt}')")
        print("  👉 บอทจะทำการกดปิดหน้าต่างที่ (671, 98)")

    print("\n💾 บันทึกรูปภาพตรวจสอบไว้ที่:")
    print("  - scratch/relic_claim_crop.png (ภาพปุ่มที่ตัดมา)")
    print("  - scratch/relic_screen_marked.png (ภาพเต็มพร้อมจุดมาร์ก)")
    print("=" * 65)

if __name__ == "__main__":
    t_hwnd = int(sys.argv[1]) if len(sys.argv) > 1 else None
    test_relic_claim_button_ocr(t_hwnd)
