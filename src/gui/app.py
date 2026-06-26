import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import queue
import threading

# pyrefly: ignore [missing-import]
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
# pyrefly: ignore [missing-import]
from PyQt5.QtGui import QFont
# pyrefly: ignore [missing-import]
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QScrollArea, QFrame, QGridLayout,
    QTextEdit, QGroupBox, QStatusBar, QMessageBox, QListWidget, QListWidgetItem, QProgressBar, QFormLayout,
    QStackedWidget, QButtonGroup, QFileDialog
)

from src.config import config
from src.db.database import DatabaseManager
from src.core.recorder import ScreenRecorder
from src.core.tracker import Tracker
from src.core.screenshot import ScreenshotEngine
from src.gui.styles import THEME_QSS
from src.gui.widgets import (
    StatCard, PulsingDot, SectionLabel, TimelineItemWidget, ScreenshotThumbnail
)
from src.gui.dialogs import SettingsDialog
from src.gui.workers import AnalysisWorker

class MainWindow(QMainWindow):
    sig_new_event = pyqtSignal(dict)
    sig_new_screenshot = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} v{config.APP_VERSION}")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)

        self.db = DatabaseManager(config.OUTPUT_DIR / "ai_screen_processor.db")
        self.db.init_database()

        self._session_id: Optional[int] = None
        self._recorder: Optional[ScreenRecorder] = None
        self._tracker: Optional[Tracker] = None
        self._screenshot_engine: Optional[ScreenshotEngine] = None
        self._recording_start: Optional[datetime] = None
        self._event_count = 0
        self._screenshot_count = 0

        self._analysis_queue = queue.Queue()
        self._bg_thread = threading.Thread(target=self._bg_analysis_loop, daemon=True)
        self._bg_thread.start()

        self._build_ui()
        self._connect_signals()
        self._start_clock()

    def _bg_analysis_loop(self):
        from src.core.analyzer import AIAnalyzer
        import logging
        analyzer = AIAnalyzer()
        while True:
            item = self._analysis_queue.get()
            if item is None:
                break
            ss_id, filepath = item
            try:
                result = analyzer.analyze_full(filepath)
                self.db.update_screenshot_analysis(
                    ss_id,
                    ocr_text=result["ocr_text"],
                    ai_description=result["ai_description"],
                    ui_elements=result.get("ui_elements", "")
                )
            except Exception as e:
                logging.error(f"Background AI failed: {e}")
            self._analysis_queue.task_done()

    def _build_ui(self):
        self.setStyleSheet(THEME_QSS)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 1. Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("background: #18181b; border-right: 1px solid #27272a;")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 24, 0, 24)
        side_layout.setSpacing(8)

        # Logo / Title
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(24, 0, 24, 24)
        dot = QLabel("◈")
        dot.setStyleSheet("color: #06b6d4; font-size: 24px; border: none;")
        name = QLabel(f"<b>{config.APP_NAME}</b>")
        name.setStyleSheet("color: #ffffff; font-size: 15px; border: none;")
        brand_layout.addWidget(dot)
        brand_layout.addWidget(name)
        brand_layout.addStretch()
        side_layout.addLayout(brand_layout)

        # Navigation Buttons
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        nav_items = [
            ("Dashboard", self._build_dashboard_tab),
            ("Timeline", self._build_timeline_tab),
            ("Screenshots", self._build_screenshots_tab),
            ("Reports", self._build_reports_tab)
        ]
        
        self.stacked = QStackedWidget()
        root.addWidget(sidebar)
        root.addWidget(self.stacked, 1)

        for i, (text, func) in enumerate(nav_items):
            btn = QPushButton(f"  {text}")
            btn.setCheckable(True)
            btn.setProperty("class", "NavButton")
            self.nav_group.addButton(btn, i)
            side_layout.addWidget(btn)
            
            page = func()
            self.stacked.addWidget(page)
            
        self.nav_group.buttonClicked[int].connect(self.stacked.setCurrentIndex)
        self.nav_group.button(0).setChecked(True)

        side_layout.addStretch()

        # Recording Status
        status_frame = QFrame()
        status_frame.setStyleSheet("border: none; border-top: 1px solid #27272a; border-radius: 0;")
        stat_layout = QVBoxLayout(status_frame)
        stat_layout.setContentsMargins(24, 24, 24, 0)
        
        rec_row = QHBoxLayout()
        self.pulse_dot = PulsingDot()
        self.rec_label = QLabel("NOT RECORDING")
        self.rec_label.setStyleSheet("color: #71717a; font-size: 11px; font-weight: 600; border: none;")
        rec_row.addWidget(self.pulse_dot)
        rec_row.addWidget(self.rec_label)
        rec_row.addStretch()
        stat_layout.addLayout(rec_row)

        self.clock_label = QLabel("00:00:00")
        self.clock_label.setStyleSheet(
            "color: #06b6d4; font-family: 'Cascadia Code','Courier New',monospace;"
            "font-size: 24px; font-weight: 700; border: none; margin-top: 8px;"
        )
        stat_layout.addWidget(self.clock_label)
        
        settings_btn = QPushButton("⚙  Settings")
        settings_btn.setStyleSheet("margin-top: 16px;")
        settings_btn.clicked.connect(self._open_settings)
        stat_layout.addWidget(settings_btn)

        side_layout.addWidget(status_frame)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._status_label = QLabel("Ready")
        self.status.addWidget(self._status_label)

    def _build_dashboard_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        ctrl_group = QGroupBox("Recording Controls")
        ctrl_layout = QHBoxLayout(ctrl_group)
        ctrl_layout.setSpacing(12)

        self.start_btn = QPushButton("  ▶  Start Recording")
        self.start_btn.setObjectName("btn-start")
        self.start_btn.setFixedHeight(48)
        self.start_btn.clicked.connect(self._start_recording)

        self.stop_btn = QPushButton("  ■  Stop Recording")
        self.stop_btn.setObjectName("btn-stop")
        self.stop_btn.setFixedHeight(48)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_recording)

        self.upload_btn = QPushButton("  📁  Upload Video")
        self.upload_btn.setObjectName("btn-upload")
        self.upload_btn.setFixedHeight(48)
        self.upload_btn.clicked.connect(self._upload_video)

        ctrl_layout.addWidget(self.start_btn)
        ctrl_layout.addWidget(self.stop_btn)
        ctrl_layout.addWidget(self.upload_btn)
        ctrl_layout.addStretch()

        layout.addWidget(ctrl_group)

        stats_group = QGroupBox("Live Statistics")
        stats_layout = QHBoxLayout(stats_group)
        stats_layout.setSpacing(12)

        self.stat_fps         = StatCard("FPS",         "0",  "#3b82f6")
        self.stat_events      = StatCard("Events",      "0",  "#8b5cf6")
        self.stat_screenshots = StatCard("Screenshots", "0",  "#10b981")
        self.stat_duration    = StatCard("Duration",    "0:00","#f97316")

        for s in [self.stat_fps, self.stat_events, self.stat_screenshots, self.stat_duration]:
            stats_layout.addWidget(s)
        stats_layout.addStretch()
        layout.addWidget(stats_group)

        log_group = QGroupBox("Live Event Log")
        log_layout = QVBoxLayout(log_group)

        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setMaximumHeight(240)
        self.event_log.setFont(QFont("Cascadia Code", 11))
        self.event_log.setPlaceholderText("Events will appear here when recording starts…")
        log_layout.addWidget(self.event_log)
        layout.addWidget(log_group)

        info_group = QGroupBox("Session Info")
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(8)

        self.info_start = QLabel("—")
        self.info_recording = QLabel("—")
        self.info_session_id = QLabel("—")

        info_layout.addRow("Session ID:", self.info_session_id)
        info_layout.addRow("Started:", self.info_start)
        info_layout.addRow("Recording:", self.info_recording)
        layout.addWidget(info_group)

        layout.addStretch()
        return w

    def _build_timeline_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        layout.addWidget(SectionLabel("Activity Timeline"))

        self.timeline_list = QListWidget()
        self.timeline_list.setSpacing(3)
        self.timeline_list.setSelectionMode(QListWidget.NoSelection)
        layout.addWidget(self.timeline_list)
        return w

    def _build_screenshots_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.addWidget(SectionLabel("Captured Screenshots"))
        toolbar.addStretch()
        open_dir_btn = QPushButton("📁  Open Folder")
        open_dir_btn.clicked.connect(lambda: os.startfile(str(config.SCREENSHOTS_DIR)))
        toolbar.addWidget(open_dir_btn)
        layout.addLayout(toolbar)

        self.ss_scroll = QScrollArea()
        self.ss_scroll.setWidgetResizable(True)
        self.ss_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.ss_container = QWidget()
        self.ss_grid = QGridLayout(self.ss_container)
        self.ss_grid.setSpacing(14)
        self.ss_grid.setContentsMargins(0, 0, 0, 0)
        self.ss_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.ss_scroll.setWidget(self.ss_container)
        layout.addWidget(self.ss_scroll)
        self._ss_col = 0
        self._ss_row = 0
        return w

    def _build_reports_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        layout.addWidget(SectionLabel("Report Generation"))

        gen_frame = QGroupBox("Generate AI Report")
        gen_layout = QVBoxLayout(gen_frame)

        desc = QLabel(
            "Analyzes all screenshots with OpenRouter AI, builds a timeline, "
            "generates an AI session summary, and exports reports."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #64748b; font-size: 13px;")

        self.gen_btn = QPushButton("✦  Generate Full AI Report")
        self.gen_btn.setObjectName("btn-report")
        self.gen_btn.setFixedHeight(44)
        self.gen_btn.setEnabled(False)
        self.gen_btn.clicked.connect(self._generate_report)

        self.gen_progress = QProgressBar()
        self.gen_progress.setValue(0)
        self.gen_progress.setVisible(False)

        self.gen_status_lbl = QLabel("")
        self.gen_status_lbl.setStyleSheet("color: #3b82f6; font-size: 12px;")

        gen_layout.addWidget(desc)
        gen_layout.addWidget(self.gen_btn)
        gen_layout.addWidget(self.gen_progress)
        gen_layout.addWidget(self.gen_status_lbl)
        layout.addWidget(gen_frame)

        self.report_links_group = QGroupBox("Generated Reports")
        links_layout = QVBoxLayout(self.report_links_group)

        self.report_pdf_btn  = QPushButton("📄  Open PDF Report")
        self.open_dir_btn    = QPushButton("📁  Open Reports Folder")

        self.report_pdf_btn.setEnabled(False)
        links_layout.addWidget(self.report_pdf_btn)

        self.open_dir_btn.setEnabled(True)
        self.open_dir_btn.clicked.connect(lambda: os.startfile(str(config.REPORTS_DIR)))
        links_layout.addWidget(self.open_dir_btn)

        layout.addWidget(self.report_links_group)

        summary_group = QGroupBox("AI Session Summary Preview")
        summary_layout = QVBoxLayout(summary_group)
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setPlaceholderText("AI-generated session summary will appear here after report generation…")
        self.summary_text.setMaximumHeight(160)
        summary_layout.addWidget(self.summary_text)
        layout.addWidget(summary_group)

        layout.addStretch()
        return w

    def _connect_signals(self):
        self.sig_new_event.connect(self._on_new_event_ui)
        self.sig_new_screenshot.connect(self._on_new_screenshot_ui)

    def _start_clock(self):
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)

    def _update_clock(self):
        if self._recording_start and self._recorder and self._recorder.is_recording:
            elapsed = datetime.now() - self._recording_start
            secs = int(elapsed.total_seconds())
            h, rem = divmod(secs, 3600)
            m, s = divmod(rem, 60)
            self.clock_label.setText(f"{h:02d}:{m:02d}:{s:02d}")
            self.stat_duration.set_value(f"{m:02d}:{s:02d}" if not h else f"{h}:{m:02d}:{s:02d}")

    def _start_recording(self):
        if not config.GCP_PROJECT_ID:
            QMessageBox.warning(self, "Project ID Required", "Please set your GCP Project ID in Settings before starting.")
            self._open_settings()
            return

        self._session_id = self.db.create_session()
        self._recording_start = datetime.now()
        self._event_count = 0
        self._screenshot_count = 0

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.upload_btn.setEnabled(False)
        self.gen_btn.setEnabled(False)
        self.pulse_dot.start_pulsing()
        self.rec_label.setText("● RECORDING")
        self.rec_label.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 700;")
        self.info_start.setText(self._recording_start.strftime("%H:%M:%S"))
        self.info_session_id.setText(str(self._session_id))
        self._log_event("System", "Recording started", "#22c55e")

        self._recorder = ScreenRecorder(on_fps_update=self._on_fps_update)
        self._recorder.start()
        self.info_recording.setText(str(config.RECORDINGS_DIR / "session_*.mp4"))

        self._screenshot_engine = ScreenshotEngine(on_screenshot=self._on_screenshot_captured)
        self._screenshot_engine.start()

        self._tracker = Tracker(callback=self._on_event_captured)
        self._tracker.start()

        self._set_status("Recording in progress…")

    def _stop_recording(self):
        if self._tracker: self._tracker.stop()
        if self._screenshot_engine: self._screenshot_engine.stop()

        recording_path = None
        if self._recorder:
            self._recorder.stop()
            recording_path = str(self._recorder.filepath) if self._recorder.filepath else None

        if self._session_id:
            self.db.end_session(self._session_id, recording_path)

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.upload_btn.setEnabled(True)
        self.gen_btn.setEnabled(True)
        self.pulse_dot.stop_pulsing()
        self.rec_label.setText("STOPPED")
        self.rec_label.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600;")
        self._log_event("System", "Recording stopped", "#f97316")
        self._set_status(f"Recording saved. Session ID: {self._session_id}")

    def _upload_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.avi *.mkv *.mov)")
        if not file_path:
            return

        self._session_id = self.db.create_session()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.upload_btn.setEnabled(False)
        self.gen_btn.setEnabled(False)

        self._log_event("System", f"Processing uploaded video: {Path(file_path).name}", "#f97316")
        self._set_status("Extracting video frames...")

        from src.gui.workers import VideoUploadWorker
        self._video_worker = VideoUploadWorker(self._session_id, file_path, self.db, self)
        self._video_worker.progress.connect(self._on_video_progress)
        self._video_worker.new_screenshot.connect(self._on_video_screenshot)
        self._video_worker.finished.connect(self._on_video_finished)
        self._video_worker.error.connect(self._on_video_error)
        self._video_worker.start()

    def _on_video_error(self, err: str):
        self.start_btn.setEnabled(True)
        self.upload_btn.setEnabled(True)
        self.gen_btn.setEnabled(True)
        QMessageBox.critical(self, "Video Upload Error", f"An error occurred while processing the video:\n\n{err}")
        self._set_status("Video processing failed.")

    def _on_video_progress(self, pct, msg):
        self._set_status(msg)

    def _on_video_screenshot(self, data):
        self._analysis_queue.put((data["id"], data["filepath"]))
        self.sig_new_screenshot.emit(data)
        self._screenshot_count += 1
        self.stat_screenshots.set_value(str(self._screenshot_count))
        # Log a generic timeline event for the video frame capture
        self.db.insert_event(self._session_id, event_type="screen_change", x=0, y=0, window_name="Video")
        self._event_count += 1
        self.stat_events.set_value(str(self._event_count))
        
        # Emit signal to update the UI timeline
        event_dict = {
            "event": "screen_change",
            "window": "Video",
            "x": 0,
            "y": 0,
            "time": datetime.now().strftime("%I:%M %p")
        }
        self.sig_new_event.emit(event_dict)

    def _on_video_finished(self):
        self.db.end_session(self._session_id)
        self.upload_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.gen_btn.setEnabled(True)
        self._log_event("System", "Video processing complete.", "#10b981")
        self._set_status(f"Video saved to Session {self._session_id}. Ready to Generate Report.")

    def _on_event_captured(self, event: dict):
        if self._session_id:
            self.db.insert_event(
                self._session_id,
                event_type=event["event"],
                x=event["x"], y=event["y"],
                window_name=event["window"]
            )
        if self._screenshot_engine:
            self._screenshot_engine.on_mouse_event(event)

        self._event_count += 1
        event["time"] = datetime.now().strftime("%I:%M %p")
        self.sig_new_event.emit(event)

    def _on_screenshot_captured(self, filepath: str, trigger_type: str, x: int, y: int):
        ss_id = None
        if self._session_id:
            ss_id = self.db.insert_screenshot(self._session_id, filepath, trigger_type)

        from src.core.screenshot import annotate_in_thread
        
        def _on_annotated(ann_path: str):
            if ss_id:
                self.db.update_screenshot_analysis(ss_id, annotated_path=ann_path)
                self._analysis_queue.put((ss_id, ann_path if ann_path else filepath))
                
            self.sig_new_screenshot.emit({
                "id": ss_id,
                "filepath": filepath,
                "annotated_path": ann_path,
                "trigger_type": trigger_type,
                "timestamp": datetime.now().isoformat()
            })
            
        annotate_in_thread(filepath, x, y, trigger_type, callback=_on_annotated)
        self._screenshot_count += 1

    def _on_fps_update(self, fps: float):
        self.stat_fps.set_value(f"{fps:.1f}")

    def _on_new_event_ui(self, event: dict):
        ev_type = event.get("event", "")
        window  = event.get("window", "")
        x, y    = event.get("x", 0), event.get("y", 0)

        self.stat_events.set_value(str(self._event_count))
        self.stat_screenshots.set_value(str(self._screenshot_count))

        col_map = {
            "left_click": "#ef4444", "right_click": "#f97316",
            "double_click": "#c084fc", "scroll": "#0ea5e9",
            "window_change": "#10b981", "move": "#94a3b8",
        }
        col = col_map.get(ev_type, "#64748b")

        if ev_type != "move":
            desc = ev_type.replace("_", " ").title()
            if window: desc += f" · {window[:40]}"
            self._log_event(event.get("time", ""), f"({x},{y}) {desc}", col)

            from src.reporting.timeline import EVENT_DESCRIPTIONS
            entry = {
                "time": event.get("time", ""),
                "action": EVENT_DESCRIPTIONS.get(ev_type, desc),
                "event_type": ev_type,
                "window": window,
            }
            self._add_timeline_entry(entry)

    def _on_new_screenshot_ui(self, ss_data: dict):
        self.stat_screenshots.set_value(str(self._screenshot_count))
        thumb = ScreenshotThumbnail(ss_data)
        self.ss_grid.addWidget(thumb, self._ss_row, self._ss_col)
        self._ss_col += 1
        if self._ss_col >= 3:
            self._ss_col = 0
            self._ss_row += 1

    def _generate_report(self):
        if not self._session_id: return
        self.gen_btn.setEnabled(False)
        self.gen_progress.setVisible(True)
        self.gen_progress.setValue(0)

        self._worker = AnalysisWorker(self._session_id)
        self._worker.progress.connect(self._on_report_progress)
        self._worker.finished.connect(self._on_report_done)
        self._worker.error.connect(self._on_report_error)
        self._worker.start()

    def _on_report_progress(self, pct: int, msg: str):
        self.gen_progress.setValue(pct)
        self.gen_status_lbl.setText(msg)
        self._set_status(msg)

    def _on_report_done(self, paths: dict):
        self.gen_progress.setValue(100)
        self.gen_btn.setEnabled(True)

        def _open(p): return lambda: os.startfile(p) if p and Path(p).exists() else None

        if paths.get("pdf"): self.report_pdf_btn.setEnabled(True); self.report_pdf_btn.clicked.connect(_open(paths["pdf"]))

        session = self.db.get_session(self._session_id)
        if session.get("summary"):
            self.summary_text.setPlainText(session["summary"])

        self.gen_status_lbl.setText("✓ Report generated successfully!")
        self._set_status("Report generation complete.")

    def _on_report_error(self, err: str):
        self.gen_btn.setEnabled(True)
        self.gen_progress.setVisible(False)
        QMessageBox.critical(self, "Report Error", err)

    def _log_event(self, time_str: str, text: str, color: str = "#0f172a"):
        html = f'<span style="color:#64748b">[{time_str}]</span> <span style="color:{color}">{text}</span>'
        self.event_log.append(html)
        sb = self.event_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _add_timeline_entry(self, entry: dict):
        item = QListWidgetItem()
        widget = TimelineItemWidget(entry)
        h = 90 if entry.get("window") else 72
        item.setSizeHint(QSize(self.timeline_list.width(), h))
        self.timeline_list.addItem(item)
        self.timeline_list.setItemWidget(item, widget)
        self.timeline_list.scrollToBottom()

    def _set_status(self, msg: str):
        self._status_label.setText(msg)

    def _open_settings(self):
        SettingsDialog(self).exec_()

    def closeEvent(self, event):
        if self._recorder and self._recorder.is_recording:
            reply = QMessageBox.question(self, "Recording Active", "Recording is still active. Stop and exit?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self._stop_recording()
            else:
                event.ignore()
                return
        event.accept()

def run_app():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
