import cv2
import cv2.data
import numpy as np
import time

class DrowsinessDetector:
    def __init__(self, eye_ar_thresh=0.25, eye_ar_consec_frames=48):
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.eye_ar_thresh = eye_ar_thresh
        self.eye_ar_consec_frames = eye_ar_consec_frames
        self.eye_closed_counter = 0
        self.last_alert_time = 0
        self.alert_cooldown = 10.0
        self.is_drowsy = False

    def detect_eyes(self, face_roi):
        eyes = self.eye_cascade.detectMultiScale(
            face_roi,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        return eyes
    
    def eye_aspect_ratio(self, eye_region):
        return np.mean(eye_region) / 255.0
    
    def check_drowsiness(self, face_roi, current_time):
        eyes = self.detect_eyes(face_roi)

        if len(eyes) < 2:
            self.eye_closed_counter += 1
        else:
            eye_ar_sum = 0
            for (ex, ey, ew, eh) in eyes[:2]:
                eye_region = face_roi[ey:ey+eh, ex:ex+ew]
                eye_ar = self.eye_aspect_ratio(eye_region)
                eye_ar_sum += eye_ar

            eye_ar_avg = eye_ar_sum / len(eyes[:2])

            if eye_ar_avg < self.eye_ar_thresh:
                self.eye_closed_counter += 1
            else:
                self.eye_closed_counter = 0

        if self.eye_closed_counter >= self.eye_ar_consec_frames:
            self.is_drowsy = True

            should_alert = current_time - self.last_alert_time > self.alert_cooldown
            if should_alert:
                self.last_alert_time = current_time

            return self.is_drowsy, should_alert
        else:
            self.is_drowsy = False
            return self.is_drowsy, False
        
    def reset(self):
        self.eye_closed_counter = 0
        self.is_drowsy = False