import os
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import List
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

# Setup root logger globally accessible via this function
def setup_logging(log_file: Path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.info("Application logging initialized.")

@dataclass
class AppConfig:
    # Base paths
    BASE_DIR: Path = Path(__file__).parent.parent.absolute()
    OUTPUT_DIR: Path = BASE_DIR / "output"
    
    # Output directories
    RECORDINGS_DIR: Path = OUTPUT_DIR / "recordings"
    SCREENSHOTS_DIR: Path = OUTPUT_DIR / "screenshots"
    ANNOTATED_DIR: Path = OUTPUT_DIR / "annotated"
    TIMELINE_DIR: Path = OUTPUT_DIR / "timeline"
    REPORTS_DIR: Path = OUTPUT_DIR / "reports"
    LOGS_DIR: Path = OUTPUT_DIR / "logs"
    AI_RESULTS_DIR: Path = OUTPUT_DIR / "ai_results"
     
    # Application Constants
    APP_NAME: str = "AI Screen Activity Analyzer"
    APP_VERSION: str = "2.0.0"
    
    # Application Settings
    RECORDING_FPS: int = int(os.getenv("FPS", "10"))
    IDLE_TIMEOUT_SECONDS: int = int(os.getenv("IDLE_TIMEOUT_SECONDS", "60"))
    SCREENSHOT_ON_CLICK: bool = os.getenv("SCREENSHOT_ON_CLICK", "True").lower() in ['true', '1', 't']
    SCREENSHOT_THRESHOLD: float = float(os.getenv("SCREENSHOT_THRESHOLD", "0.95"))

    # Ollama Models "gemma4:e2b","llava:7b","qwen3"
    OLLAMA_VISION_MODEL: str = os.getenv("OLLAMA_VISION_MODEL", "llava:7b")
    OLLAMA_TEXT_MODEL: str = os.getenv("OLLAMA_TEXT_MODEL", "phi3")

    # API Settings
    GCP_PROJECT_ID: str = os.getenv("PROJECT_ID", "thunai-interns")
    GCP_LOCATION: str = os.getenv("LOCATION", "asia-south1")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    local_key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "service_account.json")
    if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ and os.path.exists(local_key_path):
     os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = local_key_path

    # OCR Settings
    OCR_LANGUAGES: List[str] = None
    OCR_USE_GPU: bool = os.getenv("OCR_USE_GPU", "False").lower() in ['true', '1', 't']

    # ROI Settings (Region of Interest)
    DYNAMIC_ROI_ENABLED: bool = os.getenv("DYNAMIC_ROI_ENABLED", "False").lower() in ['true', '1', 't']
    SMART_CONTENT_CROP: bool = os.getenv("SMART_CONTENT_CROP", "True").lower() in ['true', '1', 't']
    CONTENT_MARGIN_TOP: int = int(os.getenv("CONTENT_MARGIN_TOP", "130")) # Pixels for browser tabs/URL
    CONTENT_MARGIN_BOTTOM: int = int(os.getenv("CONTENT_MARGIN_BOTTOM", "60")) # Pixels for taskbar
    ROI_ENABLED: bool = os.getenv("ROI_ENABLED", "False").lower() in ['true', '1', 't']
    ROI_X: int = int(os.getenv("ROI_X", "0"))
    ROI_Y: int = int(os.getenv("ROI_Y", "0"))
    ROI_WIDTH: int = int(os.getenv("ROI_WIDTH", "0"))
    ROI_HEIGHT: int = int(os.getenv("ROI_HEIGHT", "0"))
    
    # OmniParser Config
    OMNIPARSER_ENABLED: bool = os.getenv("OMNIPARSER_ENABLED", "False").lower() in ['true', '1', 't']
    OMNIPARSER_MODEL_ID: str = os.getenv("OMNIPARSER_MODEL_ID", "microsoft/OmniParser-v2.0")

    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    OMNIPARSER_DIR = PROJECT_ROOT / "OmniParser"
    ICON_DETECT_DIR = OMNIPARSER_DIR / "weights" / "icon_detect"
    ICON_DETECT_MODEL = ICON_DETECT_DIR / "model.pt"
    ICON_CAPTION_DIR = OMNIPARSER_DIR / "weights" / "icon_caption_florence"

    def __post_init__(self):
        if self.OCR_LANGUAGES is None:
            self.OCR_LANGUAGES = ['en']
    def ensure_directories(self) -> None:
        """Creates all necessary output directories."""
        dirs = [
            self.RECORDINGS_DIR, self.SCREENSHOTS_DIR, self.ANNOTATED_DIR, 
            self.TIMELINE_DIR, self.REPORTS_DIR, self.LOGS_DIR, self.AI_RESULTS_DIR
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

# Singleton configuration instance
config = AppConfig()
