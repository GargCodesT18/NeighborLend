from pathlib import Path
from ultralytics import YOLO

MODEL_PATH = Path(__file__).resolve().parents[2] / "ai_service" / "best_model.pt"

model = YOLO(str(MODEL_PATH))


def detect_objects(image_bytes: bytes):
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp:
        temp.write(image_bytes)
        temp_path = temp.name

    try:
        results = model(temp_path, conf=0.25, verbose=False)

        detections = []

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                detections.append({
                    "class": model.names[class_id],
                    "confidence": round(confidence, 4)
                })

        return detections

    finally:
        Path(temp_path).unlink(missing_ok=True) 