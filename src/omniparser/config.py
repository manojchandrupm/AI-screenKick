from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Microsoft OmniParser repository
OMNIPARSER_DIR = PROJECT_ROOT / "OmniParser"

# Weights
WEIGHTS_DIR = OMNIPARSER_DIR / "weights"

ICON_DETECT_DIR = WEIGHTS_DIR / "icon_detect"
ICON_DETECT_MODEL = ICON_DETECT_DIR / "model.pt"

ICON_CAPTION_DIR = WEIGHTS_DIR / "icon_caption_florence"

# Device
try:
    import torch
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
except Exception:
    DEVICE = "cpu"