import sys
import os
sys.path.insert(0, os.path.abspath("."))
import win32gui
import cv2
import numpy as np
from window_manager import find_render_hwnd, _printwindow_capture
from rapidocr_onnxruntime import RapidOCR

def test_hwnd(hwnd):
    ocr = RapidOCR()
    render_h = find_render_hwnd(hwnd)
    print(f"Parent HWND: {hwnd} -> Render HWND: {render_h}")
    
    img = _printwindow_capture(render_h)
    if img is None:
        print("Fallback to parent capture...")
        img = _printwindow_capture(hwnd)
        
    if img is None:
        print("❌ Cannot capture frame")
        return
        
    print(f"Captured shape: {img.shape}")
    frame = cv2.resize(img, (800, 450))
    cv2.imwrite("scratch/lobby_full.png", frame)
    
    # Crop user coordinates: x: 300-350, y: 50-80
    roi1 = frame[50:80, 300:350]
    # Crop slightly wider: x: 280-380, y: 35-95
    roi2 = frame[35:95, 280:380]
    
    cv2.imwrite("scratch/relic_roi1.png", roi1)
    cv2.imwrite("scratch/relic_roi2.png", roi2)
    
    roi1_big = cv2.resize(roi1, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    res1, _ = ocr(roi1_big)
    print("\n🔍 OCR Result [x: 300-350, y: 50-80]:")
    if res1:
        for it in res1:
            print(f"  👉 '{it[1]}' (conf: {it[2]:.2f})")
    else:
        print("  (No text detected)")
        
    roi2_big = cv2.resize(roi2, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    res2, _ = ocr(roi2_big)
    print("\n🔍 OCR Result [x: 280-380, y: 35-95]:")
    if res2:
        for it in res2:
            print(f"  👉 '{it[1]}' (conf: {it[2]:.2f})")
    else:
        print("  (No text detected)")

if __name__ == "__main__":
    import sys
    h = int(sys.argv[1]) if len(sys.argv) > 1 else 262182
    test_hwnd(h)
