import cv2
import time
import os
import sys
import argparse
from datetime import datetime
from detector import FaceEmotionDetector
from utils import AudioFeedback, DataLogger

def parse_arguments():
    parser = argparse.ArgumentParser(description='Facial Emotion Detection System with Audio Feedback')
    parser.add_argument('--no-audio', action='store_true', help='Disable audio feedback')
    parser.add_argument('--use-gtts', action='store_true', help='Use Google Text-to-Speech instead of pyttsx3')
    parser.add_argument('--no-save', action='store_true', help='Disable saving logs')
    parser.add_argument('--report', action='store_true', help='Generate reports and exit')
    parser.add_argument('--video', type=str, default='0', help='Path to video file or camera index (default: 0)')
    return parser.parse_args()

def main():
    args = parse_arguments()

    if args.report:
        generate_reports()
        return
    
    if args.video.isdigit():
        cap = cv2.VideoCapture(int(args.video))
    else:
        cap = cv2.VideoCapture(args.video)

    if not cap.isOpened():
        print("Error: Could not open video source")
        return
    
    print("Starting enhanced facial emotion detection system...")

    detector = FaceEmotionDetector()

    audio_feedback = None
    if not args.no_audio:
        audio_feedback = AudioFeedback(use_gtts=args.use_gtts)

    data_logger = None
    if not args.no_save:
        data_logger = DataLogger(csv_path='data/emotion_logs.csv', db_path='data/emotion_logs.db')

    prev_frame_time = 0
    new_frame_time = 0

    log_interval = 1.0
    last_log_time = time.time()

    speak_interval = 3.0
    last_speak_time = 0

    print("System ready! Press 'q' to quit, 'r' to generate reports.")

    while True:
        ret, frame = cap.read()
        current_time = time.time()

        if not ret:
            print("Error: Failed to capture image")
            break

        new_frame_time = time.time()
        fps = 1/(new_frame_time - prev_frame_time) if prev_frame_time > 0 else 0
        prev_frame_time = new_frame_time

        frame = cv2.flip(frame, 1)
        faces, gray = detector.detect_faces(frame)
        current_emotions = []
        is_anyone_drowsy = False

        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            emotion, confidence, is_drowsy, eye_intensity = detector.detect_emotion(face_roi, x, y, w, h, current_time)
            current_emotions.append((emotion, confidence))

            if is_drowsy:
                is_anyone_drowsy = True

            color = detector.emotion_colors.get(emotion, (200, 200, 200))
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            emotion_text = f"{emotion.capitalize()}: {confidence:.2f}"
            cv2.putText(frame, emotion_text, (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            if is_drowsy:
                cv2.putText(frame, "DROWSY!", (x, y+h+30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                
            if data_logger and current_time - last_log_time >= log_interval:
                data_logger.log_emotion(emotion, confidence, fps, eye_intensity, is_drowsy)
                last_log_time = current_time
        
        if audio_feedback and current_time - last_speak_time >= speak_interval and current_emotions:
            last_speak_time = current_time

            if is_anyone_drowsy:
                message = audio_feedback.get_emotion_message("neutral", is_drowsy=True)
                audio_feedback.speak(message, "drowsy")
            else:
                sad_found = False
                highest_conf_emotion = None
                highest_conf = 0

                for emotion, conf in current_emotions:
                    if emotion == "sad":
                        sad_found = True
                        message = audio_feedback.get_emotion_message(emotion)
                        audio_feedback.speak(message, emotion)
                        break
                    elif conf > highest_conf:
                        highest_conf = conf
                        highest_conf_emotion = emotion

                if not sad_found and highest_conf_emotion:
                    message = audio_feedback.get_emotion_message(highest_conf_emotion)
                    audio_feedback.speak(message, highest_conf_emotion)

        cv2.putText(frame, f"FPS: {int(fps)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 0), 2)
        
        cv2.putText(frame, "Press 'q' to quit, 'r' fot reports", (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(frame, "Smile for happy, frown for sad, furrow brow for angry",
                    (10, frame.shape[0] - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        cv2.imshow("Enhanced Facial Emotion Detector", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('r'):
            if data_logger:
                generate_reports(data_logger)
            else:
                print("Data logging is disabled. Connot generate reports.")

    cap.release()
    cv2.destroyAllWindows()

def generate_reports(data_logger=None):
    if data_logger is None:
        data_logger = DataLogger(csv_path='data/emotion_logs.csv', db_path='data/emotion_logs.db')

    print("Generating reports...")

    daily_report = data_logger.generate_daily_report(output_path='data/daily_report.html')
    if daily_report:
        print(f"Daily report generated: {daily_report}")
    else:
        print("No data available for daily report.")

    today = datetime.now().strftime("%Y-%m-%d")
    hourly_report = data_logger.generate_hourly_report(day=today, output_path='data/hourly_report.html')
    if hourly_report:
        print(f"Hourly report generated: {hourly_report}")
    else:
        print("No data available for hourly report.")

if __name__ == "__main__":
    os.makedirs('data', exist_ok=True)
    main()