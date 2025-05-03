import cv2
import time
import os
import numpy as np

class FaceEmotionDetector:
    def __init__(self):
        self.face_cascade_path = "haarcasecade_frontalface_default.xml"
        if not os.path.exists(self.face_cascade_path):
            print("Downloading face detection model...")
            url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
            import urllib.request
            urllib.request.urlretrieve(url, self.face_cascade_path)
            print("Model downloaded successfully!")

        self.face_cascade = cv2.CascadeClassifier(self.face_cascade_path)

        self.eye_cascade_path = "haarcascade_eye.xml"
        if not os.path.exists(self.eye_cascade_path):
            print("Downloading eye detection model...")
            url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_eye.xml"
            import urllib.request
            urllib.request.urlretrieve(url, self.eye_cascade_path)
            print("Eye model downloaded successfully!")

        self.eye_cascade = cv2.CascadeClassifier(self.eye_cascade_path)

        self.emotion_colors = {
            "happy": (0, 255, 0),
            "sad": (255, 0, 0),
            "angry": (0, 0, 255),
            "surprised": (255, 0, 255),
            "neutral": (255, 255, 255)
        }

        self.current_emotion = "neutral"
        self.emotion_stability = 0
        self.smile_threshold = 0.4
        self.last_faces = []

        self.eyes_closed_time = 0
        self.is_eyes_closed = False
        self.drowsiness_threshold = 2.0
        self.drowsiness_detected = False

    def detect_faces(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        return faces, gray
    
    def detect_eyes(self, gray_face):
        eyes = self.eye_cascade.detectMultiScale(
            gray_face,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(20, 20)
        )
        return eyes
    
    def detect_drowsiness(self, face_roi, current_time):
        eyes = self.detect_eyes(face_roi)

        if len(eyes) < 2:
            if not self.is_eyes_closed:
                self.is_eyes_closed = True
                self.eyes_closed_time = current_time

            if current_time - self.eyes_closed_time > self.drowsiness_threshold:
                self.drowsiness_detected = True
                return True
        else :
            self.is_eyes_closed = False
            self.drowsiness_detected = False

        return False
    
    def detect_smile(self, face_roi):
        height, width = face_roi.shape

        mouth_top = int(height * 0.6)
        mouth_bottom = int(height * 0.9)
        mouth_left = int(width * 0.3)
        mouth_right = int(width * 0.7)

        mouth_roi = face_roi[mouth_top:mouth_bottom, mouth_left:mouth_right]
        avg_intensity = np.mean(mouth_roi)
        normalized_intensity = avg_intensity / 255.0

        return normalized_intensity > self.smile_threshold
    
    def detect_emotion(self, face_roi, face_x, face_y, face_w, face_h, current_time):
        height, width = face_roi.shape

        eye_region_top = int(height * 0.2)
        eye_region_bottom = int(height * 0.5)
        mouth_region_top = int(height * 0.6)
        mouth_region_bottom = int(height * 0.9)

        eye_region = face_roi[eye_region_top:eye_region_bottom, :]
        mouth_region = face_roi[mouth_region_top:mouth_region_bottom, :]

        is_smiling = self.detect_smile(face_roi)
        eye_intensity = np.mean(eye_region) / 255.0
        mouth_intensity = np.mean(mouth_region) / 255.0

        is_drowsy = self.detect_drowsiness(face_roi, current_time)

        self.last_faces.append((face_x, face_y, face_w, face_h))
        if len(self.last_faces) > 10:
            self.last_faces.pop(0)

        face_movement = 0
        if len(self.last_faces) > 5:
            diffs  = []
            for i in range(1, len(self.last_faces)):
                prev_x, prev_y, _, _ = self.last_faces[i-1]
                curr_x, curr_y, _, _ = self.last_faces[i]
                diff = abs(prev_x - curr_x) + abs(prev_y - curr_y)
                diffs.append(diff)
            face_movement = sum(diffs) / len(diffs)

        # rules
        if is_smiling and eye_intensity > 0.4:
            emotion = "happy"
            confidence = 0.7 + (eye_intensity * 0.3)
        elif face_movement > 10:
            emotion = "surprised"
            confidence = min(0.5 + (face_movement / 50), 0.9)
        elif eye_intensity < 0.3 and mouth_intensity < 0.3:
            emotion = "sad"
            confidence = 0.5 + ((1 - eye_intensity) * 0.3)
        elif eye_intensity < 0.3 and mouth_intensity > 0.4:
            emotion = "angry"
            confidence = 0.5 + ((1 - eye_intensity) * 0.3)
        else:
            emotion = "neutral"
            confidence = 0.6 

        if emotion == self.current_emotion:
            self.emotion_stability += 1
        else:
            self.emotion_stability -= 1

        if self.emotion_stability > 5:
            self.emotion_stability = 5
        elif self.emotion_stability < 0:
            self.emotion_stability = 0
            self.current_emotion = emotion

        return self.current_emotion, confidence, is_drowsy, eye_intensity