# pyrefly: ignore [missing-import]
import cv2
# pyrefly: ignore [missing-import]
import mss
import numpy as np
import threading
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional, Callable, Dict, Any
# pyrefly: ignore [missing-import]
from skimage.metrics import structural_similarity as ssim


from src.config import config

logger = logging.getLogger(__name__)

class ScreenshotManager:
    """Handles saving raw and annotated screenshots to disk."""
    def __init__(self):
        self.screenshots_dir = config.SCREENSHOTS_DIR
        self.annotated_dir = config.ANNOTATED_DIR

    def apply_roi(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = 0, 0, w, h
        
        # Apply strict coordinate ROI if enabled
        if config.ROI_ENABLED and config.ROI_WIDTH > 0 and config.ROI_HEIGHT > 0:
            x1 = max(0, config.ROI_X)
            y1 = max(0, config.ROI_Y)
            x2 = min(w, x1 + config.ROI_WIDTH)
            y2 = min(h, y1 + config.ROI_HEIGHT)
            
        # Apply smart inner crop (margins) for tabs/taskbar
        if config.SMART_CONTENT_CROP:
            y1 = min(y2, y1 + config.CONTENT_MARGIN_TOP)
            y2 = max(y1, y2 - config.CONTENT_MARGIN_BOTTOM)

        if x2 > x1 and y2 > y1 and (x1 > 0 or y1 > 0 or x2 < w or y2 < h):
            return frame[y1:y2, x1:x2]
        return frame

    def save_screenshot(self, frame: np.ndarray, prefix: str = "capture_") -> Tuple[str, str]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        filename = f"{prefix}{timestamp}.png"
        filepath = self.screenshots_dir / filename
        try:
            cv2.imwrite(str(filepath), frame)
            return str(filepath), filename
        except Exception as e:
            logger.error(f"Failed to save screenshot: {e}")
            return "", ""

    def save_annotated(self, frame: np.ndarray, original_filename: str) -> str:
        filepath = self.annotated_dir / f"annotated_{original_filename}"
        try:
            cv2.imwrite(str(filepath), frame)
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save annotated screenshot: {e}")
            return ""

class ScreenChangeDetector:
    """Detects visual changes in the screen using SSIM."""
    def __init__(self, threshold: float = 0.95):
        self.threshold = threshold
        self.last_frame = None

    def reset(self):
        self.last_frame = None

    def has_significant_change(self, frame: np.ndarray) -> bool:
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.last_frame is None:
            self.last_frame = gray_frame
            return True
            
        score, _ = ssim(self.last_frame, gray_frame, full=True)
        is_changed = score < self.threshold
        
        if is_changed:
            self.last_frame = gray_frame
            
        return is_changed

class ScreenshotEngine:
    """Monitors screen for changes and handles manual captures."""
    def __init__(self, on_screenshot: Callable[[str, str, int, int], None]):
        self.on_screenshot = on_screenshot
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        self.change_detector = ScreenChangeDetector(threshold=config.SCREENSHOT_THRESHOLD)
        self.manager = ScreenshotManager()
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1]


    def start(self):
        self.running = True
        self.change_detector.reset()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        logger.info("Screenshot engine started.")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Screenshot engine stopped.")

    def _grab_frame(self) -> Optional[np.ndarray]:
        try:
            sct_img = self.sct.grab(self.monitor)
            img = np.array(sct_img)
            bgr_img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            # Dynamic Active Window ROI
            if config.DYNAMIC_ROI_ENABLED:
                try:
                    # pyrefly: ignore [missing-import]
                    import pygetwindow as gw
                    window = gw.getActiveWindow()
                    if window:
                        x1 = max(0, window.left - self.monitor["left"])
                        y1 = max(0, window.top - self.monitor["top"])
                        x2 = min(bgr_img.shape[1], x1 + window.width)
                        y2 = min(bgr_img.shape[0], y1 + window.height)
                        if x2 > x1 and y2 > y1:
                            bgr_img = bgr_img[y1:y2, x1:x2]
                except Exception as e:
                    logger.error(f"Dynamic ROI failed: {e}")
                    
            return self.manager.apply_roi(bgr_img)
        except Exception as e:
            logger.error(f"Failed to grab frame: {e}")
            return None

    def on_mouse_event(self, event: Dict[str, Any]):
        if not config.SCREENSHOT_ON_CLICK:
            return
            
        ev_type = event.get("event")
        if ev_type in ["left_click", "right_click", "double_click"]:
            frame = self._grab_frame()
            if frame is not None:
                raw_path, _ = self.manager.save_screenshot(frame, "click_")

                
                # Offset coordinates relative to the captured monitor
                x = int(event.get("x", 0)) - self.monitor["left"]
                y = int(event.get("y", 0)) - self.monitor["top"]
                
                # Offset coordinates further if ROI is applied
                if config.ROI_ENABLED and config.ROI_WIDTH > 0 and config.ROI_HEIGHT > 0:
                    x -= config.ROI_X
                    y -= config.ROI_Y
                
                self.on_screenshot(raw_path, ev_type, x, y)


    def _loop(self):
        # Disabled automatic pixel-change screenshots.
        # Screenshots will now only trigger on explicit actions (e.g. clicks).
        while self.running:
            time.sleep(0.1)

def annotate_in_thread(filepath: str, x: int, y: int, trigger_type: str, callback: Callable[[str], None]):
    """Adds a visual marker on the screenshot asynchronously."""
    def worker():
        try:
            frame = cv2.imread(filepath)
            if frame is None:
                callback("")
                return
                
            mgr = ScreenshotManager()
            if "click" in trigger_type:
                # 5. Create a Zoom-In View (Crop)
                crop_size = 200
                x1_crop = max(0, x - crop_size)
                y1_crop = max(0, y - crop_size)
                x2_crop = min(frame.shape[1], x + crop_size)
                y2_crop = min(frame.shape[0], y + crop_size)
                crop = frame[y1_crop:y2_crop, x1_crop:x2_crop]
                crop_path = mgr.annotated_dir / f"crop_{Path(filepath).name}"
                cv2.imwrite(str(crop_path), crop)
                
                # 3. Highlight the Entire Clicked UI Region
                padding = 40
                x1_box = max(0, x - padding)
                y1_box = max(0, y - padding)
                x2_box = min(frame.shape[1], x + padding)
                y2_box = min(frame.shape[0], y + padding)
                cv2.rectangle(frame, (x1_box, y1_box), (x2_box, y2_box), (0, 255, 255), 2)

                # 2. Draw a Crosshair Instead of Only a Circle
                color = (0, 0, 255) # Red for click
                cv2.circle(frame, (x, y), 20, color, 3)
                cv2.line(frame, (x - 25, y), (x + 25, y), color, 2)
                cv2.line(frame, (x, y - 25), (x, y + 25), color, 2)
                cv2.circle(frame, (x, y), 4, color, -1)

                # 4. Add Click Metadata
                label = f"{trigger_type} ({x},{y})"
                cv2.putText(frame, label, (x + 30, y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
                # 6. Verify Coordinate Alignment
                logger.info(f"Click: ({x},{y}) Image: {frame.shape[1]}x{frame.shape[0]}")
                
            filename = Path(filepath).name
            annotated_path = mgr.save_annotated(frame, filename)
            callback(annotated_path)
        except Exception as e:
            logger.error(f"Annotation error: {e}")
            callback("")
            
    threading.Thread(target=worker, daemon=True).start()
