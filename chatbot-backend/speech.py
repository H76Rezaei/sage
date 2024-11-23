import speech_recognition as sr
from io import BytesIO
from fastapi import UploadFile

from gtts import gTTS
from playsound import playsound




def voice_to_text(audio: UploadFile):
  
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
   
    tts = gTTS(text=text, lang='en')
    tts.save(filename)