import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.omniparser.service import omniparser_service

print("Before:", omniparser_service.initialized)

omniparser_service.initialize()

print("After:", omniparser_service.initialized)

print("YOLO Loaded:", omniparser_service.yolo_model is not None)
print("Caption Model Loaded:", omniparser_service.caption_model is not None)
print("Processor Loaded:", omniparser_service.caption_processor is not None)