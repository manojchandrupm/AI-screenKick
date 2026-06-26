import sys
import ctypes
from pathlib import Path

try:
    # Make process DPI aware so pynput coordinates match mss physical pixels exactly
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

# Ensure src is in the python path
src_dir = Path(__file__).parent
project_root = src_dir.parent
sys.path.insert(0, str(project_root))

# Pre-load PyTorch in the main thread to prevent [WinError 1114] DLL initialization failures 
# when it gets imported later inside background worker threads (like AnalysisWorker).
try:
    import torch
except ImportError:
    pass

from src.config import config, setup_logging
from src.gui.app import run_app

def main():
    # Ensure all output directories exist
    config.ensure_directories()
    
    # Initialize application logging
    log_file = config.LOGS_DIR / "app.log"
    setup_logging(log_file)
    
    # Start the GUI
    run_app()

if __name__ == "__main__":
    main()
