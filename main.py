import cv2
import time
import os
import numpy as np

class SimpleFaceEmotionDetector:
    def __init__(self):
        self.face_cascade_path = "haarcascade_frontalface_default.xml"
        if not os.path.exists(self.face_cascade_path):
            print("Downloading face detection model...")
            url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
            import urllib.request
            urllib.request.urlretrieve(url, self.face_cascade_path)
            print("Model downloaded successfully!")

        self.face_cascade = cv2.CascadeClassifier(self.face_cascade_path)

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
        self.last_fasces = []

    def detect_faces(self, frame):
        """Detect faces in the given frame using Haar Cascade"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        return faces, gray
    
    def detect_smile(self, face_roi):
        """A simple smile detection based on pixel intensity in mouth region"""
        height, width = face_roi.shape

        mouth_top = int(height * 0.6)
        mouth_bottom = int(height * 0.9)
        mouth_left = int(width * 0.3)
        mouth_right = int(width * 0.7)

        mouth_roi = face_roi[mouth_top:mouth_bottom, mouth_left:mouth_right]
        avg_intensity = np.mean(mouth_roi)
        normalized_intensity = avg_intensity / 255.0

        return normalized_intensity > self.smile_threshold
    
    def detect_emotion(self, face_roi, face_x, face_y, face_w, face_h):
        """Simple emotion detection based on facial features
        This is a simplified approach and not as accurate as ML models.
        """
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

        self.last_fasces.append((face_x, face_y, face_w, face_h))
        if len(self.last_fasces) > 10:
            self.last_fasces.pop(0)

        face_movement = 0
        if len(self.last_fasces) > 5:
            diffs = []
            for i in range(1, len(self.last_fasces)):
                prev_x, prev_y, _, _ = self.last_fasces[i-1]
                curr_x, curr_y, _, _ = self.last_fasces[i]
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
        elif eye_intensity < 0.3  and mouth_intensity > 0.4:
            emotion = "angry"
            confidence = 0.5 + ((1 - eye_intensity) * 0.3)
        else :
            emotion = "neutral"
            confidence = 0.6

        if emotion == self.current_emotion:
            self.emotion_stability += 1
        else :
            self.emotion_stability -= 1

        if self.emotion_stability > 5:
            self.emotion_stability = 5
        elif self.emotion_stability < 0:
            self.emotion_stability = 0
            self.current_emotion = emotion

        return self.current_emotion, confidence
    
def main():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open webcam")
        return
    
    print("Starting simple facial emotion detection...")

    detector = SimpleFaceEmotionDetector()

    # fps
    prev_frame_time = 0
    new_frame_time = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture image")
            break

        new_frame_time = time.time()
        fps = 1/(new_frame_time-prev_frame_time) if prev_frame_time > 0 else 0
        prev_frame_time = new_frame_time

        frame = cv2.flip(frame, 1)
        faces, gray = detector.detect_faces(frame)

        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            emotion, confidence = detector.detect_emotion(face_roi, x, y, w, h)
            color = detector.emotion_colors.get(emotion, (200, 200, 200))
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

            label = f"{emotion.capitalize()}: {confidence:.2f}"
            cv2.putText(frame, label, (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
        cv2.putText(frame, f"FPS: {int(fps)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 0), 2)
        
        cv2.putText(frame, "Press 'q' to quit", (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(frame, "Smile for happy, frown for sad, furrow brow for angry",
                    (10, frame.shape[0] - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        cv2.imshow("Simple Facial Emotion Detector", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()