import speech_recognition as sr
from io import BytesIO
from fastapi import UploadFile
from gtts import gTTS
import os
from playsound import playsound


def voice_to_text(audio: UploadFile):
    """
    Convert audio to text using SpeechRecognition.
    """
    recognizer = sr.Recognizer()

    # Read audio data from UploadFile directly
    try:
        with sr.AudioFile(audio.file) as source:
            print("Recognizing speech...")
            audio_recorded = recognizer.record(source)
            text = recognizer.recognize_google(audio_recorded)
            return {"success": True, "text": text}
    except sr.UnknownValueError:
        return {"success": False, "error": "Could not understand the audio."}
    except sr.RequestError as e:
        return {"success": False, "error": f"Could not request results from Google Speech Recognition service; {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}


def text_to_speech(text, filename='response.mp3', play_sound=False):
    """
    Convert text to speech and save as an MP3 file.
    Optionally, play the sound after saving.
    """
    try:
        tts = gTTS(text=text, lang='en')
        tts.save(filename)
        
        # Optionally, play the sound if needed
        if play_sound:
            try:
                playsound(filename)
            except Exception as e:
                print(f"Error playing sound: {e}")
    except Exception as e:
        print(f"Error converting text to speech: {e}")
