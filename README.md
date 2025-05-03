# Simple Facial Emotion Detection

This project uses OpenCV to detect faces and a simple rule-based system to identify emotions from facial expressions in real-time using a webcam.

## Requirements

- Python
- Webcam

## Installation

1. Create a virtual environment (optional but recommended)

   ```
   python -m venv venv
   venv\Scripts\activate
   ```

2. Install required packages
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the main script:

```
python main.py
```

- The webcam will open and start detecting faces and emotions.
- The detected emotion will be displayed on the frame with a colored box.
- Press 'q' to quit the application.

## Features

- Real-time face detection using Haar Cascades
- Simple emotion detection (happy, sad, angry, surprised, neutral)
- FPS counter
- Colored bounding boxes for different emotions
- No complex dependencies - uses only OpenCV and NumPy

## How it works

This program uses a simple rule-based approach to detect emotions:

- Happy: Detected when smiling (based on pixel intensity in mouth region)
- Sad: Low intensity in both eye and mouth regions
- Angry: Low intensity in eye region with higher intensity in mouth region
- Surprised: Detected based on rapid face movement
- Neutral: Default state when no other emotion is strongly detected

This is a simplified approach and not as accurate as deep learning models, but it works without requiring complex dependencies.

## License

This project is licensed under [nnackpt](https://github.com/nnackpt) License.
