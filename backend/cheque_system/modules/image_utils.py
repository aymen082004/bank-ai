import os
import cv2
import base64
from config import CROP_DIR


def web_path(path):
    if path is None:
        return None
    return path.replace("\\", "/")


def crop_bbox(image, bbox, padding=15):
    x1, y1, x2, y2 = [int(v) for v in bbox]

    h, w = image.shape[:2]

    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(w, x2 + padding)
    y2 = min(h, y2 + padding)

    return image[y1:y2, x1:x2]


def save_crop(crop, prefix, filename):
    crop_filename = f"{prefix}_{filename}"
    crop_path = os.path.join(CROP_DIR, crop_filename)
    cv2.imwrite(crop_path, crop)
    return crop_path


def image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")