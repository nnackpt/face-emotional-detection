import pyttsx3
import threading
import time
from gtts import gTTS
import os
import pygame
import tempfile
import platform

class AudioFeedback:
    def __init__(self, use_gtts=False):
        self.use_gtts = use_gtts
        self.is_speaking = False
        self.last_emotion = None
        self.last_speech_time = 0
        self.speech_cooldown = 10  # Cooldown time in seconds

        if not use_gtts:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 0.9)
            voices = self.engine.getProperty('voices')

            thai_voice = None
            for voice in voices:
                if "thai" in voice.name.lower():
                    thai_voice = voice.id
                    break

            if thai_voice:
                self.engine.setProperty('voice', thai_voice)
        else:
            pygame.mixer.init()

    def speak(self, text, emotion=None):
        current_time = time.time()
        if emotion == self.last_emotion and current_time - self.last_speech_time < self.speech_cooldown:
            return
        
        self.last_emotion = emotion
        self.last_speech_time = current_time

        thread = threading.Thread(target=self._speak_in_thread, args=(text, emotion))
        thread.daemon = True
        thread.start()

    def _speak_in_thread(self, text, emotion):
        if self.is_speaking:
            return
        
        self.is_speaking = True

        try:
            if self.use_gtts:
                self._speak_gtts(text)
            else:
                self._speak_pyttsx3(text, emotion)
        finally:
            self.is_speaking = False

    def _speak_pyttsx3(self, text, emotion):
        if emotion == "happy":
            self.engine.setProperty('rate', 170)
            self.engine.setProperty('volume', 1.0)
        elif emotion == "sad":
            self.engine.setProperty('rate', 130),
            self.engine.setProperty('volume', 0.7)
        elif emotion == "angry":
            self.engine.setProperty('rate', 180)
            self.engine.setProperty('volume', 1.0)
        elif emotion == 'surprised':
            self.engine.setProperty('rate', 190)
            self.engine.setProperty('volume', 1.0)
        elif emotion == "drowsy":
            self.engine.setProperty('rate', 140)
            self.engine.setProperty('volume', 1.0)
        else:
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 0.9)

        self.engine.say(text)
        self.engine.runAndWait()

    def _speak_gtts(self, text):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            temp_filename = tmp_file.name

        tts = gTTS(text=text, lang='th', slow=False)
        tts.save(temp_filename)

        pygame.mixer.music.load(temp_filename)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        try:
            os.unlink(temp_filename)
        except:
            pass

    def get_emotion_message(self, emotion, is_drowsy=False):
        if is_drowsy:
            return "คุณดูเหมือนจะง่วงนอน คุณควรพักผ่อนสักครู่นะครับ"
        
        if emotion == "happy":
            messages = [
                "คุณดูมีความสุขมากเลยนะคะ ดีใจด้วยครับ",
                "รอยยิ้มของคุณดูสดใสมากเลย",
                "วันนี้คุณดูร่าเริงดีจัง"
            ]
        elif emotion == "sad":
            messages = [
                "คุณดูเศร้านะครับ มีอะไรให้ช่วยไหมครับ",
                "อย่าเสียใจไปเลยนะครับ ทุกอย่างจะดีขึ้นครับ",
                "ผมอยู่ตรงนี้นะครับ หากคุณต้องการคนคุยด้วย"
                "ขอให้คุณมีกำลังใจนะครับ สู้ๆ ครับ"
            ]
        elif emotion == "angry":
            messages = [
                "คุณดูหงุดหงิดนะครับ ลองหายใจเข้าลึกๆ สักครู่ไหมครับ"
                "อย่าโกรธเลยครับ ใจเย็นๆนะครับ ไอควย"
                "มีอะไรทำให้คุณอารมณ์ไม่ดีรึเปล่าครับ"
            ]
        elif emotion == 'surprised':
            messages = [
                "คุณดูแปลกใจนะครับ มีอะไรน่าตื่นเต้นล่ะไอสัส"
                "เป็นควยอะไรหรือเปล่าครับ คุณดูตกใจ"
            ]
        else:
            messages = [
                "สวัสดีครับ มีอะไรให้ช่วยไหม",
                "คุณดูสบายดีนะครับวันนี้",
                "มีอะไรให้ช่วยไหมไอควาย"
            ]

        import random
        return random.choice(messages)