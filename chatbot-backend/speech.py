import os
from io import BytesIO
from fastapi import UploadFile
from TTS.api import TTS
from playsound import playsound
import whisper


# Load the Whisper model (choose 'tiny', 'base', 'small',Large )
model = whisper.load_model("small")


def voice_to_text(audio_data: BytesIO):
    """
    Convert audio to text using OpenAI's Whisper model.
    """
    try:
        # Save the audio data to a temporary file
        with open("temp_audio.wav", "wb") as f:
            f.write(audio_data.getvalue())

        # Use the Whisper model to transcribe the audio
        print("Recognizing speech using Whisper...")
        result = model.transcribe("temp_audio.wav")
        text = result.get("text", "")

        # Clean up temporary file
        os.remove("temp_audio.wav")

        if text:
            return {"success": True, "text": text}
        else:
            return {"success": False, "error": "Could not recognize text from audio."}

    except Exception as e:
        return {"success": False, "error": f"An error occurred: {str(e)}"}


def text_to_speech(text, filename='response_audio.mp3', play_sound=False):
    try:
        tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")
        
        filepath = os.path.join(os.getcwd(), filename) 

        tts.tts_to_file(text=text, file_path=filepath)

        if os.path.exists(filepath):
            print(f"Audio file {filepath} exists.")
        else:
            print(f"{filepath} does not exist.")

    except Exception as e:
        print(f"Error converting text to speech: {e}")

