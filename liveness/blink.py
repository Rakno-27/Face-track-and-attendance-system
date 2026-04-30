import cv2
import math
import logging

try:
    import mediapipe as mp
except ImportError:
    mp = None
    logging.warning("MediaPipe is not installed. Blink detection will not work.")

class BlinkDetector:
    def __init__(self, required_blinks=3, ear_threshold=0.22, consecutive_frames=2):
        self.required_blinks = required_blinks
        self.ear_threshold = ear_threshold
        self.consecutive_frames = consecutive_frames

        self.blink_count = 0
        self.frame_counter = 0
        self.passed = False
        
        if mp is not None:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        else:
            self.face_mesh = None

        # Left eye indices (MediaPipe Face Mesh)
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        # Right eye indices
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]

    def reset(self):
        self.blink_count = 0
        self.frame_counter = 0
        self.passed = False

    def _euclidean_distance(self, p1, p2):
        return math.hypot(p1.x - p2.x, p1.y - p2.y)

    def _calculate_ear(self, landmarks, eye_indices):
        # MediaPipe uses normalized coordinates
        p_left = landmarks[eye_indices[0]]
        p_top1 = landmarks[eye_indices[1]]
        p_top2 = landmarks[eye_indices[2]]
        p_right = landmarks[eye_indices[3]]
        p_bottom1 = landmarks[eye_indices[4]]
        p_bottom2 = landmarks[eye_indices[5]]

        # Vertical eye distances
        v1 = self._euclidean_distance(p_top1, p_bottom2)
        v2 = self._euclidean_distance(p_top2, p_bottom1)
        # Horizontal eye distance
        h = self._euclidean_distance(p_left, p_right)

        # Compute EAR
        if h == 0: return 0
        ear = (v1 + v2) / (2.0 * h)
        return ear

    def update(self, frame_bgr):
        if self.passed or self.face_mesh is None:
            return {
                "passed": self.passed,
                "blinks": self.blink_count,
                "ear": 0.0
            }

        # Convert the BGR image to RGB
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        ear = 0.0
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            
            left_ear = self._calculate_ear(landmarks, self.LEFT_EYE)
            right_ear = self._calculate_ear(landmarks, self.RIGHT_EYE)
            
            ear = (left_ear + right_ear) / 2.0

            if ear < self.ear_threshold:
                self.frame_counter += 1
            else:
                if self.frame_counter >= self.consecutive_frames:
                    self.blink_count += 1
                self.frame_counter = 0

            if self.blink_count >= self.required_blinks:
                self.passed = True

        return {
            "passed": self.passed,
            "blinks": self.blink_count,
            "ear": round(ear, 3)
        }
