from pathlib import Path
from app.config import get_settings

MODEL_PATH = get_settings().ai_model_path_abs

_model = None
_model_loaded = False


def _get_model():
    global _model, _model_loaded
    if _model_loaded:
        return _model

    _model_loaded = True
    try:
        from ultralytics import YOLO
        _model = YOLO(str(MODEL_PATH))
    except Exception as exc:
        # Keep the API and photo upload flow available when model weights or
        # optional inference dependencies are unavailable.
        print(f"Object detection unavailable: {exc}")
    return _model


def detect_objects(image_bytes: bytes):
    model = _get_model()
    if model is None:
        return []

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp:
        temp.write(image_bytes)
        temp_path = temp.name

    try:
        # Use smaller image size (320px) for faster inference on CPU
        # conf=0.45 matches AI_CONFIDENCE_THRESHOLD from config
        results = model(temp_path, imgsz=320, conf=0.45, verbose=False, stream=False)

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
