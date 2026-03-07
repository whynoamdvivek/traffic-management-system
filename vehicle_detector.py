# vehicle_detector.py
from ultralytics import YOLO
import cv2

# load once (downloads yolov8n.pt automatically first run)
_model = YOLO("yolov8n.pt")

def detect_vehicles(frame, conf_threshold=0.25):
    """
    Simple vehicle detector (no emergency detection).
    Returns:
      count (int), boxes (list of (x1,y1,x2,y2,score))
    Only COCO vehicle classes considered: car, motorcycle, bus, truck.
    """
    results = _model(frame)[0]
    vehicle_classes = {2, 3, 5, 7}  # car, motorcycle, bus, truck
    boxes = []
    count = 0

    for r in results.boxes.data:
        x1, y1, x2, y2, score, cls_id = r.tolist()
        score = float(score)
        cls_id = int(cls_id)
        if score < conf_threshold:
            continue
        if cls_id in vehicle_classes:
            count += 1
            boxes.append((int(x1), int(y1), int(x2), int(y2), float(score)))

    return count, boxes
