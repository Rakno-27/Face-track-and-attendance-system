import cv2
import time
import threading
import logging

from recognition.face_service import identify_frame
from utils.attendance_service import get_current_session, mark_attendance

try:
    from liveness.blink import BlinkDetector
except ImportError:
    BlinkDetector = None

class CameraManager:
    def __init__(self, app):
        self.app = app
        self.video_source = 0
        self.cap = None
        self.is_running = False
        self.thread = None
        self.current_frame = None
        self.condition = threading.Condition()
        self.liveness = BlinkDetector() if BlinkDetector else None
        
    def start(self):
        if not self.is_running:
            self.cap = cv2.VideoCapture(self.video_source)
            self.is_running = True
            self.thread = threading.Thread(target=self._loop)
            self.thread.daemon = True
            self.thread.start()
            logging.info("Background camera thread started.")
            
    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
            self.cap = None
        logging.info("Background camera thread stopped.")
            
    def _loop(self):
        frame_idx = 0
        last_session_check = 0
        cached_session = None
        last_results = []
        scale = 0.25
        
        while self.is_running:
            try:
                ret, frame = self.cap.read()
            except:
                ret, frame = False, None
                
            if not ret or frame is None:
                time.sleep(0.01)
                continue
                
            frame_idx += 1
            out_frame = frame.copy()
            
            liveness_status = {"passed": True}
            if self.liveness:
                liveness_status = self.liveness.update(out_frame)
                blinks = liveness_status["blinks"]
                passed = liveness_status["passed"]
                if passed:
                    cv2.putText(out_frame, "Liveness Passed", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                else:
                    cv2.putText(out_frame, f"Blinks: {blinks} / {self.liveness.required_blinks}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            
            if frame_idx % 5 == 0:
                small = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
                last_results = identify_frame(small)
                
            if time.time() - last_session_check > 10:
                try:
                    cached_session = get_current_session(app=self.app)
                except Exception:
                    pass
                last_session_check = time.time()
            
            is_open = False
            subject, lecture, start_time, end_time = "", "", "", ""
            
            if cached_session:
                is_open = (cached_session.get("status") == "open")
                if is_open:
                    subject = cached_session["session"].get("subject", "")
                    lecture = cached_session["session"].get("lecture", "")
                    start_time = cached_session["session"].get("start", "")
                    end_time = cached_session["session"].get("end", "")

            for r in last_results:
                top, right, bottom, left = [int(coord / scale) for coord in r["box"]]
                color = (0, 255, 0) if r['recognized'] else (0, 0, 255)
                cv2.rectangle(out_frame, (left, top), (right, bottom), color, 2)
                label = f"{r['name']} ({r['confidence']}%)"
                cv2.putText(out_frame, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                if frame_idx % 5 == 0:
                    if is_open and r['recognized'] and liveness_status.get("passed", True):
                        ok, msg = mark_attendance(r["student_id"], r["name"], r["confidence"], subject, lecture, start_time, end_time, self.app)
                        if ok and self.liveness:
                            self.liveness.reset()
            
            ret, buffer = cv2.imencode('.jpg', out_frame)
            if ret:
                with self.condition:
                    self.current_frame = buffer.tobytes()
                    self.condition.notify_all()

    def wait_and_get_frame(self):
        with self.condition:
            self.condition.wait(timeout=1.0)
            return self.current_frame
