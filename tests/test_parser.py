from pathlib import Path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.omniparser.service import omniparser_service

image_path = Path(r"D:\ENTRANS_INTERN\AI_screen_processor\output\screenshots\video_click20260618_181807_346.png")

print("Initializing OmniParser...")
omniparser_service.initialize()

print("Parsing image...")

result = omniparser_service.parse_screen(str(image_path))

print("\n========== RESULT ==========")

print(type(result))
print(result.keys())

print("\nDetected Elements:")

for item in result["parsed_content"]:
    print(item)

print("\nTotal Elements:", len(result["parsed_content"]))