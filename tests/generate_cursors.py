# import cv2
# import numpy as np
# import os

# out_dir = r"d:\ENTRANS_INTERN\AI_screen_processor\assets\cursors"
# os.makedirs(out_dir, exist_ok=True)

# # 1. Arrow (white filled triangle with black border)
# arrow = np.zeros((24, 24, 3), dtype=np.uint8)
# pts = np.array([[2, 2], [2, 20], [7, 15], [12, 23], [15, 22], [10, 14], [18, 14]], np.int32)
# cv2.fillPoly(arrow, [pts], (255, 255, 255))
# cv2.polylines(arrow, [pts], True, (0, 0, 0), 1)
# # Convert to grayscale
# arrow_gray = cv2.cvtColor(arrow, cv2.COLOR_BGR2GRAY)
# cv2.imwrite(os.path.join(out_dir, "arrow.png"), arrow_gray)

# # 2. Hand (simplified pointer)
# hand = np.zeros((24, 24, 3), dtype=np.uint8)
# cv2.circle(hand, (12, 12), 6, (255, 255, 255), -1)
# cv2.circle(hand, (12, 12), 6, (0, 0, 0), 1)
# cv2.line(hand, (12, 6), (12, 0), (255,255,255), 3)
# cv2.line(hand, (12, 6), (12, 0), (0,0,0), 1)
# hand_gray = cv2.cvtColor(hand, cv2.COLOR_BGR2GRAY)
# cv2.imwrite(os.path.join(out_dir, "hand.png"), hand_gray)

# # 3. I-beam (text cursor)
# ibeam = np.zeros((24, 24, 3), dtype=np.uint8)
# cv2.line(ibeam, (12, 2), (12, 22), (255, 255, 255), 2)
# cv2.line(ibeam, (8, 2), (16, 2), (255, 255, 255), 2)
# cv2.line(ibeam, (8, 22), (16, 22), (255, 255, 255), 2)
# ibeam_gray = cv2.cvtColor(ibeam, cv2.COLOR_BGR2GRAY)
# cv2.imwrite(os.path.join(out_dir, "ibeam.png"), ibeam_gray)

# print(f"Generated default cursor templates in {out_dir}")
