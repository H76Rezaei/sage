import speech_recognition as sr
from io import BytesIO
from fastapi import UploadFile

from gtts import gTTS
from playsound import playsound
import os



def voice_to_text(audio: UploadFile):
    """
    Convert audio to text using SpeechRecognition.
    """
    recognizer = sr.Recognizer()
    
    # Read audio data from UploadFile
    audio_data = audio.file.read()
    
    # Convert byte data to AudioFile
    audio_file = BytesIO(audio_data)
    
    try:
        with sr.AudioFile(audio_file) as source:
            print("Recognizing speech...")
            audio_recorded = recognizer.record(source)
            text = recognizer.recognize_google(audio_recorded)
            return {"success": True, "text": text}
    except sr.UnknownValueError:
        return {"success": False, "error": "Could not understand the audio."}
    except sr.RequestError as e:
        return {"success": False, "error": f"Could not request results from Google Speech Recognition service; {str(e)}"}


# Function to convert text to speech
def text_to_speech(text, filename='response.mp3'):
    """
    Convert text to speech and save as an MP3 file.
    """
    tts = gTTS(text=text, lang='en')
    tts.save(filename)
    # Optionally, play the sound if needed
    os.system(f"start {filename}")