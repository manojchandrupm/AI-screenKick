import os
from pathlib import Path
# pyrefly: ignore [missing-import]
from PyQt5.QtCore import Qt, QTimer
# pyrefly: ignore [missing-import]
from PyQt5.QtGui import QPixmap
# pyrefly: ignore [missing-import]
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)

class StatCard(QFrame):
    """A minimal stat display card."""
    def __init__(self, label: str, value: str = "0", accent: str = "#06b6d4", parent=None):
        super().__init__(parent)
        self._accent = accent
        self.setFixedSize(160, 90)
        self.setObjectName("StatCardFrame")
        self.setStyleSheet(f"""
            QFrame#StatCardFrame {{
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 12px;
                border-left: 3px solid {accent};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)

        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {accent};")

        self.label_lbl = QLabel(label.upper())
        self.label_lbl.setStyleSheet("font-size: 10px; letter-spacing: 1.5px; color: #71717a;")

        layout.addWidget(self.value_lbl)
        layout.addWidget(self.label_lbl)

    def set_value(self, v: str):
        self.value_lbl.setText(str(v))


class PulsingDot(QLabel):
    """Animated recording indicator dot."""
    def __init__(self, parent=None):
        super().__init__("●", parent)
        self.setStyleSheet("color: #ef4444; font-size: 14px; border: none;")
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._blink)
        self._visible = True

    def start_pulsing(self):
        self._timer.start(600)

    def stop_pulsing(self):
        self._timer.stop()
        self.setStyleSheet("color: #3f3f46; font-size: 14px; border: none;")

    def _blink(self):
        self._visible = not self._visible
        col = "#ef4444" if self._visible else "#27272a"
        self.setStyleSheet(f"color: {col}; font-size: 14px; border: none;")


class SectionLabel(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text.upper(), parent)
        self.setStyleSheet(
            "font-size: 10px; letter-spacing: 2px; color: #06b6d4;"
            "font-weight: 700; padding: 0 0 8px 0;"
        )


class HRule(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setStyleSheet("color: #27272a;")


class TimelineItemWidget(QFrame):
    """Single item in the live timeline list — two-row vertical layout."""
    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("TimelineFrame")
        self.setStyleSheet("""
            QFrame#TimelineFrame {
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 8px;
            }
            QFrame#TimelineFrame:hover { border-color: #06b6d4; }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(3)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.setContentsMargins(0, 0, 0, 0)

        ev_colors = {
            "left_click":    "#ef4444",
            "right_click":   "#f97316",
            "double_click":  "#8b5cf6",
            "scroll":        "#0ea5e9",
            "window_change": "#10b981",
            "idle":          "#f59e0b",
            "pixel_change":  "#06b6d4",
            "click":         "#ef4444",
        }
        col = ev_colors.get(entry.get("event_type", ""), "#06b6d4")

        dot = QLabel("●")
        dot.setFixedWidth(14)
        dot.setStyleSheet(f"color: {col}; font-size: 11px; padding-top: 1px;")

        action_lbl = QLabel(entry.get("action", ""))
        action_lbl.setStyleSheet(
            "color: #d4d4d8; font-weight: 600; font-size: 13px;"
        )
        action_lbl.setWordWrap(True)

        time_lbl = QLabel(entry.get("time", ""))
        time_lbl.setStyleSheet(
            "color: #06b6d4; font-family: 'Cascadia Code','Courier New',monospace;"
            "font-size: 11px; font-weight: 600;"
        )
        time_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        time_lbl.setFixedWidth(72)

        row1.addWidget(dot)
        row1.addWidget(action_lbl, 1)
        row1.addWidget(time_lbl)
        outer.addLayout(row1)

        window = entry.get("window", "")
        if window:
            row2 = QHBoxLayout()
            row2.setSpacing(0)
            row2.setContentsMargins(22, 0, 0, 0)
            win_lbl = QLabel(window[:80])
            win_lbl.setStyleSheet("color: #a1a1aa; font-size: 11px;")
            win_lbl.setWordWrap(True)
            row2.addWidget(win_lbl, 1)
            outer.addLayout(row2)


class ScreenshotThumbnail(QFrame):
    """Clickable screenshot card with AI description."""
    def __init__(self, ss_data: dict, parent=None):
        super().__init__(parent)
        self.ss_data = ss_data
        self.setFixedWidth(280)
        self.setObjectName("ScreenshotFrame")
        self.setStyleSheet("""
            QFrame#ScreenshotFrame {
                background: #18181b; border: 1px solid #27272a;
                border-radius: 10px;
            }
            QFrame#ScreenshotFrame:hover { border-color: #06b6d4; }
        """)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(0)

        self.img_lbl = QLabel()
        self.img_lbl.setAlignment(Qt.AlignCenter)
        self.img_lbl.setFixedHeight(158)
        self.img_lbl.setStyleSheet("border-radius: 10px 10px 0 0; background: #09090b;")

        img_path = ss_data.get("annotated_path") or ss_data.get("filepath", "")
        if img_path and Path(img_path).exists():
            pix = QPixmap(img_path).scaled(
                280, 158, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            self.img_lbl.setPixmap(pix)
        else:
            self.img_lbl.setText("No preview")
            self.img_lbl.setStyleSheet("color: #71717a; border-radius: 10px 10px 0 0; background: #09090b;")

        info = QWidget()
        info.setContentsMargins(10, 6, 10, 0)
        info_layout = QVBoxLayout(info)
        info_layout.setSpacing(3)
        info_layout.setContentsMargins(0, 0, 0, 0)

        time_str = ss_data.get("timestamp", "")[:19].replace("T", " ")
        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet("color: #71717a; font-size: 11px;")

        trigger = ss_data.get("trigger_type", "")
        trigger_lbl = QLabel(trigger.replace("_", " ").title())
        trigger_lbl.setStyleSheet("color: #06b6d4; font-size: 10px; font-weight: 600; letter-spacing: 0.5px;")

        ai_desc = ss_data.get("ai_description", "")
        if ai_desc:
            desc_lbl = QLabel(ai_desc[:80] + ("…" if len(ai_desc) > 80 else ""))
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet("color: #e4e4e7; font-size: 11px;")
            info_layout.addWidget(desc_lbl)

        info_layout.addWidget(trigger_lbl)
        info_layout.addWidget(time_lbl)

        layout.addWidget(self.img_lbl)
        layout.addWidget(info)

    def mousePressEvent(self, event):
        img_path = self.ss_data.get("annotated_path") or self.ss_data.get("filepath", "")
        if img_path and Path(img_path).exists():
            os.startfile(img_path)
