import sys
import logging
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
# pyrefly: ignore [missing-import]
from src.core.omniparser_detector import OmniParserDetector
from src.config import config

def test_omniparser():
    # Make sure we have a test image
    test_dir = config.SCREENSHOTS_DIR
    test_images = list(test_dir.glob("*.png"))
    
    if not test_images:
        print("No test images found in output/screenshots/")
        return
        
    test_image = test_images[0]
    
    print("Initializing OmniParser...")
    detector = OmniParserDetector()
    
    print(f"Testing detection on {test_image}...")
    detections = detector.parse(str(test_image))
    
    print("\n--- RESULTS ---")
    print(f"Found {len(detections)} elements!")
    for d in detections:
        print(f"[{d['id']}] {d['label']} (confidence: {d['score']}) at {d['box']}")

if __name__ == "__main__":
    test_omniparser()
