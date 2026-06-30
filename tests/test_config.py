import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.omniparser.config import *

print(PROJECT_ROOT)
print(OMNIPARSER_DIR)
print(WEIGHTS_DIR)
print(ICON_DETECT_MODEL)
print(ICON_CAPTION_DIR)
print(DEVICE)