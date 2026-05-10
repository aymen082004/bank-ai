import cv2
from detectron2.config import get_cfg
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog

from config import CLASS_NAMES, MODEL_PATH


cfg = get_cfg()
cfg.merge_from_file(
    model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml")
)

cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(CLASS_NAMES)
cfg.MODEL.WEIGHTS = MODEL_PATH
cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5
cfg.MODEL.DEVICE = "cpu"

predictor = DefaultPredictor(cfg)

metadata = MetadataCatalog.get("bankia_dataset")
metadata.thing_classes = CLASS_NAMES


def get_best_detection(detections, class_name):
    filtered = [d for d in detections if d["class"] == class_name]

    if not filtered:
        return None

    return max(filtered, key=lambda x: x["score"])


def get_best_detection_multi(detections, class_names):
    filtered = [d for d in detections if d["class"] in class_names]

    if not filtered:
        return None

    return max(filtered, key=lambda x: x["score"])


def detect_fields(image):
    outputs = predictor(image)
    instances = outputs["instances"].to("cpu")

    boxes = instances.pred_boxes.tensor.numpy()
    classes = instances.pred_classes.numpy()
    scores = instances.scores.numpy()

    detections = []

    for box, cls, score in zip(boxes, classes, scores):
        detections.append({
            "class": CLASS_NAMES[int(cls)],
            "score": round(float(score), 3),
            "bbox": [round(float(x), 2) for x in box]
        })

    return detections, instances


def draw_result_image(image, instances):
    visualizer = Visualizer(
        image[:, :, ::-1],
        metadata=metadata,
        scale=0.8
    )

    result = visualizer.draw_instance_predictions(instances)
    result_image = result.get_image()[:, :, ::-1]

    return result_image