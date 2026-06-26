import logging
from typing import Callable, Dict, Any, Optional

try:
    import pynput
    from pynput import mouse
    # pyrefly: ignore [missing-import]
    import pygetwindow as gw
    TRACKING_AVAILABLE = True
except ImportError:
    TRACKING_AVAILABLE = False

logger = logging.getLogger(__name__)

class Tracker:
    """Tracks mouse events and associated active windows."""
    
    def __init__(self, callback: Callable[[Dict[str, Any]], None]):
        self.callback = callback
        self.listener: Optional['pynput.mouse.Listener'] = None

    def start(self):
        if not TRACKING_AVAILABLE:
            logger.error("pynput or pygetwindow not installed. Tracking disabled.")
            return
            
        self.listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )
        self.listener.start()
        logger.info("Mouse and Window tracker started.")

    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener = None
        logger.info("Mouse and Window tracker stopped.")

    def get_active_window(self) -> str:
        if not TRACKING_AVAILABLE:
            return ""
        try:
            active_window = gw.getActiveWindow()
            return active_window.title if active_window else ""
        except Exception:
            return ""

    def _trigger_event(self, event_type: str, x: float, y: float, **kwargs):
        event_data = {
            "event": event_type,
            "x": int(x),
            "y": int(y),
            "window": self.get_active_window()
        }
        event_data.update(kwargs)
        self.callback(event_data)

    def on_move(self, x, y):
        self._trigger_event("move", x, y)

    def on_click(self, x, y, button, pressed):
        if pressed:
            event_type = "left_click" if button == mouse.Button.left else "right_click"
            self._trigger_event(event_type, x, y, button=str(button))

    def on_scroll(self, x, y, dx, dy):
        self._trigger_event("scroll", x, y, dx=dx, dy=dy)
