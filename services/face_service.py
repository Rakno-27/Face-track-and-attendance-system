import base64
import logging
import numpy as np
from io import BytesIO
from PIL import Image
try:
    import face_recognition
except ImportError:
    face_recognition = None

# Using the unified models safely mapped correctly explicitly
from models import Student
from encoding_utils import deserialize_encoding

TOLERANCE = 0.45

known_encodings, known_ids, known_names = [], [], []

def reload_cache(app):
    global known_encodings, known_ids, known_names
    with app.app_context():
        logging.info("Optimizing System Memory natively via Database Cache...")
        encs, ids, names = [], [], []
        
        st_list = Student.query.filter(Student.encoding.isnot(None)).all()
        for s in st_list:
            arr = deserialize_encoding(s.encoding)
            if arr is not None:
                encs.append(arr)
                ids.append(str(s.roll_number))
                names.append(s.name)
                
        known_encodings, known_ids, known_names = encs, ids, names
        logging.info(f"Loaded {len(encs)} SQLAlchemy encodings definitively mapping globally.")

def encode_from_b64(b64_str):
    if not face_recognition: return None
    try:
        raw = base64.b64decode(b64_str.split(",")[-1])
        img = Image.open(BytesIO(raw)).convert("RGB")
        arr = np.array(img)
        
        h, w = arr.shape[:2]
        if w > 640:
            scale = 640 / w
            import cv2
            arr = cv2.resize(arr, (0, 0), fx=scale, fy=scale)
            
        locs = face_recognition.face_locations(arr)
        if not locs:
            logging.warning("No face locations found during encoding.")
            return None
        logging.info("Generated 1 face encoding successfully.")
        encs = face_recognition.face_encodings(arr, [locs[0]])
        return encs[0] if encs else None
    except Exception as e:
        logging.error(f"Error extracting encoding: {e}")
        return None

def identify_frame(frame):
    if not known_encodings or not face_recognition:
        return []

    rgb = np.ascontiguousarray(frame[:, :, ::-1])
    locs = face_recognition.face_locations(rgb)
    if not locs:
        return []
        
    logging.info(f"Detected {len(locs)} face(s) in frame.")
    encs = face_recognition.face_encodings(rgb, locs)

    results = []
    for enc, loc in zip(encs, locs):
        dists = face_recognition.face_distance(known_encodings, enc)
        idx = int(np.argmin(dists))
        best_d = float(dists[idx])

        if best_d <= TOLERANCE:
            logging.info(f"Matched {known_names[idx]} (Dist: {best_d:.3f} <= {TOLERANCE})")
            results.append({
                "name": known_names[idx],
                "student_id": known_ids[idx],
                "confidence": round((1 - best_d) * 100, 1),
                "box": loc,
                "recognized": True
            })
        else:
            logging.info(f"Unknown face (Best Dist: {best_d:.3f} > {TOLERANCE})")
            results.append({
                "name": "Unknown",
                "student_id": None,
                "confidence": 0,
                "box": loc,
                "recognized": False
            })
    return results
