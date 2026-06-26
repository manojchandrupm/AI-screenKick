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
from typing import Optional, Callable

from src.config import config

logger = logging.getLogger(__name__)

class ScreenRecorder:
    """Continuously records the screen and saves to an MP4 file."""

    def __init__(self, on_fps_update: Optional[Callable[[float], None]] = None):
        self.output_dir = config.RECORDINGS_DIR
        self.fps = config.RECORDING_FPS
        self.on_fps_update = on_fps_update
        self.is_recording = False
        self.thread: Optional[threading.Thread] = None
        self.video_writer = None
        self._filepath: Optional[Path] = None

    @property
    def filepath(self) -> Optional[Path]:
        return self._filepath

    def start(self) -> None:
        if self.is_recording:
            return
            
        self.is_recording = True
        self.thread = threading.Thread(target=self._record_loop, daemon=True)
        self.thread.start()
        
        # Start FPS reporter thread
        if self.on_fps_update:
            threading.Thread(target=self._fps_reporter, daemon=True).start()
            
        logger.info("Screen recording started.")

    def stop(self) -> None:
        if not self.is_recording:
            return
        self.is_recording = False
        if self.thread:
            self.thread.join()
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        logger.info(f"Screen recording stopped. Saved to {self._filepath}")

    def _fps_reporter(self) -> None:
        while self.is_recording:
            if self.on_fps_update:
                self.on_fps_update(float(self.fps))
            time.sleep(1)

    def _record_loop(self) -> None:
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                width = monitor["width"]
                height = monitor["height"]
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self._filepath = self.output_dir / f"session_{timestamp}.mp4"
                
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                self.video_writer = cv2.VideoWriter(str(self._filepath), fourcc, self.fps, (width, height))

                frame_duration = 1.0 / self.fps
                
                while self.is_recording:
                    start_time = time.time()
                    
                    sct_img = sct.grab(monitor)
                    img = np.array(sct_img)
                    
                    # Convert from BGRA to BGR
                    frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    self.video_writer.write(frame)
                    
                    elapsed = time.time() - start_time
                    sleep_time = max(0, frame_duration - elapsed)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
        except Exception as e:
            logger.error(f"Error in screen recording loop: {e}")
            self.is_recording = False
