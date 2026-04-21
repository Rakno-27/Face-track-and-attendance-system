import cv2
import time
import threading
import logging

from services.face_service import identify_frame
from services.attendance_service import get_current_session, mark_attendance

class CameraManager:
    def __init__(self, app):
        self.app = app
        self.video_source = 0
        self.cap = None
        self.is_running = False
        self.thread = None
        self.current_frame = None
        self.condition = threading.Condition()
        
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
        while self.is_running:
            try:
                ret, frame = self.cap.read()
            except:
                ret, frame = False, None
                
            if not ret or frame is None:
                time.sleep(0.5)
                continue
                
            frame_idx += 1
            out_frame = frame.copy()
            
            if frame_idx % 2 == 0:
                scale = 0.25
                small = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
                results = identify_frame(small)
                
                is_open = False
                subject, lecture, start_time, end_time = "", "", "", ""
                try:
                    sess = get_current_session(app=self.app)
                    is_open = (sess["status"] == "open")
                    if is_open:
                        subject = sess["session"]["subject"]
                        lecture = sess["session"]["lecture"]
                        start_time = sess["session"]["start"]
                        end_time = sess["session"]["end"]
                except Exception as e:
                    pass

                for r in results:
                    top, right, bottom, left = [int(coord / scale) for coord in r["box"]]
                    color = (0, 255, 0) if r['recognized'] else (0, 0, 255)
                    cv2.rectangle(out_frame, (left, top), (right, bottom), color, 2)
                    label = f"{r['name']} ({r['confidence']}%)"
                    cv2.putText(out_frame, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    
                    if is_open and r['recognized']:
                        mark_attendance(r["student_id"], r["name"], r["confidence"], subject, lecture, start_time, end_time, self.app)
            
            ret, buffer = cv2.imencode('.jpg', out_frame)
            if ret:
                with self.condition:
                    self.current_frame = buffer.tobytes()
                    self.condition.notify_all()

    def wait_and_get_frame(self):
        with self.condition:
            self.condition.wait(timeout=1.0)
            return self.current_frame
