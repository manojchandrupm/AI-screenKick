from pathlib import Path
import sys

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Microsoft OmniParser repository
OMNIPARSER_ROOT = PROJECT_ROOT / "OmniParser"

# Add OmniParser to Python path
if str(OMNIPARSER_ROOT) not in sys.path:
    sys.path.insert(0, str(OMNIPARSER_ROOT))

# pyrefly: ignore [missing-import]
from util.utils import (
    get_yolo_model,
    get_caption_model_processor,
    check_ocr_box,
    get_som_labeled_img,
)

from src.omniparser.parser import parse_image

print("✅ OmniParser imported successfully")

class OmniParserService:
    """
    Singleton service for OmniParser models.
    """

    def __init__(self):
        self.yolo_model = None
        self.caption_processor = None
        self.caption_model = None
        self.initialized = False

    def initialize(self):
        """
        Load all OmniParser models once.
        """
        if self.initialized:
            return

        from src.omniparser.config import (
            ICON_DETECT_MODEL,
            ICON_CAPTION_DIR,
            DEVICE,
        )
        print("Loading YOLO model...")
        self.yolo_model = get_yolo_model(str(ICON_DETECT_MODEL))
        print("✅ YOLO loaded")

        print("Loading Florence model...")
        caption = get_caption_model_processor(
            model_name="florence2",
            model_name_or_path=str(ICON_CAPTION_DIR),
            device=DEVICE,
        )

        self.caption_model = caption["model"]
        self.caption_processor = caption["processor"]

        print("✅ Florence loaded")

        self.initialized = True
    
    def parse_screen(self, image_path):
            """
            Parse a screenshot using the loaded OmniParser models.
            """
            if not self.initialized:
                self.initialize()

            return parse_image(
                image_path=image_path,
                yolo_model=self.yolo_model,
                caption_model_processor={
                    "model": self.caption_model,
                    "processor": self.caption_processor,
                },
        )    
    print("✅ OmniParser initialized.") 

omniparser_service = OmniParserService()