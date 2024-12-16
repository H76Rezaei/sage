import speech_recognition as sr
from io import BytesIO
from fastapi import UploadFile
from gtts import gTTS
import os
from playsound import playsound
from TTS.api import TTS
from nltk.tokenize import sent_tokenize
import torch
from pydub import AudioSegment

def get_device():
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():  # For macOS
        return "mps"
    else:
        return "cpu"

device = get_device()

tts_model = TTS(model_name="tts_models/en/vctk/fast_pitch").to(device)

#list available speakers
print("Available speakers:", tts_model.speakers)

def voice_to_text(audio_data: BytesIO):
    """
    Convert audio to text using SpeechRecognition.
    """
    recognizer = sr.Recognizer()

    # Use the BytesIO object directly
    try:
        with sr.AudioFile(audio_data) as source:
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
        print(f"Audio file saved as: {filename}")  # Log the file path

        # Check if the file exists
        if os.path.exists(filename):
            print(f"Audio file {filename} exists.")
        else:
            print(f"Audio file {filename} does not exist.")

        # Optionally, play the sound if needed
        if play_sound:
            try:
                playsound(filename)
            except Exception as e:
                print(f"Error playing sound: {e}")
    except Exception as e:
        print(f"Error converting text to speech: {e}")


def new_tts(text, filename='response.wav', play_sound=False, model_name="tts_models/en/vctk/fast_pitch"):
    """
    Convert text to speech using Coqui TTS and save as an audio file.
    Optionally, play the sound after saving.
    """
    try:
        # Load the TTS model
        #tts = TTS(model_name)

        # Synthesize speech from text and save it as a WAV file
        tts_model.tts_to_file(text=text, file_path=filename)
        print(f"Audio file saved as: {filename}")  # Log the file path

        # Check if the file exists
        if os.path.exists(filename):
            print(f"Audio file {filename} exists.")
        else:
            raise FileNotFoundError(f"Audio file {filename} does not exist.")

        # Optionally, play the sound if needed
        if play_sound:
            try:
                from playsound import playsound
                playsound(filename)
            except Exception as e:
                print(f"Error playing sound: {e}")
    except Exception as e:
        print(f"Error converting text to speech: {e}")

def cashed(text, filename='response.wav'):
    try:
        tts_model.tts_to_file(text=text, file_path=filename, speaker="VCTK_p225")
        print(f"Audio file saved as: {filename}")
    except Exception as e:
        print(f"Error converting text to speech: {e}")


def new_tts_incremental(text, filename='response.wav', model_name="tts_models/en/vctk/fast_pitch"):
    """
    Convert text to speech incrementally using Coqui TTS and save output for each chunk.
    """
    try:
        #tts = TTS(model_name)
        sentences = sent_tokenize(text)  # Split text into sentences
        audio_chunks = []

        for i, sentence in enumerate(sentences):
            temp_filename = f"chunk_{i}.wav"
            tts_model.tts_to_file(text=sentence, file_path=temp_filename)
            audio_chunks.append(temp_filename)

        # Concatenate chunks into a single audio file
        combined = AudioSegment.empty()
        for chunk in audio_chunks:
            combined += AudioSegment.from_file(chunk)

        combined.export(filename, format="wav")
        print(f"Audio file saved as: {filename}")
        return filename
    except Exception as e:
        print(f"Error converting text to speech incrementally: {e}")
        return None
