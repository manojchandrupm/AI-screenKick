import base64
import io
# pyrefly: ignore [missing-import]

# pyrefly: ignore [missing-import]
from PIL import Image
from pathlib import Path
import sys
# pyrefly: ignore [missing-import]
import cv2
import numpy as np
import base64

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OMNIPARSER_ROOT = PROJECT_ROOT / "OmniParser"

if str(OMNIPARSER_ROOT) not in sys.path:
    sys.path.insert(0, str(OMNIPARSER_ROOT))
    
# pyrefly: ignore [missing-import]
from util.utils import (
    check_ocr_box,
    get_som_labeled_img,
)

def parse_image(
    image_path,
    yolo_model,
    caption_model_processor,
    box_threshold=0.15,
):
    """
    Parse a screenshot using OmniParser.

    Args:
        image_path: Path to image.
        yolo_model: Loaded YOLO model.
        caption_model_processor: Loaded Florence model.

    Returns:
        Dictionary containing parsed results.
    """

    image = Image.open(image_path)

    box_overlay_ratio = max(image.size) / 3200

    draw_bbox_config = {
        "text_scale": 0.8 * box_overlay_ratio,
        "text_thickness": max(int(2 * box_overlay_ratio), 1),
        "text_padding": max(int(3 * box_overlay_ratio), 1),
        "thickness": max(int(3 * box_overlay_ratio), 1),
    }

    (text, ocr_bbox), _ = check_ocr_box(
        image,
        display_img=False,
        output_bb_format="xyxy",
        easyocr_args={"text_threshold": 0.8},
        use_paddleocr=False,
    )

    labeled_img, label_coordinates, parsed_content = get_som_labeled_img(
        image,
        yolo_model,
        BOX_TRESHOLD=box_threshold,
        output_coord_in_ratio=True,
        ocr_bbox=ocr_bbox,
        draw_bbox_config=draw_bbox_config,
        caption_model_processor=caption_model_processor,
        ocr_text=text,
        use_local_semantics=False,
        iou_threshold=0.5,
        scale_img=False,
        batch_size=128,
    )

    annotated = base64.b64decode(labeled_img)
    annotated_np = np.frombuffer(annotated, np.uint8)
    annotated_img = cv2.imdecode(annotated_np, cv2.IMREAD_COLOR)

    annotated_path = str(image_path).replace(
        "screenshots",
        "annotated"
    )

    annotated_path = annotated_path.replace(
        Path(image_path).name,
        f"annotated_{Path(image_path).name}"
    )
    Path(annotated_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(annotated_path, annotated_img)

    return {
        "labeled_image": labeled_img,
        "annotated_path": annotated_path,
        "label_coordinates": label_coordinates,
        "parsed_content": parsed_content,
    }