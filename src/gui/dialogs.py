import os
# pyrefly: ignore [missing-import]
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox,
    QCheckBox, QLabel, QDialogButtonBox
)
from src.config import config
from src.gui.widgets import SectionLabel

class SettingsDialog(QDialog):
    """Configuration dialog for the application."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(480, 360)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(SectionLabel("Configuration"))

        hint = QLabel(
            '☁ Authenticate using Google Cloud Default Credentials'
        )
        hint.setStyleSheet("color: #71717a; font-size: 11px;")
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(12)

        self.project_id_edit = QLineEdit()
        self.project_id_edit.setPlaceholderText("your-gcp-project-id")
        self.project_id_edit.setText(config.GCP_PROJECT_ID)

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("e.g. us-central1")
        self.location_edit.setText(config.GCP_LOCATION)

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("e.g. gemini-2.5-flash")
        self.model_edit.setText(config.GEMINI_MODEL)

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(5, 30)
        self.fps_spin.setValue(config.RECORDING_FPS)
        self.fps_spin.setSuffix(" FPS")

        self.click_cb = QCheckBox("Capture on mouse click")
        self.click_cb.setChecked(config.SCREENSHOT_ON_CLICK)

        self.idle_spin = QSpinBox()
        self.idle_spin.setRange(10, 300)
        self.idle_spin.setValue(config.IDLE_TIMEOUT_SECONDS)
        self.idle_spin.setSuffix(" seconds")

        form.addRow("GCP Project ID", self.project_id_edit)
        form.addRow("GCP Location",   self.location_edit)
        form.addRow("Vision Model",       self.model_edit)
        form.addRow("Recording FPS",      self.fps_spin)
        form.addRow("Idle Timeout",       self.idle_spin)
        layout.addLayout(form)
        layout.addWidget(self.click_cb)
        layout.addStretch()

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _save(self):
        config.GCP_PROJECT_ID = self.project_id_edit.text().strip()
        config.GCP_LOCATION = self.location_edit.text().strip()
        config.GEMINI_MODEL = self.model_edit.text().strip() or config.GEMINI_MODEL
        config.RECORDING_FPS = self.fps_spin.value()
        config.IDLE_TIMEOUT_SECONDS = self.idle_spin.value()
        config.SCREENSHOT_ON_CLICK = self.click_cb.isChecked()
        
        os.environ["PROJECT_ID"] = config.GCP_PROJECT_ID
        os.environ["LOCATION"] = config.GCP_LOCATION
        os.environ["GEMINI_MODEL"] = config.GEMINI_MODEL
        
        self.accept()
