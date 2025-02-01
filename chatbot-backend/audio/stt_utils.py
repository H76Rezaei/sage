import speech_recognition as sr
from io import BytesIO
from fastapi import UploadFile
import os
from playsound import playsound
from TTS.api import TTS
from nltk.tokenize import sent_tokenize
import torch
from pydub import AudioSegment
import librosa
import numpy as np
import whisper


device= ("cuda" if torch.cuda.is_available() 
            else "mps" if torch.backends.mps.is_available() 
            else "cpu")


# Load the Whisper model (choose 'tiny', 'base', 'small', 'large')
model = whisper.load_model("base").to(device)

model = torch.quantization.quantize_dynamic(
    model, {torch.nn.Linear}, dtype=torch.qint8  # For dynamic quantization
)


def downsample_audio(audio_data: BytesIO) -> BytesIO:
    """
    Downsample audio to 16kHz mono for faster processing.
    """
    audio_data.seek(0)
    audio = AudioSegment.from_file(audio_data)
    audio = audio.set_frame_rate(16000).set_channels(1)
    
    output_buffer = BytesIO()
    audio.export(output_buffer, format="wav")
    output_buffer.seek(0)
    return output_buffer

def voice_to_text(audio_data: BytesIO):
    """
    Convert audio to text using OpenAI's Whisper model with proper handling for input data.
    """
    try:
        # Downsample the audio to 16kHz mono
        audio_data = downsample_audio(audio_data)

        # Load the audio as a waveform using librosa
        print("Converting BytesIO to waveform...")
        y, sr = librosa.load(audio_data, sr=16000, mono=True)  # Force 16kHz and mono

        # Use Whisper model to transcribe
        print("Recognizing speech using Whisper...")
        result = model.transcribe(y, fp16=False)  # Use waveform directly (16kHz expected)
        text = result.get("text", "")

        if text:
            return {"success": True, "text": text}
        else:
            return {"success": False, "error": "Could not recognize text from audio."}

    except Exception as e:
        return {"success": False, "error": f"An error occurred: {str(e)}"}