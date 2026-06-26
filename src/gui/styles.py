THEME_QSS = """
QMainWindow, QWidget {
    background-color: #09090b;
    color: #d4d4d8;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}

/* Sidebar Navigation Buttons */
QPushButton.NavButton {
    background: transparent;
    color: #a1a1aa;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0px;
    padding: 12px 20px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
}
QPushButton.NavButton:hover {
    background: #18181b;
    color: #f4f4f5;
}
QPushButton.NavButton:checked {
    background: #18181b;
    color: #06b6d4;
    border-left: 3px solid #06b6d4;
    font-weight: 600;
}

/* Regular Buttons */
QPushButton {
    background: #18181b;
    color: #d4d4d8;
    border: 1px solid #27272a;
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 500;
    font-size: 13px;
}
QPushButton:hover { background: #27272a; border-color: #3f3f46; }
QPushButton:pressed { background: #09090b; }

QPushButton#btn-start {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #06b6d4, stop:1 #0891b2);
    color: #ffffff; border: none; font-size: 14px; font-weight: 700;
    padding: 12px 32px; border-radius: 10px;
}
QPushButton#btn-start:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #22d3ee, stop:1 #06b6d4);
}
QPushButton#btn-stop {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #ef4444, stop:1 #dc2626);
    color: #ffffff; border: none; font-size: 14px; font-weight: 700;
    padding: 12px 32px; border-radius: 10px;
}
QPushButton#btn-stop:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #f87171, stop:1 #ef4444);
}
QPushButton#btn-report {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #8b5cf6, stop:1 #7c3aed);
    color: #ffffff; border: none; font-weight: 700; padding: 10px 24px;
    border-radius: 8px;
}
QPushButton#btn-report:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #a78bfa, stop:1 #8b5cf6);
}

QScrollArea { border: none; background: transparent; }
QScrollBar:vertical {
    background: #09090b; width: 8px; border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #27272a; border-radius: 4px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #3f3f46; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QTextEdit, QLineEdit {
    background: #18181b; color: #d4d4d8;
    border: 1px solid #27272a; border-radius: 8px; padding: 8px;
    selection-background-color: #06b6d4;
    selection-color: #ffffff;
}
QTextEdit:focus, QLineEdit:focus { border-color: #06b6d4; outline: none; }

QLabel { color: #d4d4d8; }

QStatusBar { background: #09090b; color: #71717a; border-top: 1px solid #27272a; }

QProgressBar {
    background: #18181b; border: 1px solid #27272a; border-radius: 6px;
    text-align: center; color: #ffffff; height: 12px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #06b6d4, stop:1 #22d3ee);
    border-radius: 6px;
}

QListWidget {
    background: #18181b; border: 1px solid #27272a;
    border-radius: 8px; outline: none;
}
QListWidget::item { padding: 8px 12px; border-bottom: 1px solid #09090b; }
QListWidget::item:selected {
    background: #27272a; color: #ffffff; border-left: 3px solid #06b6d4;
}
QListWidget::item:hover { background: #27272a; }

QGroupBox {
    border: 1px solid #27272a; border-radius: 10px;
    margin-top: 14px; padding-top: 10px; font-weight: 600;
    color: #e4e4e7;
    background: #18181b;
}
QGroupBox::title {
    subcontrol-origin: margin; left: 12px; padding: 0 6px;
    color: #e4e4e7;
    background: #18181b;
}

QCheckBox { color: #a1a1aa; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 2px solid #3f3f46; border-radius: 4px;
    background: #18181b;
}
QCheckBox::indicator:checked {
    background: #06b6d4; border-color: #06b6d4;
}

QSpinBox {
    background: #18181b; color: #d4d4d8;
    border: 1px solid #27272a; border-radius: 6px; padding: 4px 8px;
}

QDialog {
    background: #09090b; color: #d4d4d8;
}
QFormLayout QLabel { color: #a1a1aa; }
QDialogButtonBox QPushButton { min-width: 80px; }
"""
